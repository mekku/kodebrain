---
id: kb-workflow-onboard
type: capability
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-workflow
source_files:
  - kodebrain/skill/SKILL.md
  - docs/design/spec/workflow-model.md
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/capability
  - domain/kb-workflow
  - status/active
---

# Onboard

Part of [[kb-workflow|Workflow domain]].

## Short Summary

Unified, idempotent project onboarding — works on greenfield (no code), brownfield (existing codebase), partial KBs, and legacy KBs. Single command: `/kodebrain onboard [path]`.

## Why It Exists

Every project starts somewhere different. A new project has no code. An existing project has code but no KB. A project with a partial KB has gaps. The user should not need to know which sub-command to run — `onboard` detects state and does the right thing.

## How It Works

1. Detect project state (greenfield, new_brownfield, partial_kb, legacy_kb, stale_kb, onboarded)
2. Discover existing intent from project docs, existing KB, ADRs, README
3. Interview user only if project-level intent is absent, ambiguous, or contradictory
4. Create or repair Project Contract + architecture skeleton
5. Run harvest for source evidence
6. Map domains from intent + observed evidence
7. Progressive deep mapping by priority (entry points, high-connectivity domains, core outcomes)
8. Write reports (gaps, drift, unmapped files, suspected legacy, needs review)
9. Compile graph indexes (nodes.json, edges.json, file-index.json)
10. Write Obsidian config + install platform configs

## Runtime Path

See [[kb-workflow-onboard-flow|Onboard Flow]] for the full flow.

1. `/kodebrain onboard [path]` — Claude Code skill invocation
2. `project_state.py` — classify state + gap map
3. `project_inventory.py` — file inventory
4. `harvest.py` — extract source evidence
5. Agent writes Markdown pages
6. `compile_graph.py` — compile graph indexes
7. `timeline.py` — generate timeline if history exists
8. `kodebrain install` — platform config (optional)

## API Entry Point

`/kodebrain onboard [path]`

## Related Concepts

- [[kb-workflow-greenfield-mode|Greenfield Mode]] — onboarding without code
- [[kb-workflow-brownfield-mode|Brownfield Mode]] — onboarding existing codebase
- [[kb-core-provenance|Provenance]] — distinguishes intent from observation during mapping
- [[kb-core-knowledge-layers|Knowledge Layers]] — onboard builds all three layers

## Related Models

None directly — onboard produces pages, not structured records.

## Known Risks

None currently flagged.

## Source Evidence

- `kodebrain/skill/SKILL.md` — "Sub-command: onboard" section with 12 steps
- `docs/design/spec/workflow-model.md` — "Unified Onboarding Command" section

## Status Notes

Active. vNext integration with substrate scripts is tracked in implementation plan.

## Open Questions

None.
