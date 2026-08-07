---
id: kb-core
type: domain
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-core
source_files:
  - docs/design/spec/knowledge-model.md
  - schema/node.schema.json
  - schema/edge.schema.json
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/domain
  - domain/kb-core
  - status/active
---

# Core Domain

## Responsibility

Define what knowledge *means* in Kode Brain — the mental model (three layers), truth model (intent vs observed), provenance and confidence as separate axes, harvest policy, drift detection, and graph compilation from Markdown wiki-links.

## Owns

- Three-layer knowledge model: Project Contract → Knowledge Map → Evidence
- Provenance labels: `human`, `project_document`, `source_code`, `configuration`, `runtime`, `test`, `git`, `generated`
- Confidence labels: `verified`, `supported`, `inferred`, `ambiguous`, `stale`, `needs_human_review`
- Knowledge role labels: `intent`, `observed`, `mixed`
- Drift detection: intent vs observed disagreement → drift record
- Harvest policy: escalation model (Level 0–4), deterministic harvest as first step
- Graph compilation: Markdown wiki-links → nodes.json + edges.json
- Field contracts: `schema/node.schema.json`, `schema/edge.schema.json`

## Does Not Own

- Project structure and layout — see [[kb-project|Project domain]]
- Onboarding workflow and change lifecycle — see [[kb-workflow|Workflow domain]]
- Decision/incident records and timeline — see [[kb-history|History domain]]
- Precedence rules and spec authority — see [[kb-governance|Governance domain]]
- Deterministic script implementation — see [[kb-substrate|Substrate domain]]

## Depends On

- [[kb-project|Project domain]] — node ID format, page layout for writing knowledge pages
- [[kb-substrate|Substrate domain]] — harvest.py for source evidence, compile_graph.py for graph compilation
- [[kb-governance|Governance domain]] — spec authority for canonical ownership

## Used By

- [[kb-workflow|Workflow domain]] — onboarding and change reconciliation read/write KB pages
- [[kb-history|History domain]] — timeline generation references KB nodes
- All domains — every domain produces knowledge pages that follow this domain's model

## Core Concepts

- [[kb-core-knowledge-layers|Knowledge Layers]] — Project Contract, Knowledge Map, Evidence
- [[kb-core-provenance|Provenance]] — where a claim came from
- [[kb-core-confidence|Confidence]] — how trustworthy a claim is
- [[kb-core-knowledge-role|Knowledge Role]] — intent vs observed vs mixed
- [[kb-core-drift|Drift]] — disagreement between intent and observation
- [[kb-core-harvest-policy|Harvest Policy]] — source-reading escalation model

## Capabilities

- [[kb-core-graph-compilation|Graph Compilation]] — Markdown → graph JSON
- [[kb-core-drift-detection|Drift Detection]] — surface intent vs observation gaps
- [[kb-core-harvest|Harvest]] — deterministic source extraction

## Core Flows

- [[kb-core-graph-compile-flow|Graph Compile Flow]] — wiki-link extraction → edge inference → JSON output

## Data Ownership

| Model | Ownership | Shared With |
|---|---|---|
| [[kb-core-knowledge-node-model|Knowledge Node]] | owned | all domains |
| [[kb-core-knowledge-edge-model|Knowledge Edge]] | owned | all domains |

## Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `compile_graph.py` | Script | Markdown → nodes.json + edges.json + file-index.json |
| `harvest.py` | Script | Source file → export/import/route/status briefs |
| `spec_validator.py` | Script | Validate KB pages against node schema |

## Invariants

- Markdown knowledge pages are canonical; graph JSON is derived
- Provenance and confidence are separate fields — never conflated
- Human notes in `<!-- human-note -->` blocks are never overwritten
- A claim without source evidence must be marked `inferred`
- Intent and observed reality disagreement → drift record, not silent resolution

## Legacy / Migration

- vNext schemas (node.schema.json, edge.schema.json) are current
- Hierarchical node IDs (`auth/login-flow`) are legacy — migrated to flat (`auth-login-flow`) by migrate_kb.py

## Risks

None currently flagged.

## Source Areas

| Path | Purpose |
|---|---|
| `docs/design/spec/knowledge-model.md` | Canonical knowledge model spec |
| `schema/node.schema.json` | Node field contract |
| `schema/edge.schema.json` | Edge field contract |
| `kodebrain/skill/scripts/compile_graph.py` | Graph compiler implementation |
| `kodebrain/skill/scripts/harvest.py` | Harvest implementation |
| `kodebrain/skill/scripts/spec_validator.py` | Schema validator |

## Open Questions

None at this time.
