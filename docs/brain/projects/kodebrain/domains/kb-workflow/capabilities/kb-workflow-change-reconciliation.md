---
id: kb-workflow-change-reconciliation
type: capability
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
  - type/capability
  - domain/kb-workflow
  - status/active
---

# Change Reconciliation

Part of [[kb-workflow|Workflow domain]].

## Short Summary

After implementation, reconcile the intended change with what was actually built — compare intent vs implementation, update KB pages, surface drift, capture lessons, and move the change to completed.

## Why It Exists

Without reconciliation, the KB drifts from reality. Code changes but the KB stays frozen. Over time, the KB becomes untrustworthy. Reconciliation ensures every material change updates the knowledge map.

## How It Works

1. Harvest/review changed source files
2. Compare intended change (from active change record) vs actual implementation
3. Update affected KB pages (domain hubs, capabilities, flows, concepts)
4. Surface any drift between intent and implementation
5. Fill in change record: Outcome, Deviations From Plan, Lessons Learned
6. Mark change `change_state: reconciled`
7. Move change record from `changes/active/` to `changes/completed/`
8. Regenerate timeline + events

## Runtime Path

See [[kb-workflow-change-reconciliation-flow|Change Reconciliation Flow]].

## API Entry Point

Not a user-facing command. Triggered by agent after implementation.

## Related Concepts

- [[kb-workflow-change-lifecycle|Change Lifecycle]] — reconciliation is the final lifecycle state
- [[kb-core-drift|Drift]] — surfaced during reconciliation
- [[kb-history-lesson-promotion|Lesson Promotion]] — incidents → decisions → invariants

## Related Models

- Change record — moves from active to completed during reconciliation

## Known Risks

None currently flagged.

## Source Evidence

- `docs/design/spec/workflow-model.md` — "Change-First Workflow" section with reconciliation steps
- `docs/design/spec/workflow-model.md` — "Change Record Structure" with Outcome, Deviations, Lessons Learned

## Status Notes

Active. vNext implementation in progress.

## Open Questions

None.
