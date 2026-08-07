---
id: kb-history-decision-lifecycle
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-history
source_files:
  - docs/design/spec/history-model.md
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-history
  - status/active
---

# Decision Lifecycle

Part of [[kb-history|History domain]].

## Short Summary

Decision lifecycle is owned by History: `active → superseded → deprecated`. A new decision may `supersede` an older one via lineage; the old decision is preserved, never rewritten. Superseded state is derived by the compiler.

## Why This Concept Exists

Decisions change over time. A team chooses X, later chooses Y. Without lineage, you cannot trace why Y was chosen and what X was. With lineage, the trail is preserved — the old decision remains as evidence of the path taken.

## How It Works

| decision_state | Meaning |
|---|---|
| `active` | Current governing decision for this concern |
| `superseded` | Replaced by a newer decision via lineage; preserved for trace |
| `deprecated` | Intentionally retired without direct replacement; concern may no longer apply |

Lineage mechanism:
```yaml
# New decision (active)
decision_state: active
supersedes:
  - old-decision-id
```

The compiler derives `superseded_by` on the old decision and sets its effective `decision_state` to `superseded`. The old decision body is never rewritten.

## Where It Appears

Used by:
- [[kb-history-decision-lineage-flow|Decision Lineage Flow]] — supersede → derive → preserve
- [[kb-history-timeline-generation|Timeline Generation]] — lineage appears in timeline

Also relevant in [[kb-workflow-change-lifecycle|Change Lifecycle]] — the boundary: Workflow owns Change lifecycle; History owns Decision lifecycle.

## Common Misunderstanding

**`superseded` is not deleted.** A superseded decision remains in the KB as a historical record. It is not removed. Its `decision_state` reflects that it is no longer current, but the knowledge is preserved.

**`deprecated` means "this concern no longer applies."** It is different from `superseded` — there is no replacement decision because the concern itself is obsolete.

## Source Evidence

- `docs/design/spec/history-model.md` — "Decision Lineage" and "Decision Lifecycle" sections
- `docs/design/spec/governance.md` — Workflow/History boundary: History owns Decision lifecycle

## Status Notes

Current design. No migration needed.

## Open Questions

None.
