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
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Reuse shared frontmatter parser
sys.path.insert(0, str(Path(__file__).resolve().parent))
from frontmatter import parse as parse_frontmatter


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


def _hash_file(file_path: Path) -> str:
    """SHA-256 hex digest of file contents."""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _extract_status(file_path: Path, fm: dict) -> tuple[str, bool]:
    """Return (status, requires_confirmation) from frontmatter or content markers.

    Priority: frontmatter ``status`` field > explicit status line in preamble >
    content markers in preamble only > fallback.
    """
    # 1. Frontmatter status field (from shared parser)
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

def _load_existing_inventory(graph_dir: Path | None) -> dict[str, dict]:
    """Load existing intent-sources.json and index by path for resolution carry-over."""
    if not graph_dir:
        return {}
    existing_path = graph_dir / "intent-sources.json"
    if not existing_path.exists():
        return {}
    try:
        existing = json.loads(existing_path.read_text())
        return {s["path"]: s for s in existing.get("sources", [])}
    except (json.JSONDecodeError, KeyError, OSError):
        return {}


def scan_intent_sources(root: Path, kb_dir: Path | None = None) -> dict:
    """Scan *root* for intent documents and classify each.

    On re-run, preserves ``resolution`` for sources whose file hash is
    unchanged. New sources get ``resolution.state: pending``.
    ``pending_confirmation`` is derived from unresolved sources, not from
    document status.
    """
    graph_dir = (kb_dir / "graph") if kb_dir else None
    previous = _load_existing_inventory(graph_dir)

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

            file_hash = _hash_file(match_path)
            fm, _body = parse_frontmatter(text)
            status, requires_confirmation = _extract_status(match_path, fm)

            # Preserve resolution if file unchanged from previous inventory
            prev = previous.get(rel)
            if prev and prev.get("_file_hash") == file_hash and "resolution" in prev:
                resolution = prev["resolution"]
            else:
                resolution = {
                    "state": "pending",
                    "provenance": None,
                    "resolved_at": None,
                }

            entry: dict = {
                "path": rel,
                "kind": kind,
                "status": status,
                "authority": authority,
                "requires_confirmation": requires_confirmation,
                "resolution": resolution,
                "last_modified": _git_last_modified(root, rel),
                "title": fm.get("title", fm.get("name", "")),
                "_file_hash": file_hash,
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

    # pending_confirmation derived from resolution state, not document status
    pending = sum(1 for s in sources if s["resolution"]["state"] == "pending")
    accepted = sum(1 for s in sources if s["resolution"]["state"] == "accepted")
    partial = sum(1 for s in sources if s["resolution"]["state"] == "partial")
    rejected = sum(1 for s in sources if s["resolution"]["state"] == "rejected")

    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root.resolve()),
        "discovered": discovered,
        "confirmed": confirmed,
        "draft_or_unknown": draft_or_unknown,
        "historical": historical,
        "pending_resolution": pending,
        "accepted": accepted,
        "partial": partial,
        "rejected": rejected,
        "pending_confirmation": pending > 0,
        "sources": sources,
    }

    return result


def apply_resolution(kb_dir: Path, source_path: str, state: str) -> dict | None:
    """Apply a human resolution to one intent source.

    ``state`` must be one of: accepted, partial, rejected, deferred.

    Updates ``intent-sources.json`` in place and returns the full inventory
    with recalculated counts. Returns None if the source is not found.
    """
    valid_states = {"accepted", "partial", "rejected", "deferred"}
    if state not in valid_states:
        raise ValueError(f"Invalid resolution state: {state}. Must be one of {valid_states}")

    inventory_path = kb_dir / "graph" / "intent-sources.json"
    if not inventory_path.exists():
        print(f"Error: {inventory_path} not found — run intent_inventory.py first", file=sys.stderr)
        return None

    inventory = json.loads(inventory_path.read_text())
    sources = inventory.get("sources", [])
    target = next((s for s in sources if s["path"] == source_path), None)

    if target is None:
        print(f"Error: source '{source_path}' not found in inventory", file=sys.stderr)
        return None

    target["resolution"] = {
        "state": state,
        "provenance": "human",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }

    # Recalculate counts
    pending = sum(1 for s in sources if s["resolution"]["state"] == "pending")
    accepted = sum(1 for s in sources if s["resolution"]["state"] == "accepted")
    partial = sum(1 for s in sources if s["resolution"]["state"] == "partial")
    rejected = sum(1 for s in sources if s["resolution"]["state"] == "rejected")

    inventory["pending_resolution"] = pending
    inventory["accepted"] = accepted
    inventory["partial"] = partial
    inventory["rejected"] = rejected
    inventory["pending_confirmation"] = pending > 0
    inventory["scanned_at"] = datetime.now(timezone.utc).isoformat()

    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
    return inventory


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
    parser.add_argument(
        "--resolve",
        nargs=2,
        metavar=("SOURCE_PATH", "STATE"),
        help="Apply human resolution: <path> <accepted|partial|rejected|deferred>",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f'Error: root "{root}" does not exist', file=sys.stderr)
        sys.exit(1)

    # ── --resolve mode ──────────────────────────────────────────────────────
    if args.resolve:
        if not args.kb_dir:
            print("Error: --resolve requires --kb-dir", file=sys.stderr)
            sys.exit(1)
        source_path, state = args.resolve
        result = apply_resolution(Path(args.kb_dir), source_path, state)
        if result is None:
            sys.exit(1)
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(json_str + "\n")
        print(json_str)
        return

    result = scan_intent_sources(root, Path(args.kb_dir) if args.kb_dir else None)

    json_str_persist = json.dumps(result, indent=2, ensure_ascii=False)
    # Strip internal hashes for stdout/file output (persisted KB copy keeps them)
    result_clean = json.loads(json_str_persist)
    for s in result_clean.get("sources", []):
        s.pop("_file_hash", None)
    json_str_clean = json.dumps(result_clean, indent=2, ensure_ascii=False)

    # Write to KB dir if specified (with hashes for change detection)
    if args.kb_dir:
        kb_path = Path(args.kb_dir)
        kb_path.mkdir(parents=True, exist_ok=True)
        graph_dir = kb_path / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        output_path = graph_dir / "intent-sources.json"
        output_path.write_text(json_str_persist + "\n")
        print(f"Intent sources written to {output_path}", file=sys.stderr)

    # Write to explicit output file
    if args.output:
        Path(args.output).write_text(json_str_clean + "\n")
        print(f"Intent sources written to {args.output}", file=sys.stderr)

    # Default: stdout (clean, no internal hashes)
    if not args.output and not args.kb_dir:
        print(json_str_clean)


if __name__ == "__main__":
    main()
