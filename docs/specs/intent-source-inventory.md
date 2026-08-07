# Intent Source Inventory

**Status:** DRAFT v0.1 — awaiting user confirmation
**Created:** 2026-08-07
**Domain:** kb-workflow (onboard), kb-substrate (harvest)

---

## Purpose

Add a deterministic Intent Source Inventory phase to onboard — before source-code harvest — so
intent documents (specs, ADRs, PRDs, architecture docs, human notes) are discovered, classified,
and confirmed before the Project Contract is built. Without this phase, onboard reconstructs intent
from source code silently, which produces false consensus (drift = 0) when intent docs and source
disagree.

## Trigger

`/kodebrain onboard` — insert between state detection (Step 1) and any source harvesting. Also
runnable standalone: `harvest.py --intent-sources <root>`.

## Non-Negotiable Principles

1. **Intent before observation.** Intent docs are the primary input; source confirms or challenges,
   never replaces.
2. **Deterministic where possible.** Filesystem scan + file-kind classification = script, not LLM.
   LLM used only for semantic classification of *ambiguous* documents.
3. **Minimal human interview.** Ask only when the machine cannot decide: draft status confirmation,
   document authority ambiguity. Never ask "describe your project."
4. **Unknown is honest.** `decision_date: unknown` is more truthful than recording today's date.
   Inferred rationale marked `needs_review` is better than fabricated Decision.
5. **No silent drift resolution.** Intent-observed disagreement produces a drift record; never
   silently resolved to one side.

## Proposed Phase Insertion

```
Current onboard:
  State Detection → [Discover Intent (manual LLM)] → Interview → Project Contract → ...
                                                                              ↓
                                                                     Source Harvest (H1-H5)
                                                                              ↓
                                                                     Compile → Validate → Summary

After:
  State Detection → Intent Source Inventory (deterministic) → Adaptive Interview (1 Q max)
                                                                              ↓
                                                              Project Contract (intent-aware)
                                                                              ↓
                                                              Source Harvest → Compile → Validate
                                                                              ↓
                                                              Drift: intent vs observed surfaced
```

## Steps — Intent Source Inventory

### Step 1: Repository Scan (deterministic)

Scan project root for potential intent sources using a file-kind lookup table
(no LLM — shell `find` / Python `Path.glob` is sufficient):

| Glob pattern | Kind | Default authority |
|---|---|---|
| `docs/specs/**/*.md`, `docs/spec/**/*.md` | specification | high (if confirmed) |
| `docs/architecture/**/*.md`, `docs/design/**/*.md` | architecture_doc | high (if confirmed) |
| `docs/adr/**/*.md`, `**/decisions/**/*.md` | adr | high |
| `README.md`, `README.*.md` | readme | medium |
| `**/PRD*.md`, `**/product-requirement*.md`, `**/product_brief*.md` | prd | high (if confirmed) |
| `docs/brain/**/*.md` (existing KB, if partial/legacy) | existing_kb | medium (stale possible) |
| `**/CONTRIBUTING.md`, `**/ARCHITECTURE.md` | convention | medium |
| `**/DESIGN.md`, `**/ROADMAP.md` | design_doc | medium |
| Human-authored notes (user-supplied path or convention) | human_note | highest |

Output: flat list `{path, matched_glob, kind, default_authority}`.

### Step 2: Status Extraction (deterministic)

For each discovered intent source, extract status signals from the file content:

1. **Frontmatter `status`** field: `draft`, `review`, `approved`, `current`, `historical`, `superseded`
2. **Git blame age**: last meaningful edit date (not onboarding activity)
3. **Header markers**: `DRAFT`, `WIP`, `v0.1`, `CONFIRMED`, `DEPRECATED`

Classification rules (deterministic — no LLM):

| Signal | status | requires_confirmation |
|---|---|---|
| `status: draft` or header `DRAFT` | `draft` | true |
| `status: approved` or `status: current` | `current` | false |
| `status: historical` or `status: superseded` | `historical` | false |
| No status marker, file > 90 days old | `unknown` | true |
| No status marker, file < 90 days old | `unknown` | true |

`requires_confirmation: true` when status is `draft` or `unknown` — the document may still be
the project's authoritative intent but the machine cannot tell.

### Step 3: Classification (LLM-light)

Only for documents where `kind` or authority is genuinely ambiguous after Steps 1-2.
Default: accept `default_authority` from lookup table + `status` from Step 2.

LLM reads first ~100 lines of each ambiguous document. Classification prompt is constrained to
a single multiple-choice question per document — no free-text summarization. Only emit fields
that the lookup table cannot provide.

### Step 4: Produce Inventory Artifact

Output `docs/brain/projects/<name>/graph/intent-sources.json`:

```json
{
  "discovered": 3,
  "confirmed": 0,
  "draft_or_unknown": 3,
  "historical": 0,
  "sources": [
    {
      "path": "docs/specs/ai-interview-builder.md",
      "kind": "specification",
      "status": "draft",
      "authority": "high",
      "requires_confirmation": true,
      "last_modified": "2026-08-05",
      "title": "AI Interview Builder",
      "covers_domains": ["interview"],
      "non_negotiable_principles": [
        "State machine: idle → listening → processing → responding",
        "Non-destructive edit",
        "InterviewSchema lifecycle: draft → active → archived"
      ]
    }
  ]
}
```

`covers_domains` and `non_negotiable_principles` are extracted by LLM from the confirmed intent
documents only — machine-readable hooks for later drift comparison.

### Step 5: Adaptive Interview (1 question max)

For each source where `requires_confirmation: true`, ask the human exactly one question:

