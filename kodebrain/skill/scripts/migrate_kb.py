#!/usr/bin/env python3
"""
kodebrain migrate-kb — legacy KB → vNext migration engine.

Markdown-first: migrates canonical Markdown pages (frontmatter + wiki-links +
file renames), then optionally rebuilds JSON graph artifacts via compile_graph.

Migration operations (on Markdown pages):
  - hierarchical IDs → flat IDs: auth/login-flow → auth-login-flow
  - camelCase → snake_case: sourceFiles → source_files, lastUpdated → last_updated
  - confidence source_supported → supported
  - wiki-link target IDs in body migrated
  - file renames when ID change affects expected path
  - adds provenance + knowledge_role if missing
  - preserves <!-- human-note --> blocks verbatim
  - creates backup before migration

JSON graph files are derived artifacts. If present, they are also migrated for
compatibility, but the primary operation is on Markdown. After migration, run
compile_graph.py to rebuild indexes from canonical Markdown.

Usage:
  python3 migrate_kb.py <kb_project_dir>                # migrate in place (with backup)
  python3 migrate_kb.py <kb_project_dir> --dry-run       # report what would change
  python3 migrate_kb.py <kb_project_dir> --check         # exit 0 if migration needed
  python3 migrate_kb.py <kb_project_dir> --compile       # also run compile_graph after
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

# ── YAML frontmatter parser (no PyYAML dependency) ────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# ── Wiki-link: [[target]] or [[target|label]] ────────────────────────────────

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(\|[^\]]+?)?\]\]")

# ── Human-note blocks ─────────────────────────────────────────────────────────

_HUMAN_NOTE_RE = re.compile(
    r"<!--\s*human-note\s*-->(.*?)<!--\s*/human-note\s*-->",
    re.DOTALL,
)

# ── File type directory mapping (for file rename logic) ───────────────────────

_TYPE_DIR: dict[str, str] = {
    "project": "",
    "domain": "domains",
    "capability": "capabilities",
    "concept": "concepts",
    "flow": "flows",
    "data_model": "models",
    "api": "apis",
    "caveat": "risks",
    "decision": "decisions",
    "legacy_area": "risks",
    "migration_state": "risks",
    "layer": "layers",
    "engine": "engines",
    "adapter": "adapters",
    "ui": "ui",
    "runtime_behavior": "runtime",
    "state": "state",
}


# ── ID migration ──────────────────────────────────────────────────────────────

def _migrate_id(old_id: str) -> str:
    """Convert auth/login-flow → auth-login-flow."""
    if "/" in old_id:
        return old_id.replace("/", "-")
    return old_id


# ── Frontmatter parsing ───────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body_without_frontmatter)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    fm: dict[str, Any] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            fm[key] = value
    return fm, body


def _parse_yaml_list(lines: list[str], start_idx: int) -> tuple[list[str], int]:
    """Parse YAML list items. Returns (items, next_index)."""
    items: list[str] = []
    i = start_idx
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip().strip('"').strip("'"))
            i += 1
        elif stripped == "" or stripped.startswith("#"):
            i += 1
        elif ":" in stripped and not stripped.startswith(" "):
            break
        else:
            i += 1
    return items, i


def _parse_frontmatter_full(text: str) -> tuple[dict[str, Any], str]:
    """Parse frontmatter including YAML list values."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    fm: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value == "" or value == "[]":
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("- "):
                    items, i = _parse_yaml_list(lines, i + 1)
                    fm[key] = items
                else:
                    fm[key] = [] if value == "[]" else ""
            elif value == "null":
                fm[key] = None
            else:
                fm[key] = value
        i += 1
    return fm, body


# ── Frontmatter serialization ─────────────────────────────────────────────────

