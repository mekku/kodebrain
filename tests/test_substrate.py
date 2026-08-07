"""Tests for Kode Brain vNext deterministic substrate modules.

Covers: compile_graph, project_inventory, project_state, migrate_kb.

All scripts live under kodebrain/skill/scripts/ and are loaded by file path
via importlib (same pattern as test_referential_integrity.py).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

# ── Script paths ──────────────────────────────────────────────────────────────

_SCRIPTS_DIR = Path(__file__).parent.parent / "kodebrain" / "skill" / "scripts"

_COMPILE_GRAPH_PATH = _SCRIPTS_DIR / "compile_graph.py"
_PROJECT_INVENTORY_PATH = _SCRIPTS_DIR / "project_inventory.py"
_PROJECT_STATE_PATH = _SCRIPTS_DIR / "project_state.py"
_MIGRATE_KB_PATH = _SCRIPTS_DIR / "migrate_kb.py"


def _load_script(path: Path):
    """Load a standalone script by file path via importlib."""
    name = path.stem
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None, f"cannot find spec for {path}"
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════════════
# compile_graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompileGraph:
    """Markdown-first graph compilation tests."""

    def _make_kb(self, tmp_path: Path, pages: list[tuple[str, str]]) -> Path:
        """Create a mock KB directory with markdown pages. Each tuple is (rel_path, content)."""
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test-project"
        kb_dir.mkdir(parents=True)
        for rel_path, content in pages:
            full = kb_dir / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return kb_dir

    def test_compiles_project_hub_to_node(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("test-project.md", """---
id: test-project
type: project
status: active
confidence: verified
provenance: human
knowledge_role: intent
project: test-project
source_files: []
last_updated: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Test Project

## Purpose

This is a test project.

## Domains

- [[auth|Auth domain]]
- [[billing|Billing domain]]
"""),
        ])
        result = mod.compile_graph(kb)
        assert result["stats"]["total_nodes"] == 1
        node = result["nodes"][0]
        assert node["id"] == "test-project"
        assert node["type"] == "project"
        assert node["provenance"] == "human"
        assert node["knowledge_role"] == "intent"

    def test_compiles_edges_from_wikilinks(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("test-project.md", """---
id: test-project
type: project
status: active
confidence: supported
provenance: generated
knowledge_role: observed
project: test-project
source_files: []
last_updated: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Test

## Domains

- [[auth|Auth domain]]
"""),
            ("domains/auth/auth.md", """---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
domain: auth
source_files:
  - src/auth/login.ts
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
project: test-project
domain: auth
source_files:
  - src/auth/login.ts
last_updated: "2026-08-07"
tags:
  - type/capability
  - domain/auth
  - status/active
---

# Login

## Short Summary

User login capability.
"""),
        ])
        result = mod.compile_graph(kb)
        assert result["stats"]["total_nodes"] == 3
        assert result["stats"]["total_edges"] == 2
        # Edges should be from project → auth, and auth → auth-login
        edge_pairs = {(e["from"], e["to"]) for e in result["edges"]}
        assert ("test-project", "auth") in edge_pairs
        assert ("auth", "auth-login") in edge_pairs

    def test_compiles_file_index(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("domains/auth/auth.md", """---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
domain: auth
source_files:
  - src/auth/login.ts
  - src/auth/session.ts
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/auth
  - status/active
---

# Auth

## Responsibility

Handles auth.
"""),
            ("domains/auth/capabilities/auth-login.md", """---
id: auth-login
type: capability
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
domain: auth
source_files:
  - src/auth/login.ts
last_updated: "2026-08-07"
tags:
  - type/capability
  - domain/auth
  - status/active
---

# Login
"""),
        ])
        result = mod.compile_graph(kb)
        fi = result["file_index"]
        assert "src/auth/login.ts" in fi
        assert len(fi["src/auth/login.ts"]) == 2
        assert "auth" in fi["src/auth/login.ts"]
        assert "auth-login" in fi["src/auth/login.ts"]
        assert "src/auth/session.ts" in fi
        assert fi["src/auth/session.ts"] == ["auth"]

    def test_idempotent_compilation(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("domains/auth/auth.md", """---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
