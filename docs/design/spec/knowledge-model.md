---
spec_id: knowledge-model
spec_role: canonical
parent: root
owns:
  - knowledge.layers
  - knowledge.truth-model
  - knowledge.provenance
  - knowledge.confidence
  - knowledge.harvest
  - knowledge.drift
  - knowledge.graph-compilation
---

# Knowledge Model

Canonical owner for: core mental model, intended vs observed truth, provenance/confidence, harvest policy, drift detection, graph compilation.

## Core Mental Model

Kode Brain uses three layers of project knowledge:

```text
┌─────────────────────────────────────────────┐
│              PROJECT CONTRACT               │
│                                             │
│ Purpose / Scope / Architecture / Domains    │
│ Invariants / Decisions / Active Changes     │
│                                             │
│        INTENDED / CANONICAL KNOWLEDGE       │
└──────────────────────┬──────────────────────┘
                       │ guides
                       ▼
┌─────────────────────────────────────────────┐
│              KNOWLEDGE MAP                  │
│                                             │
│ Capabilities / Flows / Concepts / Models    │
│ APIs / Risks / Legacy / Migration           │
│                                             │
│          EXPLANATION + NAVIGATION           │
└──────────────────────┬──────────────────────┘
                       │ grounded by
                       ▼
┌─────────────────────────────────────────────┐
│                 EVIDENCE                    │
│                                             │
│ Source / Symbols / Tests / Config / Runtime │
│ Git / Infrastructure / Human Evidence       │
│                                             │
│              OBSERVED REALITY               │
└─────────────────────────────────────────────┘
```

The Project Contract answers **what the system is intended to be**.
The Evidence layer answers **what can currently be observed**.
The Knowledge Map connects and explains the two.

Kode Brain must never silently rewrite intended knowledge from observed code or rewrite observed claims merely because a human intended something else. A disagreement becomes a **drift item**.

## Progressive Knowledge Detail

Kode Brain should use progressive detail.

Recommended navigation order:

```text
Project
  → Architecture
  → Domain
  → Active Change (when relevant)
  → Capability / Flow / Concept / Model / API / Risk
  → Evidence / Source
```

Do not require users or agents to begin with graph internals.

Node families: capability, concept, flow, layer, engine, adapter, data_model, api, ui, runtime_behavior, state, decision, caveat, legacy_area, migration_state. They are deeper knowledge, not a substitute for project-level architecture.

## Progressive Mapping for Large Projects

Kode Brain must not try to deeply document every source file before producing useful project knowledge.

Brownfield onboarding progresses:

1. inventory,
2. project intent,
3. architecture skeleton,
4. domain map,
5. runtime entry points,
6. high-value capabilities and flows,
7. frequently changed or highly connected areas,
8. task-relevant areas,
9. remaining unmapped areas.

For large repositories, process incrementally and persist progress. A partially mapped KB is acceptable if its gaps are explicit. `reports/knowledge-gaps.md` should make incomplete coverage visible.

## Harvest and Source Reading Policy

The deterministic harvest remains the preferred first step for source inspection because it lowers cost and provides reproducible evidence.

The rule **"LLM never reads raw source files" is no longer canonical.**

Use an escalation model:

```text
Level 0 — file and project inventory
Level 1 — deterministic harvest
Level 2 — manifests/configuration/document inspection
Level 3 — targeted source reading
Level 4 — human clarification
```

Source reading is appropriate when: harvest output is insufficient to determine semantics, a supported language has weak extraction coverage, dynamic wiring cannot be resolved statically, project/domain boundaries are ambiguous, a critical runtime flow needs verification, source and existing KB contradict.

Do not read an entire large codebase without reason. Read targeted source based on expected information gain.

## Intended Truth vs Observed Truth

Kode Brain must preserve the distinction between intent and observation.

Authority rules:

- human-approved project intent is authoritative for **what should be true**,
- canonical project documents are authoritative for documented intent unless superseded,
- source code and configuration are authoritative evidence for **what implementation exists**,
- runtime evidence is authoritative for **what executed in the observed runtime context**,
- generated inference is never allowed to silently override stronger authority.

When intent and observation disagree, create a drift record.

## Provenance and Confidence Are Separate

**Provenance** = where the claim came from: `human`, `project_document`, `source_code`, `configuration`, `runtime`, `test`, `git`, `generated`.

**Confidence** = how trustworthy the claim is: `verified`, `supported`, `inferred`, `ambiguous`, `stale`, `needs_human_review`.

A human statement can be authoritative intent without being verified implementation. A source-supported observation can be accurate implementation without representing intended design.

## Drift

A drift item records a meaningful disagreement between intended and observed reality.

Examples: intended architecture says only Stripe is active, but an Omise path appears live; domain contract says Orders owns cancellation, but runtime routes delegate it to Fulfillment; a completed change says an old API was removed, but routes still expose it.

Drift must be surfaced, not silently resolved. Write to `reports/drift.md`. Important drift may also become a risk/caveat node.

## Markdown-First Graph Compilation

Human-readable project knowledge is canonical. Kode Brain uses:

```text
Markdown knowledge
      │
      │ compile / index
      ▼
nodes.json
edges.json
file-index.json
search indexes
```

Graph files are derived machine indexes and must not become a second independently edited source of truth. Normal agent workflow does not manually maintain the same relationship in Markdown and JSON independently. Generated indexes can be rebuilt deterministically.

## `canonical_source` Field Semantics

A knowledge node may declare that its normative definition lives in an external canonical document:

```yaml
canonical_source:
  path: docs/design/spec/history-model.md
  anchor: decision-lifecycle
```

### Knowledge Role Constraints

- `knowledge_role: reference` — required when `canonical_source` is set. The page is a navigation/context projection of a canonical definition elsewhere. Normative questions route to `canonical_source`.
- `knowledge_role: mixed` — permitted with `canonical_source` when the page contains both reference navigation AND original observed evidence not covered by the canonical source.
- `knowledge_role: intent` — NOT permitted with `canonical_source`. Intent pages claim to own the concept; if a canonical source exists, intent is held there.

### Reference Page Template

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

### Machine Contract

The field shape is defined in `schema/node.schema.json`. This spec defines what `canonical_source` *means* — the schema defines its *form*.
