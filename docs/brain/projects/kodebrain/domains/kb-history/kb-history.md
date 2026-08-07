---
id: kb-history
type: domain
status: active
confidence: supported
provenance: project_document
knowledge_role: mixed
project: kodebrain
domain: kb-history
source_files:
  - docs/design/spec/history-model.md
  - kodebrain/skill/scripts/timeline.py
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/domain
  - domain/kb-history
  - status/active
---

# History Domain

## Responsibility

Answer the 4th Kode Brain question: **HOW DID WE GET HERE?** Owns temporal record types (decisions, incidents, milestones, completed changes), their lifecycle semantics, decision lineage, timeline/events generation, and history retrieval in agent workflows.

## Owns

- Four semantic record types: Change (completed), Decision, Incident, Milestone
- Decision lifecycle: `active`, `superseded`, `deprecated`
- Incident lifecycle: `ongoing`, `mitigated`, `resolved`
- Decision lineage: `supersedes` (stored) → `superseded_by` (derived by compiler)
- Incident record structure: what happened, root cause, why design allowed it, lesson, guardrail
- History retrieval: agents must consult history before material changes
- Reading pack "Relevant History" section
- Generated artifacts: `history/timeline.md`, `history/events.json`
- Append-only rule: records are preserved, never rewritten

## Does Not Own

- Active change process lifecycle (planned → in_progress → implemented) — see [[kb-workflow|Workflow domain]]
- When to create a change record — see [[kb-workflow|Workflow domain]]
- Reconciliation process — see [[kb-workflow|Workflow domain]]
- Project structure for history files — see [[kb-project|Project domain]]

Boundary: History owns Decision/Incident lifecycle + completed Change records. Workflow owns active Change process.

## Depends On

- [[kb-core|Core domain]] — node references in incident `linked_nodes`
- [[kb-project|Project domain]] — file layout for decisions/, incidents/, milestones/
- [[kb-substrate|Substrate domain]] — timeline.py for generation
- [[kb-workflow|Workflow domain]] — completed changes flow into history

## Used By

- [[kb-workflow|Workflow domain]] — agents consult history before changes
- Reading pack generation — Relevant History section
- All domains — decisions that affect them are recorded here

## Core Concepts

- [[kb-history-decision-lifecycle|Decision Lifecycle]] — active → superseded → deprecated
- [[kb-history-incident-lifecycle|Incident Lifecycle]] — ongoing → mitigated → resolved
- [[kb-history-decision-lineage|Decision Lineage]] — supersedes chain
- [[kb-history-append-only|Append-Only Rule]] — records preserved, never rewritten
- [[kb-history-lesson-promotion|Lesson Promotion]] — incident → decision → invariant

## Capabilities

- [[kb-history-timeline-generation|Timeline Generation]] — compile timeline.md + events.json
- [[kb-history-history-retrieval|History Retrieval]] — find relevant history before changes

## Core Flows

- [[kb-history-decision-lineage-flow|Decision Lineage Flow]] — supersede → derive → preserve old

## Data Ownership

| Model | Ownership | Shared With |
|---|---|---|
| Decision record | owned | — |
| Incident record | owned | — |
| Milestone record | owned | — |
| Change record (completed) | owned | kb-workflow (active) |

## Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `timeline.py` | Script | Generate timeline.md + events.json |
| `history/events.json` | Data | Temporal index for agent retrieval |
| `history/timeline.md` | Data | Human-readable chronological timeline |

## Invariants

- History records are append-oriented — never rewritten
- Superseded decisions are preserved; `superseded_by` is derived
- Lesson promotion path: Incident → Decision → Invariant
- History is not current truth — lessons must be promoted to constrain future behavior
- Accumulated history grows with project age — this is intentional

## Legacy / Migration

- vNext history model replaces flat change logs
- `docs/design/project-history.md` is historical design rationale, not current spec

## Risks

None currently flagged.

## Source Areas

| Path | Purpose |
|---|---|
| `docs/design/spec/history-model.md` | Canonical history spec |
| `kodebrain/skill/scripts/timeline.py` | Timeline generator |
| `docs/brain/projects/kodebrain/history/` | Generated timeline + events |
| `docs/brain/projects/kodebrain/decisions/` | Decision records |
| `docs/brain/projects/kodebrain/incidents/` | Incident records |

## Open Questions

None at this time.
