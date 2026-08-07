---
spec_id: onboard-validation-gate
spec_role: canonical
parent: root
owns:
  - validation.severity-model
  - validation.completion-state
  - validation.finding-model
---

# Onboard Completion Gate

Canonical owner for: validation severity model (ERROR/DRIFT/REVIEW), completion states (complete/complete_with_drift/needs_review/blocked), finding model.

**Ownership routing (applied after approval):**
- Validation gate process (when validation runs, onboard integration) → `workflow-model.md` (Workflow owns onboard processes)
- `canonical_source` field semantics → `knowledge-model.md` (Knowledge owns node field semantics)
- Canonical projection rules → `governance.md` (Governance owns authority rules)
- Machine shape of `canonical_source` → `schema/node.schema.json` (Schema owns field contracts)
- Severity model + completion states + finding model: this spec retains ownership

---

## Motivation

Self-onboard dogfood (commit `8760f83`) exposed that `/kodebrain onboard` can declare success while producing:

- Orphan wiki-links to non-existent pages
- Invalid provenance claims (`human + verified` for agent-consolidated content)
- Intent-vs-observed contradictions flattened into single pages
- Normative definitions duplicated from canonical specs into KB pages

The onboard process currently has no deterministic completion gate. Compiler warnings are emitted but do not block completion. Reports are independently authored prose, not derived from actual KB state.

This spec defines a **deterministic validation gate** that runs after graph compilation. Onboard may not declare `complete` without passing it.

---

## Validation Gate Process

```
Onboard → Generate KB → Compile Graph
                              ↓
                    ┌─── VALIDATION GATE ───┐
                    │                        │
                    │ 1. Referential integrity
                    │ 2. Required artifact integrity
                    │ 3. Provenance/confidence consistency
                    │ 4. Intent-observed consistency
                    │ 5. Canonical authority / projection integrity
                    │ 6. Report consistency
                    │                        │
                    └───────────┬────────────┘
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

The gate is called by the onboard workflow after `compile_graph.py` and before declaring completion. It is a deterministic Python script: same KB → same result.

---

## Severity Model

Three tiers. Each finding carries exactly one severity.

### ERROR — Onboard cannot declare complete

Structural violations that make the KB untrustworthy:

| Check | Rule |
|---|---|
| `orphan-wikilink` | Wiki-link target page does not exist AND the target is required (active change, domain hub, risk reference) |
| `missing-required-page` | Required artifact missing (project hub, domain hub for declared domain, graph indexes) |
| `invalid-provenance` | Provenance contradicts provenance source rules (see Check 3) |
| `canonical-duplication` | Page has `knowledge_role: intent` AND contains enum/state-table/contract also present in a canonical source without declaring `canonical_source` |
| `invalid-canonical-source` | `canonical_source.path` does not exist or `canonical_source.anchor` not found |

### DRIFT — Onboard completes as `complete_with_drift`

Genuine disagreements between intent and observation that the validator can detect structurally:

| Check | Rule |
|---|---|
| `intent-observed-mismatch` | Page declares `knowledge_role: intent` or `mixed` but contains `## Runtime Path` or `## Source Evidence` sections with `provenance: source_code` evidence that contradicts sections marked as intent |
| `planned-vs-runtime` | Active change describes behavior as implemented but harvest output for referenced source files shows different exports/routes |
| `completed-change-vs-implementation` | Completed change claims removal but harvest still detects the removed symbols |

### REVIEW — Onboard can complete but must surface warning

Ambiguity that deterministic checks cannot resolve:

| Check | Rule |
|---|---|
| `ambiguous-provenance` | `provenance: human` on a page with no `<!-- human-note -->` block and no interview transcript reference |
| `inferred-without-evidence` | `confidence: inferred` on a page with zero `source_files` entries |
| `possible-semantic-duplicate` | Two pages share ≥80% section heading overlap but neither declares `canonical_source` — flagged for human review |

---

## Completion States