> **`<title>`** (`<path>`, `<kind>`, status: `<status>`)
> Is this still the current specification the system should follow?
>
> [1] Yes — treat as authoritative intent
> [2] Partially — some sections superseded (let me note which)
> [3] No — mark historical / superseded
> [4] Skip — decide later

Only `draft` or `unknown` documents get interviewed. Confirmed documents (`status: current`)
are accepted without interview.

If no documents require confirmation → skip interview phase entirely.

## Impact on Project Contract

### Provenance

When intent sources exist and are confirmed, Project Contract pages carry:

```yaml
provenance: project_document   # was: source_code
knowledge_role: intent          # was: mixed
intent_sources:
  - docs/specs/ai-interview-builder.md
observed_sources:
  - package.json
  - src/**
  - web/**
```

Sections inherit semantic role:
- `Purpose`, `Scope`, `Core Outcomes` → **intended** (from spec)
- `Technology`, `Current Architecture`, `Source Areas` → **observed** (from source)
- `Drift` → **comparison** (generated)

### Drift Detection

After intent is confirmed, compare intent doc claims against observed source:

```
Intent (spec):  voice MVP → Wispr (local)
Observed:       source uses Whisper
Result:         drift item — TECHNOLOGY_DISAGREEMENT
```

```
Intent (spec):  InterviewSchema: draft → active → archived
Observed:       implementation has no state field
Result:         drift item — SCHEMA_DISAGREEMENT
```

Drift items are written to `reports/drift.md` and flagged with `confidence: inferred` until
human confirms which side wins.

## Decision Record Provenance Rules

Replace current onboard decision-generation with:

| Evidence available | Can create | Cannot create |
|---|---|---|
| Source code only | Observed architecture, Observed convention, Inferred rationale (needs_review) | Decision record |
| Human confirmation | Decision record (provenance: human) | — |
| ADR / spec / design doc | Decision record (provenance: project_document) | — |
| Commit/PR explaining why | Decision record (provenance: git) | — |

Decision records require at least one non-source evidence. Source-only "decisions" are
downgraded to Observed Architecture nodes with `confidence: inferred` and an
`rationale_note: "Inferred from implementation — not confirmed by human or doc."`.

### Date Handling

```yaml
# Decision record
decision_date: 2026-08-05   # actual decision date (from git/doc)
recorded_at: 2026-08-07      # when KB captured it
recovered_from:
  - git:abc1234
  - docs/adr/005-in-memory-repos.md

# When date unknown
decision_date: unknown
recorded_at: 2026-08-07
# honest: KB doesn't know when this was decided
```

Never set `decision_date` to `recorded_at` when the actual decision date is unknown.

## Benchmark — Two-Axis Coverage

Replace single overall score with two dimensions:

```
Implementation Coverage
  Source files mapped:  39/39  (100%)
  Unmapped files:       0
  ✅

Intent Coverage
  Intent documents discovered:  1
  Confirmed / consumed:         0
  Draft / pending:              1
  🔴 — 1 intent doc not yet confirmed
```

Add to `run_benchmark()` output:

```json
{
  "implementation_coverage": {
    "source_files_total": 39,
    "source_files_mapped": 39,
    "coverage_pct": 100.0
  },
  "intent_coverage": {
    "intent_sources_discovered": 1,
    "intent_sources_confirmed": 0,
    "intent_sources_draft_or_unknown": 1,
    "intent_sources_historical": 0,
    "intent_coverage_pct": 0.0
  }
}
```

`intent_coverage_pct` = `confirmed / max(discovered, 1) * 100`.

## Regression Gates (3 cases from external dogfood)

These are acceptance criteria — onboard is broken until they pass:

### Gate 1: Brownfield Intent Discovery

**Given:** `docs/specs/ai-interview-builder.md` marked DRAFT / awaiting confirmation.
**Onboard must:**
1. Discover it as candidate intent (in `intent-sources.json`)
2. NOT silently treat source as canonical intent
3. Ask whether the draft is still current (adaptive interview)

### Gate 2: Intent-Observed Comparison

**Given:** spec says Wispr, source says Whisper; spec says InterviewSchema has lifecycle,
implementation has no state field.
**After intent confirmed:**
1. Drift items appear in `reports/drift.md`
2. Drift count > 0 in `validation-result.json`
3. `completion_state` is NOT `complete` when unresolved drift exists

### Gate 3: Decision Recovery

**Given:** code uses in-memory repository but no why-evidence exists.
**Must not:** invent a historical Decision + rationale.
**May:** record Observed Architecture node; record Inferred Rationale marked `needs_review`.

## Implementation Plan (sketch)

| Phase | What | Where |
|---|---|---|
| 1 | `intent_inventory.py` — deterministic scan + status extraction | `kodebrain/skill/scripts/` |
| 2 | `harvest.py --intent-sources` CLI flag | `kodebrain/skill/scripts/harvest.py` |
| 3 | Update SKILL.md onboard steps: insert Intent Source Inventory as Step 2, renumber | `kodebrain/skill/SKILL.md` |
| 4 | Decision provenance gate in onboard + update SKILL.md decision rules | SKILL.md |
| 5 | Two-axis benchmark in `run_benchmark()` | `harvest.py` |
| 6 | Adaptive interview template in onboard flow (1 question per unconfirmed source) | SKILL.md |
| 7 | Regression gate acceptance criteria (manual dogfood verification) | `docs/specs/intent-source-inventory.md` (this doc) |

## Open Questions

- Should `intent-sources.json` be regenerated on every onboard, or only on first? (Lean: every onboard, but skip interview if sources unchanged and already confirmed)
- Should `docs/brain/` itself be excluded from intent source scan to prevent self-referential loops? (Lean: yes — skip `docs/brain/**`)
- Claim-level provenance? Deferred. Page-level with `intent_sources`/`observed_sources` list is sufficient for now.
