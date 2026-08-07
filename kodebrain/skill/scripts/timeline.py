#!/usr/bin/env python3
"""
kodebrain timeline — generated project timeline + events from history records.

Scans ALL Markdown pages in the KB, selects by frontmatter type
(decision | change | incident | milestone), and produces:

  history/timeline.md — chronological human-readable timeline
  history/events.json — temporal index for agent retrieval

Records are source of truth. Timeline + events are generated — never edited.

Date priority by record type:
  Change:   completed_at > started_at > last_updated > filename prefix
  Incident: resolved_at > started_at > last_updated > filename prefix
  Decision: date > last_updated > filename prefix
  Milestone: date > last_updated > filename prefix

Decision lineage: only supersedes is stored on the NEW decision.
superseded_by on old decisions is derived by the compiler (no rewrite).

Usage:
  python3 timeline.py <kb_project_dir>                      # generate both
  python3 timeline.py <kb_project_dir> --timeline-only       # timeline.md only
  python3 timeline.py <kb_project_dir> --events-only         # events.json only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Frontmatter parsing ───────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+?)?\]\]")

_HISTORY_TYPES = {"decision", "change", "incident", "milestone"}


def _parse_frontmatter(text: str) -> dict[str, Any]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            fm[key] = value
    return fm


def _parse_title(text: str) -> str:
    m = _FRONTMATTER_RE.match(text)
    body = text[m.end():] if m else text
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Untitled"


def _extract_wikilinks(body: str) -> list[str]:
    targets = _WIKILINK_RE.findall(body)
    seen: set[str] = set()
    result: list[str] = []
    for t in targets:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _date_from_filename(stem: str) -> str:
    """Extract YYYY-MM-DD from a filename like 2026-08-07-some-slug."""
    parts = stem.split("-", 3)
    if len(parts) >= 3 and parts[0].isdigit() and len(parts[0]) == 4:
        return f"{parts[0]}-{parts[1]}-{parts[2]}"
    return ""


# ── Record collection (all .md, filtered by type) ─────────────────────────────

def _collect_records(kb_dir: Path) -> list[dict[str, Any]]:
    """
    Scan all Markdown pages in KB. Return those with type in _HISTORY_TYPES.

    Each record: {date, type, title, id, path, subtype, state, linked_nodes}.
    """
    records: list[dict[str, Any]] = []

    for md in sorted(kb_dir.rglob("*.md")):
        # Skip reports and generated files
        rel = str(md.relative_to(kb_dir))
        if rel.startswith("reports/") or rel.startswith("history/"):
            continue

        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        fm = _parse_frontmatter(text)
        record_type = fm.get("type", "")

        if record_type not in _HISTORY_TYPES:
            continue

        # Filter: changes must be completed/reconciled
        if record_type == "change":
            change_state = fm.get("change_state") or fm.get("status", "")
            if change_state not in ("reconciled", "completed", "implemented"):
                continue

        title = _parse_title(text)
        record_id = fm.get("id", md.stem)

        # Date priority by record type
        if record_type == "change":
            date_str = (
                fm.get("completed_at")
                or fm.get("started_at")
                or fm.get("last_updated")
                or _date_from_filename(md.stem)
            )
        elif record_type == "incident":
            date_str = (
                fm.get("resolved_at")
                or fm.get("started_at")
                or fm.get("last_updated")
                or _date_from_filename(md.stem)
            )
        elif record_type == "decision":
            date_str = (
                fm.get("date")
                or fm.get("last_updated")
                or _date_from_filename(md.stem)
            )
        elif record_type == "milestone":
            date_str = (
                fm.get("date")
                or fm.get("last_updated")
                or _date_from_filename(md.stem)
            )
        else:
            date_str = ""

        # Lifecycle state
        state = ""
        if record_type == "decision":
            state = fm.get("decision_state", "active")
        elif record_type == "change":
            state = fm.get("change_state") or fm.get("status", "")
        elif record_type == "incident":
            state = fm.get("incident_state") or fm.get("status", "")

        # Subtype
        subtype = ""
        if record_type == "incident":
            subtype = fm.get("severity", "")
        elif record_type == "milestone":
            subtype = fm.get("significance", "")

        # Linked nodes from wiki-links in body
        body = text[_FRONTMATTER_RE.match(text).end():] if _FRONTMATTER_RE.match(text) else ""
        linked_nodes = _extract_wikilinks(body)

        # Supersedes (for lineage derivation)
        supersedes_raw = fm.get("supersedes", "")
        supersedes: list[str] = []
        if isinstance(supersedes_raw, str) and supersedes_raw:
            supersedes = [s.strip() for s in supersedes_raw.split(",") if s.strip()]
        elif isinstance(supersedes_raw, list):
            supersedes = supersedes_raw

        records.append({
            "date": date_str,
            "type": record_type,
            "title": title,
            "id": record_id,
            "subtype": subtype,
            "state": state,
            "path": str(md.relative_to(kb_dir)),
            "supersedes": supersedes,
            "linked_nodes": linked_nodes,
        })

    # Sort by date, descending
    records.sort(key=lambda r: r["date"], reverse=True)

    return records


# ── Decision lineage derivation ───────────────────────────────────────────────

def _derive_lineage(records: list[dict]) -> list[dict]:
    """
    Derive superseded_by from supersedes (single direction).

    For every decision D2 that supersedes D1, add D1.superseded_by = [D2].
    Does NOT modify records in place — returns enriched copy.
    """
    # Build supersedes map: new_id → [old_ids]
    supersedes_map: dict[str, list[str]] = {}
    for r in records:
        if r["type"] == "decision" and r["supersedes"]:
            supersedes_map[r["id"]] = r["supersedes"]

    enriched = []
    for r in records:
        rec = dict(r)
        rec["superseded_by"] = []
        for new_id, old_ids in supersedes_map.items():
            if r["id"] in old_ids:
                rec["superseded_by"].append(new_id)
                if rec["state"] == "active":
                    rec["state"] = "superseded"
        enriched.append(rec)

    return enriched


# ── Event generation ──────────────────────────────────────────────────────────

def _generate_events(records: list[dict]) -> list[dict]:
    """
    Generate a temporal event for each record.

    One record = one primary event (for now). Future: multi-event records
    (change progress entries, milestone sub-events, etc.)
    """
    events: list[dict] = []
    for r in records:
        events.append({
            "date": r["date"],
            "type": r["type"],
            "id": r["id"],
            "title": r["title"],
            "state": r.get("state", ""),
            "subtype": r.get("subtype", ""),
            "linked_nodes": r.get("linked_nodes", []),
            "path": r.get("path", ""),
        })
    events.sort(key=lambda e: e["date"], reverse=True)
    return events


# ── Timeline generation ───────────────────────────────────────────────────────

def generate_timeline(kb_dir: Path) -> str:
    """Generate history/timeline.md from all history records."""
    raw_records = _collect_records(kb_dir)
    records = _derive_lineage(raw_records)

    grouped: dict[str, dict[str, list[dict]]] = {}
    for r in records:
        date = r["date"]
        if not date or len(date) < 7:
            year, month = "Unknown", ""
        else:
            year = date[:4]
            month = date[5:7]

        month_names = {
            "01": "January", "02": "February", "03": "March",
            "04": "April", "05": "May", "06": "June",
            "07": "July", "08": "August", "09": "September",
            "10": "October", "11": "November", "12": "December",
        }
        month_name = month_names.get(month, "")
        grouped.setdefault(year, {}).setdefault(month_name, []).append(r)

    lines: list[str] = []
    lines.append("# Project Timeline")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("> This file is generated from history records. Do not edit directly.")
    lines.append("")
    lines.append(f"**Total records:** {len(records)}")
    lines.append("")

    for year in sorted(grouped.keys(), reverse=True):
        lines.append(f"## {year}")
        lines.append("")
        months = grouped[year]
        for month_name in [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December", "",
        ]:
            if month_name not in months:
                continue
            lines.append(f"### {month_name}")
            lines.append("")
            for r in months[month_name]:
                date_display = r["date"] if r["date"] else "????-??-??"
                type_icon = {
                    "Decision": "🔷", "Change": "🔧",
                    "Incident": "⚠️", "Milestone": "🏁",
                }.get(r["type"], "•")

                state_note = f" — *{r.get('state', '')}*" if r.get("state") else ""
                subtype_note = f" — *{r['subtype']}*" if r.get("subtype") else ""

                lines.append(
                    f"{date_display} — {type_icon} **{r['type']}**{subtype_note}{state_note}"
                )
                lines.append(f"{r['title']}")
                lines.append(f"[[{r['id']}|→ Read]]")

                # Show lineage for decisions
                if r.get("supersedes"):
                    lines.append(f"  Supersedes: {', '.join(f'[[{s}]]' for s in r['supersedes'])}")
                if r.get("superseded_by"):
                    lines.append(f"  Superseded by: {', '.join(f'[[{s}]]' for s in r['superseded_by'])}")

                lines.append("")

    return "\n".join(lines) + "\n"


def generate_events(kb_dir: Path) -> list[dict]:
    """Generate history/events.json from all history records."""
    records = _collect_records(kb_dir)
    return _generate_events(records)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain timeline — generate timeline + events from history records",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("kb_dir", help="Path to docs/brain/projects/<name>/ directory")
    parser.add_argument("--timeline-only", action="store_true", help="Only generate timeline.md")
    parser.add_argument("--events-only", action="store_true", help="Only output events.json")
    parser.add_argument("--output-dir", metavar="DIR", help="Write to directory (default: kb_dir/history/)")
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir).resolve()
    if not kb_dir.is_dir():
        print(f"Error: {kb_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else (kb_dir / "history")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.events_only:
        events = generate_events(kb_dir)
        print(json.dumps(events, indent=2, ensure_ascii=False))
        return

    if args.timeline_only:
        content = generate_timeline(kb_dir)
        out_path = out_dir / "timeline.md"
        out_path.write_text(content, encoding="utf-8")
        print(f"Timeline written to {out_path}", file=sys.stderr)
        return

    # Default: generate both
    timeline = generate_timeline(kb_dir)
    events = generate_events(kb_dir)

    (out_dir / "timeline.md").write_text(timeline, encoding="utf-8")
    (out_dir / "events.json").write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"Generated: {len(events)} events, timeline with {len(timeline.splitlines())} lines → {out_dir}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
