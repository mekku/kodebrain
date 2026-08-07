"""Regression tests for intent_inventory.py — brownfield intent discovery."""

import json
import os
import sys
from pathlib import Path

# Ensure the kodebrain skill scripts are importable
SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / "kodebrain" / "skill" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from intent_inventory import scan_intent_sources


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "brownfield"


def test_discovers_specification():
    """Brownfield fixture: docs/specs/product.md should be discovered as a specification."""
    result = scan_intent_sources(FIXTURE)
    sources = result["sources"]

    product_specs = [s for s in sources if "product.md" in s["path"]]
    assert len(product_specs) == 1, f"Expected 1 product.md, got {len(product_specs)}"

    spec = product_specs[0]
    assert spec["kind"] == "specification", f"kind: expected specification, got {spec['kind']}"
    assert spec["status"] == "draft", f"status: expected draft, got {spec['status']}"
    assert spec["requires_confirmation"] is True, (
        f"requires_confirmation: expected True, got {spec['requires_confirmation']}"
    )
    assert spec["authority"] == "high", f"authority: expected high, got {spec['authority']}"


def test_pending_confirmation_gate():
    """When a draft spec exists, pending_confirmation must be True."""
    result = scan_intent_sources(FIXTURE)
    assert result["pending_confirmation"] is True, (
        f"pending_confirmation must be True when draft specs exist"
    )
    assert result["draft_or_unknown"] >= 1, (
        f"draft_or_unknown must be >= 1, got {result['draft_or_unknown']}"
    )
    assert result["confirmed"] < result["discovered"], (
        "confirmed count must be less than discovered when drafts exist"
    )


def test_does_not_discover_source_files():
    """src/index.ts is source code, not an intent document — should not appear."""
    result = scan_intent_sources(FIXTURE)
    sources = result["sources"]
    src_files = [s for s in sources if "src/" in s["path"]]
    assert len(src_files) == 0, f"Source files should NOT be intent sources: {src_files}"


def test_onboard_cannot_silently_complete():
    """The onboard gate: pending_confirmation=True means cannot declare complete.

    This test encodes the regression case from external dogfood:
    If intent docs exist but aren't confirmed, onboard must NOT silently
    treat source as canonical truth.
    """
    result = scan_intent_sources(FIXTURE)

    # Simulate the onboard gate logic
    if result["pending_confirmation"]:
        can_declare_complete = False
    else:
        can_declare_complete = True

    assert can_declare_complete is False, (
        "ONBOARD GATE FAILED: pending_confirmation=True but would have silently "
        "declared complete. Intent doc exists (docs/specs/product.md, status=draft) "
        "and source code differs from spec — treating source as canonical without "
        "human confirmation would hide the drift."
    )


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_discovers_specification,
        test_pending_confirmation_gate,
        test_does_not_discover_source_files,
        test_onboard_cannot_silently_complete,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test.__name__}: {e}")
            failed += 1

    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