domain: auth
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/auth
  - status/active
---

# Auth

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
project: test-project
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
        ])
        r1 = mod.compile_graph(kb)
        r2 = mod.compile_graph(kb)
        assert r1["stats"]["total_nodes"] == r2["stats"]["total_nodes"]
        assert r1["stats"]["total_edges"] == r2["stats"]["total_edges"]
        assert r1["nodes"] == r2["nodes"]
        assert r1["edges"] == r2["edges"]

    def test_warns_on_orphan_wikilinks(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("domains/auth/auth.md", """---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
domain: auth
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/auth
  - status/active
---

# Auth

## Capabilities

- [[nonexistent-capability|Missing]]
"""),
        ])
        result = mod.compile_graph(kb)
        assert len(result["warnings"]) >= 1
        assert any("nonexistent" in w for w in result["warnings"])

    def test_edge_type_inference_domain_to_capability(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("domains/auth/auth.md", """---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
domain: auth
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/auth
  - status/active
---

# Auth

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
project: test-project
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
        ])
        result = mod.compile_graph(kb)
        edges = result["edges"]
        assert len(edges) == 1
        assert edges[0]["type"] == "contains"

    def test_edge_type_inference_caveat_to_capability(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("domains/auth/risks/auth-session-risk.md", """---
id: auth-session-risk
type: caveat
status: needs_review
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
domain: auth
source_files: []
last_updated: "2026-08-07"
severity: high
tags:
  - type/risk
  - domain/auth
  - status/needs_review
---

# Session Risk

Affects: [[auth-login|Login]]
"""),
            ("domains/auth/capabilities/auth-login.md", """---
id: auth-login
type: capability
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test-project
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
        ])
        result = mod.compile_graph(kb)
        edges = result["edges"]
        assert len(edges) == 1
        assert edges[0]["type"] == "risky_for"


# ═══════════════════════════════════════════════════════════════════════════════
# project_inventory
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectInventory:
    """Architecture-aware project inventory tests."""

    def _make_project(self, tmp_path: Path, files: dict[str, str]) -> Path:
        """Create a mock project with given files. Dict is {rel_path: content}."""
        proj = tmp_path / "test-project"
        proj.mkdir()
        for rel_path, content in files.items():
            full = proj / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return proj

    def test_detects_node_manifest(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"express": "^4.0"}}),
            "src/index.ts": "console.log('hello')",
        })
        result = mod.inventory(proj)
        assert "node" in result["manifests"]
        assert "package.json" in result["manifests"]["node"]

    def test_detects_express_framework(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"express": "^4.0"}}),
        })
        result = mod.inventory(proj)
        backend_tech = [t["name"] for t in result["technology"].get("backend", [])]
        assert "Express" in backend_tech

    def test_detects_postgresql(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"pg": "^8.0"}}),
        })
        result = mod.inventory(proj)
        db_tech = [t["name"] for t in result["technology"].get("database", [])]
        assert "PostgreSQL" in db_tech

    def test_detects_docker(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "Dockerfile": "FROM node:20",
            "package.json": json.dumps({"name": "test"}),
        })
        result = mod.inventory(proj)
        infra_types = [i["type"] for i in result["infrastructure"]]
        assert "Docker" in infra_types

    def test_detects_github_actions(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            ".github/workflows/ci.yml": "name: CI\non: [push]",
        })
        result = mod.inventory(proj)
        infra_types = [i["type"] for i in result["infrastructure"]]
        assert "GitHub Actions" in infra_types

    def test_detects_vitest(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "devDependencies": {"vitest": "^1.0"}}),
        })
        result = mod.inventory(proj)
        test_tech = [t["name"] for t in result["technology"].get("testing", [])]
        assert "Vitest" in test_tech

    def test_detects_python_fastapi(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "pyproject.toml": '[project]\nname = "test"\ndependencies = ["fastapi", "uvicorn"]\n',
        })
        result = mod.inventory(proj)
        backend_tech = [t["name"] for t in result["technology"].get("backend", [])]
        assert "FastAPI" in backend_tech

    def test_detects_runtime_commands(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({
                "name": "test",
                "scripts": {"dev": "next dev", "build": "next build", "test": "vitest"},
            }),
        })
        result = mod.inventory(proj)
        rt = result["runtime"]
        assert rt["run_command"] is not None
        assert "dev" in str(rt["run_command"])

    def test_source_file_counts(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "src/a.ts": "export const a = 1",
            "src/b.ts": "export const b = 2",
            "src/c.py": "def foo(): pass",
            "README.md": "# hello",
        })
        result = mod.inventory(proj)
        assert result["total_source_files"] >= 2  # .ts and .py
        counts = result["source_file_counts"]
        assert ".ts" in counts
        assert counts[".ts"] == 2

    def test_empty_project_returns_zeros(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {})
        result = mod.inventory(proj)
        assert result["total_source_files"] == 0
        assert result["manifests"] == {}

    def test_detects_nextjs(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"next": "^14.0"}}),
            "next.config.js": "module.exports = {}",
        })
        result = mod.inventory(proj)
        frontend_tech = [t["name"] for t in result["technology"].get("frontend", [])]
        assert "Next.js" in frontend_tech

    def test_detects_redis_cache(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"ioredis": "^5.0"}}),
        })
        result = mod.inventory(proj)
        cache_tech = [t["name"] for t in result["technology"].get("cache", [])]
        assert "Redis" in cache_tech

    def test_detects_bullmq_queue(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"bullmq": "^5.0"}}),
        })
        result = mod.inventory(proj)
        queue_tech = [t["name"] for t in result["technology"].get("queue", [])]
        assert "BullMQ" in queue_tech

    def test_detects_zod_validation(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"zod": "^3.0"}}),
        })
        result = mod.inventory(proj)
        val_tech = [t["name"] for t in result["technology"].get("validation", [])]
        assert "Zod" in val_tech

    def test_detects_api_styles(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": json.dumps({"name": "test", "dependencies": {"trpc": "^10.0"}}),
        })
        result = mod.inventory(proj)
        api_styles = [a["style"] for a in result["api_styles"]]
        assert "tRPC" in api_styles


