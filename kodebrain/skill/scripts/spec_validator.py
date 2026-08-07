#!/usr/bin/env python3
"""
kodebrain spec-validator — deterministic specification authority checker.

Scans docs/ for spec_role frontmatter and validates structural rules:
  - every canonical spec declares a parent (unless root)
  - parent-chain reachability to root (no broken links, no cycles)
  - no concern has multiple canonical owners (owns[] list)
  - deprecated/superseded specs identify their replacement
  - implementation plans reference the canonical spec they implement

Uses the shared frontmatter.py parser (single parser for whole system).

Usage:
  python3 spec_validator.py <docs_dir>                # validate
  python3 spec_validator.py <docs_dir> --strict       # exit 1 on warnings
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from frontmatter import parse as _parse_frontmatter

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
        "reachability": {spec_id: reachable_to_root},
        "cycles": [spec_ids],
      }
    """
    errors: list[dict] = []
    warnings: list[dict] = []
    docs_with_role: list[tuple[str, dict]] = []

    # Collect all .md files with spec_role frontmatter
    for md in sorted(docs_dir.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, _ = _parse_frontmatter(text)
        if "spec_role" in fm:
            docs_with_role.append((str(md.relative_to(docs_dir)), fm))

    _canonical_roles = {"canonical", "canonical-root"}

    # ── Build spec index ─────────────────────────────────────────────────────
    spec_index: dict[str, dict] = {}  # spec_id → {path, fm, role, parent, owns}
    duplicate_spec_ids: list[tuple[str, str, str]] = []  # [(spec_id, path1, path2)]
    for path, fm in docs_with_role:
        sid = fm.get("spec_id", "")
        if sid:
            if sid in spec_index:
                duplicate_spec_ids.append((sid, spec_index[sid]["path"], path))
                continue

            # Parse owns as list (shared parser handles multi-line YAML)
            owns_raw = fm.get("owns", [])
            owns: list[str] = []
            if isinstance(owns_raw, list):
                owns = owns_raw
            elif isinstance(owns_raw, str) and owns_raw:
                owns = [o.strip() for o in owns_raw.split(",") if o.strip()]

            spec_index[sid] = {
                "path": path,
                "role": fm.get("spec_role", ""),
                "parent": fm.get("parent", ""),
                "owns": owns,
            }

    # Report duplicate spec_ids
    for sid, path1, path2 in duplicate_spec_ids:
        errors.append({
            "rule": "duplicate-spec-id",
            "doc": f"{path1}, {path2}",
            "detail": f"spec_id '{sid}' declared in multiple documents.",
        })

    # ── Rule: canonical root must exist ──────────────────────────────────────
    canonical = {
        sid: info for sid, info in spec_index.items()
        if info["role"] in _canonical_roles
    }

    roots = [sid for sid, info in canonical.items() if sid == "root"]
    if not roots:
        warnings.append({
            "rule": "root-required",
            "doc": "-",
            "detail": "No document with spec_id: root found. Add one.",
        })
    elif len(roots) > 1:
        errors.append({
            "rule": "single-root",
            "doc": ", ".join(spec_index[r]["path"] for r in roots),
            "detail": "Multiple spec_id: root found. Exactly one required.",
        })

    # ── Rule: canonical docs must declare parent (unless root) ───────────────
    for sid, info in canonical.items():
        if sid == "root":
            continue
        if not info["parent"]:
            warnings.append({
                "rule": "parent-required",
                "doc": info["path"],
                "detail": f"Canonical spec '{sid}' has no parent. Add parent: <parent-id>.",
            })

    # ── Rule: parent-chain reachability to root ──────────────────────────────
    reachability: dict[str, str] = {}  # spec_id → "root" | "broken:<id>" | "cycle"
    cycles: list[list[str]] = []

    def _trace_to_root(sid: str, visited: list[str]) -> str:
        if sid in visited:
            cycles.append(visited + [sid])
            return f"cycle:{sid}"
        if sid not in spec_index:
            return f"broken:{sid}"
        info = spec_index[sid]
        parent = info["parent"]
        if not parent:
            if info["role"] in _canonical_roles and sid != "root":
                return "no-parent"
            return "root" if sid == "root" else "no-parent"
        if parent not in spec_index:
            return f"broken:{parent}"
        parent_info = spec_index[parent]
        if parent_info["role"] not in _canonical_roles:
            warnings.append({
                "rule": "parent-not-canonical",
                "doc": info["path"],
                "detail": f"Parent '{parent}' is not canonical (role: {parent_info['role']}).",
            })
        return _trace_to_root(parent, visited + [sid])

    for sid in canonical:
        reachability[sid] = _trace_to_root(sid, [])

    broken = {sid: r for sid, r in reachability.items() if r != "root"}
    for sid, reason in broken.items():
        if reason.startswith("broken:"):
            missing = reason.split(":", 1)[1]
            errors.append({
                "rule": "parent-chain-broken",
                "doc": spec_index[sid]["path"],
                "detail": f"Parent '{spec_index[sid]['parent']}' not found (looking for '{missing}').",
            })
        elif reason.startswith("cycle:"):
            errors.append({
                "rule": "parent-chain-cycle",
                "doc": spec_index[sid]["path"],
                "detail": f"Parent chain contains cycle: {' → '.join(reason.split(':', 1)[1].split(','))}",
            })
        elif reason == "no-parent":
            # Already warned above as parent-required
            pass

    if cycles:
        warnings.append({
            "rule": "cycles-detected",
            "doc": ", ".join(spec_index.get(c[0], {}).get("path", c[0]) for c in cycles if c),
            "detail": f"{len(cycles)} cycle(s) in spec parent chain.",
        })

    # ── Rule: no duplicate canonical owners for the same concern ─────────────
    concern_owners: dict[str, list[str]] = {}  # concern → [spec_id]
    for sid, info in canonical.items():
        for concern in info["owns"]:
            concern_owners.setdefault(concern, []).append(sid)

    duplicates = {c: owners for c, owners in concern_owners.items() if len(owners) > 1}
    for concern, owners in duplicates.items():
        errors.append({
            "rule": "duplicate-owner",
            "doc": ", ".join(spec_index[o]["path"] for o in owners),
            "detail": f"Concern '{concern}' owned by {len(owners)} canonical specs. Exactly one required.",
        })

    # ── Rule: deprecated/superseded specs identify valid replacement ──────────
    for path, fm in docs_with_role:
        role = fm.get("spec_role", "")
        if role in ("historical", "superseded", "deprecated"):
            replaced_by = fm.get("superseded_by", "")
            if not replaced_by:
                warnings.append({
                    "rule": "superseded-no-replacement",
                    "doc": path,
                    "detail": f"Spec with role '{role}' does not declare superseded_by.",
                })
            else:
                # Verify target exists and is canonical
                target_path = docs_dir / replaced_by
                if target_path.exists():
                    # File exists — check its role
                    try:
                        target_text = target_path.read_text(encoding="utf-8", errors="replace")
                        target_fm, _ = _parse_frontmatter(target_text)
                        target_role = target_fm.get("spec_role", "")
                        if target_role not in _canonical_roles:
                            warnings.append({
                                "rule": "superseded-target-not-canonical",
                                "doc": path,
                                "detail": f"superseded_by target '{replaced_by}' is not canonical (role: {target_role}).",
                            })
                    except OSError:
                        pass
                else:
                    # Try as spec_id lookup
                    target_spec = spec_index.get(replaced_by)
                    if not target_spec:
                        warnings.append({
                            "rule": "superseded-target-missing",
                            "doc": path,
                            "detail": f"superseded_by target '{replaced_by}' not found as file or spec_id.",
                        })
                    elif target_spec["role"] not in _canonical_roles:
                        warnings.append({
                            "rule": "superseded-target-not-canonical",
                            "doc": path,
                            "detail": f"superseded_by target '{replaced_by}' exists but is not canonical (role: {target_spec['role']}).",
                        })

    # ── Rule: implementation plans reference canonical spec ───────────────────
    for path, fm in docs_with_role:
        role = fm.get("spec_role", "")
        if role == "implementation-plan":
            implements = fm.get("implements", "")
            if isinstance(implements, list):
                implements_list = implements
            elif isinstance(implements, str) and implements:
                implements_list = [i.strip() for i in implements.split(",") if i.strip()]
            else:
                implements_list = []
            if not implements_list:
                warnings.append({
                    "rule": "plan-no-reference",
                    "doc": path,
                    "detail": "Implementation plan does not declare which canonical spec it implements.",
                })
            else:
                # Verify each referenced spec exists AND is canonical
                for ref in implements_list:
                    ref_path = docs_dir / ref
                    if not ref_path.exists():
                        warnings.append({
                            "rule": "plan-reference-missing",
                            "doc": path,
                            "detail": f"Referenced spec '{ref}' not found at expected path.",
                        })
                        continue
                    # Verify target is canonical
                    try:
                        ref_text = ref_path.read_text(encoding="utf-8", errors="replace")
                        ref_fm, _ = _parse_frontmatter(ref_text)
                        ref_role = ref_fm.get("spec_role", "")
                        if ref_role not in _canonical_roles:
                            warnings.append({
                                "rule": "plan-reference-not-canonical",
                                "doc": path,
                                "detail": f"Referenced spec '{ref}' is not canonical (role: {ref_role}). Plans should reference canonical specs.",
                            })
                    except OSError:
                        pass

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "canonical_docs": [info["path"] for info in canonical.values()],
        "reachability": reachability,
        "cycles": [c for c in cycles],
        "duplicate_owners": [
            {"concern": c, "owners": [spec_index[o]["path"] for o in owners]}
            for c, owners in duplicates.items()
        ],
    }


