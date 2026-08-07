"""Regression tests for validate.py — decision provenance guard, intent inventory gate."""

import json
import os
import sys
import tempfile
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / "kodebrain" / "skill" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from validate import run_validation, check_provenance_consistency
from intent_inventory import scan_intent_sources, apply_resolution, _non_negotiable_principles

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "brownfield"


# ── helpers ──────────────────────────────────────────────────────────────

def _make_kb(graph_dir: Path, nodes: list[dict], edges=None, intent_sources=None):
    """Scaffold a minimal KB for validator testing."""
    kb_project_dir = graph_dir.parent
    graph_dir.mkdir(parents=True, exist_ok=True)

    # Write project hub page (required artifact)
    (kb_project_dir / "test.md").write_text(
        "---\nid: test\ntype: project\nname: Test Project\nstatus: active\n"
        "confidence: supported\nprovenance: project_document\nknowledge_role: mixed\n"
        "project: test\n---\n\n# Test Project\n\nPurpose: testing.\n")

    (graph_dir / "nodes.json").write_text(json.dumps(nodes))
    (graph_dir / "edges.json").write_text(json.dumps(edges or []))
    (graph_dir / "diagnostics.json").write_text(json.dumps({}))
    (graph_dir / "file-index.json").write_text("{}")
    (graph_dir / "file-hashes.json").write_text("{}")
    (kb_project_dir / "reports").mkdir(parents=True, exist_ok=True)
    (kb_project_dir / "domains").mkdir(parents=True, exist_ok=True)
    domain_dir = kb_project_dir / "domains" / "test"
    domain_dir.mkdir(parents=True, exist_ok=True)
    (domain_dir / "test.md").write_text(
        "---\nid: test-domain\ntype: domain\nname: Test Domain\nstatus: active\n"
        "confidence: supported\nprovenance: project_document\nknowledge_role: mixed\n"
        "project: test\ndomain: test\n---\n\n# Test Domain\n\nTest domain hub.\n")
    if intent_sources is not None:
        (graph_dir / "intent-sources.json").write_text(json.dumps(intent_sources))


def _kb_dir(tmpdir: Path) -> Path:
    return tmpdir / "docs" / "brain" / "projects" / "test"


# ── Decision provenance tests ────────────────────────────────────────────

def test_decision_source_code_is_error():
    """type=decision + provenance=source_code must produce ERROR."""
    findings = check_provenance_consistency(
        Path("."),
        [{"id": "d1", "type": "decision", "provenance": "source_code",
          "confidence": "supported", "knowledge_role": "mixed", "source_files": []}]
    )
    errors = [f for f in findings if f["rule"] == "invalid-decision-provenance"]
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"
    assert errors[0]["severity"] == "ERROR"


def test_decision_project_document_is_valid():
    """type=decision + provenance=project_document should pass."""
    findings = check_provenance_consistency(
        Path("."),
        [{"id": "d2", "type": "decision", "provenance": "project_document",
          "confidence": "supported", "knowledge_role": "intent", "source_files": []}]
    )
    errors = [f for f in findings if f["rule"] == "invalid-decision-provenance"]
    assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"


def test_concept_source_code_is_valid():
    """type=concept + provenance=source_code should pass (observed architecture)."""
    findings = check_provenance_consistency(
        Path("."),
        [{"id": "c1", "type": "concept", "provenance": "source_code",
          "confidence": "supported", "knowledge_role": "observed", "source_files": ["src/foo.ts"]}]
    )
    errors = [f for f in findings if f["rule"] == "invalid-decision-provenance"]
    assert len(errors) == 0, f"Observed concept should not trigger decision guard: got {len(errors)} errors"


# ── Intent inventory gate tests (actual validate.py) ─────────────────────

def test_intent_inventory_missing_produces_review():
    """validate.py emits REVIEW when intent-sources.json is missing."""
    with tempfile.TemporaryDirectory() as td:
        kb = _kb_dir(Path(td))
        _make_kb(kb / "graph", [])

        result = run_validation(kb, Path(td))
        intent_findings = [f for f in result.get("findings", [])
                           if f.get("check") == "intent-inventory-gate"]
        assert len(intent_findings) >= 1, f"Expected >=1 intent finding, got {len(intent_findings)}"
        assert intent_findings[0]["severity"] == "REVIEW"
        assert intent_findings[0]["rule"] == "intent-inventory-missing"


