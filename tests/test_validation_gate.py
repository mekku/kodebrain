"""Adversarial tests for the onboard validation gate.

Reproduces every dogfood failure from commit aca380f — each test proves
a specific correctness fix. Uses importlib to load validate.py and
compile_graph.py by file path (same pattern as test_substrate.py).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent / "kodebrain" / "skill" / "scripts"
_VALIDATE_PATH = _SCRIPTS_DIR / "validate.py"
_COMPILE_GRAPH_PATH = _SCRIPTS_DIR / "compile_graph.py"
_FRONTMATTER_PATH = _SCRIPTS_DIR / "frontmatter.py"


def _load_script(path: Path):
    scripts_dir = str(path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    name = path.stem
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None, f"cannot find spec for {path}"
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════════════
# Shared frontmatter parser: nested map support
# ═══════════════════════════════════════════════════════════════════════════════

class TestFrontmatterNestedMap:
    """Shared frontmatter parser handles nested YAML maps."""

    def test_parses_canonical_source_as_nested_dict(self) -> None:
        sys.path.insert(0, str(_SCRIPTS_DIR))
        from frontmatter import parse
        fm, body = parse("""---
id: test-page
type: concept
canonical_source:
  path: docs/design/spec/history-model.md
  anchor: decision-lifecycle
knowledge_role: reference
---

# Test Page

Content here.
""")
        assert fm["id"] == "test-page"
        assert isinstance(fm["canonical_source"], dict)
        assert fm["canonical_source"]["path"] == "docs/design/spec/history-model.md"
        assert fm["canonical_source"]["anchor"] == "decision-lifecycle"
        assert fm["knowledge_role"] == "reference"

    def test_nested_map_next_to_scalars(self) -> None:
        sys.path.insert(0, str(_SCRIPTS_DIR))
        from frontmatter import parse
        fm, _ = parse("""---
id: test
type: concept
canonical_source:
  path: foo.md
knowledge_role: reference
status: active
---
""")
        assert fm["canonical_source"] == {"path": "foo.md"}
        assert fm["knowledge_role"] == "reference"
        assert fm["status"] == "active"

    def test_nested_map_roundtrip_serialize(self) -> None:
        sys.path.insert(0, str(_SCRIPTS_DIR))
        from frontmatter import parse, serialize
        original = """---
id: test
canonical_source:
  path: spec/knowledge-model.md
  anchor: provenance
---
"""
        fm, _ = parse(original)
        serialized = serialize(fm)
        assert "canonical_source:" in serialized
        assert "  path:" in serialized or "  path " in serialized


# ═══════════════════════════════════════════════════════════════════════════════
# compile_graph: canonical_source in node output
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompileGraphCanonicalSource:
    """compile_graph preserves canonical_source in node output."""

    def _make_kb(self, tmp_path: Path, pages: list[tuple[str, str]]) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        for rel_path, content in pages:
            full = kb_dir / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return kb_dir

    def test_node_includes_canonical_source(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("concepts/decision-lifecycle.md", """---
id: kb-history-decision-lifecycle
type: concept
status: active
confidence: supported
provenance: generated
knowledge_role: reference
project: test
domain: kb-history
source_files: []
last_updated: "2026-08-07"
tags:
  - type/concept
  - domain/kb-history
canonical_source:
  path: docs/design/spec/history-model.md
  anchor: decision-lifecycle
---

# Decision Lifecycle

