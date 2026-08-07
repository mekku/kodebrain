#!/usr/bin/env python3
"""
kodebrain timeline — generated project timeline from history records.

Reads decisions/, changes/completed/, incidents/, and milestones/ from
docs/brain/projects/<name>/ and produces a chronological timeline in
history/timeline.md.

Records are source of truth. Timeline is a generated view — never edited.

Usage:
  python3 timeline.py <kb_project_dir>                      # generate timeline
  python3 timeline.py <kb_project_dir> --output timeline.md # write to file
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
    """Extract the first # Heading from markdown body."""
    m = _FRONTMATTER_RE.match(text)
    body = text[m.end():] if m else text
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Untitled"


# ── Record collection ─────────────────────────────────────────────────────────

def _collect_records(kb_dir: Path) -> list[dict[str, Any]]:
    """
    Collect all history records with their dates and types.
    Returns list of {date, type, title, id, path}.
    """
    records: list[dict[str, Any]] = []

    # Directories to scan
    scan_dirs: dict[str, str] = {
        "decisions": "Decision",
        "changes/completed": "Change",
        "incidents": "Incident",
        "milestones": "Milestone",
    }

    for rel_dir, record_type in scan_dirs.items():
        scan_path = kb_dir / rel_dir
        if not scan_path.is_dir():
            continue

        for md in sorted(scan_path.rglob("*.md")):
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            fm = _parse_frontmatter(text)
            title = _parse_title(text)
            record_id = fm.get("id", md.stem)

            # Determine date
            date_str = (
                fm.get("date")
                or fm.get("started_at")
                or fm.get("completed_at")
                or fm.get("last_updated")
                or ""
            )

            # Extract date prefix from ID (YYYY-MM-DD-...)
            if not date_str and "-" in md.stem:
                parts = md.stem.split("-", 3)
                if len(parts) >= 3 and parts[0].isdigit():
                    date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"

            # Categorize: decision_state for decisions, severity for incidents
            subtype = ""
            if record_type == "Decision":
                subtype = fm.get("decision_state", "")
            elif record_type == "Incident":
                subtype = fm.get("severity", "")

            records.append({
                "date": date_str,
                "type": record_type,
                "title": title,
                "id": record_id,
                "subtype": subtype,
                "path": str(md.relative_to(kb_dir)),
            })

    # Sort by date, descending
    records.sort(key=lambda r: r["date"], reverse=True)

    return records


# ── Timeline generation ───────────────────────────────────────────────────────

def generate_timeline(kb_dir: Path) -> str:
    """
    Generate history/timeline.md from all history records.

    Returns the Markdown content.
    """
    records = _collect_records(kb_dir)

    # Group by year, then month
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

    # Build output
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
            "July", "August", "September", "October", "November", "December",
            "",
        ]:
            if month_name not in months:
                continue
            month_records = months[month_name]

            lines.append(f"### {month_name}")
            lines.append("")

            for r in month_records:
                date_display = r["date"] if r["date"] else "????-??-??"
                type_icon = {
                    "Decision": "🔷",
                    "Change": "🔧",
                    "Incident": "⚠️",
                    "Milestone": "🏁",
                }.get(r["type"], "•")

                subtype_note = ""
                if r["subtype"]:
                    subtype_note = f" — *{r['subtype']}*"

                lines.append(
                    f"{date_display} — {type_icon} **{r['type']}**{subtype_note}"
                )
                lines.append(f"{r['title']}")
                lines.append(f"[[{r['id']}|→ Read]]")
                lines.append("")

    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain timeline — generate project timeline from history records",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "kb_dir",
        help="Path to docs/brain/projects/<name>/ directory",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write to file (default: stdout)",
    )
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir).resolve()
    if not kb_dir.is_dir():
        print(f"Error: {kb_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    content = generate_timeline(kb_dir)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"Timeline written to {args.output}", file=sys.stderr)
    else:
        print(content)


if __name__ == "__main__":
    main()