def test_intent_pending_produces_blocking():
    """validate.py emits BLOCKING_INCOMPLETE when pending_resolution > 0."""
    with tempfile.TemporaryDirectory() as td:
        kb = _kb_dir(Path(td))
        _make_kb(kb / "graph", [], intent_sources={
            "discovered": 2,
            "confirmed": 0,
            "draft_or_unknown": 2,
            "pending_resolution": 2,
            "accepted": 0,
            "pending_confirmation": True,
            "sources": [
                {"path": "docs/specs/product.md", "kind": "specification",
                 "status": "draft", "authority": "high",
                 "resolution": {"state": "pending", "provenance": None, "resolved_at": None}},
                {"path": "docs/adr/001.md", "kind": "adr",
                 "status": "draft", "authority": "high",
                 "resolution": {"state": "pending", "provenance": None, "resolved_at": None}},
            ]
        })

        result = run_validation(kb, Path(td))
        intent_findings = [f for f in result.get("findings", [])
                           if f.get("check") == "intent-inventory-gate"]
        blocking = [f for f in intent_findings if f["severity"] == "BLOCKING_INCOMPLETE"]
        assert len(blocking) == 1, f"Expected 1 BLOCKING, got {len(blocking)}"
        assert result["completion_state"] == "blocked", \
            f"Expected blocked, got {result['completion_state']}"


def test_intent_all_resolved_produces_clean():
    """validate.py emits no BLOCKING when all intent resolved."""
    with tempfile.TemporaryDirectory() as td:
        kb = _kb_dir(Path(td))
        _make_kb(kb / "graph", [], intent_sources={
            "discovered": 1,
            "confirmed": 0,
            "draft_or_unknown": 0,
            "pending_resolution": 0,
            "accepted": 1,
            "pending_confirmation": False,
            "sources": [
                {"path": "docs/specs/product.md", "kind": "specification",
                 "status": "draft", "authority": "high",
                 "resolution": {"state": "accepted", "provenance": "human",
                                "resolved_at": "2026-08-07T00:00:00Z"}},
            ]
        })

        result = run_validation(kb, Path(td))
        intent_findings = [f for f in result.get("findings", [])
                           if f.get("check") == "intent-inventory-gate"]
        blocking = [f for f in intent_findings if f["severity"] == "BLOCKING_INCOMPLETE"]
        assert len(blocking) == 0, f"Expected 0 BLOCKING, got {len(blocking)}"
        # completion_state should NOT be blocked (may be needs_review from other checks)
        assert result["completion_state"] != "blocked", \
            f"Expected non-blocked, got {result['completion_state']}"


# ── Intent inventory resolution persistence ──────────────────────────────

def test_resolution_persists_across_rescan():
    """apply_resolution survives re-scan when file unchanged."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Create fixture
        (root / "docs" / "specs").mkdir(parents=True)
        (root / "docs" / "specs" / "product.md").write_text(
            "---\nstatus: draft\n---\n\n**Status:** DRAFT v0.1\n\n# Product\n\nA counter API.\n\n## Non-Negotiable\n- Atomic\n"
        )

        kb = root / "docs" / "brain" / "projects" / "test"
        (kb / "graph").mkdir(parents=True)

        # First scan
        result1 = scan_intent_sources(root, kb)
        assert result1["pending_confirmation"] is True
        assert result1["discovered"] >= 1

        # Write to KB
        (kb / "graph" / "intent-sources.json").write_text(
            json.dumps(result1, indent=2))

        # Apply resolution
        apply_resolution(kb, "docs/specs/product.md", "accepted")

        # Re-scan — resolution preserved
        result2 = scan_intent_sources(root, kb)
        spec = [s for s in result2["sources"] if "product.md" in s["path"]][0]
        assert spec["resolution"]["state"] == "accepted", \
            f"Resolution not preserved: {spec['resolution']}"
        assert result2["accepted"] == 1
        assert result2["pending_resolution"] == 0


# ── Resolution state machine tests ────────────────────────────────────────

def test_current_document_auto_accepted_not_pending():
    """status=current → resolution=accepted, not counted as pending."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs" / "architecture").mkdir(parents=True)
        (root / "docs" / "architecture" / "overview.md").write_text(
            "---\nstatus: current\n---\n\n**Status:** CURRENT\n\n# Architecture\n\nOverview.\n"
        )

        result = scan_intent_sources(root)
        arch = [s for s in result["sources"] if "architecture" in s["path"]][0]
        assert arch["resolution"]["state"] == "accepted", \
            f"Expected auto-accepted, got {arch['resolution']['state']}"
        assert arch["resolution"]["provenance"] == "project_document"
        assert result["pending_resolution"] == 0
        assert result["pending_confirmation"] is False