def _serialize_frontmatter(fm: dict[str, Any]) -> str:
    """Serialize frontmatter dict back to YAML string."""
    lines = ["---"]
    # Order important fields first
    priority = ["id", "type", "status", "confidence", "provenance",
                "knowledge_role", "project", "domain"]
    written: set[str] = set()

    for key in priority:
        if key in fm:
            val = fm[key]
            if isinstance(val, list):
                lines.append(f"{key}:")
                for item in val:
                    lines.append(f"  - {item}")
            elif val is None:
                lines.append(f"{key}: null")
            elif isinstance(val, str) and (" " in val or val == ""):
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")
            written.add(key)

    for key, val in fm.items():
        if key in written:
            continue
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        elif val is None:
            lines.append(f"{key}: null")
        elif isinstance(val, str) and (" " in val or val == ""):
            lines.append(f'{key}: "{val}"')
        else:
            lines.append(f"{key}: {val}")

    lines.append("---")
    return "\n".join(lines) + "\n"


# ── Migration on frontmatter ──────────────────────────────────────────────────

def _migrate_frontmatter(fm: dict[str, Any]) -> tuple[dict[str, Any], bool, bool]:
    """
    Migrate a single page's frontmatter. Returns (new_fm, id_changed, fields_changed).
    """
    new_fm: dict[str, Any] = {}
    fields_changed = False

    for old_key, value in fm.items():
        new_key = _FIELD_MAP.get(old_key, old_key)
        if new_key != old_key:
            fields_changed = True
        new_fm[new_key] = value

    # Migrate ID
    id_changed = False
    if "id" in new_fm:
        old_id = new_fm["id"]
        new_id = _migrate_id(old_id)
        if new_id != old_id:
            new_fm["id"] = new_id
            id_changed = True

    # Migrate confidence
    if "confidence" in new_fm:
        old_conf = new_fm["confidence"]
        new_fm["confidence"] = _CONFIDENCE_MAP.get(old_conf, old_conf)
        if new_fm["confidence"] != old_conf:
            fields_changed = True

    # Add provenance if missing
    if "provenance" not in new_fm:
        src_files = new_fm.get("source_files", [])
        if isinstance(src_files, list) and src_files:
            new_fm["provenance"] = "source_code"
        elif new_fm.get("confidence") == "verified":
            new_fm["provenance"] = "human"
        else:
            new_fm["provenance"] = "generated"
        fields_changed = True

    # Add knowledge_role if missing
    if "knowledge_role" not in new_fm:
        if new_fm.get("provenance") == "human":
            new_fm["knowledge_role"] = "intent"
        else:
            new_fm["knowledge_role"] = "observed"
        fields_changed = True

    return new_fm, id_changed, fields_changed


# ── Wiki-link migration in body ───────────────────────────────────────────────

def _migrate_wikilinks(body: str) -> tuple[str, int]:
    """Replace hierarchical wiki-link targets with flat IDs. Returns (new_body, count_migrated)."""
    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        target = m.group(1).strip()
        label = m.group(2) or ""
        if "/" in target:
            count += 1
            new_target = _migrate_id(target)
            return f"[[{new_target}{label}]]"
        return m.group(0)

    new_body = _WIKILINK_RE.sub(_replace, body)
    return new_body, count


# ── File rename logic ─────────────────────────────────────────────────────────

def _expected_path(kb_dir: Path, node_id: str, node_type: str) -> Path:
    """Derive expected file path from flat node ID and type."""
    parts = node_id.split("-", 1)
    domain = parts[0] if parts else ""

    if node_type == "project":
        return kb_dir / f"{node_id}.md"
    elif node_type == "domain":
        return kb_dir / "domains" / node_id / f"{node_id}.md"
    else:
        type_dir = _TYPE_DIR.get(node_type, "misc")
        return kb_dir / "domains" / domain / type_dir / f"{node_id}.md"


# ── Page discovery ────────────────────────────────────────────────────────────

def _discover_pages(kb_dir: Path) -> list[Path]:
    """Find all knowledge pages under KB dir (skip reports, reading-packs, backups)."""
    pages: list[Path] = []
    for md in sorted(kb_dir.rglob("*.md")):
        rel = str(md.relative_to(kb_dir))
        if rel.startswith("reports/") or "backup" in rel.lower():
            continue
        pages.append(md)
    return pages


# ── Detection ─────────────────────────────────────────────────────────────────

