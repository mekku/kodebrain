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
Test project that validates the Kode Brain onboarding pipeline end-to-end.
It exercises state detection, gap mapping, and graph compilation.

## Primary Users / Actors
- Backend developers building API services
- Frontend developers consuming the API
- DevOps engineers managing deployment pipelines

## Core Outcomes
1. Users can authenticate and receive session tokens
2. Users can create and manage resources through the API
3. System emits audit events for all state-changing operations

## Scope
### In Scope
- Authentication and session management
- Resource CRUD operations
- Audit logging and event emission

### Out of Scope
- Payment processing
- Third-party integrations beyond the core API

## Technology Summary
| Role | Tech |
|---|---|
| Frontend | React with Next.js |
| Backend | Express on Node.js |
| Database | PostgreSQL via Prisma ORM |
| Cache | Redis |
| Queue | BullMQ |

## System Architecture
The system follows a layered architecture with domain-driven design.
Each domain owns its data and exposes capabilities through service boundaries.
Infrastructure is containerized and deployed on Kubernetes.

## Domains
- [[auth|Auth domain]] — manages authentication and session lifecycle
- [[resources|Resources domain]] — CRUD operations for core resources

## Runtime Entry Points
- `npm start` — HTTP API server on port 3000
- `npm run worker` — Background job processor

## External Systems
- Stripe — payment processing (planned, not yet integrated)
- SendGrid — transactional email delivery

## System-wide Invariants
- All state-changing operations must produce audit events
- Session tokens expire after 24 hours of inactivity
- Database migrations are forward-only, never rolled back

## Current Risks / Legacy / Migration
- Auth module partially migrated from v1 session store to v2 JWT-based store
- Legacy admin panel still serves on /admin (migration planned Q4)

## Active Changes
- [[changes/active/2026-08-01-migrate-sessions|Migrate sessions to JWT]]

