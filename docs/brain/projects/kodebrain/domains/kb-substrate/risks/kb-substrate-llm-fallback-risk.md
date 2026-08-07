---
id: kb-substrate-llm-fallback-risk
type: risk
status: active
confidence: supported
provenance: project_document
knowledge_role: mixed
project: kodebrain
domain: kb-substrate
source_files:
  - kodebrain/skill/SKILL.md
  - docs/design/implementation-plan-vnext.md
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/risk
  - domain/kb-substrate
  - status/active
---

# LLM Fallback Risk

Part of [[kb-substrate|Substrate domain]].

## Risk Summary

Substrate scripts (harvest.py, compile_graph.py, project_state.py, etc.) exist and are functional, but the default onboard workflow in SKILL.md may fall back to LLM-driven mapping instead of using the deterministic scripts. This means onboard quality depends on the LLM's consistency rather than deterministic tooling.

## Severity

MED — onboard still works via LLM, but is less reproducible and more expensive than the substrate path.

## Affected Capabilities

- [[kb-workflow-onboard|Onboard]] — harvest + state classification steps
- [[kb-core-graph-compilation|Graph Compilation]] — compile_graph.py vs LLM link extraction

## Mitigation

Tracked in vNext implementation plan. Steps:
1. Integrate `project_state.py` → state detection (Phase 0)
2. Integrate `harvest.py` → source evidence (Phase 4)
3. Integrate `compile_graph.py` → graph indexes (Phase 9)
4. Integrate `timeline.py` → history generation (Phase 11)

## Status

Active risk. Mitigation in progress via vNext implementation.

## Source Evidence

- `kodebrain/skill/SKILL.md` — references substrate scripts but default code path is LLM-driven
- `docs/design/implementation-plan-vnext.md` — tracks substrate integration as implementation milestone
