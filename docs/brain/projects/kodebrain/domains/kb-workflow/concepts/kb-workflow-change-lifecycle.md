---
id: kb-workflow-change-lifecycle
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-workflow
source_files:
  - docs/design/spec/workflow-model.md
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-workflow
  - status/active
---

# Change Lifecycle

Part of [[kb-workflow|Workflow domain]].

## Short Summary

The Change lifecycle governs how a material code change moves from intent through implementation to reconciled knowledge: `planned → in_progress → implemented → reconciled`. It is owned by the Workflow domain because Change is both a development process and a historical record.

## Why This Concept Exists

Without a change lifecycle, KB updates happen after code is written (if at all), and there is no trace from "we decided to do X" through "we did X" to "the KB now reflects X." The lifecycle ensures material changes leave a complete trail.

## How It Works

```text
Task arrives
  ↓
Read Project Contract + relevant domains
  ↓
Retrieve relevant history
  ↓
Create active change with change_state: planned       ← Workflow owns this
  ↓
Record architecture/decision impact
  ↓
Implement code (change_state: in_progress)
  ↓
Progress Log entries accumulate
  ↓
Harvest/review changed evidence
  ↓
Compare intended vs implementation
  ↓
Reconcile KB (change_state: implemented)
  ↓
Fill Outcome, Deviations, Lessons Learned
  ↓
Mark reconciled → move to changes/completed/          ← History owns completed record
  ↓
Regenerate timeline + events
```

| change_state | Meaning | Owner |
|---|---|---|
| `planned` | Intent recorded, implementation not started | Workflow |
| `in_progress` | Implementation underway | Workflow |
| `implemented` | Code complete, not yet reconciled with KB | Workflow |
| `reconciled` | KB updated, drift checked, lessons captured | Workflow → History (completed) |

## Where It Appears

Used by:
- [[kb-workflow-change-reconciliation|Change Reconciliation]] — the process that moves change through lifecycle states
- [[kb-workflow-onboard|Onboard]] — onboard itself may create an active change

Boundary with [[kb-history|History]]: Workflow owns the active Change process. History owns the completed Change record + all Decision/Incident lifecycle semantics.

## Common Misunderstanding

**`change_state` is not the same as KB `status`.** A change record carries `change_state: in_progress` while its KB `status` remains `active`. The `status` field describes knowledge quality; `change_state` describes process phase. These are separate fields, enforced in the schema.

**`reconciled` does not mean "perfect."** It means the KB has been updated to reflect the implementation, drift has been checked, and lessons have been captured. Some drift may remain as explicit drift items.

## Source Evidence

- `docs/design/spec/workflow-model.md` — "Change Lifecycle States" and full lifecycle diagram
- `docs/design/spec/governance.md` — "Boundary between Workflow and History" (GoV-003)

## Status Notes

Current design. vNext migration is implementing this lifecycle.

## Open Questions

None.