## Where To Start
Read this page, then pick a domain from the Domains section relevant to your task.
Check the Active Changes section for in-progress work that may affect your changes.
Use /kodebrain reading-pack for focused context before touching code.
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
        # Also create a legacy Markdown page for Markdown-first migration
        domain_dir = kb_dir / "domains" / "auth" / "flows"
        domain_dir.mkdir(parents=True)
        (domain_dir / "login.md").write_text("""---
id: auth/login-flow
type: flow
name: Login Flow
summary: Handles user login
project: test
domain: auth
status: active
confidence: source_supported
sourceFiles:
  - src/auth/login.ts
sourceSymbols:
  - loginHandler
lastUpdated: "2026-05-07"
createdBy: knowledge_builder
tags:
  - type/flow
  - domain/auth
  - status/active
---

# Login Flow

## Short Summary
Handles user login.

## Depends On
- [[auth/session-model|Session Model]]

## Part Of
- [[auth-login|Login capability]]
""")
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
        # Detection now scans Markdown first — finds hierarchical IDs and camelCase
        assert any("hierarchical" in r or "camelCase" in r or "sourceFiles" in r for r in reasons)

    def test_detects_vnext_no_migration_needed(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        # Create vNext KB with flat IDs, snake_case, provenance, knowledge_role
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test-project"
        page = kb_dir / "domains" / "auth" / "flows"
        page.mkdir(parents=True)
        (page / "auth-login-flow.md").write_text("""---
id: auth-login-flow
type: flow
name: Login Flow
summary: Handles user login
project: test
domain: auth
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
source_files:
  - src/auth/login.ts
last_updated: "2026-08-07"
tags:
  - type/flow
  - domain/auth
  - status/active
---

# Login Flow

Handles user authentication.
""")
        # Graph files
        graph_dir = kb_dir / "graph"
        graph_dir.mkdir(parents=True)
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
        (graph_dir / "nodes.json").write_text(json.dumps([vnext_node]))
        (graph_dir / "edges.json").write_text("[]")
        (graph_dir / "file-index.json").write_text("{}")
        (graph_dir / "file-hashes.json").write_text("{}")
        needs, version, reasons = mod._detect_legacy(kb_dir)
        assert needs is False

    def test_migrate_hierarchical_id_to_flat(self, tmp_path: Path) -> None:
        mod = _load_script(_MIGRATE_KB_PATH)
        kb = self._make_kb(tmp_path, [self._legacy_node()])
        report = mod.migrate(kb, dry_run=False)
        assert report["migrated"] is True
        # Markdown page has hierarchical ID → gets migrated
        assert report["ids_renamed"] >= 1

        # File was renamed: login.md → auth-login-flow.md
        new_page = kb / "domains" / "auth" / "flows" / "auth-login-flow.md"
        assert new_page.exists()
        content = new_page.read_text()
        assert "auth-login-flow" in content
        assert "auth/login-flow" not in content

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
        # Add human-note blocks to the existing page
        page = kb / "domains" / "auth" / "flows" / "login.md"
        content = page.read_text()
        content += "\n<!-- human-note -->\nThis is a verified observation about the auth flow.\n<!-- /human-note -->\n"
        page.write_text(content)

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
Integration test project for validating the Kode Brain onboarding pipeline.
Exercises state detection, gap mapping, and graph compilation end-to-end.

## Primary Users / Actors
- Backend developers building and maintaining API services
- Frontend developers consuming the REST and GraphQL endpoints

## Core Outcomes
1. Users can authenticate using email and password credentials
2. Users can create, read, update, and delete resources via the REST API
3. All state changes produce audit events for compliance and debugging

## Scope
### In Scope
- Authentication and session management with JWT tokens
- Resource CRUD operations with validation and authorization

### Out of Scope
- Payment processing and subscription management
- Real-time WebSocket or Server-Sent Event endpoints

## Technology Summary
| Role | Tech |
|---|---|
| Frontend | React with Next.js |
| Backend | Express on Node.js |
| Database | PostgreSQL via Prisma |
| Cache | Redis |
| Queue | BullMQ |

## System Architecture
Layered monolith following domain-driven design. Each domain owns its data
and exposes capabilities through service boundaries. Infrastructure is
containerized with Docker and deployed on Kubernetes.

## Domains
- [[auth|Auth domain]] — manages authentication and session lifecycle

## Runtime Entry Points
- `npm start` — HTTP API server on port 3000
- `npm run worker` — background job processor for queues

## External Systems
- Stripe — payment processing for subscription billing
- SendGrid — transactional email delivery for notifications

## System-wide Invariants
- All state-changing operations must produce audit events with unique IDs
- Session tokens expire after 24 hours of inactivity by default

## Current Risks
- Auth module partially migrated from legacy session store to JWT tokens
- Legacy admin panel still serves on /admin, migration planned Q4

## Active Changes
None.

## Where To Start
Read this page for orientation, then pick a domain from the Domains section.
Use /kodebrain reading-pack for focused context before touching any source code.
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


# ═══════════════════════════════════════════════════════════════════════════════
# Adversarial / regression tests for correctness fixes
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlaceholderDetection:
    """Section quality grading — placeholder vs substantive."""

    def _make_project_with_hub(self, tmp_path: Path, hub_content: str) -> Path:
        proj = tmp_path / "test-project"
        proj.mkdir()
        (proj / "src").mkdir(parents=True, exist_ok=True)
        (proj / "src" / "index.ts").write_text("export const x = 1")
        kb_dir = proj / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        (kb_dir / "test.md").write_text(hub_content)
        # Graph files
        graph_dir = kb_dir / "graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "nodes.json").write_text("[]")
        (graph_dir / "edges.json").write_text("[]")
        (graph_dir / "file-index.json").write_text("{}")
        (graph_dir / "file-hashes.json").write_text("{}")
        # Architecture + domains
        (kb_dir / "architecture").mkdir(parents=True, exist_ok=True)
        (kb_dir / "architecture" / "overview.md").write_text("# Overview\n\nThe system has three services.")
        (kb_dir / "domains" / "auth").mkdir(parents=True)
        (kb_dir / "domains" / "auth" / "auth.md").write_text("# Auth")
        return proj

    def test_template_placeholder_detected(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project_with_hub(tmp_path, """---
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
{{What this project is for}}

## Primary Users / Actors
TBD

## Core Outcomes
...

## Scope
## Technology Summary
## System Architecture
## Domains
## Runtime Entry Points
## External Systems
## System-wide Invariants
## Current Risks / Legacy / Migration
## Active Changes
## Where To Start
""")
        result = mod.classify(proj)
        hub = result["hub_sections_found"]
        # Template variables → placeholder
        assert hub["purpose"] == "placeholder"
        # TBD → placeholder
        assert hub["actors"] == "placeholder"
        # Bare "..." → placeholder
        assert hub["core_outcomes"] == "placeholder"

    def test_substantive_section_detected(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project_with_hub(tmp_path, """---
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
This project provides authentication and authorization services for the
entire platform ecosystem including web, mobile, and API clients.

## Primary Users / Actors
- End users logging in via web and mobile applications
- Third-party developers using the OAuth API
- Internal admin operators managing user permissions

## Core Outcomes
1. Users can authenticate with email/password, SSO, and passkeys
2. Session tokens are issued with configurable TTL and refresh policies
3. Audit events are emitted for all authentication state changes
4. Rate limiting prevents brute-force attacks on login endpoints

## Scope
### In Scope
- Authentication
### Out of Scope
- Billing

## Technology Summary
React + Express + PostgreSQL

## System Architecture
Layered monolith with domain-driven design.

## Domains
- [[auth|Auth]]
- [[users|Users]]

## Runtime Entry Points
- `npm start` — HTTP server

## External Systems
- Stripe for billing

## System-wide Invariants
- All writes are idempotent

## Current Risks / Legacy / Migration
None.

## Active Changes
None.

## Where To Start
Read this page first.
""")
        result = mod.classify(proj)
        hub = result["hub_sections_found"]
        assert hub["purpose"] == "substantive"
        assert hub["actors"] == "substantive"
        # Should NOT be placeholder despite "..." not being content
        assert hub["core_outcomes"] in ("substantive", "partial")

    def test_partial_kb_with_placeholders(self, tmp_path: Path) -> None:
        """A KB with only template placeholders should be partial_kb, not onboarded."""
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = self._make_project_with_hub(tmp_path, """---
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
{{What this project is for}}

## Primary Users / Actors

## Core Outcomes

## Scope
## Technology Summary
## System Architecture
## Domains
## Runtime Entry Points
## External Systems
## System-wide Invariants
## Current Risks / Legacy / Migration
## Active Changes
## Where To Start
""")
        result = mod.classify(proj)
        assert result["state"] == "partial_kb"


class TestIgnoreDirFiltering:
    """Source counting must skip node_modules, dist, vendor, etc."""

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        (proj / "node_modules" / "lodash").mkdir(parents=True, exist_ok=True)
        (proj / "node_modules" / "lodash" / "index.js").write_text("module.exports = {}")
        (proj / "src").mkdir(parents=True, exist_ok=True)
        (proj / "src" / "index.ts").write_text("export const x = 1")

        count = mod._count_source_files(proj)
        assert count == 1  # only src/index.ts, not the node_modules file

    def test_skips_dist_and_build(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        (proj / "dist").mkdir(parents=True, exist_ok=True)
        (proj / "dist" / "bundle.js").write_text("(()=>{})()")
        (proj / "build").mkdir(parents=True, exist_ok=True)
        (proj / "build" / "output.js").write_text("// built")
        (proj / "src").mkdir(parents=True, exist_ok=True)
        (proj / "src" / "main.ts").write_text("export {}")

        count = mod._count_source_files(proj)
        assert count == 1  # only src/main.ts

    def test_skips_vendor_and_pycache(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        vendor_lib = proj / "vendor" / "lib"
        vendor_lib.mkdir(parents=True)
        (vendor_lib / "lib.go").write_text("package lib")
        pycache = proj / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "mod.cpython-312.pyc").write_text("")
        (proj / "main.go").write_text("package main")

        count = mod._count_source_files(proj)
        assert count == 1  # only main.go


class TestHashBasedStaleness:
    """Staleness must use file-hashes.json hash comparison, not mtime."""

    def test_stale_when_hash_differs(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        # Create a source file
        src_file = proj / "src" / "index.ts"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("export const x = 1")

        # Create KB with a hash that doesn't match
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
tags: []
---

# Test

## Purpose
Test project that validates the Kode Brain onboarding pipeline end-to-end.
It exercises state detection, gap mapping, and graph compilation reliably.

## Primary Users / Actors
- Backend developers building API services for the platform

## Core Outcomes
1. Users can authenticate and receive session tokens securely
2. Users can create and manage resources through the REST API

## Scope
### In Scope
- Authentication and session management
### Out of Scope
- Payment processing and billing

## Technology Summary
React with Next.js frontend and Express backend.

## System Architecture
Layered monolith following domain-driven design principles.

## Domains
- [[auth|Auth domain]]

## Runtime Entry Points
- `npm start` — HTTP server on port 3000

## External Systems
- Stripe for payment processing

## System-wide Invariants
- All writes are idempotent with retry support

## Current Risks / Legacy / Migration
None at this time.

## Active Changes
None.

## Where To Start
Read this page, then pick a domain from the Domains section.
""")
        # Architecture
        (kb_dir / "architecture").mkdir(parents=True, exist_ok=True)
        (kb_dir / "architecture" / "overview.md").write_text("# Overview\n\nThe system consists of three main services.")
        (kb_dir / "architecture" / "technology.md").write_text("# Technology\n\nTypeScript, Express, PostgreSQL.")
        (kb_dir / "domains" / "auth").mkdir(parents=True, exist_ok=True)
        (kb_dir / "domains" / "auth" / "auth.md").write_text("# Auth\n\nHandles authentication.")
        # Graph
        graph_dir = kb_dir / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "nodes.json").write_text("[]")
        (graph_dir / "edges.json").write_text("[]")
        (graph_dir / "file-index.json").write_text("{}")
        # Hash file with WRONG hash
        (graph_dir / "file-hashes.json").write_text(
            json.dumps({"src/index.ts": "0000000000000000000000000000000000000000000000000000000000000000"})
        )

        result = mod.classify(proj)
        assert result["state"] == "stale_kb"

    def test_not_stale_when_hash_matches(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_STATE_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        src_file = proj / "src" / "index.ts"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("export const x = 1")

        import hashlib
        real_hash = hashlib.sha256(src_file.read_bytes()).hexdigest()

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
tags: []
---

# Test

## Purpose
Test project that validates the Kode Brain onboarding pipeline end-to-end.
It exercises state detection, gap mapping, and graph compilation reliably.

## Primary Users / Actors
- Backend developers building API services for the platform

## Core Outcomes
1. Users can authenticate and receive session tokens securely
2. Users can create and manage resources through the REST API

## Scope
### In Scope
- Authentication and session management
### Out of Scope
- Payment processing and billing

## Technology Summary
React with Next.js frontend and Express backend.

## System Architecture
Layered monolith following domain-driven design principles.

## Domains
- [[auth|Auth domain]]

## Runtime Entry Points
- `npm start` — HTTP server on port 3000

## External Systems
- Stripe for payment processing

## System-wide Invariants
- All writes are idempotent with retry support

## Current Risks / Legacy / Migration
None at this time.

## Active Changes
None.

## Where To Start
Read this page, then pick a domain from the Domains section.
""")
        (kb_dir / "architecture").mkdir(parents=True, exist_ok=True)
        (kb_dir / "architecture" / "overview.md").write_text("# Overview\n\nThe system has several components.")
        (kb_dir / "architecture" / "technology.md").write_text("# Technology\n\nTypeScript, PostgreSQL, Redis.")
        (kb_dir / "domains" / "auth").mkdir(parents=True, exist_ok=True)
        (kb_dir / "domains" / "auth" / "auth.md").write_text("# Auth\n\nHandles authentication and authorization.")
        graph_dir = kb_dir / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "nodes.json").write_text("[]")
        (graph_dir / "edges.json").write_text("[]")
        (graph_dir / "file-index.json").write_text("{}")
        (graph_dir / "file-hashes.json").write_text(
            json.dumps({"src/index.ts": real_hash})
        )

        result = mod.classify(proj)
        assert result["state"] == "onboarded"


class TestSectionAwareEdges:
    """Edges must derive relationship from section context, not just node types."""

    def _make_kb(self, tmp_path: Path, pages: list[tuple[str, str]]) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        for rel_path, content in pages:
            full = kb_dir / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return kb_dir

    def test_used_by_reverses_direction(self, tmp_path: Path) -> None:
        """'## Used By' section should create depends_on from the linked node TO source."""
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("domains/orders/orders.md", """---
id: orders
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: orders
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/orders
  - status/active
---

# Orders

## Depends On
- [[payments|Payments]]

## Used By
- [[admin|Admin]]
"""),
            ("domains/payments/payments.md", """---
id: payments
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: payments
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/payments
  - status/active
---

# Payments
"""),
            ("domains/admin/admin.md", """---
id: admin
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: admin
source_files: []
last_updated: "2026-08-07"
tags:
  - type/domain
  - domain/admin
  - status/active
---

# Admin
"""),
        ])
        result = mod.compile_graph(kb)
        edges = {(e["from"], e["to"], e["type"]) for e in result["edges"]}

        # orders → payments : depends_on (Depends On section, forward)
        assert ("orders", "payments", "depends_on") in edges
        # admin → orders : depends_on (Used By section, reversed)
        assert ("admin", "orders", "depends_on") in edges
        # Should NOT have orders → admin (wrong direction)
        assert ("orders", "admin", "depends_on") not in edges

    def test_risks_section_creates_risky_for(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
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

## Risks
- [[auth-session-risk|Session risk]]
"""),
            ("domains/auth/risks/auth-session-risk.md", """---
id: auth-session-risk
type: caveat
status: needs_review
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
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

## Affects
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
        ])
        result = mod.compile_graph(kb)
        edges = {(e["from"], e["to"], e["type"]) for e in result["edges"]}

        # "## Risks" on auth page → risky_for from risk node to auth (reverse)
        assert ("auth-session-risk", "auth", "risky_for") in edges
        # "## Affects" on risk page → risky_for from risk to capability (forward)
        assert ("auth-session-risk", "auth-login", "risky_for") in edges