def test_historical_document_auto_rejected_not_pending():
    """status=historical → resolution=rejected, not counted as pending."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs" / "adr").mkdir(parents=True)
        (root / "docs" / "adr" / "001-old.md").write_text(
            "---\nstatus: historical\n---\n\n**Status:** HISTORICAL\n\n# ADR 001\n\nSuperseded.\n"
        )

        result = scan_intent_sources(root)
        adr = [s for s in result["sources"] if "001-old" in s["path"]][0]
        assert adr["resolution"]["state"] == "rejected", \
            f"Expected auto-rejected, got {adr['resolution']['state']}"
        assert result["pending_resolution"] == 0


def test_draft_document_pending_blocks():
    """status=draft → resolution=pending → validator blocked."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs" / "specs").mkdir(parents=True)
        (root / "docs" / "specs" / "product.md").write_text(
            "---\nstatus: draft\n---\n\n**Status:** DRAFT v0.1\n\n# Product\n\nA spec.\n"
        )

        result = scan_intent_sources(root)
        spec = [s for s in result["sources"] if "product" in s["path"]][0]
        assert spec["resolution"]["state"] == "pending"
        assert result["pending_resolution"] >= 1
        assert result["pending_confirmation"] is True


def test_deferred_still_blocks():
    """resolution=deferred → still counts as pending_resolution, validator blocked."""
    with tempfile.TemporaryDirectory() as td:
        kb = _kb_dir(Path(td))
        _make_kb(kb / "graph", [], intent_sources={
            "discovered": 1, "pending_resolution": 1, "accepted": 0,
            "pending_confirmation": True,
            "document_status": {"draft": 1, "current": 0, "historical": 0, "unknown": 0},
            "resolution": {"accepted": 0, "partial": 0, "rejected": 0, "pending": 0, "deferred": 1},
            "sources": [{
                "path": "docs/specs/product.md", "kind": "specification",
                "status": "draft", "authority": "high",
                "resolution": {"state": "deferred", "provenance": "human",
                               "resolved_at": "2026-08-07T00:00:00Z"}
            }]
        })

        result = run_validation(kb, Path(td))
        intent_findings = [f for f in result["findings"]
                           if f.get("check") == "intent-inventory-gate"]
        blocking = [f for f in intent_findings if f["severity"] == "BLOCKING_INCOMPLETE"]
        assert len(blocking) >= 1, f"deferred should block, got {len(blocking)} blocking"
        assert result["completion_state"] == "blocked"


def test_partial_without_note_blocks():
    """resolution=partial without note → still unresolved, validator blocked."""
    with tempfile.TemporaryDirectory() as td:
        kb = _kb_dir(Path(td))
        _make_kb(kb / "graph", [], intent_sources={
            "discovered": 1, "pending_resolution": 1, "accepted": 0,
            "pending_confirmation": True,
            "document_status": {"draft": 1, "current": 0, "historical": 0, "unknown": 0},
            "resolution": {"accepted": 0, "partial": 1, "rejected": 0, "pending": 0, "deferred": 0},
            "sources": [{
                "path": "docs/specs/product.md", "kind": "specification",
                "status": "draft", "authority": "high",
                "resolution": {"state": "partial", "provenance": "human",
                               "resolved_at": "2026-08-07T00:00:00Z"}
            }]
        })

        result = run_validation(kb, Path(td))
        intent_findings = [f for f in result["findings"]
                           if f.get("check") == "intent-inventory-gate"]
        blocking = [f for f in intent_findings if f["severity"] == "BLOCKING_INCOMPLETE"]
        assert len(blocking) >= 1, f"partial-without-note should block, got {len(blocking)}"


