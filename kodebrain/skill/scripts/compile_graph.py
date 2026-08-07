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

from frontmatter import parse as _parse_frontmatter_full

# ── Wiki-link: [[target]] or [[target|label]] ────────────────────────────────

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+?)?\]\]")

# ── Section → edge semantics ──────────────────────────────────────────────────
# Each entry: (section_regex, edge_type, direction)
# direction: "forward" = source→target, "reverse" = target→source

_SECTION_EDGE_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"^Depends\s+On$", re.IGNORECASE), "depends_on", "forward"),
    (re.compile(r"^Dependencies$", re.IGNORECASE), "depends_on", "forward"),
    (re.compile(r"^Used\s+By$", re.IGNORECASE), "depends_on", "reverse"),
    (re.compile(r"^Owns$", re.IGNORECASE), "contains", "forward"),
    (re.compile(r"^Contains$", re.IGNORECASE), "contains", "forward"),
    (re.compile(r"^Capabilities$", re.IGNORECASE), "contains", "forward"),
    (re.compile(r"^Core\s+Flows$", re.IGNORECASE), "contains", "forward"),
    (re.compile(r"^Key\s+Concepts$", re.IGNORECASE), "uses", "forward"),
    (re.compile(r"^Related\s+Concepts$", re.IGNORECASE), "uses", "forward"),
    (re.compile(r"^Related\s+Models$", re.IGNORECASE), "uses", "forward"),
    (re.compile(r"^Risks$|^Known\s+Risks$", re.IGNORECASE), "risky_for", "reverse"),
    (re.compile(r"^Affects$", re.IGNORECASE), "risky_for", "forward"),
    (re.compile(r"^Implements$", re.IGNORECASE), "implements", "forward"),
    (re.compile(r"^Replaces$", re.IGNORECASE), "replaces", "forward"),
    (re.compile(r"^Replaced\s+By$", re.IGNORECASE), "replaced_by", "forward"),
    (re.compile(r"^Part\s+Of$", re.IGNORECASE), "part_of_flow", "forward"),
    (re.compile(r"^See\s+Also$", re.IGNORECASE), "related_to", "forward"),
    (re.compile(r"^Where\s+It\s+Is\s+Used$|^Where\s+It\s+Appears$", re.IGNORECASE), "uses", "reverse"),
]

# Fallback: node-type-pair rules when section context is absent/ambiguous
_EDGE_FALLBACK: dict[tuple[str, str], str] = {
    ("domain", "capability"): "contains",
    ("domain", "flow"): "contains",
    ("domain", "concept"): "contains",
    ("domain", "data_model"): "contains",
    ("domain", "domain"): "depends_on",
    ("capability", "flow"): "part_of_flow",
    ("capability", "data_model"): "uses",
    ("capability", "concept"): "uses",
    ("capability", "capability"): "uses",
    ("flow", "capability"): "implements",
    ("flow", "data_model"): "uses",
    ("flow", "concept"): "uses",
    ("flow", "flow"): "calls",
    ("caveat", "capability"): "risky_for",
    ("caveat", "flow"): "risky_for",
    ("caveat", "data_model"): "risky_for",
    ("caveat", "domain"): "risky_for",
    ("decision", "capability"): "supported_by",
    ("decision", "concept"): "supported_by",
    ("decision", "flow"): "supported_by",
    ("incident", "capability"): "risky_for",
    ("incident", "flow"): "risky_for",
    ("incident", "domain"): "risky_for",
    ("incident", "decision"): "related_to",
    ("incident", "incident"): "related_to",
    ("milestone", "domain"): "related_to",
    ("milestone", "capability"): "related_to",
    ("milestone", "decision"): "supported_by",
}


def _infer_edge_type_from_section(section_heading: str | None) -> tuple[str, str] | None:
    """Return (edge_type, direction) from section heading, or None if unrecognized."""
    if not section_heading:
        return None
    for pattern, edge_type, direction in _SECTION_EDGE_RULES:
        if pattern.search(section_heading):
            return (edge_type, direction)
    return None


def _infer_edge_type_fallback(source_type: str, target_type: str) -> str:
    """Fallback edge type from node-type pair."""
    return _EDGE_FALLBACK.get((source_type, target_type), "related_to")