def _format_report(result: dict) -> str:
    lines: list[str] = []
    lines.append("# Spec Authority Validation Report")
    lines.append("")

    if result["valid"] and not result["warnings"]:
        lines.append("**Result: PASS** — 0 errors, 0 warnings.")
    elif result["valid"]:
        lines.append(f"**Result: PASS with {len(result['warnings'])} warning(s)**")
    else:
        lines.append(f"**Result: FAIL** — {len(result['errors'])} error(s), {len(result['warnings'])} warning(s)")
    lines.append("")

    lines.append(f"Canonical specs: {len(result['canonical_docs'])}")
    lines.append(f"Reachability: {sum(1 for v in result['reachability'].values() if v == 'root')}/{len(result['reachability'])} reach root")
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
            lines.append(f"- **{d['concern']}**: {', '.join(d['owners'])}")
        lines.append("")

    if result["cycles"]:
        lines.append("## Cycles")
        for c in result["cycles"]:
            lines.append(f"- {' → '.join(c)}")
        lines.append("")

    unreachable = {sid: r for sid, r in result["reachability"].items() if r != "root"}
    if unreachable:
        lines.append("## Unreachable Specs")
        for sid, reason in unreachable.items():
            lines.append(f"- **{sid}**: {reason}")
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
        # Convert non-serializable types
        output = {k: v for k, v in result.items()}
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    else:
        print(_format_report(result))

    if args.strict and (result["errors"] or result["warnings"]):
        sys.exit(1)
    elif not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
