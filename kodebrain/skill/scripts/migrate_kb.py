#!/usr/bin/env python3
"""
kodebrain migrate-kb — legacy KB → vNext migration engine.

Detects old KB format, normalizes IDs and field names, preserves human
notes verbatim, and produces a migration report.

Migration operations:
  - hierarhical IDs → flat IDs: auth/login-flow → auth-login-flow
  - camelCase → snake_case: sourceFiles → source_files, lastUpdated → last_updated
  - confidence source_supported → supported
  - adds provenance field (source_code default for existing nodes)
  - adds knowledge_role field (observed default for existing nodes)
  - preserves <!-- human-note --> blocks verbatim
  - creates backup before migration
  - generates migration report

Usage:
  python3 migrate_kb.py <kb_project_dir>            # migrate in place (with backup)
  python3 migrate_kb.py <kb_project_dir> --dry-run   # report what would change
  python3 migrate_kb.py <kb_project_dir> --check     # check if migration needed (exit code)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Old → new field mappings ──────────────────────────────────────────────────

_FIELD_MAP: dict[str, str] = {
    "sourceFiles": "source_files",
    "sourceSymbols": "source_symbols",
    "pagePath": "page_path",
    "lastUpdated": "last_updated",
    "lastReviewed": "last_reviewed",
    "createdBy": "created_by",
}

_CONFIDENCE_MAP: dict[str, str] = {
    "source_supported": "supported",
}

# ── ID migration: hierarchical → flat ─────────────────────────────────────────

def _migrate_id(old_id: str) -> str:
    """Convert auth/login-flow → auth-login-flow."""
    return old_id.replace("/", "-")


def _migrate_node(node: dict[str, Any]) -> dict[str, Any]:
    """Migrate a single node from legacy format to vNext."""
    migrated: dict[str, Any] = {}

    for old_key, value in node.items():
        new_key = _FIELD_MAP.get(old_key, old_key)
        migrated[new_key] = value

    # Migrate ID
    if "id" in migrated:
        migrated["id"] = _migrate_id(migrated["id"])

    # Migrate confidence
    if "confidence" in migrated:
        migrated["confidence"] = _CONFIDENCE_MAP.get(
            migrated["confidence"], migrated["confidence"]
        )

    # Add provenance if missing (default: source_code for source-backed nodes, generated otherwise)
    if "provenance" not in migrated:
        if migrated.get("source_files"):
            migrated["provenance"] = "source_code"
        elif migrated.get("confidence") == "verified":
            migrated["provenance"] = "human"
        else:
            migrated["provenance"] = "generated"

    # Add knowledge_role if missing
    if "knowledge_role" not in migrated:
        if migrated.get("provenance") == "human":
            migrated["knowledge_role"] = "intent"
        else:
            migrated["knowledge_role"] = "observed"

    return migrated


def _migrate_edge(edge: dict[str, Any]) -> dict[str, Any]:
    """Migrate a single edge from legacy format to vNext."""
    migrated: dict[str, Any] = {}

    for old_key, value in edge.items():
        new_key = _FIELD_MAP.get(old_key, old_key)
        migrated[new_key] = value

    # Migrate from/to IDs
    if "from" in migrated:
        migrated["from"] = _migrate_id(migrated["from"])
    if "to" in migrated:
        migrated["to"] = _migrate_id(migrated["to"])

    # Migrate confidence
    if "confidence" in migrated:
        migrated["confidence"] = _CONFIDENCE_MAP.get(
            migrated["confidence"], migrated["confidence"]
        )

    # Add provenance if missing
    if "provenance" not in migrated:
        migrated["provenance"] = "generated"

    return migrated


def _migrate_file_index(file_index: dict[str, list[str]]) -> dict[str, list[str]]:
    """Migrate file-index keys (source file paths stay same; node IDs in values get migrated)."""
    return {
        path: [_migrate_id(nid) for nid in node_ids]
        for path, node_ids in file_index.items()
    }


# ── Detection ─────────────────────────────────────────────────────────────────

def _detect_legacy(kb_dir: Path) -> tuple[bool, str | None, list[str]]:
    """
    Check if KB needs migration.

    Returns (needs_migration, version, reasons).
    """
    reasons: list[str] = []
    version: str | None = None

    nodes_json = kb_dir / "graph" / "nodes.json"
    if not nodes_json.exists():
        return False, None, ["no nodes.json found"]

    try:
        nodes = json.loads(nodes_json.read_text())
        if isinstance(nodes, dict) and "nodes" in nodes:
            nodes = nodes["nodes"]
    except (json.JSONDecodeError, OSError) as e:
        return False, None, [f"cannot read nodes.json: {e}"]

    if not isinstance(nodes, list) or not nodes:
        return False, None, ["nodes.json is empty"]

    first = nodes[0]

    # Check for old field names
    if "sourceFiles" in first:
        reasons.append("camelCase field 'sourceFiles' detected (should be source_files)")
    if "lastUpdated" in first:
        reasons.append("camelCase field 'lastUpdated' detected (should be last_updated)")
    if "createdBy" in first:
        reasons.append("camelCase field 'createdBy' detected (should be created_by)")

    # Check for hierarchical IDs
    if "id" in first and "/" in first["id"]:
        reasons.append("hierarchical ID detected (should be flat hyphen-separated)")

    # Check for old confidence values
    if first.get("confidence") == "source_supported":
        reasons.append("confidence 'source_supported' detected (should be 'supported')")

    # Check for missing fields
    if "provenance" not in first:
        reasons.append("missing 'provenance' field")
    if "knowledge_role" not in first:
        reasons.append("missing 'knowledge_role' field")

    # Detect format version
    if "sourceFiles" in first and "provenance" not in first:
        version = "0.1"
    elif "source_files" in first and "provenance" not in first:
        version = "0.2"
    elif "provenance" in first:
        version = "1.0"

    return len(reasons) > 0, version, reasons


# ── Human-note preservation ───────────────────────────────────────────────────

_HUMAN_NOTE_RE = re.compile(
    r"<!--\s*human-note\s*-->(.*?)<!--\s*/human-note\s*-->",
    re.DOTALL,
)


def _extract_human_notes(text: str) -> list[str]:
    """Extract human-note blocks from markdown. Returns block contents."""
    return [m.group(1).strip() for m in _HUMAN_NOTE_RE.finditer(text)]


# ── Main migration ────────────────────────────────────────────────────────────

def migrate(kb_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    """
    Migrate a legacy KB to vNext format.

    Returns migration report:
      {
        "migrated": bool,
        "version_from": str | null,
        "version_to": "1.0",
        "dry_run": bool,
        "backup_path": str | null,
        "nodes_migrated": int,
        "edges_migrated": int,
        "ids_renamed": int,
        "fields_renamed": int,
        "human_notes_preserved": int,
        "warnings": [str, ...],
      }
    """
    needs, old_version, reasons = _detect_legacy(kb_dir)

    report: dict[str, Any] = {
        "migrated": False,
        "version_from": old_version,
        "version_to": "1.0",
        "dry_run": dry_run,
        "backup_path": None,
        "nodes_migrated": 0,
        "edges_migrated": 0,
        "ids_renamed": 0,
        "fields_renamed": 0,
        "human_notes_preserved": 0,
        "warnings": [],
    }

    if not needs:
        report["warnings"].append("KB is already vNext — no migration needed")
        return report

    report["migrated"] = True

    graph_dir = kb_dir / "graph"

    # ── Backup ─────────────────────────────────────────────────────────────────
    if not dry_run:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = kb_dir.parent / f"{kb_dir.name}.backup-{timestamp}"
        shutil.copytree(kb_dir, backup_dir)
        report["backup_path"] = str(backup_dir.relative_to(kb_dir.parent.parent))
    else:
        report["backup_path"] = "(dry run — no backup created)"

    # ── Migrate nodes.json ─────────────────────────────────────────────────────
    nodes_path = graph_dir / "nodes.json"
    if nodes_path.exists():
        try:
            nodes_raw = json.loads(nodes_path.read_text())
            is_wrapped = isinstance(nodes_raw, dict) and "nodes" in nodes_raw
            nodes = nodes_raw["nodes"] if is_wrapped else nodes_raw
        except (json.JSONDecodeError, OSError) as e:
            report["warnings"].append(f"cannot read nodes.json: {e}")
            return report

        migrated_nodes = []
        ids_renamed = 0
        fields_renamed = 0

        for node in nodes:
            old_id = node.get("id", "")
            new_node = _migrate_node(node)
            new_id = new_node.get("id", "")

            if old_id != new_id:
                ids_renamed += 1

            # Count renamed fields
            for old_key in _FIELD_MAP:
                if old_key in node:
                    fields_renamed += 1

            migrated_nodes.append(new_node)

        report["nodes_migrated"] = len(migrated_nodes)
        report["ids_renamed"] = ids_renamed
        report["fields_renamed"] = fields_renamed

        if not dry_run:
            if is_wrapped:
                nodes_raw["nodes"] = migrated_nodes
                nodes_raw["schema_version"] = "1.0"
                nodes_path.write_text(json.dumps(nodes_raw, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                nodes_path.write_text(json.dumps(migrated_nodes, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Migrate edges.json ─────────────────────────────────────────────────────
    edges_path = graph_dir / "edges.json"
    if edges_path.exists():
        try:
            edges_raw = json.loads(edges_path.read_text())
            is_wrapped = isinstance(edges_raw, dict) and "edges" in edges_raw
            edges = edges_raw["edges"] if is_wrapped else edges_raw
        except (json.JSONDecodeError, OSError) as e:
            report["warnings"].append(f"cannot read edges.json: {e}")
            return report

        migrated_edges = [_migrate_edge(e) for e in edges]
        report["edges_migrated"] = len(migrated_edges)

        if not dry_run:
            if is_wrapped:
                edges_raw["edges"] = migrated_edges
                edges_path.write_text(json.dumps(edges_raw, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                edges_path.write_text(json.dumps(migrated_edges, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Migrate file-index.json ────────────────────────────────────────────────
    fi_path = graph_dir / "file-index.json"
    if fi_path.exists():
        try:
            fi = json.loads(fi_path.read_text())
            migrated_fi = _migrate_file_index(fi)
            if not dry_run:
                fi_path.write_text(json.dumps(migrated_fi, indent=2, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, OSError) as e:
            report["warnings"].append(f"cannot read file-index.json: {e}")

    # ── Preserve human notes in markdown pages ─────────────────────────────────
    notes_count = 0
    for md in sorted(kb_dir.rglob("*.md")):
        if "backup" in str(md):
            continue
        try:
            content = md.read_text(encoding="utf-8", errors="replace")
            notes = _extract_human_notes(content)
            notes_count += len(notes)
        except OSError:
            pass
    report["human_notes_preserved"] = notes_count

    # ── Write migration report ─────────────────────────────────────────────────
    if not dry_run and report["migrated"]:
        report_path = kb_dir / "reports" / "migration.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_format_migration_report(report), encoding="utf-8")

    return report


def _format_migration_report(report: dict[str, Any]) -> str:
    """Render migration report as Markdown."""
    return f"""# KB Migration Report

