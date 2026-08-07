# External Dogfood Gate 2 Fix

**Status:** DRAFT v0.1 — implementation required
**Created:** 2026-08-07
**Domain:** kb-workflow, kb-substrate, graph compiler, validation
**Evidence repo:** `mekku/sampard-ai`

---

## Purpose

Fix two generic failures exposed by external dogfood after Intent Source Inventory began working:

1. Intent↔observed comparison findings are currently written directly to `reports/drift.md`, then erased by `validate.py`, because reports are derived projections rebuilt from validator findings.
2. Canonical Markdown pages encode semantic node type in `tags: [type/<kind>]`, while `compile_graph.py` reads only top-level `type:`. This compiles many nodes as `type: unknown`, causing type-dependent validation and graph semantics to silently fail.

This spec closes the execution loop from accepted intent to durable validation state:

```text
Accepted Intent
      ↓
Intent↔Observed Comparison
      ↓
graph/intent-observed-findings.json   ← canonical comparison input
      ↓
validate.py consumes findings
      ↓
validation-result.json
      ↓
reports/drift.md                       ← projection only
```

And establishes one machine-readable node type contract:

```text
Markdown semantic type
      ↓
compile_graph.py
      ↓
node.type
      ↓
validation / edge fallback / benchmark
```

---

## External Dogfood Evidence

On `sampard-ai`:

- `docs/specs/ai-interview-builder.md` is discovered as intent and human-accepted.
- Intent inventory reports `accepted: 1`, `pending_resolution: 0`.
- Project Hub records `intent_sources` and `provenance: project_document`.
- The accepted spec says voice uses **Wispr local**.
- Observed implementation contains `src/ai/transcriber/whisper.ts` and uses `WhisperTranscriber`.
- The accepted spec defines `InterviewSchema: draft → active → archived`.
- Observed `InterviewSchema` has no schema lifecycle/state field.
- Despite these disagreements, current validation reports:
  - `completion_state: complete`
  - `drift_count: 0`
  - `reports/drift.md: No drift detected.`

The same repo still contains a Decision page with `provenance: source_code`, yet provenance validation passes because the compiled node type is `unknown` rather than `decision`.

These are product/process failures, not `sampard-ai` cleanup issues.

---

## Root Cause A — Comparison Writes a Derived Report

Current Step 8 instructs the agent to write drift directly to:

```text
reports/drift.md
```

But `validate.py` intentionally treats reports as pure projections and executes:

```text
validation findings
      ↓
render_reports_from_findings()
      ↓
overwrite reports/drift.md
```

Therefore an LLM can correctly detect a disagreement and write it, but validation has no canonical input representing that finding. The next validator run erases the result and returns `drift_count: 0`.

### Non-negotiable rule

**Agents and comparison steps MUST NOT author validation-derived reports directly.**

`reports/drift.md`, `reports/needs-review.md`, and `reports/knowledge-gaps.md` remain projections only.

---

## Fix A — Canonical Intent↔Observed Findings Artifact

Add:

```text
docs/brain/projects/<project>/graph/intent-observed-findings.json
```

This is the handoff between the semantic comparison step and deterministic validation.

