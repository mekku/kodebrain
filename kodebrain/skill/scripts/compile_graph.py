#!/usr/bin/env python3
"""
kodebrain compile-graph — deterministic Markdown-first graph compiler.

Reads Markdown pages with YAML frontmatter and wiki-links from
docs/brain/projects/<name>/ and produces:

  nodes.json      — one node per Markdown page (from frontmatter)
  edges.json      — one edge per wiki-link (body [[id|label]])
  file-index.json — reverse index: source_file → [node_id, ...]

This is the single compilation path. Markdown is canonical.
Graph JSON is derived — never independently edited.

Usage:
  python3 compile_graph.py <kb_project_dir>                    # full compile
  python3 compile_graph.py <kb_project_dir> --check            # validate only (exit code)
  python3 compile_graph.py <kb_project_dir> --output-dir <dir> # write to alt dir
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ── YAML frontmatter parser (no PyYAML dependency) ───────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# ── Wiki-link: [[target]] or [[target|label]] ────────────────────────────────

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+?)?\]\]")

# ── Edge type inference: (source_type, target_type) → edge_type ──────────────

_EDGE_RULES: dict[tuple[str, str], str] = {
    ("domain", "capability"): "contains",
    ("domain", "flow"): "contains",
    ("domain", "concept"): "contains",
    ("domain", "data_model"): "contains",
    ("domain", "api"): "contains",
    ("domain", "caveat"): "contains",
    ("domain", "decision"): "contains",
    ("domain", "domain"): "depends_on",
    ("capability", "flow"): "part_of_flow",
    ("capability", "data_model"): "uses",
    ("capability", "concept"): "uses",
    ("capability", "api"): "exposes",
    ("capability", "capability"): "uses",
    ("flow", "capability"): "implements",
    ("flow", "data_model"): "uses",
    ("flow", "concept"): "uses",
    ("flow", "flow"): "calls",
    ("concept", "data_model"): "uses",
    ("concept", "concept"): "related_to",
    ("caveat", "capability"): "risky_for",
    ("caveat", "flow"): "risky_for",
    ("caveat", "data_model"): "risky_for",
    ("caveat", "domain"): "risky_for",
    ("decision", "capability"): "supported_by",
    ("decision", "concept"): "supported_by",
    ("decision", "flow"): "supported_by",
    ("data_model", "data_model"): "related_to",
    ("legacy_area", "capability"): "replaces",
    ("migration_state", "capability"): "replaces",
}


def _infer_edge_type(source_type: str, target_type: str) -> str:
    return _EDGE_RULES.get((source_type, target_type), "related_to")


# ── Frontmatter parsing ──────────────────────────────────────────────────────

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
            # Handle YAML list items (lines starting with -)
            if value == "":
                fm[key] = []
            else:
                fm[key] = value
    return fm, body


def _parse_yaml_list(lines: list[str], start_idx: int, key: str) -> tuple[list[str], int]:
    """Parse a YAML list value from frontmatter lines. Returns (items, next_index)."""
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
    """Parse frontmatter including YAML list values for tags and source_files."""
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
                # Check if next line starts a list
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("- "):
                    items, i = _parse_yaml_list(lines, i + 1, key)
                    fm[key] = items
                else:
                    fm[key] = [] if value == "[]" else ""
            elif value == "null":
                fm[key] = None
            else:
                fm[key] = value
        i += 1
    return fm, body


# ── Wiki-link extraction ─────────────────────────────────────────────────────

def _extract_wikilinks(body: str) -> list[str]:
    """Return deduplicated list of target node IDs from wiki-links in body."""
    targets = _WIKILINK_RE.findall(body)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in targets:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result


# ── Page discovery ───────────────────────────────────────────────────────────

def _discover_pages(kb_dir: Path) -> list[Path]:
    """Find all Markdown pages under the KB project directory."""
    pages: list[Path] = []
    for md in sorted(kb_dir.rglob("*.md")):
        # Skip report/reading-pack files (not knowledge pages)
        rel = str(md.relative_to(kb_dir))
        if rel.startswith("reports/"):
            continue
        pages.append(md)
    return pages


# ── Main compilation ─────────────────────────────────────────────────────────

def compile_graph(kb_dir: Path) -> dict[str, Any]:
    """
    Compile nodes.json, edges.json, and file-index.json from Markdown pages.

    Returns:
        {
          "nodes": [...],
          "edges": [...],
          "file_index": {...},
          "stats": {...},
          "warnings": [...]
        }
    """
    pages = _discover_pages(kb_dir)
    nodes: list[dict] = []
    edges: list[dict] = []
    file_index: dict[str, list[str]] = {}
    node_ids: set[str] = set()
    warnings: list[str] = []

    for path in pages:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            warnings.append(f"cannot read {path.relative_to(kb_dir)}: {e}")
            continue

        fm, body = _parse_frontmatter_full(text)

        # ── Build node ───────────────────────────────────────────────────────
        node_id = fm.get("id", "")
        if not node_id:
            # Derive ID from path: domains/auth/auth.md → auth
            rel = path.relative_to(kb_dir)
            parts = list(rel.parts)
            if len(parts) >= 3 and parts[0] == "domains":
                node_id = parts[1]  # domain slug
            elif path.stem == path.parent.name:
                node_id = path.stem
            else:
                warnings.append(f"no id in frontmatter, cannot derive: {rel}")
                continue

        node_type = fm.get("type", "unknown")
        # Map template-specific types to canonical node types
        type_map = {
            "architecture_overview": "domain",
            "architecture_technology": "domain",
            "architecture_runtime": "domain",
            "architecture_data": "domain",
            "architecture_deployment": "domain",
            "architecture_integrations": "domain",
            "change": "decision",
        }
        node_type = type_map.get(node_type, node_type)

        # Parse source_files from frontmatter (can be YAML list or comma-separated)
        source_files_raw = fm.get("source_files", [])
        if isinstance(source_files_raw, str):
            source_files = [s.strip() for s in source_files_raw.split(",") if s.strip()]
        elif isinstance(source_files_raw, list):
            source_files = source_files_raw
        else:
            source_files = []

        # Parse tags
        tags_raw = fm.get("tags", [])
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        elif isinstance(tags_raw, list):
            tags = tags_raw
        else:
            tags = []

        node: dict[str, Any] = {
            "id": node_id,
            "type": node_type,
            "name": fm.get("name", fm.get("title", node_id.replace("-", " ").title())),
            "summary": "",
            "project": fm.get("project", ""),
            "domain": fm.get("domain", ""),
            "status": fm.get("status", "active"),
            "confidence": fm.get("confidence", "inferred"),
            "provenance": fm.get("provenance", "generated"),
            "knowledge_role": fm.get("knowledge_role", "observed"),
            "source_files": source_files,
            "page_path": str(path.relative_to(kb_dir.parent)) if kb_dir.parent.name == "projects" else str(path.relative_to(kb_dir)),
            "tags": tags,
            "last_updated": fm.get("last_updated", ""),
            "last_reviewed": fm.get("last_reviewed", ""),
        }

        # Optional fields
        if "severity" in fm:
            node["severity"] = fm["severity"]
        if "source_symbols" in fm:
            raw_sym = fm["source_symbols"]
            if isinstance(raw_sym, list):
                node["source_symbols"] = raw_sym
            elif isinstance(raw_sym, str) and raw_sym:
                node["source_symbols"] = [s.strip() for s in raw_sym.split(",") if s.strip()]

        # Extract summary from first non-heading paragraph after frontmatter
        if not fm.get("summary"):
            body_clean = body.strip()
            for line in body_clean.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and len(stripped) > 10:
                    node["summary"] = stripped[:500]
                    break

        if fm.get("summary"):
            node["summary"] = fm["summary"]

        nodes.append(node)
        node_ids.add(node_id)

        # ── Update file_index ────────────────────────────────────────────────
        for sf in source_files:
            file_index.setdefault(sf, [])
            if node_id not in file_index[sf]:
                file_index[sf].append(node_id)

        # ── Build edges from wiki-links ───────────────────────────────────────
        targets = _extract_wikilinks(body)
        source_type = node_type
        for target_id in targets:
            edges.append({
                "from": node_id,
                "to": target_id,
                "type": "related_to",  # resolved in second pass
                "confidence": "inferred",
                "provenance": "generated",
                "label": "",
                "last_updated": fm.get("last_updated", ""),
            })

    # ── Second pass: resolve edge types using known node types ────────────────
    node_type_map: dict[str, str] = {n["id"]: n["type"] for n in nodes}
    orphan_targets: list[str] = []

    for edge in edges:
        target_id = edge["to"]
        target_type = node_type_map.get(target_id)
        if target_type is None:
            orphan_targets.append(target_id)
            edge["confidence"] = "needs_human_review"
            continue
        source_type = node_type_map.get(edge["from"], "unknown")
        edge["type"] = _infer_edge_type(source_type, target_type)
        edge["confidence"] = "supported" if source_type != "unknown" else "inferred"

    # Remove edges with orphan targets and warn
    edges = [e for e in edges if e["to"] in node_type_map]

    if orphan_targets:
        unique_orphans = sorted(set(orphan_targets))
        warnings.append(
            f"{len(orphan_targets)} wiki-link(s) point to non-existent nodes: "
            + ", ".join(unique_orphans[:10])
            + (f" and {len(unique_orphans) - 10} more" if len(unique_orphans) > 10 else "")
        )

    # ── Stats ─────────────────────────────────────────────────────────────────
    from collections import Counter
    type_counts = Counter(n["type"] for n in nodes)
    status_counts = Counter(n["status"] for n in nodes)
    conf_counts = Counter(n["confidence"] for n in nodes)

    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "nodes_by_type": dict(type_counts),
        "nodes_by_status": dict(status_counts),
        "nodes_by_confidence": dict(conf_counts),
        "unmapped_files": sum(1 for v in file_index.values() if not v),
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "file_index": file_index,
        "stats": stats,
        "warnings": warnings,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain compile-graph — Markdown-first graph compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "kb_dir",
        help="Path to docs/brain/projects/<name>/ directory",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate only — exit 0 if graph is consistent, exit 1 on warnings",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        help="Write output files to this directory (default: kb_dir/graph/)",
    )
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir).resolve()
    if not kb_dir.is_dir():
        print(f"Error: {kb_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = compile_graph(kb_dir)

    # Print warnings to stderr
    for w in result["warnings"]:
        print(f"Warning: {w}", file=sys.stderr)

    if args.check:
        if result["warnings"]:
            print(f"FAIL: {len(result['warnings'])} warning(s)", file=sys.stderr)
            sys.exit(1)
        print(f"OK: {result['stats']['total_nodes']} nodes, {result['stats']['total_edges']} edges", file=sys.stderr)
        return

    out_dir = Path(args.output_dir) if args.output_dir else (kb_dir / "graph")
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "nodes.json").write_text(
        json.dumps(result["nodes"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "edges.json").write_text(
        json.dumps(result["edges"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "file-index.json").write_text(
        json.dumps(result["file_index"], indent=2, ensure_ascii=False), encoding="utf-8"
    )

    s = result["stats"]
    print(
        f"Graph compiled: {s['total_nodes']} nodes, {s['total_edges']} edges, "
        f"{len(result['file_index'])} files indexed → {out_dir}",
        file=sys.stderr,
    )
    # Print stats to stdout for the LLM to read
    print(json.dumps(result["stats"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
