---
id: kb-substrate
type: domain
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: kodebrain
domain: kb-substrate
source_files:
  - kodebrain/skill/scripts/harvest.py
  - kodebrain/skill/scripts/compile_graph.py
  - kodebrain/skill/scripts/timeline.py
  - kodebrain/skill/scripts/project_state.py
  - kodebrain/skill/scripts/project_inventory.py
  - kodebrain/skill/scripts/migrate_kb.py
  - kodebrain/skill/scripts/spec_validator.py
  - kodebrain/skill/scripts/frontmatter.py
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/domain
  - domain/kb-substrate
  - status/active
---

# Substrate Domain

## Responsibility

Deterministic Python scripts that provide the computational substrate for Kode Brain — source harvesting, graph compilation, timeline generation, project state classification, inventory, KB migration, and schema validation. These scripts are called by the agent during skill execution; they are not user-facing.

## Owns

- `harvest.py` — deterministic source extraction: exports, routes, imports, imported_by, status signals, test detection
- `compile_graph.py` — Markdown wiki-link extraction → nodes.json + edges.json + file-index.json
- `timeline.py` — history record → timeline.md + events.json
- `project_state.py` — project state classifier + knowledge gap map
- `project_inventory.py` — file inventory + topology
- `migrate_kb.py` — legacy KB format migration (hierarchical → flat IDs, camelCase → snake_case)
- `spec_validator.py` — validate KB pages against node/edge schema
- `frontmatter.py` — YAML frontmatter parser

## Does Not Own

- When scripts are called — see [[kb-workflow|Workflow domain]] (SKILL.md behavior)
- What the scripts produce semantically — see [[kb-core|Core domain]] (knowledge model)
- KB page layout — see [[kb-project|Project domain]]

## Depends On

- [[kb-core|Core domain]] — harvest extracts symbols, compile_graph infers edge types from knowledge model
- [[kb-project|Project domain]] — compile_graph expects flat IDs and standard paths

## Used By

- [[kb-workflow|Workflow domain]] — onboard, scan, update all call substrate scripts
- [[kb-history|History domain]] — timeline generation calls timeline.py

## Core Concepts

- [[kb-substrate-harvest-escalation|Harvest Escalation Model]] — Level 0–4 source reading
- [[kb-substrate-sha-detection|SHA-256 Change Detection]] — hash-based dirty file detection

## Capabilities

- [[kb-substrate-harvest|Source Harvest]] — extract symbols from source files
- [[kb-substrate-compile-graph|Graph Compilation]] — compile Markdown → graph JSON
- [[kb-substrate-timeline|Timeline Generation]] — compile history → timeline + events
- [[kb-substrate-state-classification|State Classification]] — detect project onboarding state
- [[kb-substrate-migration|KB Migration]] — migrate legacy format
- [[kb-substrate-validation|Schema Validation]] — validate KB against schemas

## Core Flows

None — scripts are single-invocation, not multi-step flows.

## Data Ownership

| Model | Ownership | Shared With |
|---|---|---|
| Harvest output (JSON) | owned | kb-core (consumes) |
| Graph indexes | owned (generates) | kb-core (defines semantics) |
| File hashes | owned | kb-workflow (consumes for scan/update) |

## Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `harvest.py <root>` | Script | Full harvest |
| `harvest.py <root> --hashes <file>` | Script | Incremental harvest (dirty files only) |
| `harvest.py <root> --files f1 f2` | Script | Targeted harvest (specific files) |
| `harvest.py --build-index <nodes.json>` | Script | Build file-index.json |
| `harvest.py --benchmark <kb_dir> --source-root <root>` | Script | Benchmark metrics |
| `compile_graph.py <kb_dir>` | Script | Compile graph indexes |
| `timeline.py <kb_dir>` | Script | Generate timeline + events |

## Invariants

- Scripts are deterministic: same input → same output
- Scripts use only Python stdlib (no pip dependencies)
- Scripts are called as subprocesses, not imported as libraries
- Markdown is canonical; graph JSON is derived and rebuildable

## Legacy / Migration

- `migrate_kb.py` handles legacy hierarchical IDs → flat format
- Substrate modules not yet fully integrated into SKILL.md onboard workflow — SKILL.md references them but default code path is LLM-driven (vNext work in progress)

## Risks

- [[kb-substrate-llm-fallback-risk|LLM Fallback Risk]] — substrate scripts exist but onboard workflow may fall back to LLM-driven mapping instead of using deterministic scripts

## Source Areas

| Path | Purpose |
|---|---|
| `kodebrain/skill/scripts/harvest.py` | Source harvest |
| `kodebrain/skill/scripts/compile_graph.py` | Graph compiler |
| `kodebrain/skill/scripts/timeline.py` | Timeline generator |
| `kodebrain/skill/scripts/project_state.py` | State classifier |
| `kodebrain/skill/scripts/project_inventory.py` | File inventory |
| `kodebrain/skill/scripts/migrate_kb.py` | KB migration |
| `kodebrain/skill/scripts/spec_validator.py` | Schema validator |
| `kodebrain/skill/scripts/frontmatter.py` | Frontmatter parser |

## Open Questions

- Substrate integration into onboard workflow — currently SKILL.md references scripts but the default path is LLM-driven. vNext implementation plan tracks this.
