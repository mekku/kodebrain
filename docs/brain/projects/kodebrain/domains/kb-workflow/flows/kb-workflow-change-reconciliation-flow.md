---
id: kb-workflow-change-reconciliation-flow
type: flow
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
  - type/flow
  - domain/kb-workflow
  - status/active
---

# Change Reconciliation Flow

Part of [[kb-workflow|Workflow domain]]. Implements [[kb-workflow-change-reconciliation|Change Reconciliation]].

## Short Summary

Agent completes implementation → harvest changed files → compare intent vs implementation → update KB pages → surface drift → fill Outcome/Deviations/Lessons → mark reconciled → move to completed → regenerate timeline.

## Entry Point

| Field | Value |
|---|---|
| Type | `agent_workflow` |
| Value | Post-implementation trigger |
| Handler | Agent following change lifecycle |

## Steps

| # | Description | Symbol | Side Effects |
|---|---|---|---|
| 1 | Harvest/review changed source files | `harvest.py --files <changed>` or `git diff` | produces updated source briefs |
| 2 | Compare intended change vs implementation | Agent compares active change record vs harvest output | identifies matches and deviations |
| 3 | Update affected KB pages | Agent writes domain/capability/flow pages | sets `confidence: supported` on updated pages |
| 4 | Surface drift (if any) | Agent writes `reports/drift.md` | creates drift items for intent/observation gaps |
| 5 | Fill change record: Outcome | Agent writes change record | Outcome: success / partial / abandoned / rolled_back |
| 6 | Fill change record: Deviations From Plan | Agent writes change record | what differed from intent |
| 7 | Fill change record: Lessons Learned | Agent writes change record | what to do differently next time |
| 8 | Fill change record: Follow-ups + Regressions | Agent writes change record | known issues introduced |
| 9 | Mark change `change_state: reconciled` | Agent updates frontmatter | change transitions to complete |
| 10 | Move to `changes/completed/` | Agent moves file | active → completed |
| 11 | Regenerate timeline + events | `timeline.py <kb_dir>` | updates `history/timeline.md` + `history/events.json` |

## Data Movement

| From | To | Via |
|---|---|---|
| Changed source files | Harvest briefs | `harvest.py` |
| Active change record + harvest briefs | Updated KB pages | Agent (comparison + writing) |
| Updated KB pages + completed change | `history/events.json` | `timeline.py` |

## Cache / State Behavior

- `file-hashes.json` updated with new hashes after reconciliation
- Drift items are additive — they accumulate in `reports/drift.md`
- Completed change records are preserved permanently

## Concepts Required

- [[kb-workflow-change-lifecycle|Change Lifecycle]] — reconciliation is the final state
- [[kb-core-drift|Drift]] — surfaced during step 4
- [[kb-workflow-status-lifecycle-separation|Status vs Lifecycle]] — change goes `reconciled`, KB `status` stays appropriate
- [[kb-history-lesson-promotion|Lesson Promotion]] — lessons may become decisions → invariants

## Error Paths

- Implementation completely diverged from plan → Outcome: `partial` or `abandoned`, significant Deviations
- Harvest fails on changed files → Level 3 targeted source reading fallback
- KB pages conflict with other concurrent changes → surface as drift, do not silently merge

## Source Evidence

- `docs/design/spec/workflow-model.md` — "Change-First Workflow" full lifecycle diagram
- `docs/design/spec/workflow-model.md` — "Change Record Structure" with all required sections

## Known Risks

None currently flagged.

## Status Notes

Active. vNext implementation in progress.

## Open Questions

None.