**Migrated:** {report["migrated"]}
**From version:** {report["version_from"] or "unknown"}
**To version:** {report["version_to"]}
**Date:** {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

## Changes

| Operation | Count |
|---|---|
| Nodes migrated | {report["nodes_migrated"]} |
| Edges migrated | {report["edges_migrated"]} |
| IDs renamed (hierarchical → flat) | {report["ids_renamed"]} |
| Field names normalized | {report["fields_renamed"]} |
| Human-note blocks preserved | {report["human_notes_preserved"]} |

## Backup

{report["backup_path"]}

## Warnings

{"".join(f'- {w}\\n' for w in report["warnings"]) if report["warnings"] else "None"}

## Verification

After migration:
1. Run `compile_graph.py` to rebuild graph indexes.
2. Check `reports/drift.md` for any surfaced intent-vs-source drift.
3. Review any nodes marked `needs_human_review`.
"""


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain migrate-kb — legacy → vNext migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "kb_dir",
        help="Path to docs/brain/projects/<name>/ directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 if migration is needed, exit 1 if already vNext",
    )
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir).resolve()
    if not kb_dir.is_dir():
        print(f"Error: {kb_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.check:
        needs, version, reasons = _detect_legacy(kb_dir)
        if needs:
            print(f"Migration needed (version: {version or 'unknown'})")
            for r in reasons:
                print(f"  - {r}")
            sys.exit(0)
        else:
            print(f"KB is vNext (version: {version or '1.0'})")
            sys.exit(1)

    report = migrate(kb_dir, dry_run=args.dry_run)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
