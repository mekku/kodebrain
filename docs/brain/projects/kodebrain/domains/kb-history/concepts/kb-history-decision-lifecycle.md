---
id: kb-history-decision-lifecycle
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: reference
project: kodebrain
domain: kb-history
canonical_source:
  path: docs/design/spec/history-model.md
  anchor: Decision Lifecycle
source_files: []
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-history
  - status/active
---

# Decision Lifecycle

Part of [[kb-history|History domain]].

## Canonical Definition

See: [docs/design/spec/history-model.md#Decision Lifecycle]

Decision lifecycle is owned by History: `active → superseded → deprecated`. A new decision may `supersede` an older one via lineage; the old decision is preserved, never rewritten. Superseded state is derived by the compiler.

## Project Context

Kode Brain tracks architectural decisions through their full lifecycle. The compiler derives `superseded_by` on old decisions when a newer decision declares `supersedes`. Old decision bodies are never rewritten — the trail is preserved as evidence.

Lineage mechanism:
```yaml
# New decision (active)
decision_state: active
supersedes:
  - old-decision-id
```

Boundary: Workflow owns Change lifecycle; History owns Decision lifecycle. See [[kb-workflow-change-lifecycle|Change Lifecycle]].

## Relationships

- [[kb-history-decision-lineage-flow|Decision Lineage Flow]] — supersede → derive → preserve
- [[kb-history-timeline-generation|Timeline Generation]] — lineage appears in timeline
- [[kb-workflow-change-lifecycle|Change Lifecycle]] — Workflow/History boundary

## Evidence

- `docs/design/spec/history-model.md` — Decision Lifecycle and Decision Lineage sections
- `docs/design/spec/governance.md` — Workflow/History boundary: History owns Decision lifecycle
