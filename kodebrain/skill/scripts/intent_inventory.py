#!/usr/bin/env python3
"""
kodebrain intent-inventory — deterministic scan for project intent documents.

Discovers specifications, ADRs, architecture docs, PRDs, READMEs, and other
intent-bearing files BEFORE source-code harvest. Produces ``intent-sources.json``
so onboard can distinguish "what we said we'd build" from "what we actually built."

Usage:
  python3 intent_inventory.py <root>                        # stdout JSON
  python3 intent_inventory.py <root> --output out.json      # write to file
  python3 intent_inventory.py <root> --kb-dir docs/brain/projects/<name>  # KB path
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── frontmatter parse (inline — avoids import path complexity) ──────────

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_simple_frontmatter(text: str) -> dict:
    """Extract flat key: value pairs from YAML frontmatter."""
    m = _FM_RE.match(text)
    if not m:
        return {}
    result: dict = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            result[key] = val
    return result


# ── glob patterns ────────────────────────────────────────────────────────

INTENT_GLOBS: list[tuple[str, str, str]] = [
    # (glob, kind, default_authority)
    ("docs/specs/**/*.md", "specification", "high"),
    ("docs/spec/**/*.md", "specification", "high"),
    ("docs/design/spec/**/*.md", "specification", "high"),
    ("docs/architecture/**/*.md", "architecture_doc", "high"),
    ("docs/design/**/*.md", "architecture_doc", "high"),
    ("docs/adr/**/*.md", "adr", "high"),
    ("**/decisions/**/*.md", "adr", "high"),
    ("docs/**/adr/**/*.md", "adr", "high"),
    ("README.md", "readme", "medium"),
    ("README.*.md", "readme", "medium"),
    ("**/PRD*.md", "prd", "high"),
    ("**/product-requirement*.md", "prd", "high"),
    ("**/product_brief*.md", "prd", "high"),
    ("**/CONTRIBUTING.md", "convention", "medium"),
    ("**/ARCHITECTURE.md", "convention", "medium"),
    ("**/DESIGN.md", "design_doc", "medium"),
    ("**/ROADMAP.md", "design_doc", "medium"),
]

# Paths to skip (never intent sources)
SKIP_PREFIXES: list[str] = [
    "node_modules/",
    ".git/",
    "dist/",
    "build/",
    "__pycache__/",
    ".claude/",
    "docs/brain/",
    "venv/",
    ".venv/",
    ".tox/",
]

# ── status extraction ────────────────────────────────────────────────────

DRAFT_MARKERS: list[str] = [
    r"\bDRAFT\b",
    r"\bWIP\b",
    r"\bv0\.\d+\b",
    r"\bawaiting\s+(user\s+)?confirmation\b",
    r"\bnot\s+yet\s+(confirmed|approved)\b",
]

CONFIRMED_MARKERS: list[str] = [
    r"\bCONFIRMED\b",
    r"\bAPPROVED\b",
    r"\bCURRENT\b",
]

HISTORICAL_MARKERS: list[str] = [
    r"\bDEPRECATED\b",
    r"\bSUPERSEDED\b",
    r"\bHISTORICAL\b",
    r"\bARCHIVED\b",
]


def _extract_status(file_path: Path, fm: dict) -> tuple[str, bool]:
    """Return (status, requires_confirmation) from frontmatter or content markers.

    Priority: frontmatter ``status`` field > explicit status line in preamble >
    content markers in preamble only > git age fallback.
    """
    # 1. Frontmatter status field
    fm_status = fm.get("status", "").strip().lower()
    if fm_status in ("draft", "wip"):
        return ("draft", True)
    if fm_status in ("approved", "current", "active"):
        return ("current", False)
    if fm_status in ("historical", "superseded", "deprecated", "archived"):
        return ("historical", False)

    # 2. Read preamble — text before first ## heading (where metadata lives)
    try:
        full_text = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        return ("unknown", True)

    # Split at first ## heading to isolate preamble/metadata section
    preamble = re.split(r'^## ', full_text, maxsplit=1, flags=re.MULTILINE)[0]
    preamble_upper = preamble.upper()

    # 2a. Explicit status line: **Status:** DRAFT or Status: CURRENT
    status_line = re.search(
        r'\*{0,2}Status:\*{0,2}\s*(.+)',
        preamble, re.IGNORECASE
    )
    if status_line:
        status_text = status_line.group(1).strip().upper()
        if any(m in status_text for m in ['DRAFT', 'WIP', 'AWAITING']):
            return ("draft", True)
        if any(m in status_text for m in ['CURRENT', 'APPROVED', 'CONFIRMED', 'ACTIVE']):
            return ("current", False)
        if any(m in status_text for m in ['HISTORICAL', 'SUPERSEDED', 'DEPRECATED', 'ARCHIVED']):
            return ("historical", False)

    # 3. Content markers in preamble only (not body — avoids template text false match)
    if any(re.search(p, preamble_upper) for p in HISTORICAL_MARKERS):
        return ("historical", False)
    if any(re.search(p, preamble_upper) for p in CONFIRMED_MARKERS):
        return ("current", False)
    if any(re.search(p, preamble_upper) for p in DRAFT_MARKERS):
        return ("draft", True)

    # 4. Fallback: unknown
    return ("unknown", True)


def _non_negotiable_principles(text: str) -> list[str]:
    """Extract non-negotiable principles from a confirmed spec."""
    principles: list[str] = []
    in_section = False
    for line in text.split("\n"):
        if re.match(r"^##\s+.*[Nn]on.[Nn]egotiable", line):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            stripped = line.strip()
            if stripped.startswith("- ") or (stripped and stripped[0].isdigit() and ". " in stripped):
                principles.append(stripped.lstrip("- 0123456789. "))
            elif stripped and not principles:
                # Might be a prose paragraph in the section
                principles.append(stripped)
    return principles


def _covers_domains(fm: dict, text: str) -> list[str]:
    """Guess which domains this intent doc covers."""
    domains = fm.get("domain", "")
    if not domains:
        domains = fm.get("domains", "")
    if domains:
        if isinstance(domains, list):
            return domains
        return [d.strip() for d in str(domains).split(",")]
    # Try to find domain mentions in first 100 lines
    found: list[str] = []
    for line in text.split("\n")[:100]:
        m = re.search(r"(?:domain|module|component)[\s:]+(\w[\w-]*)", line, re.IGNORECASE)
        if m:
            found.append(m.group(1))
    return list(dict.fromkeys(found))  # dedupe, preserve order


# ── git age ──────────────────────────────────────────────────────────────

def _git_last_modified(root: Path, rel_path: str) -> str | None:
    """Return ISO date of last meaningful git commit touching this file."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%aI", "--", rel_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ── main inventory ───────────────────────────────────────────────────────