| State | Condition | Onboard behavior |
|---|---|---|
| `complete` | Zero ERROR, zero DRIFT | Onboard declares success |
| `complete_with_drift` | Zero ERROR, one or more DRIFT | Onboard completes; drift items written to `reports/drift.md`; summary warns |
| `needs_review` | Zero ERROR, one or more REVIEW | Onboard completes; review items written to `reports/needs-review.md`; summary notes pending review |
| `blocked` | One or more ERROR | Onboard does NOT declare success; ERROR items listed; user told to resolve before re-running |

When both DRIFT and REVIEW exist without ERROR → `complete_with_drift` (DRIFT takes precedence over REVIEW).

---

## Check Details

### Check 1 — Referential Integrity

**Input:** `edges.json` + all `.md` pages in KB directory

**Rules:**
- For every edge in `edges.json`, verify `target` page exists
- Required reference types (from sections: "Active Changes", "Depends On" in project hub) → ERROR if missing
- Non-required reference types (from sections: "Related Concepts", "See Also") → REVIEW if missing

**Implementation:** Walk edges.json, check file existence for each target. Classify by edge provenance (which section the link came from).

### Check 2 — Required Artifact Integrity

**Input:** `nodes.json` + KB directory listing

**Rules:**
- Project hub (`<project>.md`) must exist → ERROR if missing
- Every domain declared in project hub must have `<domain>.md` → ERROR if missing
- `graph/nodes.json`, `graph/edges.json`, `graph/file-index.json` must exist → ERROR if missing
- `graph/file-hashes.json` must exist → REVIEW if missing (can be regenerated)

### Check 3 — Provenance/Confidence Consistency

**Input:** `nodes.json` + page frontmatter

**Rules:**

| Pattern | Severity | Why |
|---|---|---|
| `provenance: human` + `confidence: verified` + zero `source_files` + no `<!-- human-note -->` block + no interview transcript in the KB | **ERROR** | `verified` is human-only; cannot be claimed without evidence of human review |
| `provenance: human` + page contains sections matching harvest output patterns (exports, routes tables) | **REVIEW** | Human-authored pages should not contain machine-extracted detail without attribution |
| `provenance: source_code` + `confidence: verified` | **ERROR** | `verified` is human-only; source_code provenance cannot be verified without human |
| `provenance: generated` + `confidence` other than `inferred` or `needs_human_review` | **ERROR** | Generated content cannot claim `supported` or `verified` |
| `knowledge_role: intent` + `source_files` contains files with harvest status `deprecated` | **DRIFT** | Intent page claims ownership of deprecated code |

### Check 4 — Intent-Observed Consistency

**Input:** `nodes.json` + page body patterns

**Rules:**

| Pattern | Severity | Why |
|---|---|---|
| `knowledge_role: intent` + page contains `## Runtime Path` or `## Source Evidence` section | **REVIEW** | Intent pages describe what should be; observed sections belong in observed pages or mixed pages |
| `knowledge_role: mixed` + no DRIFT items referencing this page AND gap between intent claim and observed evidence detectable structurally | **DRIFT** | Mixed page with internal contradiction that hasn't been surfaced |
| Page declares a deterministic 12-step runtime path in a "## Steps" table + a "## Status Notes" or knowledge gap elsewhere says the path is still LLM-driven | **DRIFT** | Contradiction within same page |

**Implementation note for Check 4, rule 3:** Detect when a page under `knowledge_role: intent` or `mixed` contains both a structured step table AND text matching patterns like "still in progress", "not yet integrated", "tracked in implementation plan", "LLM-driven", "default path is". This is the structural signal of the substrate integration contradiction found in dogfood.

### Check 5 — Canonical Authority / Projection Integrity

**Input:** `nodes.json` + `canonical_source` fields + canonical source registry

**Canonical Source Registry:** A list of known canonical document paths + their owned concepts. Initial registry:

