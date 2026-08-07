---
type: report
project: kodebrain
confidence: supported
provenance: generated
last_updated: "2026-08-07"
---

# Knowledge Gaps

Generated during onboard 2026-08-07.

## Gap Map

| Dimension | Status |
|---|---|
| Purpose | found_in_docs — `docs/design/spec.md`, project hub |
| Actors | found_in_docs — project hub, knowledge-model spec |
| Core Outcomes | found_in_docs — project hub, governance spec (success criteria) |
| Scope | found_in_docs — project hub, governance spec (non-goals) |
| Technology | inferred_from_project — pyproject.toml, source files |
| Architecture | found_in_docs — spec.md system architecture section |
| Runtime | inferred_from_project — SKILL.md + scripts |
| External Integrations | found_in_docs — Obsidian (optional), Claude Code (required) |
| Domains | found_in_docs — 6 domains declared in project hub |
| Domain Boundaries | found_in_docs — spec.md boundary rules, governance boundary rules |
| Invariants | found_in_docs — each domain spec declares invariants |
| Legacy/Migration | found_in_docs — vNext migration tracked in implementation plan |

## Remaining Gaps

| Gap | Severity | Notes |
|---|---|---|
| Substrate integration into onboard | MED | SKILL.md references substrate scripts; default code path still LLM-driven. Tracked in vNext implementation plan |
| History records populated | LOW | directories exist, no actual decision/incident/milestone records written yet |
| Deeper capability/flow pages for history and governance | LOW | core domains well-covered; history and governance have thinner coverage |

## Next Steps

1. Implement vNext substrate integration (harvest → compile → timeline in onboard flow)
2. Populate at least one decision record for the spec tree decomposition
3. Deep-map remaining capabilities as needed during implementation
