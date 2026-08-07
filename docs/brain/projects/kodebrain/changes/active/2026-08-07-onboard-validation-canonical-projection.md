---
id: 2026-08-07-onboard-validation-canonical-projection
type: change
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: kodebrain
change_state: planned
source_files: []
last_updated: "2026-08-07"
tags:
  - type/change
  - status/active
---

# Onboard Validation Gate + Canonical Projection

## Intent

Add a deterministic **Onboard Completion Gate** that validates generated KB output before onboarding declares success. The gate runs after compile_graph and produces a structured `validation-result.json` with severity-graded findings. Reports (drift, needs-review, knowledge-gaps) become rendered views of validation state, not independently authored prose.

Add a **`canonical_source`** field to the Knowledge Node schema so KB pages that reference external canonical definitions do not duplicate normative truth.

## Why

Self-onboard dogfood (commit `8760f83`) exposed 4 failures that current onboarding does not detect:

1. **Change-first workflow broken** — material change (full KB onboard + rename + platform install) produced no active change record. Compiler warns orphan wiki-links but onboard declares success anyway.
2. **Provenance invalid** — Project Hub marked `human + verified` but was agent-consolidated from canonical specs. Reports are independently authored prose, not derived from actual KB state.
3. **Intent vs observed flattened** — Onboard flow describes deterministic substrate pipeline as current runtime, but Knowledge Gaps admits default path is still LLM-driven. Drift report says "None detected."
4. **Canonical truth duplicated** — Decision Lifecycle, Change Lifecycle copied enum-by-enum from `docs/design/spec/*.md` into KB concept pages. One concept → two authoritative places.

The gate must detect all four failure modes from structural signals alone (no NLP).

## Affected Domains

- [[kb-workflow|Workflow]] — onboard flow gains validation step before completion
- [[kb-core|Core]] — new `canonical_source` field, validation checks on provenance/confidence consistency
- [[kb-governance|Governance]] — canonical authority model extended with projection rules
- [[kb-substrate|Substrate]] — new deterministic validator script

## Architecture Impact

### Onboard flow: new validation gate

```
Onboard → Generate KB → Compile Graph
                              ↓
                         VALIDATE (new gate)
                              ├ orphan wiki-links
                              ├ missing required pages
                              ├ provenance consistency
                              ├ intent-vs-observed contradictions
                              ├ canonical-source duplication
                              └ report consistency
                              ↓
                    validation-result.json
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
               drift.md   needs-    knowledge-
                          review.md gaps.md
                              │
                              ▼
                    completion_state
```

### Severity tiers

| Tier | Meaning | Effect |
|---|---|---|
| **ERROR** | Structural violation, missing required artifact, invalid provenance, canonical duplication | Onboard cannot declare complete |
| **DRIFT** | Intent ≠ observed, planned architecture ≠ current runtime | Onboard completes as `complete_with_drift` |
| **REVIEW** | Ambiguous provenance, inferred claims lacking evidence | Onboard can complete but must surface warning |

### Completion states

| State | Condition |
|---|---|
| `complete` | Zero ERROR, zero DRIFT |
| `complete_with_drift` | Zero ERROR, some DRIFT |
| `needs_review` | Zero ERROR, REVIEW items present |
| `blocked` | Any ERROR present |

### canonical_source field

```yaml
canonical_source:
  path: docs/design/spec/history-model.md
  anchor: decision-lifecycle
```

Rule: if `canonical_source` exists, the KB page must NOT claim itself as canonical owner. It may summarize context/navigation but normative questions route to the source.

Template for reference pages:
```markdown
## Canonical Definition
See: [[canonical-source-path#anchor]]

## Project Context
...

## Relationships
...

## Evidence
...
```

No "How It Works" section with redefined enum contracts.

### Reports as derived views

`validation-result.json` is canonical. `drift.md`, `needs-review.md`, `knowledge-gaps.md` are rendered from it. No agent-authored prose that can contradict the validation data.

## Expected Behavior Changes

- `/kodebrain onboard` runs validation gate before declaring completion
- Onboard summary reports actual completion state, not optimistic "all clear"
- Compiler warnings become validation input, not ignored
- KB pages with `canonical_source` use reference template, not full concept template

## Invariants

- Validation runs deterministically — same KB → same result
- Reports never contradict `validation-result.json`
- A page with `canonical_source` must not redefine the canonical definition
- Onboard completion state must reflect actual validation findings

## Expected Source Areas

- `kodebrain/skill/scripts/validate.py` — new deterministic validator
- `kodebrain/skill/SKILL.md` — onboard flow updated with validation step
- `schema/node.schema.json` — new `canonical_source` field
- `templates/concept.md` — new reference variant
- `docs/design/spec/workflow-model.md` — onboard flow spec updated
- `docs/design/spec/knowledge-model.md` — canonical_source model defined
- `docs/design/spec/governance.md` — projection rules added

## Acceptance Criteria

Running the validation gate against the KB produced by commit `8760f83` must:

1. **NOT return `complete`** — at minimum `needs_review`
2. Detect at minimum:
   - **ERROR:** missing active change target (`changes/active/2026-08-07-vnext-substrate`)
   - **ERROR/REVIEW:** invalid provenance on project hub (`human + verified` for agent-consolidated content)
   - **DRIFT:** intended deterministic onboard pipeline vs observed LLM-driven default path
   - **ERROR:** normative lifecycle concept pages duplicate canonical definitions without `canonical_source`

## Progress Log

- **2026-08-07:** Change record created. Step 0 — dogfood: this change record itself is the first artifact produced. Validation Gate spec to follow.