class TestArchitectureNodeType:
    """Architecture pages must compile as 'architecture' type, not 'domain'."""

    def test_architecture_not_domain(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        (kb_dir / "architecture").mkdir(parents=True, exist_ok=True)
        (kb_dir / "architecture" / "overview.md").write_text("""---
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
""")
        (kb_dir / "architecture" / "technology.md").write_text("""---
id: arch-technology
type: architecture_technology
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: test
source_files: []
last_updated: "2026-08-07"
tags: []
---

# Technology
""")

        result = mod.compile_graph(kb_dir)
        types = {n["type"] for n in result["nodes"]}
        assert "architecture" in types
        assert "domain" not in types  # architecture pages should not be domains


class TestStructuredManifestParsing:
    """Inventory must parse structured manifests, not just substring match."""

    def test_exact_package_match_from_json(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        (proj / "package.json").write_text(json.dumps({
            "name": "test",
            "dependencies": {"express": "^4.0", "pg": "^8.0"},
            "devDependencies": {"vitest": "^1.0", "typescript": "^5.0"},
        }))

        pkgs = mod._extract_package_names(proj)
        assert "express" in pkgs
        assert "pg" in pkgs
        assert "vitest" in pkgs
        assert "typescript" in pkgs

    def test_exact_match_from_pyproject(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        (proj / "pyproject.toml").write_text("""
[project]
name = "test"
dependencies = ["fastapi", "uvicorn", "sqlalchemy>=2.0"]
""")

        pkgs = mod._extract_package_names(proj)
        assert "fastapi" in pkgs
        assert "uvicorn" in pkgs
        assert "sqlalchemy" in pkgs

    def test_exact_match_from_go_mod(self, tmp_path: Path) -> None:
        mod = _load_script(_PROJECT_INVENTORY_PATH)
        proj = tmp_path / "test-project"
        proj.mkdir()
        (proj / "go.mod").write_text("""module example.com/app

go 1.21

require (
\tgithub.com/gin-gonic/gin v1.9.0
\tgithub.com/jackc/pgx/v5 v5.5.0
\tgithub.com/go-redis/redis/v8 v8.11.0
)
""")

        pkgs = mod._extract_package_names(proj)
        assert "gin" in pkgs or "gin-gonic" in pkgs
        assert "pgx" in pkgs or "pgx/v5" in pkgs
        assert "redis" in pkgs or "redis/v8" in pkgs


# ═══════════════════════════════════════════════════════════════════════════════
# Project History — timeline, incidents, milestones
# ═══════════════════════════════════════════════════════════════════════════════

_TIMELINE_PATH = _SCRIPTS_DIR / "timeline.py"


class TestTimeline:
    """Timeline generation from history records."""

    def _make_kb_with_history(self, tmp_path: Path) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)

        # Decision
        dec_dir = kb_dir / "decisions"
        dec_dir.mkdir(parents=True)
        (dec_dir / "2026-03-15-use-redis.md").write_text("""---
id: infra-2026-03-15-use-redis
type: decision
decision_state: superseded
date: "2026-03-15"
superseded_by:
  - infra-2026-08-01-use-valkey
---

# Decision: Use Redis for caching
""")
        (dec_dir / "2026-08-01-use-valkey.md").write_text("""---
id: infra-2026-08-01-use-valkey
type: decision
decision_state: active
date: "2026-08-01"
supersedes:
  - infra-2026-03-15-use-redis
---

# Decision: Migrate to Valkey
""")

        # Completed change
        changes_dir = kb_dir / "changes" / "completed"
        changes_dir.mkdir(parents=True)
        (changes_dir / "2026-07-20-migrate-sessions.md").write_text("""---
id: 2026-07-20-migrate-sessions
type: change
status: reconciled
outcome: success
started_at: "2026-07-15"
completed_at: "2026-07-20"
---

# Change: Migrate sessions to JWT
""")

        # Incident
        inc_dir = kb_dir / "incidents"
        inc_dir.mkdir(parents=True)
        (inc_dir / "2026-06-10-duplicate-capture.md").write_text("""---
id: payment-2026-06-10-duplicate-capture
type: incident
severity: high
status: resolved
started_at: "2026-06-10"
resolved_at: "2026-06-11"
domain: payment
---

# Incident: Duplicate Payment Capture
""")

        # Milestone
        ms_dir = kb_dir / "milestones"
        ms_dir.mkdir(parents=True)
        (ms_dir / "2026-04-01-mvp-launch.md").write_text("""---
id: 2026-04-01-mvp-launch
type: milestone
date: "2026-04-01"
significance: product
---

# Milestone: MVP Launched
""")

        return kb_dir

    def test_collects_all_record_types(self, tmp_path: Path) -> None:
        mod = _load_script(_TIMELINE_PATH)
        kb = self._make_kb_with_history(tmp_path)
        records = mod._collect_records(kb)
        types = {r["type"] for r in records}
        assert "decision" in types
        assert "change" in types
        assert "incident" in types
        assert "milestone" in types

    def test_sorts_by_date_descending(self, tmp_path: Path) -> None:
        mod = _load_script(_TIMELINE_PATH)
        kb = self._make_kb_with_history(tmp_path)
        records = mod._collect_records(kb)
        dates = [r["date"] for r in records if r["date"]]
        assert dates == sorted(dates, reverse=True)

    def test_generates_timeline_markdown(self, tmp_path: Path) -> None:
        mod = _load_script(_TIMELINE_PATH)
        kb = self._make_kb_with_history(tmp_path)
        timeline = mod.generate_timeline(kb)
        assert "# Project Timeline" in timeline
        assert "## 2026" in timeline
        assert "Duplicate Payment Capture" in timeline
        assert "MVP Launched" in timeline
        assert "Use Redis" in timeline
        assert "Migrate to Valkey" in timeline
        assert "Migrate sessions" in timeline

    def test_empty_kb_produces_empty_timeline(self, tmp_path: Path) -> None:
        mod = _load_script(_TIMELINE_PATH)
        kb = tmp_path / "docs" / "brain" / "projects" / "empty"
        kb.mkdir(parents=True)
        timeline = mod.generate_timeline(kb)
        assert "**Total records:** 0" in timeline


class TestCompileGraphWithHistory:
    """compile_graph handles incident and milestone node types."""

    def _make_kb(self, tmp_path: Path, pages: list[tuple[str, str]]) -> Path:
        kb_dir = tmp_path / "docs" / "brain" / "projects" / "test"
        kb_dir.mkdir(parents=True)
        for rel_path, content in pages:
            full = kb_dir / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return kb_dir

    def test_compiles_incident_as_node(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("incidents/payment-duplicate.md", """---
id: payment-duplicate
type: incident
severity: high
status: resolved
domain: payment
project: test
confidence: verified
provenance: human
knowledge_role: observed
last_updated: "2026-08-07"
tags:
  - type/incident
  - domain/payment
---

# Incident: Duplicate Capture

## Affects
- [[payment-capture|Capture capability]]
"""),
            ("domains/payment/capabilities/payment-capture.md", """---
id: payment-capture
type: capability
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: test
domain: payment
source_files: []
last_updated: "2026-08-07"
tags:
  - type/capability
  - domain/payment
  - status/active
---

# Capture
"""),
        ])
        result = mod.compile_graph(kb)
        types = {n["type"] for n in result["nodes"]}
        assert "incident" in types
        # Incident → capability edge should be risky_for
        edges = {(e["from"], e["to"], e["type"]) for e in result["edges"]}
        assert ("payment-duplicate", "payment-capture", "risky_for") in edges

    def test_compiles_milestone_as_node(self, tmp_path: Path) -> None:
        mod = _load_script(_COMPILE_GRAPH_PATH)
        kb = self._make_kb(tmp_path, [
            ("milestones/mvp-launch.md", """---
id: mvp-launch
type: milestone
date: "2026-04-01"
significance: product
project: test
confidence: verified
provenance: human
knowledge_role: intent
last_updated: "2026-08-07"
tags:
  - type/milestone
---

# Milestone: MVP Launched

## Related Decisions
- [[core-use-postgres|Use PostgreSQL]]
"""),
            ("decisions/core-use-postgres.md", """---
id: core-use-postgres
type: decision
decision_state: active
status: active
confidence: verified
provenance: human
knowledge_role: intent
project: test
domain: core
source_files: []
last_updated: "2026-08-07"
tags:
  - type/decision
  - domain/core
---

# Decision: Use PostgreSQL
"""),
        ])
        result = mod.compile_graph(kb)
        types = {n["type"] for n in result["nodes"]}
        assert "milestone" in types
        assert "decision" in types
