---
id: kodebrain
type: project
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
source_files: []
last_updated: "2026-08-07"
last_reviewed: "2026-08-07"
tags:
  - type/project
  - status/active
---

# Kode Brain

## Purpose

Kode Brain is a living project knowledge and coordination system for software projects. It converts an imperfect, growing codebase into a structured knowledge map so humans and AI agents can understand and modify the system without rediscovering everything from scratch.

It answers four questions:
1. What SHOULD the system be? — Project Contract, architecture, domains, invariants
2. What IS the system? — Source, config, runtime, tests
3. What are we CHANGING? — Active changes, drift
4. HOW DID WE GET HERE? — Completed changes, decisions, incidents, milestones

## Primary Users / Actors

- Human developers and project owners who need orientation and design context
- Coding agents that need structured knowledge before editing source
- Review and maintenance agents that need to verify intent vs implementation
- Future contributors who must understand the project without rediscovering it

## Core Outcomes

1. A project can be onboarded from greenfield (no code) or brownfield (existing codebase) with a single idempotent command
2. The knowledge map stays current through deterministic harvest, targeted source reading, and agent-driven updates
3. Intent and observed reality are tracked separately — disagreements surface as drift, not silent overwrites
4. Material changes leave a trace from intent through implementation to reconciled knowledge
5. Accumulated history (decisions, incidents, completed changes) prevents repeated mistakes

## Scope

### In Scope

- Project knowledge mapping: domains, capabilities, flows, concepts, models, APIs, risks
- Structured evidence: source symbols, config, runtime signals, git history
- Drift detection between intended architecture and observed implementation
- Change-first workflow: record intent before implementation, reconcile after
- Project history: decisions (with lineage), incidents, milestones, generated timeline
- Markdown-first canonical knowledge with compiled graph indexes
- Greenfield project definition via intent interview
- Progressive mapping for large codebases
- Multi-platform agent instruction installation (Claude Code, Cursor, Windsurf, etc.)

### Out of Scope

- Automatic code rewriting or deletion
- Runtime behavior guarantees from static analysis alone
- Exhaustive documentation of every trivial function
- Database service requirement
- Obsidian requirement (optional graph view)

## Technology Summary

| Role | Technology |
|---|---|
| Language | Python 3.9+ |
| Package | pip-installable (`kodebrain`) |
| Build | hatchling |
| Schema | JSON Schema (draft 2020-12) |
| Testing | Pytest |
| Storage | Flat Markdown + JSON files (no database required) |
| Version control | Git (SHA-256 file hashes for change detection) |

## System Architecture

Kode Brain is a CLI tool + Claude Code skill. The skill (`kodebrain/skill/SKILL.md`) defines agent behavior. Deterministic Python scripts (`kodebrain/skill/scripts/`) provide the substrate: harvest, compile_graph, project_inventory, project_state, migrate_kb, timeline, spec_validator, frontmatter parser.

Knowledge is stored as Markdown pages with YAML frontmatter. Graph indexes (nodes.json, edges.json, file-index.json) are compiled from Markdown — Markdown is canonical, JSON is derived.

Specification authority is a tree: `docs/design/spec.md` (root) delegates to 5 canonical child specs under `docs/design/spec/`.

## Domains

- [[kb-core|Core domain]] — knowledge model, provenance, confidence, drift
- [[kb-workflow|Workflow domain]] — onboarding, change lifecycle, agent behavior
- [[kb-history|History domain]] — decisions, incidents, milestones, events, timeline
- [[kb-project|Project domain]] — structure, layout, architecture, naming, IDs
- [[kb-governance|Governance domain]] — precedence, compatibility, spec authority
- [[kb-substrate|Substrate domain]] — deterministic scripts (harvest, compile, inventory, migrate, timeline)

## Runtime Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `kodebrain` | CLI | Install skill and platform configs (`kodebrain install`) |
| `/kodebrain onboard` | Skill | Unified onboarding command |
| `harvest.py` | Script | Deterministic source extraction |
| `compile_graph.py` | Script | Markdown → graph JSON compiler |
| `project_state.py` | Script | Project state classifier + gap map |
| `timeline.py` | Script | History timeline + events generation |

## External Systems

None required at runtime. Kode Brain operates on local files only. Optional Obsidian integration for graph visualization.

## System-wide Invariants

- Markdown knowledge pages are canonical; graph JSON is derived and rebuildable
- Every concept has exactly one canonical specification owner
- Confidence and provenance are separate fields — never conflated
- Status (KB quality) and lifecycle state (process phase) are separate fields
- Human notes in `<!-- human-note -->` blocks are never overwritten
- History records are append-only; superseded decisions are preserved, not rewritten

## Current Risks / Legacy / Migration

- vNext migration in progress: schemas, templates, and compilers have been updated; SKILL.md is current
- Older design docs (taxonomy.md, skills.md, agents.md, workflows.md) are historical — superseded by canonical specs
- Legacy KB format (hierarchical IDs, camelCase fields) handled by `migrate_kb.py`
- Substrate modules (compile_graph, project_state, etc.) not yet integrated into onboard workflow — SKILL.md references them but the default code path is LLM-driven

## Active Changes

- [[2026-08-07-onboard-validation-canonical-projection|Onboard Validation Gate + Canonical Projection]]

## Where To Start

1. Read `docs/design/spec.md` for the canonical product specification
2. Read relevant domain pages under `docs/brain/projects/kodebrain/domains/`
3. Check `changes/active/` for in-progress work
4. Use `/kodebrain reading-pack "<task>"` for focused context
