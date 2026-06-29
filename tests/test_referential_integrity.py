"""Referential-integrity gate tests for kodebrain graph validation.

This is the project's first test module. ``harvest.py`` lives under
``kodebrain/skill/scripts/`` and is a standalone script (not an installed
package), so it is loaded by file path via ``importlib``.

Covers the orphan-EDGE gate: any edge whose ``from``/``to`` references a node id
that does not exist must be detected and must FAIL graph validation.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# ── Load harvest.py by file path (no package install) ───────────────────────────
_HARVEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "kodebrain" / "skill" / "scripts" / "harvest.py"
)
_spec = importlib.util.spec_from_file_location("harvest", _HARVEST_PATH)
assert _spec and _spec.loader
harvest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harvest)


def _nodes(*ids: str) -> list[dict]:
    """Build minimal node dicts (id only) for the given ids."""
    return [{"id": i} for i in ids]


# ── detect_orphan_edges (pure detector) ─────────────────────────────────────────

def test_detect_orphan_edges_flags_missing_from() -> None:
    nodes = _nodes("a", "b")
    edges = [{"from": "ghost", "to": "b", "type": "calls"}]
    orphans = harvest.detect_orphan_edges(nodes, edges)
    assert len(orphans) == 1
    assert orphans[0]["from"] == "ghost"
    assert orphans[0]["missing"] == ["from"]


def test_detect_orphan_edges_flags_missing_to() -> None:
    nodes = _nodes("a", "b")
    edges = [{"from": "a", "to": "ghost", "type": "calls"}]
    orphans = harvest.detect_orphan_edges(nodes, edges)
    assert orphans[0]["missing"] == ["to"]


def test_detect_orphan_edges_clean_graph_returns_empty() -> None:
    nodes = _nodes("a", "b")
    edges = [{"from": "a", "to": "b", "type": "calls"}]
    assert harvest.detect_orphan_edges(nodes, edges) == []


# ── assert_no_orphan_edges (default-fail gate) ──────────────────────────────────

def test_assert_no_orphan_edges_raises_and_names_missing_id() -> None:
    nodes = _nodes("a", "b")
    edges = [{"from": "ghost-node", "to": "b", "type": "calls"}]
    with pytest.raises(harvest.OrphanEdgeError) as exc:
        harvest.assert_no_orphan_edges(nodes, edges)
    # Diagnostic must name the offending edge and the missing node id.
    assert "ghost-node" in str(exc.value)


def test_assert_no_orphan_edges_clean_graph_passes() -> None:
    nodes = _nodes("a", "b")
    edges = [{"from": "a", "to": "b", "type": "calls"}]
    assert harvest.assert_no_orphan_edges(nodes, edges) is None


# ── run_benchmark wiring (the validation path itself must FAIL) ──────────────────

def test_run_benchmark_fails_on_orphan_edge(tmp_path: Path) -> None:
    """The --benchmark/validation path must raise on an orphan edge,
    before touching file-index.json / file-hashes.json."""
    graph = tmp_path / "graph"
    graph.mkdir()
    (graph / "nodes.json").write_text(
        json.dumps({"nodes": [{"id": "a", "type": "concept", "status": "active",
                               "confidence": "verified", "domain": "d"}]})
    )
    (graph / "edges.json").write_text(
        json.dumps({"edges": [{"from": "a", "to": "ghost", "type": "calls"}]})
    )
    with pytest.raises(harvest.OrphanEdgeError) as exc:
        harvest.run_benchmark(tmp_path, None)
    assert "ghost" in str(exc.value)