```yaml
registry:
  - path: docs/design/spec/knowledge-model.md
    owns:
      - knowledge.layers
      - provenance
      - confidence
      - knowledge_role
      - drift
      - harvest-policy
      - graph-compilation
  - path: docs/design/spec/project-model.md
    owns:
      - project.structure
      - project.layout
      - node-id-format
      - domain-contract
  - path: docs/design/spec/workflow-model.md
    owns:
      - onboarding.process
      - change-lifecycle
      - change-record-structure
      - status-lifecycle-separation
  - path: docs/design/spec/history-model.md
    owns:
      - decision-lifecycle
      - decision-lineage
      - incident-lifecycle
      - incident-record
      - milestone-record
  - path: docs/design/spec/governance.md
    owns:
      - spec-authority
      - precedence
      - compatibility
      - non-goals
      - success-criteria
```

**Rules:**

| Pattern | Severity | Why |
|---|---|---|
| Page has `knowledge_role: intent` + page content contains enum/state-table matching a concept owned by a canonical source + page does NOT declare `canonical_source` pointing to that source | **ERROR** | Canonical duplication — one concept, two authoritative places |
| Page declares `canonical_source` + page `knowledge_role` is NOT `reference` or `mixed` | **REVIEW** | A page pointing to external canonical source should declare itself as reference, not intent |
| `canonical_source.path` references a file not in the canonical registry | **REVIEW** | Unregistered canonical source — may be legitimate but should be reviewed |
| Page declares `canonical_source` + page contains `## How It Works` or `## Specification` section with redefined contracts | **ERROR** | Reference page must not redefine the canonical contract |