## Canonical Definition
See: [docs/design/spec/history-model.md#decision-lifecycle]

## Project Context
This is how decisions work in this project.
"""),
        ])
        result = mod.compile_graph(kb)
        node = result["nodes"][0]
        assert "canonical_source" in node
        assert node["canonical_source"]["path"] == "docs/design/spec/history-model.md"
        assert node["canonical_source"]["anchor"] == "decision-lifecycle"

    def test_node_without_canonical_source_omits_field(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("concepts/normal-page.md", """---
id: normal-page
type: concept
status: active
confidence: supported
provenance: generated
knowledge_role: intent
project: test
domain: test-domain
source_files: []
last_updated: "2026-08-07"
tags:
  - type/concept
  - domain/test-domain
---

# Normal Page

No canonical source here.
"""),
        ])
        result = mod.compile_graph(kb)
        node = result["nodes"][0]
        assert "canonical_source" not in node


# ═══════════════════════════════════════════════════════════════════════════════
# compile_graph: diagnostics for orphan wikilinks
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompileGraphDiagnostics:
    """Compiler emits diagnostics.json for orphan wikilinks."""

    def _make_kb(self, tmp_path: Path, pages: list[tuple[str, str]]) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        for rel_path, content in pages:
            full = kb_dir / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return kb_dir

    def test_orphan_wikilink_produces_diagnostic(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("test.md", """---
id: test
type: project
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Test

## Active Changes
- [[changes/active/2026-08-07-nonexistent|Missing change]]
"""),
        ])
        result = mod.compile_graph(kb)
        assert "diagnostics" in result
        assert len(result["diagnostics"]) >= 1
        diag = result["diagnostics"][0]
        assert diag["type"] == "orphan_wikilink"
        assert diag["target"] == "changes/active/2026-08-07-nonexistent"
        assert diag["source"] == "test"

    def test_valid_wikilink_no_diagnostic(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("test.md", """---
id: test
type: project
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Test

## Domains
- [[auth|Auth]]
"""),
            ("domains/auth/auth.md", """---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: auth
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/auth
  - status/active
---

# Auth
"""),
        ])
        result = mod.compile_graph(kb)
        assert len(result["diagnostics"]) == 0

    def test_orphan_edge_dropped_from_edges(self, tmp_path: Path) -> None:
        """Orphan edges must not appear in edges.json (graph integrity)."""
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("test.md", """---
id: test
type: project
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Test

## Active Changes
- [[ghost|Ghost page]]
"""),
        ])
        result = mod.compile_graph(kb)
        # diagnostics has the orphan
        assert len(result["diagnostics"]) == 1
        # edges must NOT contain the orphan
        orphan_edges = [e for e in result["edges"] if e["to"] == "ghost"]
        assert len(orphan_edges) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Validation: referential integrity via diagnostics + page_path
# ═══════════════════════════════════════════════════════════════════════════════

class TestReferentialIntegrity:
    """Check 1 uses diagnostics + nodes_map[target].page_path."""

    def test_detects_orphan_from_diagnostics(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        (kb_dir / "graph").mkdir(parents=True)
        (kb_dir / "graph" / "nodes.json").write_text(json.dumps([
            {"id": "test", "type": "project", "page_path": "test/test.md"},
        ]))
        (kb_dir / "graph" / "edges.json").write_text("[]")
        (kb_dir / "graph" / "file-index.json").write_text("{}")
        (kb_dir / "graph" / "file-hashes.json").write_text("{}")
        (kb_dir / "graph" / "diagnostics.json").write_text(json.dumps([
            {"type": "orphan_wikilink", "source": "test", "target": "ghost", "edge_type": "references", "section": "Active Changes"},
        ]))
        (kb_dir / "domains").mkdir(parents=True)

        # Create actual page at resolved path (resolve_page_path strips project name)
        (kb_dir / "test.md").write_text("# Test")

        result = mod.run_validation(kb_dir, tmp_path)
        ref_findings = [f for f in result["findings"] if f["check"] == "referential-integrity"]
        assert len(ref_findings) >= 1
        orphan = [f for f in ref_findings if f["target"] == "ghost"]
        assert len(orphan) == 1
        assert orphan[0]["severity"] == "ERROR"

    def test_false_positive_suppressed_by_page_path(self, tmp_path: Path) -> None:
        """When nodes_map[target].page_path exists and file is real, skip the finding."""
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        (kb_dir / "graph").mkdir(parents=True)

        # Create actual target page (resolve_page_path strips project name prefix)
        # resolve_page_path("test/changes/active/2026-08-07-test.md", kb_dir.name="test")
        # → strips "test/" → "changes/active/2026-08-07-test.md" → kb_dir / that
        (kb_dir / "changes" / "active").mkdir(parents=True)
        (kb_dir / "changes" / "active" / "2026-08-07-test.md").write_text("# Test Change")

        (kb_dir / "graph" / "nodes.json").write_text(json.dumps([
            {"id": "test", "type": "project", "page_path": "test/test.md"},
            {"id": "changes/active/2026-08-07-test", "type": "change",
             "page_path": "test/changes/active/2026-08-07-test.md"},
        ]))
        (kb_dir / "graph" / "edges.json").write_text("[]")
        (kb_dir / "graph" / "file-index.json").write_text("{}")
        (kb_dir / "graph" / "file-hashes.json").write_text("{}")
        (kb_dir / "graph" / "diagnostics.json").write_text(json.dumps([
            {"type": "orphan_wikilink", "source": "test", "target": "changes/active/2026-08-07-test", "edge_type": "references", "section": "Active Changes"},
        ]))

        (kb_dir / "test.md").write_text("# Test")
        (kb_dir / "domains").mkdir(parents=True)

        result = mod.run_validation(kb_dir, tmp_path)
        ref_findings = [f for f in result["findings"] if f["check"] == "referential-integrity"]
        assert len(ref_findings) == 0  # page_path resolved — false positive suppressed


# ═══════════════════════════════════════════════════════════════════════════════
# Validation: canonical duplication detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalDuplication:
    """Check 5 detects canonical duplication structurally."""

    def _make_kb_with_spec(self, tmp_path: Path) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        (kb_dir / "graph").mkdir(parents=True)

        # Create canonical spec
        spec_dir = tmp_path / "docs" / "design" / "spec"
        spec_dir.mkdir(parents=True)
        (spec_dir / "history-model.md").write_text("""---
spec_id: history-model
spec_role: canonical
parent: root
---

# History Model

## Decision Lifecycle

| State | Description |
|---|---|
| `active` | Currently in effect |
| `superseded` | Replaced by newer decision |
| `deprecated` | No longer applicable |
""")
        return kb_dir

    def test_intent_page_duplicating_canonical_enums_detected(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = self._make_kb_with_spec(tmp_path)

        # Create intent page that copies lifecycle states without canonical_source
        (kb_dir / "concepts").mkdir(parents=True, exist_ok=True)
        (kb_dir / "concepts" / "decision-lifecycle.md").write_text("""---
id: kb-history-decision-lifecycle
type: concept
status: active
confidence: supported
provenance: generated
knowledge_role: intent
project: test
domain: kb-history
source_files: []
last_updated: "2026-08-07"
tags:
  - type/concept
  - domain/kb-history
---

# Decision Lifecycle

## How It Works

Decisions go through these states:

| State | Description |
|---|---|
| `active` | Currently in effect |
| `superseded` | Replaced by newer decision |
| `deprecated` | No longer applicable |
""")

        (kb_dir / "graph" / "nodes.json").write_text(json.dumps([
            {"id": "kb-history-decision-lifecycle", "type": "concept", "knowledge_role": "intent",
             "page_path": "test/concepts/decision-lifecycle.md"},
        ]))
        (kb_dir / "graph" / "edges.json").write_text("[]")
        (kb_dir / "graph" / "diagnostics.json").write_text("[]")

        result = mod.run_validation(kb_dir, tmp_path)
        can_findings = [f for f in result["findings"] if f["check"] == "canonical-authority"]
        dup_findings = [f for f in can_findings if f.get("rule") == "canonical-duplication"]
        assert len(dup_findings) >= 1

    def test_reference_page_with_canonical_source_no_duplication_error(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = self._make_kb_with_spec(tmp_path)

        # Create reference page with canonical_source — should NOT be flagged
        (kb_dir / "concepts").mkdir(parents=True, exist_ok=True)
        (kb_dir / "concepts" / "decision-lifecycle.md").write_text("""---
id: kb-history-decision-lifecycle
type: concept
status: active
confidence: supported
provenance: generated
knowledge_role: reference
project: test
domain: kb-history
source_files: []
last_updated: "2026-08-07"
tags:
  - type/concept
  - domain/kb-history
canonical_source:
  path: docs/design/spec/history-model.md
  anchor: decision-lifecycle
---

# Decision Lifecycle

## Canonical Definition
See: [docs/design/spec/history-model.md#decision-lifecycle]

## Project Context
Decisions in this project follow the standard lifecycle.
""")

        (kb_dir / "graph" / "nodes.json").write_text(json.dumps([
            {"id": "kb-history-decision-lifecycle", "type": "concept", "knowledge_role": "reference",
             "page_path": "test/concepts/decision-lifecycle.md",
             "canonical_source": {"path": "docs/design/spec/history-model.md", "anchor": "decision-lifecycle"}},
        ]))
        (kb_dir / "graph" / "edges.json").write_text("[]")
        (kb_dir / "graph" / "diagnostics.json").write_text("[]")

        result = mod.run_validation(kb_dir, tmp_path)
        can_findings = [f for f in result["findings"] if f["check"] == "canonical-authority"]
        dup_findings = [f for f in can_findings if f.get("rule") == "canonical-duplication"]
        assert len(dup_findings) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Validation: provenance consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestProvenanceConsistency:
    """Check 3 detects invalid provenance/confidence combinations."""

    def test_human_verified_without_human_evidence(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        (kb_dir / "graph").mkdir(parents=True)

        # Create page without human-note block
        (kb_dir / "test.md").write_text("""---
id: test
type: project
status: active
confidence: verified
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags: []
---

# Test

## Purpose
A test project.
""")

        (kb_dir / "graph" / "nodes.json").write_text(json.dumps([
            {"id": "test", "type": "project", "provenance": "human", "confidence": "verified",
             "knowledge_role": "intent", "source_files": [],
             "page_path": "test/test.md"},
        ]))
        (kb_dir / "graph" / "edges.json").write_text("[]")
        (kb_dir / "graph" / "diagnostics.json").write_text("[]")
        (kb_dir / "domains").mkdir(parents=True)

        result = mod.run_validation(kb_dir, tmp_path)
        prv_findings = [f for f in result["findings"] if f["check"] == "provenance-consistency"]
        invalid = [f for f in prv_findings if f.get("rule") == "invalid-provenance"]
        assert len(invalid) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Validation: render_reports
# ═══════════════════════════════════════════════════════════════════════════════

class TestRenderReports:
    """Reports are derived from validation findings."""

    def test_drift_report_from_findings(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        (kb_dir / "reports").mkdir(parents=True)

        result = {
            "completion_state": "complete_with_drift",
            "summary": {"total_findings": 2, "error_count": 0, "drift_count": 1, "review_count": 1},
            "findings": [
                {"id": "DRF-001", "check": "intent-observed-consistency", "severity": "DRIFT",
                 "rule": "intent-observed-mismatch", "node": "test-page",
                 "description": "Intent page has Runtime Path section"},
                {"id": "REV-001", "check": "provenance-consistency", "severity": "REVIEW",
                 "rule": "ambiguous-provenance", "node": "other-page",
                 "description": "Provenance unclear"},
            ],
            "checks_run": {},
        }
        reports = mod.render_reports(result, kb_dir)
        assert "drift.md" in reports
        assert "DRF-001" in reports["drift.md"]
        assert "intent-observed-mismatch" in reports["drift.md"]
        assert "needs-review.md" in reports
        assert "REV-001" in reports["needs-review.md"]

    def test_empty_findings_produce_no_drift_no_review(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        reports = mod.render_reports({"findings": []}, kb_dir)
        assert "No drift detected" in reports["drift.md"]
        assert "No items need review" in reports["needs-review.md"]

    def test_knowledge_gaps_from_missing_rules(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        result = {
            "findings": [
                {"id": "ERR-001", "check": "required-artifact-integrity", "severity": "ERROR",
                 "rule": "missing-required-page", "node": "",
                 "description": "Domain hub for 'auth' is missing"},
            ]
        }
        reports = mod.render_reports(result, kb_dir)
        assert "knowledge-gaps.md" in reports
        assert "ERR-001" in reports["knowledge-gaps.md"]


# ═══════════════════════════════════════════════════════════════════════════════
# Validation: portable artifact
# ═══════════════════════════════════════════════════════════════════════════════

class TestPortableArtifact:
    """Validation output uses relative kb_path and actual check counts."""

    def test_kb_path_is_relative(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        (kb_dir / "graph").mkdir(parents=True)
        (kb_dir / "graph" / "nodes.json").write_text("[]")
        (kb_dir / "graph" / "edges.json").write_text("[]")
        (kb_dir / "graph" / "diagnostics.json").write_text("[]")
        (kb_dir / "domains").mkdir(parents=True)

        result = mod.run_validation(kb_dir, tmp_path)
        assert not result["kb_path"].startswith("/")  # not absolute
        assert "test" in result["kb_path"]

    def test_checks_run_totals_are_actual_counts(self, tmp_path: Path) -> None:
        mod = _load_script(_VALIDATE_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        (kb_dir / "graph").mkdir(parents=True)
        (kb_dir / "domains").mkdir(parents=True)

        (kb_dir / "graph" / "nodes.json").write_text(json.dumps([
            {"id": "test", "type": "project", "page_path": "projects/test/test.md",
             "provenance": "generated", "confidence": "inferred", "knowledge_role": "observed",
             "source_files": []},
        ]))
        (kb_dir / "graph" / "edges.json").write_text("[]")
        (kb_dir / "graph" / "diagnostics.json").write_text("[]")

        page = kb_dir.parent.parent / "projects" / "test" / "test.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# Test")

        result = mod.run_validation(kb_dir, tmp_path)
        checks = result["checks_run"]
        # referential: total = len(diagnostics) = 0
        assert checks["referential-integrity"]["total"] == 0
        # required-artifact: 1 hub + 0 domains + 4 graph files = 5
        assert checks["required-artifact-integrity"]["total"] == 5
        # provenance: total = len(nodes) = 1
        assert checks["provenance-consistency"]["total"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: full pipeline compile → validate
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationCompileValidate:
    """End-to-end: compile_graph produces diagnostics consumed by validate."""

    def _make_kb(self, tmp_path: Path, pages: list[tuple[str, str]]) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        (kb_dir / "graph").mkdir(parents=True)
        for rel_path, content in pages:
            full = kb_dir / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        (kb_dir / "domains").mkdir(parents=True, exist_ok=True)
        return kb_dir

    def test_orphan_detected_end_to_end(self, tmp_path: Path) -> None:
        """compile → validate: orphan wikilink produces ERROR finding."""
        comp_mod = _load_script(_COMPILE_GRAPH_PATH)
        val_mod = _load_script(_VALIDATE_PATH)

        kb = self._make_kb(tmp_path, [
            ("test.md", """---
id: test
type: project
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Test

## Active Changes
- [[changes/active/2026-08-07-nonexistent|Missing change]]
"""),
        ])

        # Compile
        compile_result = comp_mod.compile_graph(kb)
        assert len(compile_result["diagnostics"]) >= 1

        # Write output files
        graph_dir = kb / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "nodes.json").write_text(json.dumps(compile_result["nodes"], indent=2))
        (graph_dir / "edges.json").write_text(json.dumps(compile_result["edges"], indent=2))
        (graph_dir / "diagnostics.json").write_text(json.dumps(compile_result["diagnostics"], indent=2))
        (graph_dir / "file-index.json").write_text("{}")
        (graph_dir / "file-hashes.json").write_text("{}")

        # Validate
        result = val_mod.run_validation(kb, tmp_path)
        ref_findings = [f for f in result["findings"] if f["check"] == "referential-integrity"]
        assert len(ref_findings) >= 1
        orphan = [f for f in ref_findings if f["target"] == "changes/active/2026-08-07-nonexistent"]
        assert len(orphan) == 1
        assert orphan[0]["severity"] == "ERROR"
        assert result["completion_state"] == "blocked"

    def test_clean_kb_produces_complete(self, tmp_path: Path) -> None:
        """Clean KB with all links valid should produce completion_state=complete."""
        comp_mod = _load_script(_COMPILE_GRAPH_PATH)
        val_mod = _load_script(_VALIDATE_PATH)

        kb = self._make_kb(tmp_path, [
            ("test.md", """---
id: test
type: project
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Test

## Purpose
A test project that validates the Kode Brain onboarding pipeline end-to-end.
It exercises state detection, gap mapping, and graph compilation.

## Primary Users / Actors
- Backend developers building API services

## Core Outcomes
1. Users can authenticate and receive session tokens

## Scope
### In Scope
- Authentication

### Out of Scope
- Billing

## Technology Summary
TypeScript, Express, PostgreSQL.

## System Architecture
Layered monolith with DDD.

## Domains
- [[auth|Auth]]

## Runtime Entry Points
- `npm start`

## External Systems
None.

## System-wide Invariants
All writes idempotent.

## Current Risks / Legacy / Migration
None.

## Active Changes
None.

## Where To Start
Read this page.
"""),
            ("domains/auth/auth.md", """---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: auth
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/auth
  - status/active
---

# Auth

## Responsibility
Handles authentication.

## Capabilities
- [[auth-login|Login]]
"""),
            ("domains/auth/capabilities/auth-login.md", """---
id: auth-login
type: capability
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: auth
source_files: []
last_updated: "2026-08-07"
tags:
  - type/capability
  - domain/auth
  - status/active
---

# Login
"""),
            ("architecture/overview.md", """---
id: arch-overview
type: architecture_overview
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags: []
---

# Architecture Overview
"""),
        ])

        compile_result = comp_mod.compile_graph(kb)
        graph_dir = kb / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "nodes.json").write_text(json.dumps(compile_result["nodes"], indent=2))
        (graph_dir / "edges.json").write_text(json.dumps(compile_result["edges"], indent=2))
        (graph_dir / "diagnostics.json").write_text(json.dumps(compile_result["diagnostics"], indent=2))
        (graph_dir / "file-index.json").write_text("{}")
        (graph_dir / "file-hashes.json").write_text("{}")

        result = val_mod.run_validation(kb, tmp_path)
        assert result["completion_state"] == "complete"
        assert result["summary"]["error_count"] == 0