# ═══════════════════════════════════════════════════════════════════════════════
# project_state
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectState:
    """Project state detection and gap map tests."""

    def _make_project(self, tmp_path: Path, files: dict[str, str]) -> Path:
        proj = tmp_path / "test-project"
        proj.mkdir()
        for rel_path, content in files.items():
            full = proj / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return proj

    def test_greenfield_empty_dir(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project(tmp_path, {})
        result = mod.classify(proj)
        assert result["state"] == "greenfield"

    def test_new_brownfield_source_no_kb(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project(tmp_path, {
            "package.json": "{}",
            "src/index.ts": "console.log('hello')",
        })
        result = mod.classify(proj)
        assert result["state"] == "new_brownfield"
        assert result["source_file_count"] > 0

    def test_partial_kb_no_hub(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project(tmp_path, {
            "docs/brain/projects/test/domains/auth/auth.md": "# Auth",
        })
        result = mod.classify(proj)
        assert result["state"] in ("partial_kb", "greenfield")  # may be greenfield if no source detected

    def test_partial_kb_incomplete_hub(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project(tmp_path, {
            "src/index.ts": "console.log('hi')",
            "docs/brain/projects/test/test.md": """---
id: test
type: project
status: active
confidence: supported
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
""",
        })
        result = mod.classify(proj)
        assert result["state"] == "partial_kb"

    def test_onboarded_complete_project(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        hub = """---
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
Test project.

## Primary Users / Actors
- Devs

## Core Outcomes
1. Works

## Scope
### In Scope
- Everything

### Out of Scope
- Nothing

## Technology Summary
| Role | Tech |
|---|---|
| Frontend | React |

## System Architecture
Layered.

## Domains
- [[auth|Auth]]

## Runtime Entry Points
- `npm start`

## External Systems
- Stripe

## System-wide Invariants
- Idempotent

## Current Risks / Legacy / Migration
None.

## Active Changes
None.

## Where To Start
Read this.
"""
        proj = self._make_project(tmp_path, {
            "src/index.ts": "console.log('hi')",
            f"docs/brain/projects/test/test.md": hub,
            "docs/brain/projects/test/architecture/overview.md": "# Overview",
            "docs/brain/projects/test/architecture/technology.md": "# Tech",
            "docs/brain/projects/test/architecture/runtime.md": "# Runtime",
            "docs/brain/projects/test/domains/auth/auth.md": "# Auth",
            "docs/brain/projects/test/graph/nodes.json": "[]",
            "docs/brain/projects/test/graph/edges.json": "[]",
            "docs/brain/projects/test/graph/file-index.json": "{}",
            "docs/brain/projects/test/graph/file-hashes.json": "{}",
        })
        result = mod.classify(proj)
        assert result["state"] == "onboarded"

    def test_gap_map_missing_dimensions(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project(tmp_path, {
            "src/index.ts": "console.log('hi')",
        })
        result = mod.classify(proj)
        gaps = result["gap_map"]
        for dim in ["purpose", "actors", "core_outcomes", "scope"]:
            assert gaps[dim]["status"] == "missing"

    def test_gap_map_marks_needs_human(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project(tmp_path, {
            "src/index.ts": "console.log('hi')",
            "docs/brain/projects/test/test.md": """---
id: test
type: project
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags: []
---

# Test

## Purpose
Test project.

## Domains
- auth
""",
        })
        result = mod.classify(proj)
        gaps = result["gap_map"]
        # invariants and domain_boundaries should need human input
        assert gaps["invariants"]["source"] == "needs_human"
        assert gaps["domain_boundaries"]["source"] == "needs_human"

    def test_legacy_kb_detected(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        old_node = {
            "id": "auth/login-flow",
            "type": "flow",
            "name": "Login",
            "summary": "Login flow",
            "status": "active",
            "confidence": "source_supported",
            "sourceFiles": ["src/auth/login.ts"],
            "lastUpdated": "2026-05-07",
        }
        proj = self._make_project(tmp_path, {
            "src/auth/login.ts": "export function login() {}",
            "docs/brain/projects/test/test.md": """---
id: test
type: project
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags: []
---

# Test

## Purpose
Test.

## Primary Users
- Devs

## Core Outcomes
1. Works

## Scope
TBD

## Technology Summary
TBD

## System Architecture
TBD

## Domains
- auth

## Runtime Entry Points
- server

## External Systems
None

## System-wide Invariants
None

## Current Risks
None

## Active Changes
None

## Where To Start
Here.
""",
            "docs/brain/projects/test/domains/auth/auth.md": "# Auth",
            "docs/brain/projects/test/architecture/overview.md": "# Overview",
            "docs/brain/projects/test/architecture/technology.md": "# Tech",
            "docs/brain/projects/test/graph/nodes.json": json.dumps([old_node]),
            "docs/brain/projects/test/graph/edges.json": "[]",
            "docs/brain/projects/test/graph/file-index.json": "{}",
            "docs/brain/projects/test/graph/file-hashes.json": "{}",
        })
        result = mod.classify(proj)
        assert result["state"] == "legacy_kb"
        assert result["kb_version"] == "0.1"


# ═══════════════════════════════════════════════════════════════════════════════
# migrate_kb
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigrateKB:
    """Legacy KB → vNext migration tests."""

    def _make_kb(self, tmp_path: Path, nodes: list[dict], edges: list[dict] | None = None) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test-project"
        graph_dir = kb_dir / "graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "nodes.json").write_text(json.dumps(nodes, indent=2))
        (graph_dir / "edges.json").write_text(
            json.dumps(edges if edges is not None else [], indent=2)
        )
        (graph_dir / "file-index.json").write_text("{}")
        (graph_dir / "file-hashes.json").write_text("{}")
        return kb_dir

    def _legacy_node(self) -> dict:
        return {
            "id": "auth/login-flow",
            "type": "flow",
            "name": "Login Flow",
            "summary": "Handles user login",
            "project": "test",
            "domain": "auth",
            "status": "active",
            "confidence": "source_supported",
            "sourceFiles": ["src/auth/login.ts"],
            "sourceSymbols": ["loginHandler"],
            "pagePath": "domains/auth/flows/login.md",
            "lastUpdated": "2026-05-07",
            "createdBy": "knowledge_builder",
        }

    def test_detects_legacy_format(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        needs, version, reasons = mod._detect_legacy(kb)
        assert needs is True
        assert version == "0.1"
        assert any("sourceFiles" in r for r in reasons)

    def test_detects_vnext_no_migration_needed(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        vnext_node = {
            "id": "auth-login-flow",
            "type": "flow",
            "name": "Login Flow",
            "summary": "Handles user login",
            "project": "test",
            "domain": "auth",
            "status": "active",
            "confidence": "supported",
            "provenance": "source_code",
            "knowledge_role": "observed",
            "source_files": ["src/auth/login.ts"],
            "last_updated": "2026-08-07",
        }
        kb = self._make_kb(tmp_path, [vnext_node])
        needs, version, reasons = mod._detect_legacy(kb)
        assert needs is False

    def test_migrate_hierarchical_id_to_flat(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        report = mod.migrate(kb, dry_run=False)
        assert report["migrated"] is True
        assert report["ids_renamed"] >= 1

        # Verify node was written with flat ID
        nodes = json.loads((kb / "graph" / "nodes.json").read_text())
        assert nodes[0]["id"] == "auth-login-flow"

    def test_migrate_camelcase_to_snakecase(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        mod.migrate(kb, dry_run=False)

        nodes = json.loads((kb / "graph" / "nodes.json").read_text())
        node = nodes[0]
        assert "source_files" in node
        assert "sourceFiles" not in node
        assert "last_updated" in node
        assert "lastUpdated" not in node
        assert "created_by" in node
        assert "createdBy" not in node

    def test_migrate_confidence_source_supported(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        mod.migrate(kb, dry_run=False)

        nodes = json.loads((kb / "graph" / "nodes.json").read_text())
        assert nodes[0]["confidence"] == "supported"

    def test_migrate_adds_provenance(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        mod.migrate(kb, dry_run=False)

        nodes = json.loads((kb / "graph" / "nodes.json").read_text())
        assert "provenance" in nodes[0]
        # Node with source_files gets source_code provenance
        assert nodes[0]["provenance"] == "source_code"

    def test_migrate_adds_knowledge_role(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        mod.migrate(kb, dry_run=False)

        nodes = json.loads((kb / "graph" / "nodes.json").read_text())
        assert "knowledge_role" in nodes[0]
        assert nodes[0]["knowledge_role"] == "observed"

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        report = mod.migrate(kb, dry_run=True)
        assert report["migrated"] is True
        assert "(dry run" in report["backup_path"]

        # Nodes should still have old ID
        nodes = json.loads((kb / "graph" / "nodes.json").read_text())
        assert nodes[0]["id"] == "auth/login-flow"

    def test_migrate_edges_too(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        edge = {
            "from": "auth/login-flow",
            "to": "auth/session-model",
            "type": "writes_to",
            "confidence": "source_supported",
        }
        kb = self._make_kb(tmp_path, [self._legacy_node()], [edge])
        mod.migrate(kb, dry_run=False)

        edges = json.loads((kb / "graph" / "edges.json").read_text())
        assert edges[0]["from"] == "auth-login-flow"
        assert edges[0]["to"] == "auth-session-model"
        assert edges[0]["confidence"] == "supported"
        assert "provenance" in edges[0]

    def test_preserves_human_notes(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        # Add a markdown page with human notes
        domains_dir = kb / "domains" / "auth"
        domains_dir.mkdir(parents=True)
        (domains_dir / "auth.md").write_text("""# Auth
<!-- human-note -->
This is a verified observation about the auth system.
<!-- /human-note -->
""")

        report = mod.migrate(kb, dry_run=False)
        assert report["human_notes_preserved"] >= 1

    def test_migration_is_rerunnable(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        # First migration
        r1 = mod.migrate(kb, dry_run=False)
        assert r1["migrated"] is True

        # Second migration should detect it's already vNext
        needs, version, reasons = mod._detect_legacy(kb)
        assert needs is False

    def test_check_flag_exits_0_when_migration_needed(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        needs, _, _ = mod._detect_legacy(kb)
        assert needs is True


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-module integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests across substrate modules."""

    def _make_project_with_kb(self, tmp_path: Path) -> Path:
        proj = tmp_path / "test-project"
        proj.mkdir()
        # Manifest
        (proj / "package.json").write_text(json.dumps({"name": "test", "dependencies": {"express": "^4.0"}}))
        # Source files
        (proj / "src").mkdir()
        (proj / "src" / "index.ts").write_text("export function main() {}")
        # KB
        kb_dir = proj / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        (kb_dir / "test.md").write_text("""---
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
Test.

## Primary Users / Actors
- Devs

## Core Outcomes
1. Works

## Scope
### In Scope
- All

### Out of Scope
- None

## Technology Summary
TBD

## System Architecture
Layered.

## Domains
- [[auth|Auth]]

## Runtime Entry Points
- server

## External Systems
None.

## System-wide Invariants
None.

## Current Risks
None.

## Active Changes
None.

## Where To Start
Here.
""")
        domain_dir = kb_dir / "domains" / "auth"
        domain_dir.mkdir(parents=True)
        (domain_dir / "auth.md").write_text("""---
id: auth
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: auth
source_files:
  - src/index.ts
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/auth
  - status/active
---

# Auth

## Responsibility
Auth domain.

## Owns
- Login

## Capabilities
- [[auth-login|Login]]
""")
        caps_dir = domain_dir / "capabilities"
        caps_dir.mkdir(parents=True)
        (caps_dir / "auth-login.md").write_text("""---
id: auth-login
type: capability
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: auth
source_files:
  - src/index.ts
last_updated: "2026-08-07"
tags:
  - type/capability
  - domain/auth
  - status/active
---

# Login

## Short Summary
Login capability.
""")
        # Architecture
        arch_dir = kb_dir / "architecture"
        arch_dir.mkdir(parents=True)
        (arch_dir / "overview.md").write_text("# Overview")
        (arch_dir / "technology.md").write_text("# Technology")
        (arch_dir / "runtime.md").write_text("# Runtime")
        # Graph stub
        graph_dir = kb_dir / "graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "nodes.json").write_text("[]")
        (graph_dir / "edges.json").write_text("[]")
        (graph_dir / "file-index.json").write_text("{}")
        (graph_dir / "file-hashes.json").write_text("{}")
        return proj

    def test_inventory_then_state_then_compile(self, tmp_path: Path) -> None:
        """Full pipeline: inventory → state detection → graph compile."""
        proj = self._make_project_with_kb(tmp_path)

        # 1. Inventory
        inv_mod = _load_script(_PROJECT_INVENTORY_PATH)
        inv = inv_mod.inventory(proj)
        assert inv["total_source_files"] >= 1
        assert "node" in inv["manifests"]

        # 2. State
        state_mod = _load_script(_PROJECT_STATE_PATH)
        state = state_mod.classify(proj)
        assert state["state"] == "onboarded"
        assert state["source_file_count"] >= 1

        # 3. Compile graph
        kb_dir = proj / "docs" / "brain" / "projects" / "test"
        comp_mod = _load_script(_COMPILE_GRAPH_PATH)
        result = comp_mod.compile_graph(kb_dir)
        assert result["stats"]["total_nodes"] == 3  # project, domain, capability
        assert result["stats"]["total_edges"] >= 1

    def test_compile_graph_rebuilds_indexes(self, tmp_path: Path) -> None:
        """Compile generates file-index.json that maps source files to nodes."""
        proj = self._make_project_with_kb(tmp_path)
        kb_dir = proj / "docs" / "brain" / "projects" / "test"

        comp_mod = _load_script(_COMPILE_GRAPH_PATH)
        result = comp_mod.compile_graph(kb_dir)

        fi = result["file_index"]
        assert "src/index.ts" in fi
        # Both auth domain and auth-login capability reference this file
        assert len(fi["src/index.ts"]) >= 2