def test_partial_with_note_is_resolved():
    """resolution=partial + note → resolved, no blocking."""
    with tempfile.TemporaryDirectory() as td:
        kb = _kb_dir(Path(td))
        _make_kb(kb / "graph", [], intent_sources={
            "discovered": 1, "pending_resolution": 0, "accepted": 0,
            "pending_confirmation": False,
            "document_status": {"draft": 1, "current": 0, "historical": 0, "unknown": 0},
            "resolution": {"accepted": 0, "partial": 1, "rejected": 0, "pending": 0, "deferred": 0},
            "sources": [{
                "path": "docs/specs/product.md", "kind": "specification",
                "status": "draft", "authority": "high",
                "resolution": {"state": "partial", "provenance": "human",
                               "resolved_at": "2026-08-07T00:00:00Z",
                               "note": "Sections 1-3 current; voice section superseded"}
            }]
        })

        result = run_validation(kb, Path(td))
        intent_findings = [f for f in result["findings"]
                           if f.get("check") == "intent-inventory-gate"]
        blocking = [f for f in intent_findings if f["severity"] == "BLOCKING_INCOMPLETE"]
        assert len(blocking) == 0, f"partial-with-note should not block, got {len(blocking)}"
        assert result["completion_state"] != "blocked"


# ── Gate 2: Intent ↔ Observed comparison ─────────────────────────────────

def test_fixture_has_contradiction():
    """Brownfield fixture: spec says 'atomic', source says 'NOT atomic'. Drift detectable."""
    spec_path = FIXTURE / "docs" / "specs" / "product.md"
    src_path = FIXTURE / "src" / "index.ts"

    spec_text = spec_path.read_text()
    src_text = src_path.read_text()

    # Extract claims from spec
    principles = _non_negotiable_principles(spec_text)
    assert len(principles) > 0, f"No principles extracted from spec"

    # Check: "atomic" claim
    atomic_claim = [p for p in principles if "atomic" in p.lower()]
    assert len(atomic_claim) > 0, "Spec should claim atomic increment"

    # Check: source contradicts "atomic"
    assert "NOT atomic" in src_text, "Fixture source should explicitly contradict spec"
    assert "// Note: implementation is NOT atomic" in src_text

    # Drift would be: intent="atomic", observed="NOT atomic"
    # This proves the fixture is valid for Gate 2 semantic comparison.

def test_spec_claims_extracted_correctly():
    """Non-negotiable principles from the fixture spec include all 3 claims."""
    spec_text = (FIXTURE / "docs" / "specs" / "product.md").read_text()
    principles = _non_negotiable_principles(spec_text)

    # 3 principles: counters start at 0, atomic, max 999999
    assert len(principles) >= 2, f"Expected >=2 principles, got {len(principles)}: {principles}"
    has_atomic = any("atomic" in p.lower() for p in principles)
    has_counter = any("counter" in p.lower() or "start" in p.lower() for p in principles)
    assert has_atomic, f"Should find 'atomic' claim: {principles}"
    assert has_counter, f"Should find counter claim: {principles}"


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_decision_source_code_is_error,
        test_decision_project_document_is_valid,
        test_concept_source_code_is_valid,
        test_intent_inventory_missing_produces_review,
        test_intent_pending_produces_blocking,
        test_intent_all_resolved_produces_clean,
        test_resolution_persists_across_rescan,
        test_current_document_auto_accepted_not_pending,
        test_historical_document_auto_rejected_not_pending,
        test_draft_document_pending_blocks,
        test_deferred_still_blocks,
        test_partial_without_note_blocks,
        test_partial_with_note_is_resolved,
        test_fixture_has_contradiction,
        test_spec_claims_extracted_correctly,
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
            import traceback; traceback.print_exc()
            failed += 1

    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
