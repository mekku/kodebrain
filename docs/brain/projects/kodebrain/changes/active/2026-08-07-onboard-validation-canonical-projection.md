---
id: 2026-08-07-onboard-validation-canonical-projection
type: change
status: active
confidence: supported
provenance: human
knowledge_role: intent
project: kodebrain
change_state: implemented
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

### Severity model and completion states

Defined in [`onboard-validation-gate.md`](../../../design/spec/onboard-validation-gate.md):
- Severity tiers: ERROR (blocks completion), DRIFT (completes with drift), REVIEW (surfaces warning)
- Completion states: `complete`, `complete_with_drift`, `needs_review`, `blocked`

### canonical_source field

Defined in [`knowledge-model.md`](../../../design/spec/knowledge-model.md#canonical_source-field-semantics):
- KB pages with `canonical_source` use `knowledge_role: reference` and constrained template
- No "How It Works" sections with redefined enum contracts
- Normative questions route to the canonical source

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

## Implementation Evidence

### Code artifacts
- `kodebrain/skill/scripts/validate.py` — deterministic validation gate (6 checks, dynamic canonical registry, anchor validation, post-render report consistency)
- `kodebrain/skill/scripts/compile_graph.py` — edge semantics inferred before target-existence check (correct orphan severity)
- `schema/node.schema.json` — `canonical_source` field (object: path required, anchor optional)
- `kodebrain/skill/scripts/frontmatter.py` — shared parser handles nested YAML maps
- `kodebrain/skill/scripts/spec_validator.py` — structural spec authority checker (parent chain, duplicate owners, reachability)
- `templates/reference.md` — constrained reference page template (Canonical Definition, Project Context, Relationships, Evidence)

### Spec artifacts
- `docs/design/spec/onboard-validation-gate.md` — severity model, completion states, finding model (stripped to owned concerns)
- `docs/design/spec/workflow-model.md` — onboard validation gate integration + completion states added
- `docs/design/spec/knowledge-model.md` — `canonical_source` field semantics + reference template added
- `docs/design/spec/governance.md` — canonical projection rules added
- `docs/design/spec.md` — root diagram updated to 6 children, Validation Gate row corrected

### Tests
- `tests/test_validation_gate.py` — frontmatter nested map, compile canonical_source, orphan diagnostics, referential integrity (false-positive suppression), canonical duplication, provenance consistency, render reports, portable artifact, integration compile→validate
- `tests/test_referential_integrity.py` — granular referential integrity edge cases
- `tests/test_substrate.py` — existing substrate tests pass

## Deviations From Plan

- **Spec ownership reroute applied:** Validation gate process moved to workflow-model.md, canonical_source field semantics moved to knowledge-model.md, canonical projection rules moved to governance-model.md. The onboard-validation-gate.md now owns only severity model, completion states, and finding model — matching its frontmatter `owns[]`.
- **CANONICAL_REGISTRY replaced with dynamic derivation:** The hand-written registry (which diverged from actual spec `owns[]`) is replaced by `build_canonical_registry()` that scans spec frontmatter directly. One concept → one canonical owner enforced at the source.
- **Anchor validation added:** `canonical_source.anchor` is now verified to exist as a heading in the target file. Missing anchor → ERROR (invalid-canonical-source).
- **Compiler edge semantics reordered:** Edge type is now inferred before target-existence check so orphan diagnostics carry correct semantic type (depends_on, risky_for) instead of always `related_to`.
- **Report consistency becomes post-render invariant:** Reports are rendered during `run_validation()` before Check 6 runs. Stale derived artifacts cannot block validation.
- **Item count comparison added:** Check 6 now counts actual `**ID**` markers in reports, not just "None detected" text.
- **Status Notes bug fixed:** `has_subsection(body, "Status Notes", "")` replaced with `extract_section(body, "Status Notes")` check.
- **Reference template created:** `templates/reference.md` with constrained structure (Canonical Definition, Project Context, Relationships, Evidence) — no How It Works / Specification sections.

## Lessons Learned

1. **frontmatter ownership ≠ root map ≠ body definitions ≠ actual child specs:** The spec defined ownership routing in prose but didn't move the definitions. In round 2 the definitions moved to their canonical owners. The invariant "one concept → one canonical owner" must be enforced at the file level, not just declared.
2. **Hand-written registries drift:** CANONICAL_REGISTRY had different concern names than the actual spec `owns[]` (e.g. `decision-lifecycle` vs `decision.record`). Dynamic derivation from source frontmatter eliminates this class of bug.
3. **Derived artifacts must not gate validation:** Stale reports blocking validation is the same anti-pattern the system was built to prevent — derived data claiming authority over source. Reports are now rendered before the consistency check.
4. **Edge semantics must precede orphan detection:** Inferring `related_to` for all orphans hid the real severity. A missing domain dependency should be ERROR; a missing "See Also" should be REVIEW. Fixed by reordering the compiler pass.
5. **Kode Brain's change-first workflow applies to Kode Brain itself:** This change record was `planned` throughout implementation. The system it builds — recording intent before code, reconciling after — must be used by its own development. This record now reflects actual implementation state.

## Follow-ups

- KB pages `kb-history-decision-lifecycle` and `kb-workflow-change-lifecycle` need `canonical_source` + `knowledge_role: reference` to resolve the 3 canonical duplication ERRORs
- KB should be re-onboarded after fixes to verify ERROR = 0
- `change_state` should progress to `reconciled` after KB pages are fixed and re-validation passes

## Progress Log

- **2026-08-07:** Change record created. Step 0 — dogfood: this change record itself is the first artifact produced. Validation Gate spec to follow.
- **2026-08-07:** Spec written (`docs/design/spec/onboard-validation-gate.md`). Defines 6 checks, severity tiers, completion states, canonical_source field, projection rules, dogfood acceptance criteria.
- **2026-08-07:** Implementation — `validate.py` with all 6 checks, `compile_graph.py` emits diagnostics.json, `frontmatter.py` handles nested maps. Tests pass via `test_validation_gate.py`.
- **2026-08-07:** Commit `88196fa` — validation gate correctness pass: nested frontmatter, diagnostics, render, onboard integration. Spec ownership routing declared in prose but definitions not yet moved.
- **2026-08-07:** Commit (this change) — ownership reconcile: moved definitions to canonical owners, dynamic registry, anchor validation, compiler edge reorder, report postcondition, reference template, change record dogfood.
