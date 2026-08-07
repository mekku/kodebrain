#!/usr/bin/env python3
"""
kodebrain project-state — deterministic project state classifier.

Inspects a project root and its existing KB (if any) to determine the
onboarding state and produce a Knowledge Gap Map.

States:
  greenfield      — no meaningful source code, no KB
  new_brownfield  — source exists, no KB
  partial_kb      — KB exists but missing project-level knowledge
  legacy_kb       — older KB schema/format detected
  stale_kb        — KB exists but outdated vs source
  onboarded       — KB is current and project-complete

Usage:
  python3 project_state.py <root>                    # classify state
  python3 project_state.py <root> --gaps             # include gap map detail
  python3 project_state.py <root> --output state.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# ── What constitutes "meaningful source" ──────────────────────────────────────

_SOURCE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".go", ".rs", ".java", ".rb", ".php",
    ".cs", ".swift", ".kt", ".scala", ".dart",
}

_IGNORE_DIRS = {
    "node_modules", "dist", "build", "out",
    "__pycache__", "venv", ".mypy_cache",
    "vendor", "target", ".gradle",
    ".git", ".claude",
}

# ── KB structure expectations (vNext) ─────────────────────────────────────────

_PROJECT_LEVEL_FILES = [
    "<project>.md",               # project hub
]

_ARCHITECTURE_FILES = [
    "architecture/overview.md",
    "architecture/technology.md",
    "architecture/runtime.md",
    "architecture/data.md",
    "architecture/deployment.md",
    "architecture/integrations.md",
]

_GRAPH_FILES = [
    "graph/nodes.json",
    "graph/edges.json",
    "graph/file-index.json",
    "graph/file-hashes.json",
]

_REPORT_FILES = [
    "reports/knowledge-gaps.md",
    "reports/drift.md",
    "reports/unmapped-files.md",
    "reports/suspected-legacy.md",
    "reports/stale-docs.md",
    "reports/needs-review.md",
]

# ── Gap dimensions ────────────────────────────────────────────────────────────

_GAP_DIMENSIONS = [
    "purpose",
    "actors",
    "core_outcomes",
    "scope",
    "technology",
    "architecture",
    "runtime",
    "external_integrations",
    "domains",
    "domain_boundaries",
    "invariants",
    "legacy_migration",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_source_files(root: Path) -> int:
    count = 0
    try:
        for ext in _SOURCE_EXTS:
            for p in root.rglob(f"*{ext}"):
                # Skip files in ignored directories
                parts = set(p.relative_to(root).parts[:-1])
                if parts & _IGNORE_DIRS:
                    continue
                count += 1
                if count > 500:
                    return count
    except OSError:
        pass
    return count


def _find_kb_dir(root: Path) -> Path | None:
    """Find the KB project directory, if any."""
    projects_dir = root / "docs" / "brain" / "projects"
    if not projects_dir.is_dir():
        return None
    for child in sorted(projects_dir.iterdir()):
        if child.is_dir():
            return child
    return None


def _count_domain_dirs(kb_dir: Path) -> int:
    domains_dir = kb_dir / "domains"
    if not domains_dir.is_dir():
        return 0
    return sum(1 for d in domains_dir.iterdir() if d.is_dir())


def _check_file(kb_dir: Path, rel_path: str) -> bool:
    return (kb_dir / rel_path).exists()


def _detect_kb_version(kb_dir: Path) -> str | None:
    """Detect KB schema version from knowledge-base.json or node fields."""
    kb_json = kb_dir / "graph" / "knowledge-base.json"
    if kb_json.exists():
        try:
            data = json.loads(kb_json.read_text())
            return data.get("schema_version") or data.get("version")
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: check nodes.json for old field names
    nodes_json = kb_dir / "graph" / "nodes.json"
    if nodes_json.exists():
        try:
            nodes = json.loads(nodes_json.read_text())
            if isinstance(nodes, dict) and "nodes" in nodes:
                nodes = nodes["nodes"]
            if isinstance(nodes, list) and nodes:
                first = nodes[0]
                # Old format has sourceFiles (camelCase)
                if "sourceFiles" in first:
                    return "0.1"
                # vNext has source_files + provenance
                if "provenance" in first:
                    return "1.0"
                # Current transitional: source_files but no provenance
                if "source_files" in first:
                    return "0.2"
                return "0.1"
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _section_quality(content: str, heading: str) -> str:
    """
    Grade a section's content quality.

    Returns: missing | placeholder | partial | substantive
    """
    # Find the heading and extract content until next heading
    pattern = re.compile(rf"^{re.escape(heading)}.*$", re.MULTILINE)
    m = pattern.search(content)
    if not m:
        return "missing"

    start = m.end()
    # Find next heading at same level (##) or higher (#)
    next_heading = re.compile(r"^#{1,2}\s+", re.MULTILINE)
    nm = next_heading.search(content, start)
    section_body = content[start:nm.start()] if nm else content[start:]
    section_body = section_body.strip()

    if not section_body:
        return "placeholder"

    # Detect template placeholders
    placeholder_signals = [
        "{{", "}}",            # template variables
        "TBD", "TODO",          # explicit unknowns
        "tbd", "todo",
        "...",                   # trailing ellipsis with no content
    ]
    # Only flag as placeholder if these dominate the content
    stripped = section_body.replace("\n", " ").strip()
    if any(s in stripped for s in placeholder_signals) and len(stripped) < 80:
        return "placeholder"

    # Detect genuinely empty or whitespace-only
    if len(section_body) < 20:
        return "placeholder"

    # Partial: has some content but under 100 chars (likely incomplete)
    if len(section_body) < 100:
        return "partial"

    return "substantive"


def _read_project_hub_sections(kb_dir: Path) -> dict[str, str]:
    """
    Check which sections exist in the project hub page and their quality.

    Returns dict of section_key → missing | placeholder | partial | substantive.
    """
    project_md = None
    for md in kb_dir.glob("*.md"):
        project_md = md
        break
    if project_md is None:
        return {}

    try:
        content = project_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    headings = {
        "purpose": "## Purpose",
        "actors": "## Primary Users",
        "core_outcomes": "## Core Outcomes",
        "scope": "## Scope",
        "technology": "## Technology Summary",
        "architecture": "## System Architecture",
        "runtime": "## Runtime Entry Points",
        "external_integrations": "## External Systems",
        "domains": "## Domains",
        "invariants": "## System-wide Invariants",
        "legacy_migration": "## Current Risks",
        "active_changes": "## Active Changes",
    }

    result: dict[str, str] = {}
    for key, heading in headings.items():
        quality = _section_quality(content, heading)
        # Fallback: try alternate heading names
        if quality == "missing":
            alt_headings = {
                "actors": "## Actors",
                "invariants": "## Invariants",
                "external_integrations": "## Integrations",
                "legacy_migration": "## Legacy",
                "runtime": "## Entry Points",
            }
            if key in alt_headings:
                quality = _section_quality(content, alt_headings[key])
        result[key] = quality

    return result


def _build_gap_map(root: Path, kb_dir: Path | None) -> dict[str, Any]:
    """Produce structured Knowledge Gap Map."""
    gaps: dict[str, dict[str, Any]] = {}

    for dim in _GAP_DIMENSIONS:
        gaps[dim] = {
            "status": "missing",
            "source": "unknown",
            "detail": "",
        }

    if kb_dir is None:
        return gaps

    # Check project hub sections
    hub_sections = _read_project_hub_sections(kb_dir)

    # Map hub sections to gap dimensions
    section_to_dim = {
        "purpose": "purpose",
        "actors": "actors",
        "core_outcomes": "core_outcomes",
        "scope": "scope",
        "technology": "technology",
        "architecture": "architecture",
        "runtime": "runtime",
        "external_integrations": "external_integrations",
        "domains": "domains",
        "invariants": "invariants",
        "legacy_migration": "legacy_migration",
    }

    for section, dim in section_to_dim.items():
        quality = hub_sections.get(section, "missing")
        if quality != "missing":
            gaps[dim]["status"] = quality
            gaps[dim]["source"] = "project_hub"
            if quality == "placeholder":
                gaps[dim]["detail"] = f"Section '{section}' is a template placeholder — needs human input"
            elif quality == "partial":
                gaps[dim]["detail"] = f"Section '{section}' has minimal content — likely incomplete"
            else:
                gaps[dim]["detail"] = f"Section '{section}' present in project hub"

    # Check architecture files
    arch_files_present = 0
    for af in _ARCHITECTURE_FILES:
        if _check_file(kb_dir, af):
            arch_files_present += 1
    if arch_files_present > 0:
        for dim in ["architecture", "technology", "runtime"]:
            if gaps[dim]["status"] == "missing":
                gaps[dim]["status"] = "partial"
                gaps[dim]["source"] = "architecture_docs"

    # Check domain directories
    domain_count = _count_domain_dirs(kb_dir)
    if domain_count > 0:
        gaps["domains"]["status"] = "complete" if domain_count >= 2 else "partial"
        gaps["domains"]["source"] = "kb_structure"
        gaps["domains"]["detail"] = f"{domain_count} domain director{'y' if domain_count == 1 else 'ies'} found"

        # Check if domain pages have owns/does-not-own sections
        domains_dir = kb_dir / "domains"
        boundary_count = 0
        if domains_dir.is_dir():
            for domain_dir in domains_dir.iterdir():
                domain_md = domain_dir / f"{domain_dir.name}.md"
                if domain_md.exists():
                    try:
                        content = domain_md.read_text(encoding="utf-8", errors="replace")
                        if "## Owns" in content and "## Does Not Own" in content:
                            boundary_count += 1
                    except OSError:
                        pass
        if boundary_count > 0:
            gaps["domain_boundaries"]["status"] = "complete" if boundary_count >= domain_count else "partial"
            gaps["domain_boundaries"]["source"] = "domain_pages"
            gaps["domain_boundaries"]["detail"] = f"{boundary_count}/{domain_count} domains have boundary sections"

    # Check graph files
    graph_files_present = sum(1 for gf in _GRAPH_FILES if _check_file(kb_dir, gf))
    if graph_files_present >= 2:
        # Graph exists — confirms domains/architecture been mapped
        for dim in ["domains"]:
            if gaps[dim]["status"] == "missing":
                gaps[dim]["status"] = "partial"
                gaps[dim]["source"] = "graph_indexes"

    # Check reports for legacy/migration
    if _check_file(kb_dir, "reports/suspected-legacy.md"):
        gaps["legacy_migration"]["status"] = "partial"
        gaps["legacy_migration"]["source"] = "reports"

    # Mark what can likely be found vs needs human
    for dim, gap in gaps.items():
        if gap["status"] == "missing":
            dim_found_in = {
                "purpose": "found_in_docs",
                "actors": "found_in_docs",
                "core_outcomes": "found_in_docs",
                "scope": "found_in_docs",
                "technology": "inferred_from_project",
                "architecture": "inferred_from_project",
                "runtime": "inferred_from_project",
                "external_integrations": "inferred_from_project",
                "domains": "inferred_from_project",
                "domain_boundaries": "needs_human",
                "invariants": "needs_human",
                "legacy_migration": "needs_human",
            }
            gap["source"] = dim_found_in.get(dim, "unknown")

    return gaps


# ── Main classifier ───────────────────────────────────────────────────────────

def classify(root: Path) -> dict[str, Any]:
    """
    Classify the project state and build a Knowledge Gap Map.

    Returns:
        {
          "state": str,
          "state_reasons": [str, ...],
          "kb_dir": str | null,
          "kb_version": str | null,
          "source_file_count": int,
          "domain_count": int,
          "project_hub_exists": bool,
          "graph_files_present": int,
          "architecture_files_present": int,
          "gap_map": { dimension: {status, source, detail} },
        }
    """
    source_count = _count_source_files(root)
    kb_dir = _find_kb_dir(root)
    kb_version = _detect_kb_version(kb_dir) if kb_dir else None
    reasons: list[str] = []

    # ── Determine state ───────────────────────────────────────────────────────
    state: str

    if source_count == 0 and kb_dir is None:
        state = "greenfield"
        reasons.append("no source files found")
        reasons.append("no existing KB")

    elif source_count > 0 and kb_dir is None:
        state = "new_brownfield"
        reasons.append(f"{source_count}+ source files detected")
        reasons.append("no existing KB")

    elif kb_dir is not None and kb_version is not None and kb_version in ("0.1",):
        state = "legacy_kb"
        reasons.append(f"KB exists with legacy schema version {kb_version}")
        reasons.append("migration to vNext required")

    elif kb_dir is not None:
        # Check completeness
        hub_exists = bool(list(kb_dir.glob("*.md")))
        domain_count = _count_domain_dirs(kb_dir)
        graph_present = sum(1 for gf in _GRAPH_FILES if _check_file(kb_dir, gf))
        arch_present = sum(1 for af in _ARCHITECTURE_FILES if _check_file(kb_dir, af))

        hub_sections = _read_project_hub_sections(kb_dir)
        substantive = sum(1 for v in hub_sections.values() if v == "substantive")
        partial_count = sum(1 for v in hub_sections.values() if v == "partial")
        placeholder_count = sum(1 for v in hub_sections.values() if v == "placeholder")
        filled_sections = substantive + partial_count
        total_sections = len(hub_sections) if hub_sections else 12

        if not hub_exists:
            state = "partial_kb"
            reasons.append("KB directory exists but no project hub page")

        elif filled_sections < total_sections * 0.5:
            state = "partial_kb"
            reasons.append(f"project hub incomplete ({substantive} substantive, {partial_count} partial, {placeholder_count} placeholders out of {total_sections} sections)")

        elif domain_count == 0:
            state = "partial_kb"
            reasons.append("no domain directories found")

        elif arch_present < 2:
            state = "partial_kb"
            reasons.append(f"only {arch_present} architecture page(s)")

        elif graph_present < 3:
            state = "partial_kb"
            reasons.append(f"only {graph_present}/4 graph files present")

        else:
            # Check staleness: compare stored hashes vs current file hashes
            stale = False
            hashes_json = kb_dir / "graph" / "file-hashes.json"

            if hashes_json.exists():
                try:
                    stored_hashes: dict[str, str] = json.loads(hashes_json.read_text())
                    checked = 0
                    for rel_path, stored_hash in stored_hashes.items():
                        sf = root / rel_path
                        if not sf.exists():
                            stale = True
                            reasons.append(f"tracked source file deleted: {rel_path}")
                            break
                        try:
                            current_hash = hashlib.sha256(sf.read_bytes()).hexdigest()
                            if current_hash != stored_hash:
                                stale = True
                                reasons.append(f"source file changed: {rel_path}")
                                break
                        except OSError:
                            pass
                        checked += 1
                        if checked >= 200:  # sample first 200 files
                            break
                except (json.JSONDecodeError, OSError):
                    pass

            if stale:
                state = "stale_kb"
                reasons.append("stored file hashes don't match current source — KB may be stale")
            else:
                state = "onboarded"
                reasons.append("project hub complete with all required sections")
                reasons.append(f"{domain_count} domains mapped")
                reasons.append(f"architecture pages present ({arch_present}/6)")
                reasons.append(f"graph indexes present ({graph_present}/4)")
    else:
        state = "greenfield"
        reasons.append("unable to determine — defaulting to greenfield")

    # ── Build gap map ─────────────────────────────────────────────────────────
    gap_map = _build_gap_map(root, kb_dir)

    return {
        "state": state,
        "state_reasons": reasons,
        "kb_dir": str(kb_dir.relative_to(root)) if kb_dir else None,
        "kb_version": kb_version,
        "source_file_count": source_count,
        "domain_count": _count_domain_dirs(kb_dir) if kb_dir else 0,
        "project_hub_exists": bool(list(kb_dir.glob("*.md"))) if kb_dir else False,
        "graph_files_present": sum(1 for gf in _GRAPH_FILES if _check_file(kb_dir, gf)) if kb_dir else 0,
        "architecture_files_present": sum(1 for af in _ARCHITECTURE_FILES if _check_file(kb_dir, af)) if kb_dir else 0,
        "hub_sections_found": _read_project_hub_sections(kb_dir) if kb_dir else {},
        "gap_map": gap_map,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain project-state — state classifier + gap map",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root directory")
    parser.add_argument("--gaps", action="store_true", help="Include detailed gap analysis")
    parser.add_argument("--output", metavar="FILE", help="Write JSON to file (default: stdout)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = classify(root)

    if not args.gaps:
        # Compact output: state + key numbers + gap summary
        gap_summary = {dim: g["status"] for dim, g in result["gap_map"].items()}
        output = {
            "state": result["state"],
            "state_reasons": result["state_reasons"],
            "kb_dir": result["kb_dir"],
            "kb_version": result["kb_version"],
            "source_file_count": result["source_file_count"],
            "domain_count": result["domain_count"],
            "project_hub_exists": result["project_hub_exists"],
            "gap_summary": gap_summary,
        }
    else:
        output = result

    json_out = json.dumps(output, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(json_out, encoding="utf-8")
        print(f"State report written to {args.output}", file=sys.stderr)
    else:
        print(json_out)


if __name__ == "__main__":
    main()