**Implementation note for rule 1 (canonical duplication detection):** The validator does NOT use NLP. It detects structural signals:
1. Extract structured data (tables, enums, state machines) from the page body
2. Extract structured data from the canonical source file referenced in the registry
3. If both contain tables with matching headers or enum value lists → flag as potential duplication
4. If the page has `canonical_source` → not duplication (it's acknowledged reference)
5. If the page does NOT have `canonical_source` → ERROR

For the dogfood test case, the validator should detect:
- `kb-history-decision-lifecycle.md` contains a state table (`active/superseded/deprecated`) matching `docs/design/spec/history-model.md#decision-lifecycle`
- `kb-workflow-change-lifecycle.md` contains a state table (`planned/in_progress/implemented/reconciled`) + lifecycle diagram matching `docs/design/spec/workflow-model.md#change-lifecycle`
- Neither page declares `canonical_source` → ERROR

### Check 6 — Report Consistency

**Input:** `validation-result.json` + existing report files

**Rules:**
- `reports/drift.md` item count must match DRIFT item count in `validation-result.json` → ERROR if mismatch
- `reports/needs-review.md` item count must match REVIEW item count in `validation-result.json` → ERROR if mismatch
- If a report claims "None detected" but `validation-result.json` contains items of that type → ERROR

**Rationale:** Reports are derived views. They must not contradict the validation data. This prevents the dogfood failure where `needs-review.md` claimed "None" while the KB contained provenance errors.

---

## Output: validation-result.json

```json
{
  "kb_path": "docs/brain/projects/kodebrain/",
  "validated_at": "2026-08-07T...",
  "completion_state": "blocked",
  "summary": {
    "total_findings": 8,
    "error_count": 3,
    "drift_count": 2,
    "review_count": 3
  },
  "findings": [
    {
      "id": "ERR-001",
      "check": "referential-integrity",
      "severity": "ERROR",
      "rule": "orphan-wikilink",
      "node": "kodebrain",
      "target": "changes/active/2026-08-07-vnext-substrate",
      "description": "Active Change wiki-link target does not exist",
      "section": "Active Changes"
    }
  ],
  "checks_run": {
    "referential-integrity": { "total": 99, "passed": 98, "failed": 1 },
    "required-artifact-integrity": { "total": 10, "passed": 10, "failed": 0 },
    "provenance-consistency": { "total": 24, "passed": 22, "failed": 2 },
    "intent-observed-consistency": { "total": 24, "passed": 22, "failed": 2 },
    "canonical-authority": { "total": 24, "passed": 21, "failed": 3 },
    "report-consistency": { "total": 5, "passed": 5, "failed": 0 }
  }
}
```

Reports are rendered from this file — the counts in `drift.md`, `needs-review.md`, and `knowledge-gaps.md` must match the finding counts in `validation-result.json`. The onboard summary reports `completion_state`, not a hardcoded "onboard complete."

---

## `canonical_source` Field

### Schema addition

Added to `schema/node.schema.json`:

```json
"canonical_source": {
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Relative path from project root to the canonical definition"
    },
    "anchor": {
      "type": "string",
      "description": "Section anchor within the canonical document"
    }
  },
  "required": ["path"]
}
```

### Semantics

- `knowledge_role: reference` — required when `canonical_source` is set. The page is a navigation/context projection of a canonical definition elsewhere. Normative questions route to `canonical_source`.
- `knowledge_role: mixed` — permitted with `canonical_source` when the page contains both reference navigation AND original observed evidence not covered by the canonical source.
- `knowledge_role: intent` — NOT permitted with `canonical_source`. Intent pages claim to own the concept; if a canonical source exists, intent is held there.

### Template for reference pages

Pages with `canonical_source` use a constrained structure:

```markdown
## Canonical Definition
See: [canonical-source-path#anchor]

## Project Context
(How this concept manifests in this project specifically)

## Relationships
(Wiki-links to related nodes)

## Evidence
(Source files, runtime evidence where this concept is observed)
```

No `## How It Works`, `## Specification`, or enumerated contracts. The canonical source owns the definition.

---

## Canonical Projection Rules

Added to governance spec:

**Projection rule:** A KB page whose content is primarily derived from a canonical source must:
1. Declare `canonical_source` pointing to the canonical document
2. Set `knowledge_role: reference`
3. Use the reference page template (no redefined contracts)
4. Add project-specific context, relationships, and evidence — these are the page's value-add

**Anti-pattern (canonical duplication):**
```
canonical spec defines lifecycle states
    ↓
KB concept page copies the same state table
    ↓
page has knowledge_role: intent and no canonical_source
    ↓
One concept → two authoritative places
```

**Correct pattern (canonical projection):**
```
canonical spec defines lifecycle states
    ↓
KB concept page declares canonical_source
    ↓
page provides: project context, related nodes, source evidence
    ↓
Normative question → canonical source
Navigation/context question → KB page
```

---

## Dogfood Acceptance Criteria

Running the validation gate against the KB produced by commit `8760f83` must:

1. **NOT return `complete`** — minimum `needs_review`
2. Detect at minimum these findings:

| # | Finding | Check | Severity |
|---|---|---|---|
| 1 | Orphan wiki-link to `changes/active/2026-08-07-vnext-substrate` | referential-integrity | **ERROR** |
| 2 | Project Hub `provenance: human` + `confidence: verified` without human evidence | provenance-consistency | **ERROR** |
| 3 | Substrate integration described as deterministic pipeline but Knowledge Gaps says LLM-driven | intent-observed-consistency | **DRIFT** |
| 4 | `kb-history-decision-lifecycle` copies lifecycle states from `history-model.md` without `canonical_source` | canonical-authority | **ERROR** |
| 5 | `kb-workflow-change-lifecycle` copies lifecycle states + diagram from `workflow-model.md` without `canonical_source` | canonical-authority | **ERROR** |
| 6 | `needs-review.md` claims "None" but provenance error exists | report-consistency | **ERROR** |

After repairing the KB pages (Step 6) and re-running, the gate should produce `complete_with_drift` (remaining DRIFT on substrate integration, which is genuine) or `needs_review` (remaining REVIEW items).

---

## Non-Goals

- NLP-based semantic duplication detection (round 1 uses structural signals only)
- Automatic repair of validation findings
- Validation of source code correctness (the gate validates KB quality, not project code)
- Runtime behavior verification

## Success Criteria

- `/kodebrain onboard` cannot declare `complete` with broken references
- Reports never contradict `validation-result.json`
- Canonical duplication is detected structurally (same enum values in two places without `canonical_source`)
- Dogfood: gate running against `8760f83` KB returns `blocked`, not `complete`