def _detect_legacy(kb_dir: Path) -> tuple[bool, str | None, list[str]]:
    """
    Check if KB needs migration by scanning Markdown frontmatter.

    Returns (needs_migration, version, reasons).
    """
    reasons: list[str] = []
    version: str | None = None
    pages = _discover_pages(kb_dir)

    if not pages:
        # Fallback: check nodes.json
        nodes_json = kb_dir / "graph" / "nodes.json"
        if nodes_json.exists():
            try:
                nodes = json.loads(nodes_json.read_text())
                if isinstance(nodes, dict) and "nodes" in nodes:
                    nodes = nodes["nodes"]
                if isinstance(nodes, list) and nodes:
                    first = nodes[0]
                    if "sourceFiles" in first:
                        reasons.append("camelCase in nodes.json")
                        version = "0.1"
                        return True, version, reasons
                    if "id" in first and "/" in str(first["id"]):
                        reasons.append("hierarchical ID in nodes.json")
                        version = "0.2"
                        return True, version, reasons
            except (json.JSONDecodeError, OSError):
                pass
        return False, None, ["no pages or nodes.json found"]

    # Scan Markdown frontmatter
    for path in pages:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, _ = _parse_frontmatter(text)
        if not fm:
            continue

        fid = fm.get("id", "")
        if "/" in fid:
            reasons.append(f"hierarchical ID '{fid}' in {path.relative_to(kb_dir)}")
        for old_key in _FIELD_MAP:
            if old_key in fm:
                reasons.append(
                    f"camelCase field '{old_key}' in {path.relative_to(kb_dir)}"
                )
                break
        if fm.get("confidence") == "source_supported":
            reasons.append(
                f"confidence 'source_supported' in {path.relative_to(kb_dir)}"
            )
        if "provenance" not in fm:
            reasons.append(f"missing 'provenance' in {path.relative_to(kb_dir)}")
        if "knowledge_role" not in fm:
            reasons.append(f"missing 'knowledge_role' in {path.relative_to(kb_dir)}")

    # Determine version
    if any("camelCase" in r for r in reasons):
        version = "0.1"
    elif any("hierarchical" in r for r in reasons):
        version = "0.2"
    else:
        version = "1.0"

    # Deduplicate reasons (keep unique)
    seen: set[str] = set()
    unique: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            unique.append(r)

    return len(unique) > 0, version, unique[:20]  # cap at 20 reasons


# ── Main migration ────────────────────────────────────────────────────────────

