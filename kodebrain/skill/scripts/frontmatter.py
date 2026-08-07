"""
Shared YAML frontmatter parser for all Kode Brain compilers.

Single source of truth for Markdown frontmatter parsing. All compilers
(compile_graph, timeline, migrate_kb, project_state) must use this module.

Supports:
  - Simple key: value pairs
  - Multi-line YAML lists (items prefixed with -)
  - Quoted and unquoted string values
  - null values
  - Nested structures not required for current schema

Usage:
  from frontmatter import parse, serialize
  fm, body = parse(text)
  text = serialize(fm) + body
"""

from __future__ import annotations

import re
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_yaml_list(lines: list[str], start_idx: int) -> tuple[list[str], int]:
    """Parse YAML list items from lines starting at start_idx. Returns (items, next_index)."""
    items: list[str] = []
    i = start_idx
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("- "):
            val = stripped[2:].strip()
            # Remove surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            items.append(val)
            i += 1
        elif stripped == "" or stripped.startswith("#"):
            i += 1
        elif ":" in stripped and not stripped.startswith(" "):
            # Next top-level key — end of this list
            break
        else:
            i += 1
    return items, i


def parse(text: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from Markdown text.

    Returns (frontmatter_dict, body_without_frontmatter).

    Handles:
      - Simple key: value
      - Multi-line lists (items starting with -)
      - Quoted strings
      - null
    """
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
            value = value.strip()

            # Remove surrounding quotes
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            if value == "" or value == "[]":
                # Check if next line starts a YAML list
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("- "):
                    items, i = _parse_yaml_list(lines, i + 1)
                    fm[key] = items
                    continue  # i now points at next top-level key — process it
                else:
                    fm[key] = [] if value == "[]" else ""
            elif value == "null":
                fm[key] = None
            else:
                fm[key] = value

        i += 1

    return fm, body


def parse_simple(text: str) -> dict[str, Any]:
    """Parse frontmatter without list support (for simple single-value fields). Returns dict only."""
    fm, _ = parse(text)
    return fm


def serialize(fm: dict[str, Any]) -> str:
    """
    Serialize frontmatter dict back to YAML string with --- delimiters.

    Priority fields come first: id, type, status, confidence, provenance, knowledge_role.
    """
    lines = ["---"]
    priority = [
        "id", "type", "status", "confidence", "provenance",
        "knowledge_role", "project", "domain",
        "change_state", "incident_state", "decision_state",
        "severity", "outcome", "date", "started_at", "completed_at",
        "resolved_at", "significance", "supersedes",
    ]
    written: set[str] = set()

    for key in priority:
        if key in fm:
            _write_field(lines, key, fm[key])
            written.add(key)

    for key, val in fm.items():
        if key not in written:
            _write_field(lines, key, val)

    lines.append("---")
    return "\n".join(lines) + "\n"


def _write_field(lines: list[str], key: str, val: Any) -> None:
    """Write a single YAML field to lines list."""
    if isinstance(val, list):
        if not val:
            lines.append(f"{key}: []")
        else:
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
    elif val is None:
        lines.append(f"{key}: null")
    elif isinstance(val, str):
        if val == "":
            lines.append(f'{key}: ""')
        elif " " in val or ":" in val:
            lines.append(f'{key}: "{val}"')
        else:
            lines.append(f"{key}: {val}")
    else:
        lines.append(f"{key}: {val}")
