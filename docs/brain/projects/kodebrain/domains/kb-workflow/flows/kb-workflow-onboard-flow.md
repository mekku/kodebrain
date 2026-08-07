---
id: kb-workflow-onboard-flow
type: flow
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
  - type/flow
  - domain/kb-workflow
  - status/active
---

# Onboard Flow

Part of [[kb-workflow|Workflow domain]]. Implements [[kb-workflow-onboard|Onboard]].

## Short Summary

User invokes `/kodebrain onboard [path]` → Kode Brain detects project state, discovers intent, harvests source evidence, maps domains, writes KB pages, compiles graph indexes, generates reports, and installs platform configs. Idempotent and resumable.

## Entry Point

| Field | Value |
|---|---|
| Type | `skill` |
| Value | `/kodebrain onboard [path]` |
| Handler | SKILL.md "Sub-command: onboard" section |

## Steps

| # | Description | Symbol | Side Effects |
|---|---|---|---|
| 1 | Detect project state | `project_state.py` | classifies as greenfield/new_brownfield/partial_kb/legacy_kb/stale_kb/onboarded |
| 2 | Discover existing intent | Agent reads project docs | identifies known vs unknown dimensions |
| 3 | Interview user (if needed) | Agent prompts user | `provenance: human` knowledge captured |
| 4 | Create/repair Project Contract | Agent writes `<project>.md` | writes project hub |
| 5 | Write architecture skeleton | Agent writes `architecture/*.md` | writes overview, technology, runtime, data, deployment, integrations |
| 6 | Run harvest | `harvest.py <root>` | writes file-hashes.json, produces source briefs |
| 7 | Map domains | Agent writes domain hubs | writes `<domain>.md` per domain with full contract |
| 8 | Progressive deep mapping | Agent writes capability/flow/concept pages | prioritized by entry points, connectivity, core outcomes |
| 9 | Write reports | Agent writes `reports/*.md` | knowledge-gaps, drift, unmapped-files, suspected-legacy, needs-review |
| 10 | Compile graph indexes | `compile_graph.py <kb_dir>` | writes nodes.json, edges.json, file-index.json |
| 11 | Copy Obsidian config | Copy `.obsidian/` files | only on first onboard |
| 12 | Install platform configs | `kodebrain project install .` | writes agent instruction blocks |

## Data Movement

| From | To | Via |
|---|---|---|
| Source files | `file-hashes.json` + harvest briefs | `harvest.py` |
| Harvest briefs + project docs | KB Markdown pages | Agent (LLM) |
| KB Markdown pages | `nodes.json` + `edges.json` | `compile_graph.py` |
| History records | `timeline.md` + `events.json` | `timeline.py` |

## Cache / State Behavior

- `file-hashes.json` is the state cache — incremental harvest compares against it
- Existing KB pages are never deleted; gaps are filled, stale pages are flagged
- Human notes in `<!-- human-note -->` blocks are preserved verbatim

## Concepts Required

- [[kb-core-knowledge-layers|Knowledge Layers]] — onboard builds all three layers
- [[kb-core-provenance|Provenance]] — distinguishes intent (human/docs) from observation (source)
- [[kb-core-confidence|Confidence]] — pages get `supported` (from evidence) or `inferred` (deduced)
- [[kb-workflow-greenfield-mode|Greenfield Mode]] — different path when no code exists
- [[kb-workflow-brownfield-mode|Brownfield Mode]] — different path for existing codebase

## Error Paths

- No project detected (empty directory in greenfield mode) → interview user for intent
- Legacy KB format detected → run `migrate_kb.py` before mapping
- Harvest fails → fall back to Level 3 targeted source reading
- User declines interview → mark unknowns as `needs_human_review`

## Source Evidence

- `kodebrain/skill/SKILL.md` — full 12-step onboard workflow
- `docs/design/spec/workflow-model.md` — "Onboarding Workflow" phases
- `kodebrain/skill/scripts/project_state.py` — state classifier
- `kodebrain/skill/scripts/harvest.py` — source extraction

## Known Risks

None currently flagged.

## Status Notes

Active. vNext implementation in progress — substrate integration tracked in implementation plan.

## Open Questions

None.