def migrate(kb_dir: Path, dry_run: bool = False, compile_after: bool = False) -> dict[str, Any]:
    """
    Migrate legacy KB to vNext — Markdown-first.

    1. Backup KB directory
    2. For each .md page: migrate frontmatter + wiki-links + rename if needed
    3. Migrate JSON artifacts for compatibility (derived — compiler overrides)
    4. Optionally run compile_graph to rebuild indexes
    """
    needs, old_version, reasons = _detect_legacy(kb_dir)

    report: dict[str, Any] = {
        "migrated": False,
        "version_from": old_version,
        "version_to": "1.0",
        "dry_run": dry_run,
        "backup_path": None,
        "pages_scanned": 0,
        "pages_migrated": 0,
        "ids_renamed": 0,
        "fields_normalized": 0,
        "wiki_links_migrated": 0,
        "files_renamed": 0,
        "human_notes_preserved": 0,
        "json_nodes_migrated": 0,
        "json_edges_migrated": 0,
        "warnings": [],
    }

    if not needs:
        report["warnings"].append("KB is already vNext — no migration needed")
        return report

    report["migrated"] = True

    # ── Backup ─────────────────────────────────────────────────────────────────
    if not dry_run:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_dir = kb_dir.parent / f"{kb_dir.name}.backup-{timestamp}"
        shutil.copytree(kb_dir, backup_dir)
        report["backup_path"] = str(backup_dir)
    else:
        report["backup_path"] = "(dry run — no backup created)"

    # ── Phase 1: Migrate Markdown pages (canonical) ────────────────────────────
    pages = _discover_pages(kb_dir)
    report["pages_scanned"] = len(pages)

    # Build ID registry for wiki-link validation
    id_registry: dict[str, str] = {}  # old_id → new_id

    # First pass: collect ID mappings
    for path in pages:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, _ = _parse_frontmatter_full(text)
        if "id" in fm:
            old_id = fm["id"]
            new_id = _migrate_id(old_id)
            if old_id != new_id:
                id_registry[old_id] = new_id

    # Second pass: migrate each page
    for path in pages:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            report["warnings"].append(f"cannot read {path.relative_to(kb_dir)}")
            continue

        fm, body = _parse_frontmatter_full(text)
        original_text = text

        if not fm:
            continue

        # Migrate frontmatter
        new_fm, id_changed, fields_changed = _migrate_frontmatter(fm)

        # Migrate wiki-links
        new_body, wiki_count = _migrate_wikilinks(body)

        # Count human notes
        notes_count = len(_HUMAN_NOTE_RE.findall(text))

        # Determine if anything changed
        any_change = id_changed or fields_changed or wiki_count > 0

        if any_change:
            report["pages_migrated"] += 1
            if id_changed:
                report["ids_renamed"] += 1
            if fields_changed:
                report["fields_normalized"] += 1
            report["wiki_links_migrated"] += wiki_count
            report["human_notes_preserved"] += notes_count

            # Write migrated page
            if not dry_run:
                new_frontmatter_yaml = _serialize_frontmatter(new_fm)
                path.write_text(new_frontmatter_yaml + new_body, encoding="utf-8")

        # File rename if ID changed and path doesn't match expected
        if id_changed and not dry_run:
            new_id = new_fm["id"]
            node_type = new_fm.get("type", "unknown")
            expected = _expected_path(kb_dir, new_id, node_type)
            if expected.resolve() != path.resolve():
                expected.parent.mkdir(parents=True, exist_ok=True)
                path.rename(expected)
                report["files_renamed"] += 1

    # ── Phase 2: Migrate JSON artifacts (secondary — compiler overrides) ────────
    graph_dir = kb_dir / "graph"

    # nodes.json
    nodes_path = graph_dir / "nodes.json"
    if nodes_path.exists():
        try:
            nodes_raw = json.loads(nodes_path.read_text())
            is_wrapped = isinstance(nodes_raw, dict) and "nodes" in nodes_raw
            nodes = nodes_raw["nodes"] if is_wrapped else nodes_raw

            migrated_nodes = []
            for node in nodes:
                mn: dict[str, Any] = {}
                for old_key, value in node.items():
                    new_key = _FIELD_MAP.get(old_key, old_key)
                    mn[new_key] = value
                if "id" in mn:
                    mn["id"] = _migrate_id(mn["id"])
                if "confidence" in mn:
                    mn["confidence"] = _CONFIDENCE_MAP.get(mn["confidence"], mn["confidence"])
                if "provenance" not in mn:
                    mn["provenance"] = "source_code" if mn.get("source_files") else "generated"
                if "knowledge_role" not in mn:
                    mn["knowledge_role"] = "observed"
                migrated_nodes.append(mn)

            report["json_nodes_migrated"] = len(migrated_nodes)

            if not dry_run:
                if is_wrapped:
                    nodes_raw["nodes"] = migrated_nodes
                    nodes_raw["schema_version"] = "1.0"
                    nodes_path.write_text(json.dumps(nodes_raw, indent=2, ensure_ascii=False), encoding="utf-8")
                else:
                    nodes_path.write_text(json.dumps(migrated_nodes, indent=2, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, OSError) as e:
            report["warnings"].append(f"cannot migrate nodes.json: {e}")

    # edges.json
    edges_path = graph_dir / "edges.json"
    if edges_path.exists():
        try:
            edges_raw = json.loads(edges_path.read_text())
            is_wrapped = isinstance(edges_raw, dict) and "edges" in edges_raw
            edges = edges_raw["edges"] if is_wrapped else edges_raw

            migrated_edges = []
            for edge in edges:
                me: dict[str, Any] = {}
                for old_key, value in edge.items():
                    new_key = _FIELD_MAP.get(old_key, old_key)
                    me[new_key] = value
                if "from" in me:
                    me["from"] = _migrate_id(me["from"])
                if "to" in me:
                    me["to"] = _migrate_id(me["to"])
                if "confidence" in me:
                    me["confidence"] = _CONFIDENCE_MAP.get(me["confidence"], me["confidence"])
                if "provenance" not in me:
                    me["provenance"] = "generated"
                migrated_edges.append(me)

            report["json_edges_migrated"] = len(migrated_edges)

            if not dry_run:
                if is_wrapped:
                    edges_raw["edges"] = migrated_edges
                    edges_path.write_text(json.dumps(edges_raw, indent=2, ensure_ascii=False), encoding="utf-8")
                else:
                    edges_path.write_text(json.dumps(migrated_edges, indent=2, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, OSError) as e:
            report["warnings"].append(f"cannot migrate edges.json: {e}")

    # file-index.json
    fi_path = graph_dir / "file-index.json"
    if fi_path.exists():
        try:
            fi = json.loads(fi_path.read_text())
            migrated_fi = {
                path: [_migrate_id(nid) for nid in node_ids]
                for path, node_ids in fi.items()
            }
            if not dry_run:
                fi_path.write_text(json.dumps(migrated_fi, indent=2, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, OSError) as e:
            report["warnings"].append(f"cannot migrate file-index.json: {e}")

    # ── Phase 3: Optionally compile graph ──────────────────────────────────────
    compiled = False
    if compile_after and not dry_run:
        try:
            from kodebrain.skill.scripts import compile_graph as _cg
            result = _cg.compile_graph(kb_dir)
            graph_dir.mkdir(parents=True, exist_ok=True)
            (graph_dir / "nodes.json").write_text(
                json.dumps(result["nodes"], indent=2, ensure_ascii=False), encoding="utf-8"
            )
            (graph_dir / "edges.json").write_text(
                json.dumps(result["edges"], indent=2, ensure_ascii=False), encoding="utf-8"
            )
            (graph_dir / "file-index.json").write_text(
                json.dumps(result["file_index"], indent=2, ensure_ascii=False), encoding="utf-8"
            )
            compiled = True
        except ImportError:
            report["warnings"].append("compile_graph not available — JSON artifacts from phase 2 kept as-is")
        except Exception as e:
            report["warnings"].append(f"compile_graph failed: {e}")

    # ── Write migration report ─────────────────────────────────────────────────
    if not dry_run and report["migrated"]:
        report_path = kb_dir / "reports" / "migration.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_format_migration_report(report, compiled), encoding="utf-8")

    return report


def _format_migration_report(report: dict[str, Any], compiled: bool) -> str:
    """Render migration report as Markdown."""
    return f"""# KB Migration Report

**Migrated:** {report["migrated"]}
**From version:** {report["version_from"] or "unknown"}
**To version:** {report["version_to"]}
**Date:** {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

## Markdown Pages (canonical)

| Operation | Count |
|---|---|
| Pages scanned | {report["pages_scanned"]} |
| Pages migrated | {report["pages_migrated"]} |
| IDs flattened (hierarchical → flat) | {report["ids_renamed"]} |
| Fields normalized (camelCase → snake_case) | {report["fields_normalized"]} |
| Wiki-link targets migrated | {report["wiki_links_migrated"]} |
| Files renamed | {report["files_renamed"]} |
| Human-note blocks preserved | {report["human_notes_preserved"]} |

## JSON Artifacts (derived)

| Operation | Count |
|---|---|
| Nodes migrated | {report["json_nodes_migrated"]} |
| Edges migrated | {report["json_edges_migrated"]} |
| Graph recompiled | {"yes" if compiled else "no"} |

## Backup

{report["backup_path"]}

## Warnings

{"".join(f'- {w}\\n' for w in report["warnings"]) if report["warnings"] else "None"}

## Verification

After migration:
1. Run `compile_graph.py` to rebuild graph indexes from canonical Markdown.
2. Check `reports/drift.md` for any surfaced intent-vs-source drift.
3. Review any nodes marked `needs_human_review`.
"""


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain migrate-kb — Markdown-first migration",
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
    parser.add_argument(
        "--compile",
        action="store_true",
        help="Run compile_graph after migration to rebuild indexes",
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

    report = migrate(kb_dir, dry_run=args.dry_run, compile_after=args.compile)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