def scan_intent_sources(root: Path, kb_dir: Path | None = None) -> dict:
    """Scan *root* for intent documents and classify each.

    Returns the ``intent-sources.json`` structure.
    """
    sources: list[dict] = []
    seen: set[str] = set()

    for glob_pattern, kind, authority in INTENT_GLOBS:
        for match_path in root.glob(glob_pattern):
            rel = str(match_path.relative_to(root))
            if rel in seen:
                continue
            if any(rel.startswith(p) for p in SKIP_PREFIXES):
                continue
            if not match_path.is_file():
                continue
            seen.add(rel)

            try:
                text = match_path.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            fm = _parse_simple_frontmatter(text)
            status, requires_confirmation = _extract_status(match_path, fm)

            entry: dict = {
                "path": rel,
                "kind": kind,
                "status": status,
                "authority": authority,
                "requires_confirmation": requires_confirmation,
                "last_modified": _git_last_modified(root, rel),
                "title": fm.get("title", fm.get("name", "")),
            }

            # Only extract rich fields for confirmed specs
            if kind == "specification" and status == "current":
                entry["non_negotiable_principles"] = _non_negotiable_principles(text)
                entry["covers_domains"] = _covers_domains(fm, text)
            else:
                entry["covers_domains"] = _covers_domains(fm, text)

            sources.append(entry)

    # Sort: high authority first, then by kind, then by path
    authority_order = {"high": 0, "medium": 1, "low": 2}
    sources.sort(key=lambda s: (authority_order.get(s["authority"], 3), s["kind"], s["path"]))

    discovered = len(sources)
    confirmed = sum(1 for s in sources if s["status"] == "current")
    draft_or_unknown = sum(1 for s in sources if s["requires_confirmation"])
    historical = sum(1 for s in sources if s["status"] == "historical")

    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root.resolve()),
        "discovered": discovered,
        "confirmed": confirmed,
        "draft_or_unknown": draft_or_unknown,
        "historical": historical,
        "pending_confirmation": draft_or_unknown > 0,
        "sources": sources,
    }

    return result


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain intent-inventory — discover project intent documents",
    )
    parser.add_argument(
        "root",
        help="Project root directory",
    )
    parser.add_argument(
        "--output", "-o",
        help="Write JSON to file instead of stdout",
    )
    parser.add_argument(
        "--kb-dir",
        help="KB project dir (writes to <kb_dir>/graph/intent-sources.json)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f'Error: root "{root}" does not exist', file=sys.stderr)
        sys.exit(1)

    result = scan_intent_sources(root)

    json_str = json.dumps(result, indent=2, ensure_ascii=False)

    # Write to KB dir if specified
    if args.kb_dir:
        kb_path = Path(args.kb_dir)
        kb_path.mkdir(parents=True, exist_ok=True)
        graph_dir = kb_path / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        output_path = graph_dir / "intent-sources.json"
        output_path.write_text(json_str + "\n")
        print(f"Intent sources written to {output_path}", file=sys.stderr)

    # Write to explicit output file
    if args.output:
        Path(args.output).write_text(json_str + "\n")
        print(f"Intent sources written to {args.output}", file=sys.stderr)

    # Default: stdout
    if not args.output and not args.kb_dir:
        print(json_str)


if __name__ == "__main__":
    main()
