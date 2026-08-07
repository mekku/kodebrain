---
id: kb-workflow-change-lifecycle
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: reference
project: kodebrain
domain: kb-workflow
canonical_source:
  path: docs/design/spec/workflow-model.md
  anchor: Change Lifecycle States
source_files: []
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-workflow
  - status/active
---

# Change Lifecycle

Part of [[kb-workflow|Workflow domain]].

## Canonical Definition

See: [docs/design/spec/workflow-model.md#Change Lifecycle States]

The Change lifecycle governs how a material code change moves from intent through implementation to reconciled knowledge: `planned → in_progress → implemented → reconciled`. Owned by Workflow because Change is both a development process and a historical record.

## Project Context

Kode Brain's change-first workflow requires creating an active change record before implementation begins. The lifecycle ensures material changes leave a complete trail from intent to reconciled knowledge.

Boundary with [[kb-history|History]]: Workflow owns the active Change process. History owns the completed Change record and all Decision/Incident lifecycle semantics.

**`change_state` is not KB `status`.** A change record carries `change_state: in_progress` while its KB `status` remains `active`. `status` describes knowledge quality; `change_state` describes process phase. These are separate fields.

**`reconciled` does not mean "perfect."** It means the KB has been updated to reflect implementation, drift has been checked, and lessons captured. Some drift may remain as explicit drift items.

## Relationships

- [[kb-workflow-change-reconciliation|Change Reconciliation]] — the process that moves change through lifecycle states
- [[kb-workflow-onboard|Onboard]] — onboard itself may create an active change
- [[kb-history|History]] — boundary: History owns completed Change record

## Evidence

- `docs/design/spec/workflow-model.md` — Change Lifecycle States and full lifecycle diagram
- `docs/design/spec/governance.md` — Boundary between Workflow and History
