#!/usr/bin/env python3
"""
kodebrain spec-validator — deterministic specification authority checker.

Scans docs/design/ for spec_role frontmatter and validates structural rules:
  - every canonical spec is reachable from the root
  - no concern has multiple canonical owners
  - deprecated/superseded specs identify their replacement
  - implementation plans reference the canonical spec they implement
  - canonical child pages declare a parent

Does NOT check semantic consistency (that's for LLM review). Only structure.

Usage:
  python3 spec_validator.py <docs_dir>                # validate
  python3 spec_validator.py <docs_dir> --strict       # exit 1 on warnings
"""

from __future__ import annotations

import argparse
import re
import sys
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


# ── Rule checks ───────────────────────────────────────────────────────────────

def validate(docs_dir: Path) -> dict[str, Any]:
    """
    Run all structural spec-authority checks.

    Returns:
      {
        "valid": bool,
        "errors": [{rule, doc, detail}],
        "warnings": [{rule, doc, detail}],
        "canonical_docs": [path],
        "orphaned_canonical": [path],
        "duplicate_owners": [{concern, docs}],
      }
    """
    errors: list[dict] = []
    warnings: list[dict] = []
    canonical_docs: list[str] = []
    docs_with_role: list[tuple[str, dict]] = []

    # Collect all .md files with spec_role frontmatter
    for md in sorted(docs_dir.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        if "spec_role" in fm:
            docs_with_role.append((str(md.relative_to(docs_dir)), fm))

    # ── Rule: every canonical spec must be reachable from root ────────────────
    _canonical_roles = {"canonical", "canonical-root"}
    canonical = [
        (path, fm) for path, fm in docs_with_role
        if fm.get("spec_role") in _canonical_roles
    ]

    # Find root
    roots = [d for d in canonical if d[1].get("spec_id") == "root"]
    if not roots:
        warnings.append({
            "rule": "root-required",
            "doc": "-",
            "detail": "No document with spec_id: root and spec_role: canonical found. Add one.",
        })
    elif len(roots) > 1:
        errors.append({
            "rule": "single-root",
            "doc": ", ".join(r[0] for r in roots),
            "detail": "Multiple canonical roots found. Exactly one is required.",
        })

    # Check that all canonical docs have a parent (unless root)
    for path, fm in canonical:
        spec_id = fm.get("spec_id", path)
        parent = fm.get("parent", "")
        is_root = spec_id == "root"

        if not is_root and not parent:
            warnings.append({
                "rule": "parent-required",
                "doc": path,
                "detail": f"Canonical spec '{spec_id}' has no parent. Add parent: <parent-id>.",
            })

    canonical_docs = [path for path, _ in canonical]

    # ── Rule: no duplicate canonical owners for the same concern ──────────────
    # A "concern" is identified by the 'owns' list
    concern_owners: dict[str, list[str]] = {}
    for path, fm in docs_with_role:
        role = fm.get("spec_role", "")
        if role not in _canonical_roles:
            continue
        concern = fm.get("concern", "")
        if not concern:
            continue
        concern_owners.setdefault(concern, []).append(path)

    duplicates = {c: docs for c, docs in concern_owners.items() if len(docs) > 1}
    if duplicates:
        for concern, docs in duplicates.items():
            errors.append({
                "rule": "single-owner",
                "doc": ", ".join(docs),
                "detail": f"Concern '{concern}' has {len(docs)} canonical owners. Exactly one required.",
            })

    # ── Rule: deprecated/superseded specs identify their replacement ──────────
    for path, fm in docs_with_role:
        role = fm.get("spec_role", "")
        if role in ("historical", "superseded", "deprecated"):
            replaced_by = fm.get("superseded_by", "")
            if not replaced_by:
                warnings.append({
                    "rule": "superseded-no-replacement",
                    "doc": path,
                    "detail": f"Spec with role '{role}' does not declare superseded_by. Add replacement reference.",
                })

    # ── Rule: implementation plans reference the canonical spec ──────────────
    for path, fm in docs_with_role:
        role = fm.get("spec_role", "")
        if role == "implementation-plan":
            implements = fm.get("implements", "")
            if not implements:
                warnings.append({
                    "rule": "plan-no-reference",
                    "doc": path,
                    "detail": "Implementation plan does not declare which canonical spec it implements.",
                })

    # ── Rule: orphaned canonical docs (no other doc references them as parent)─
    all_parents: set[str] = set()
    for _, fm in docs_with_role:
        parent = fm.get("parent", "")
        if parent:
            all_parents.add(parent)

    spec_ids: dict[str, str] = {}
    for path, fm in canonical:
        sid = fm.get("spec_id", "")
        if sid:
            spec_ids[sid] = path

    orphaned = [
        sid for sid, path in spec_ids.items()
        if sid != "root" and sid not in all_parents
    ]
    if orphaned:
        warnings.append({
            "rule": "orphaned-canonical",
            "doc": ", ".join(orphaned),
            "detail": "Canonical specs not referenced as parent by any child. May indicate spec tree gaps.",
        })

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "canonical_docs": canonical_docs,
        "orphaned_canonical": orphaned,
        "duplicate_owners": [
            {"concern": c, "docs": d} for c, d in duplicates.items()
        ],
    }


def _format_report(result: dict) -> str:
    lines: list[str] = []
    lines.append("# Spec Authority Validation Report")
    lines.append("")

    if result["valid"]:
        lines.append("**Result: PASS** — no structural authority errors.")
    else:
        lines.append("**Result: FAIL** — structural authority errors found.")
    lines.append("")

    lines.append(f"Canonical docs: {len(result['canonical_docs'])}")
    lines.append(f"Errors: {len(result['errors'])}")
    lines.append(f"Warnings: {len(result['warnings'])}")
    lines.append("")

    if result["errors"]:
        lines.append("## Errors")
        for e in result["errors"]:
            lines.append(f"- **[{e['rule']}]** {e['doc']}: {e['detail']}")
        lines.append("")

    if result["warnings"]:
        lines.append("## Warnings")
        for w in result["warnings"]:
            lines.append(f"- **[{w['rule']}]** {w['doc']}: {w['detail']}")
        lines.append("")

    if result["duplicate_owners"]:
        lines.append("## Duplicate Concern Owners")
        for d in result["duplicate_owners"]:
            lines.append(f"- **{d['concern']}**: {', '.join(d['docs'])}")
        lines.append("")

    if result["orphaned_canonical"]:
        lines.append("## Orphaned Canonical Specs")
        lines.append(f"No child references these as parent: {', '.join(result['orphaned_canonical'])}")
        lines.append("")

    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain spec-validator — structural spec authority checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("docs_dir", nargs="?", default="docs/design", help="Path to docs directory")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any warnings")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir).resolve()
    if not docs_dir.is_dir():
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = validate(docs_dir)

    if args.json:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print(_format_report(result))

    if args.strict and (result["errors"] or result["warnings"]):
        sys.exit(1)
    elif not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