# ── Section-aware wiki-link extraction ────────────────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _extract_wikilinks_with_sections(body: str) -> list[tuple[str, str | None]]:
    """
    Return list of (target_id, section_heading) for wiki-links in body.
    section_heading is the nearest preceding heading, or None.
    """
    # Find all heading positions
    headings: list[tuple[int, str]] = []  # (char_pos, heading_text)
    for m in _HEADING_RE.finditer(body):
        headings.append((m.start(), m.group(2).strip()))

    # Find all wiki-links
    result: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for m in _WIKILINK_RE.finditer(body):
        target = m.group(1).strip()
        if not target or target in seen:
            continue
        seen.add(target)

        # Find nearest preceding heading
        link_pos = m.start()
        section: str | None = None
        for pos, heading_text in reversed(headings):
            if pos < link_pos:
                section = heading_text
                break

        result.append((target, section))

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
            "architecture_overview": "architecture",
            "architecture_technology": "architecture",
            "architecture_runtime": "architecture",
            "architecture_data": "architecture",
            "architecture_deployment": "architecture",
            "architecture_integrations": "architecture",
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
        if "change_state" in fm:
            node["change_state"] = fm["change_state"]
        if "incident_state" in fm:
            node["incident_state"] = fm["incident_state"]
        if "decision_state" in fm:
            node["decision_state"] = fm["decision_state"]
        if "outcome" in fm:
            node["outcome"] = fm["outcome"]
        if "supersedes" in fm:
            raw_sup = fm["supersedes"]
            if isinstance(raw_sup, list):
                node["supersedes"] = raw_sup
            elif isinstance(raw_sup, str) and raw_sup:
                node["supersedes"] = [s.strip() for s in raw_sup.split(",") if s.strip()]
        if "started_at" in fm:
            node["started_at"] = fm["started_at"]
        if "completed_at" in fm:
            node["completed_at"] = fm["completed_at"]
        if "resolved_at" in fm:
            node["resolved_at"] = fm["resolved_at"]
        if "significance" in fm:
            node["significance"] = fm["significance"]
        if "source_symbols" in fm:
            raw_sym = fm["source_symbols"]
            if isinstance(raw_sym, list):
                node["source_symbols"] = raw_sym
            elif isinstance(raw_sym, str) and raw_sym:
                node["source_symbols"] = [s.strip() for s in raw_sym.split(",") if s.strip()]

        # canonical_source — nested map, preserved from frontmatter via shared parser
        canonical_source_raw = fm.get("canonical_source", None)
        if canonical_source_raw and isinstance(canonical_source_raw, dict):
            node["canonical_source"] = canonical_source_raw

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

        # ── Build edges from wiki-links (section-aware) ────────────────────────
        wikilinks = _extract_wikilinks_with_sections(body)
        for target_id, section_heading in wikilinks:
            edges.append({
                "from": node_id,
                "to": target_id,
                "type": "related_to",  # resolved in second pass
                "confidence": "inferred",
                "provenance": "generated",
                "label": "",
                "section": section_heading,  # transient — used for type resolution
                "last_updated": fm.get("last_updated", ""),
            })

    # ── Second pass: resolve edge types from section context, fallback to types ─
    # Infer semantics FIRST, then check target existence.
    # This way orphan diagnostics carry the correct edge_type (depends_on, risky_for, etc.)
    # instead of always "related_to".
    node_type_map: dict[str, str] = {n["id"]: n["type"] for n in nodes}
    orphan_targets: list[str] = []

    for edge in edges:
        target_id = edge["to"]
        source_type = node_type_map.get(edge["from"], "unknown")
        target_type = node_type_map.get(target_id)
        section_heading = edge.pop("section", None)

        # 1. Infer edge type from section context or fallback — BEFORE target check
        section_result = _infer_edge_type_from_section(section_heading)
        if section_result is not None:
            edge_type, direction = section_result
            if direction == "reverse":
                # Swap from/to: "Used By" means the linked node uses us
                edge["from"], edge["to"] = edge["to"], edge["from"]
            edge["type"] = edge_type
            edge["confidence"] = "supported"
        elif target_type is not None:
            # 2. Fall back to node-type-pair inference (only when target exists)
            edge["type"] = _infer_edge_type_fallback(source_type, target_type)
            edge["confidence"] = "inferred"
        else:
            # Target unknown — can't use type-pair fallback, edge stays "related_to"
            pass

        # Restore section for orphan edges so diagnostics carry it
        if target_type is None:
            edge["section"] = section_heading

        # 2. Check target existence
        if target_type is None:
            orphan_targets.append(target_id)
            edge["confidence"] = "needs_human_review"

    # Remove edges with orphan targets and warn
    # Record diagnostics after semantic inference — validation gate consumes these
    diagnostics: list[dict] = []
    for edge in edges:
        if edge["to"] not in node_type_map:
            diagnostics.append({
                "type": "orphan_wikilink",
                "source": edge["from"],
                "target": edge["to"],
                "section": edge.get("section", ""),
                "edge_type": edge.get("type", "related_to"),
            })

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
        "diagnostics": diagnostics,
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
    (out_dir / "diagnostics.json").write_text(
        json.dumps(result["diagnostics"], indent=2, ensure_ascii=False), encoding="utf-8"
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