### Minimum schema

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-07T00:00:00Z",
  "findings": [
    {
      "id": "intent-observed-001",
      "kind": "technology_disagreement",
      "severity": "DRIFT",
      "confidence": "supported",
      "status": "unresolved",
      "intent": {
        "source": "docs/specs/ai-interview-builder.md",
        "claim": "Voice input uses Wispr local"
      },
      "observed": {
        "source": "src/ai/transcriber/whisper.ts",
        "line": 1,
        "claim": "Implementation uses WhisperTranscriber"
      }
    }
  ]
}
```

### Allowed finding severities

- `DRIFT` — intent and observation explicitly disagree.
- `REVIEW` — comparison cannot establish which interpretation is correct or evidence is incomplete.

Do not encode `ERROR` here. Structural corruption of the comparison artifact itself is validator territory.

### Allowed statuses

- `unresolved`
- `accepted_intent_wins`
- `accepted_source_wins`
- `superseded`

Unresolved `DRIFT` contributes to `complete_with_drift`.

### Comparison semantics

For each accepted intent source:

1. Extract material claims from:
   - non-negotiable principles,
   - technology choices,
   - state machines/lifecycles,
   - required data model fields,
   - explicit constraints/invariants.
2. Inspect targeted observed evidence.
3. Emit a finding only when there is enough evidence for a meaningful disagreement or review condition.
4. Source silence is `unverifiable`; it is not automatically drift.
5. Persist comparison findings in `graph/intent-observed-findings.json`.
6. Never write `reports/drift.md` directly.

LLM-driven comparison is acceptable for v1. The important invariant is that its output is structured, persisted, and validator-consumed.

---

## Validator Integration

Add a dedicated validator check, e.g.:

```text
intent-observed-external-findings
```

Behavior:

1. If `intent-observed-findings.json` is absent:
   - do not invent drift;
   - if there are accepted intent sources and comparison is required by onboard, emit `REVIEW` that comparison has not been performed.
2. If the file is malformed:
   - emit `ERROR`.
3. For every unresolved `DRIFT` item:
   - convert to a normal validator `DRIFT` finding.
4. For every `REVIEW` item:
   - convert to a normal validator `REVIEW` finding.
5. Include these findings in `all_findings` **before report rendering**.
6. `render_reports_from_findings()` remains the only writer of `reports/drift.md`.

Required result:

```text
comparison artifact contains unresolved DRIFT
      ↓
validation-result.json drift_count > 0
      ↓
completion_state = complete_with_drift
      ↓
reports/drift.md contains the finding
```

---

## Root Cause B — Node Type Contract Mismatch

Current KB pages commonly encode type as:

```yaml
tags:
  - type/decision
  - domain/interview
```

But `compile_graph.py` currently derives semantic type from:

```python
fm.get("type", "unknown")
```

This means a Decision page can compile as:

```json
{"type": "unknown"}
```

Consequences are broader than benchmark display:

- `type=decision + provenance=source_code` validator guard does not run.
- edge fallback by node-type pair becomes weaker or wrong.
- risk/model/capability counts can be wrong.
- type-based validation silently misses invalid states.

---

## Fix B — One Canonical Machine Type

Canonical Markdown pages MUST expose semantic type as a top-level machine-readable field:

```yaml
type: decision
tags:
  - type/decision
  - domain/interview
