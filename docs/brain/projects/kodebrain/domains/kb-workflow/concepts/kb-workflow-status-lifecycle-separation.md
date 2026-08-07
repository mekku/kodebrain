---
id: kb-workflow-status-lifecycle-separation
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: reference
project: kodebrain
domain: kb-workflow
canonical_source:
  path: docs/design/spec/workflow-model.md
  anchor: Status vs Lifecycle State
source_files: []
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-workflow
  - status/active
---

# Status vs Lifecycle Separation

Part of [[kb-workflow|Workflow domain]].

## Canonical Definition

See: [docs/design/spec/workflow-model.md#Status vs Lifecycle State]

Generic KB `status` describes knowledge quality (`active`, `stale`, `needs_review`). Lifecycle state is separate and type-specific (`change_state`, `decision_state`, `incident_state`). They must never be conflated.

## Project Context

In Kode Brain, every record-type page carries both `status` (knowledge quality) and its type-specific lifecycle field (process phase). A page can be `status: active` + `change_state: in_progress` — the KB page is current, the change is underway. A decision can be `status: stale` + `decision_state: active` — still governing but unreviewed.

The canonical lifecycle field owners:
- Change → Workflow (`change_state`)
- Decision → History (`decision_state`)
- Incident → History (`incident_state`)

This separation is enforced in `schema/node.schema.json`.

## Relationships

- [[kb-workflow-change-lifecycle|Change Lifecycle]] — change-specific lifecycle states
- [[kb-history-decision-lifecycle|Decision Lifecycle]] — decision-specific lifecycle states
- [[kb-history-incident-lifecycle|Incident Lifecycle]] — incident-specific lifecycle states

## Evidence

- `docs/design/spec/workflow-model.md` — Status vs Lifecycle State with ownership table
- `schema/node.schema.json` — separate `status` and lifecycle fields
