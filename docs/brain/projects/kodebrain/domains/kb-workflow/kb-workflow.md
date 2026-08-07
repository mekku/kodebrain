---
id: kb-workflow
type: domain
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-workflow
source_files:
  - docs/design/spec/workflow-model.md
  - kodebrain/skill/SKILL.md
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/domain
  - domain/kb-workflow
  - status/active
---

# Workflow Domain

## Responsibility

Define what *processes* mutate or use the knowledge base — onboarding (greenfield + brownfield), change lifecycle (planned → in_progress → implemented → reconciled), status vs lifecycle separation, and agent reading/update behavior.

## Owns

- Unified onboarding command (`/kodebrain onboard`) — idempotent, resumable, gap-driven
- Project state detection: greenfield, new_brownfield, partial_kb, legacy_kb, stale_kb, onboarded
- Greenfield onboarding: intent interview → project contract → architecture skeleton → agent instructions
- Brownfield onboarding: discover intent → scan evidence → map domains → surface drift
- Change lifecycle states: `planned`, `in_progress`, `implemented`, `reconciled`
- Change record structure: Intent, Why, Affected Domains, Architecture Impact, Progress Log, Outcome, Deviations, Lessons Learned
- Reconciliation: compare intended change vs implementation → update KB → move to completed
- Agent reading behavior: KB first, source when needed
- Agent update behavior: create active change before implementation, reconcile after

## Does Not Own

- What knowledge *means* (provenance, confidence, drift) — see [[kb-core|Core domain]]
- Change/decision/incident record schemas — see [[kb-history|History domain]]
- Decision lifecycle (active/superseded/deprecated) — see [[kb-history|History domain]]
- Incident lifecycle (ongoing/mitigated/resolved) — see [[kb-history|History domain]]
- Spec authority and precedence — see [[kb-governance|Governance domain]]

Boundary clarification: Workflow owns Change lifecycle because Change is both an active development process AND a historical record. History owns the completed Change record + Decision/Incident lifecycle.

## Depends On

- [[kb-core|Core domain]] — knowledge model for reading/writing KB pages
- [[kb-project|Project domain]] — page layout, naming conventions
- [[kb-history|History domain]] — completed change records, decision lineage
- [[kb-substrate|Substrate domain]] — harvest, project_state, project_inventory scripts
- [[kb-governance|Governance domain]] — spec authority during onboarding

## Used By

- All agent workflows — every code change follows change lifecycle
- `/kodebrain onboard` — primary user-facing command

## Core Concepts

- [[kb-workflow-change-lifecycle|Change Lifecycle]] — planned → in_progress → implemented → reconciled
- [[kb-workflow-status-lifecycle-separation|Status vs Lifecycle Separation]] — KB status ≠ process phase
- [[kb-workflow-greenfield-mode|Greenfield Mode]] — onboarding before code exists
- [[kb-workflow-brownfield-mode|Brownfield Mode]] — onboarding existing codebase

## Capabilities

- [[kb-workflow-onboard|Onboard]] — unified project onboarding
- [[kb-workflow-change-reconciliation|Change Reconciliation]] — reconcile intent with implementation

## Core Flows

- [[kb-workflow-onboard-flow|Onboard Flow]] — detect state → discover intent → harvest → map → report
- [[kb-workflow-change-reconciliation-flow|Change Reconciliation Flow]] — compare → update → surface drift → complete

## Data Ownership

| Model | Ownership | Shared With |
|---|---|---|
| Change record (active) | owned | kb-history (completed) |

## Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `/kodebrain onboard [path]` | Skill command | Primary onboarding |
| `/kodebrain scan [path]` | Skill command | Re-scan changed files |
| `/kodebrain update [--diff] [--files]` | Skill command | Update KB from code changes |
| `project_state.py` | Script | Classify project state + gap map |

## Invariants

- `onboard` is idempotent — running it twice must not corrupt existing KB
- Change lifecycle is separate from KB `status` field
- Active changes record intent before implementation, not after
- Never edit current-state architecture to pretend unimplemented future already exists
- Workflow owns Change lifecycle; History owns Decision + Incident lifecycle

## Legacy / Migration

- vNext onboard workflow replaces older `init` + `scan` split
- `init` is a legacy alias that delegates to `onboard` internally

## Risks

None currently flagged.

## Source Areas

| Path | Purpose |
|---|---|
| `docs/design/spec/workflow-model.md` | Canonical workflow spec |
| `kodebrain/skill/SKILL.md` | Agent behavior contract |
| `kodebrain/skill/scripts/project_state.py` | State classifier |
| `kodebrain/skill/scripts/project_inventory.py` | File inventory |

## Open Questions

None at this time.