```

### Rule

- `type:` is canonical machine semantics.
- `tags: type/...` is a presentation/index projection for Obsidian and search.
- New templates MUST write both consistently.
- Compiler MUST use top-level `type:` when present.

### Legacy compatibility

For existing pages that have no top-level `type:`:

1. compiler may derive type from exactly one `type/<kind>` tag;
2. emit a migration/review diagnostic indicating the page uses legacy type encoding;
3. if top-level `type:` and `type/<kind>` disagree, emit an `ERROR` or compiler diagnostic that blocks clean completion;
4. do not silently choose between contradictory type declarations.

Recommended compiler logic:

```text
explicit type present?
  yes → compare with type/* tag if present
          equal      → use explicit type
          disagree   → diagnostic/error
  no  → exactly one type/* tag?
          yes → derive legacy type + migration diagnostic
          no  → unknown + diagnostic
```

Do not make `tags` the long-term semantic authority.

---

## Required Template / Migration Changes

Update canonical templates so all generated knowledge pages include top-level `type:`.

At minimum cover:

- project
- architecture
- domain
- capability
- flow
- concept
- data_model / model
- risk
- decision
- incident
- milestone
- change

Migration does not need to rewrite all repositories immediately. Compiler fallback provides compatibility while newly generated/reconciled pages converge to the explicit field.

---

## Regression Gates

### Gate 2A — Comparison survives validation

Fixture:

```text
docs/specs/product.md
  intent: "Increment is atomic"

src/index.ts
  observed: "implementation is NOT atomic"
```

Given the spec is accepted intent, run the actual comparison + validation path.

Must assert:

```text
intent-observed-findings.json contains a DRIFT
validation-result.json drift_count > 0
completion_state == complete_with_drift
reports/drift.md contains the atomic disagreement
```

A test that merely asserts the fixture contains the words `atomic` and `NOT atomic` does **not** satisfy this gate.

### Gate 2B — Report is projection only

Given a comparison artifact containing one DRIFT:

1. run validator;
2. verify `reports/drift.md` contains exactly the validator-projected finding;
3. rerun validator;
4. output remains stable and drift is not erased.

### Gate 2C — Decision provenance reaches validator

Fixture page:

```yaml
type: decision
provenance: source_code
```

or legacy equivalent:

```yaml
tags:
  - type/decision
provenance: source_code
```

Run **compiler then validator**, not `check_provenance_consistency()` on a hand-built node.

Must assert:

```text
compiled node.type == decision
validator emits invalid-decision-provenance ERROR
completion_state == blocked
```

### Gate 2D — Type mismatch is not silent

Fixture:

```yaml
type: concept
tags:
  - type/decision
```

Must produce a compiler/validation diagnostic. It must not silently compile as either type with a clean result.

### Gate 2E — External dogfood acceptance

Re-run Kode Brain on `mekku/sampard-ai` after implementation.

Accepted intent:

```text
docs/specs/ai-interview-builder.md
```

At minimum the system should surface for review/drift:

1. Spec voice path says Wispr local; implementation uses Whisper.
2. Spec defines InterviewSchema lifecycle `draft → active → archived`; observed `InterviewSchema` has no lifecycle/state field.

Expected completion:

```text
Intent sources: 1 accepted
Pending intent: 0
Drift/review: > 0
Completion: complete_with_drift or needs_review
```

It MUST NOT return `complete / drift_count: 0` unless the intent or source has subsequently changed so the disagreements no longer exist.

---

## Out of Scope

Do not use this fix to:

- build a perfect deterministic semantic comparison engine;
- clean all `sampard-ai` KB pages manually;
- tune benchmark aesthetics;
- add unrelated graph edge semantics;
- resolve which side of each drift is correct automatically;
- rewrite historical project documents.

The goal is a transferable execution path:

```text
intent accepted
→ semantic comparison
→ canonical structured finding
→ deterministic validator consumption
→ projected report
```

---

## Implementation Order

1. Define `intent-observed-findings.json` schema/reader.
2. Change SKILL Step 8 to write the structured artifact, never `drift.md`.
3. Add validator ingestion before report rendering.
4. Fix canonical node type generation/templates.
5. Add compiler fallback + mismatch diagnostics for legacy `type/*` tags.
6. Replace fixture-only Gate 2 tests with actual comparison→validation integration tests.
7. Add compiler→validator Decision provenance regression.
8. Re-onboard `sampard-ai` and record external result without manually cleaning repo-specific output.

---

## Definition of Done

This fix is done only when all are true:

- [ ] Agent/LLM comparison never writes validation reports directly.
- [ ] Comparison findings persist in a canonical structured artifact.
- [ ] Validator consumes that artifact before rendering reports.
- [ ] An unresolved comparison DRIFT produces `complete_with_drift`.
- [ ] Generated Markdown pages have explicit top-level semantic `type:`.
- [ ] Legacy `type/*` tags compile with explicit migration diagnostics.
- [ ] Conflicting top-level type and tag type cannot pass silently.
- [ ] Compiler→validator test catches source-only Decision provenance.
- [ ] Atomic fixture produces real DRIFT through the full execution path.
- [ ] `sampard-ai` no longer reports false `complete / drift_count: 0` while the accepted Wispr/Whisper and schema-lifecycle disagreements remain.
