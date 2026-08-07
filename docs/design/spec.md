# Kode Brain vNext — Canonical Product & Knowledge Spec

**Status:** Canonical
**Applies to:** Kode Brain vNext
**Last aligned:** 2026-08-07 (consolidation pass — Project History, lifecycle states, flat IDs absorbed)

> This document is the current product contract for Kode Brain. When it conflicts with older documents under `docs/design/`, this document wins until those documents are migrated.

---

## 1. Product Definition

Kode Brain is a **living project knowledge and coordination system for software projects**.

It is not only a codebase documentation generator. It must support a project from the moment the project is conceived, through implementation, maintenance, migration, and long-term evolution.

Kode Brain answers four questions:

1. **What SHOULD the system be?** — Project Contract, architecture direction, domain responsibilities, decisions, invariants. Intended reality.
2. **What IS the system?** — Source code, configuration, runtime behavior, tests, infrastructure. Observed reality.
3. **What are we CHANGING?** — Active changes, drift between intent and observation.
4. **HOW DID WE GET HERE?** — Completed changes, superseded decisions, incidents, milestones, lessons. Semantic project memory that accumulates value as the project ages.

The primary users are:

- human developers and project owners,
- coding agents,
- review and maintenance agents,
- future contributors who need to understand the project without rediscovering it from scratch.

---

## 1.1 System Diagram

```text
                    KODE BRAIN SYSTEM
              "Living knowledge for software projects"
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    KNOWLEDGE MODEL   WORKFLOW MODEL    PROJECT MEMORY
    (what is true)    (how we act)      (how we got here)
          │                │                │
          ▼                ▼                ▼
   Project Contract    Onboarding       Decisions (lineage)
   Architecture        Reading Pack     Completed Changes
   Domains             Active Change    Incidents
   Invariants          Reconciliation   Milestones
   Evidence/Drift      Agent Rules      Timeline (generated)
```

Each box links to its canonical specification section within this document.
The diagram is navigational — trace a concept from root to its single authoritative definition.

---

## 2. Core Mental Model

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

---

## 3. Kode Brain Must Support Two First-Class Project Modes

### 3.1 Greenfield Mode — before meaningful code exists

Kode Brain may be initialized before implementation begins.

In this mode Kode Brain acts as a lightweight project-definition and architecture assistant.

It must:

1. interview the user to understand intent,
2. create the initial Project Contract,
3. define initial architecture and technology choices when known,
4. define domain boundaries and responsibilities,
5. record important decisions and invariants,
6. create an implementation-ready project knowledge skeleton,
7. make that knowledge available to coding agents before they write code.

The Project Contract is the initial canonical specification for implementation.

The absence of source code is not an error and must not prevent onboarding.

### 3.2 Brownfield Mode — an existing codebase

Kode Brain must also onboard existing projects, including large legacy projects and projects that were partially onboarded before.

In this mode Kode Brain must:

1. discover existing project documents and prior KB content,
2. determine how much project intent is already known,
3. interview the user only for important missing or conflicting intent,
4. build or repair the Project Contract,
5. scan observed implementation evidence,
6. build architecture and domain maps progressively,
7. surface drift, uncertainty, legacy areas, and unmapped areas.

A large repository must not require a complete deep scan before the KB becomes useful.

---

## 4. Unified Onboarding Command

The preferred user-facing operation is:

```bash
/kodebrain onboard [path]
```

`onboard` is **idempotent, resumable, and gap-driven**.

The user should not need to know whether they need `init`, `scan`, `resume`, `migrate`, or `repair`.

Kode Brain determines the project state itself:

```text
fresh project / no code
new codebase / no KB
partial KB
existing KB with missing project-level knowledge
stale KB
older schema / older Kode Brain format
well-onboarded project
```

Legacy commands may remain temporarily for compatibility, but `onboard` is the canonical onboarding workflow.

---

## 5. Onboarding Workflow

### Phase 0 — Detect Project and KB State

Inspect:

- repository and file topology,
- existing `docs/brain/`,
- README and project docs,
- manifests and build files,
- existing Kode Brain schema/version,
- current completeness of project-level knowledge.

Produce an internal **Knowledge Gap Map**.

The gap map determines which later phases need to run.

---

### Phase 1 — Discover Existing Intent

Before inferring project purpose from code, search for intent in:

- Project Contract / existing Kode Brain pages,
- README,
- ADRs,
- product or design documentation,
- architecture documentation,
- explicit human notes.

Kode Brain must distinguish between documentation that describes **intended/current architecture** and historical or stale documentation when possible.

---

### Phase 2 — Intent Alignment Interview

If project-level intent is absent, materially incomplete, ambiguous, or contradictory, interview the user before deep mapping.

Do not interview merely because a particular file is missing. Interview only for knowledge that materially improves project interpretation.

The minimum interview should establish, where relevant:

1. **Purpose and users** — what the project is and who it serves.
2. **Core outcomes/workflows** — the small number of things the system fundamentally must accomplish.
3. **Known system shape** — apps, services, workers, major components, if the user knows them.
4. **Critical external systems** — important third-party or organizational dependencies.
5. **Known legacy/migration areas** — code or subsystems the user already knows should not be treated as intended architecture.

For greenfield projects, the interview may additionally establish:

- initial technology constraints,
- deployment constraints,
- security/privacy constraints,
- expected integrations,
- initial domain boundaries,
- critical non-functional requirements.

The interview should remain short by default. Unknown answers are valid; Kode Brain should investigate what can be discovered automatically.

---

### Phase 3 — Create or Repair the Project Contract

Create a project-level knowledge skeleton before deep mapping.

Canonical structure:

```text
docs/brain/projects/<project>/
  <project>.md

  architecture/
    overview.md
    technology.md
    runtime.md
    data.md
    deployment.md
    integrations.md

  domains/
    <domain>/
      <domain>.md
      capabilities/
      flows/
      concepts/
      models/
      apis/
      decisions/
      risks/

  decisions/

  changes/
    active/
    completed/

  incidents/

  milestones/

  history/
    timeline.md       ← generated (timeline.py)
    events.json       ← generated temporal index

  graph/
    nodes.json
    edges.json
    file-index.json
    file-hashes.json

  reports/
    knowledge-gaps.md
    drift.md
    unmapped-files.md
    suspected-legacy.md
    stale-docs.md
    needs-review.md
    reading-packs/
```

Not every file must contain content immediately. The structure may be progressively populated.

---

## 6. Project Hub Contract

`<project>.md` is the required **START HERE** page for both humans and agents.

It should allow a contributor to form a useful mental model of the system within roughly one or two minutes.

Required sections:

```md
# <Project Name>

## Purpose

## Primary Users / Actors

## Core Outcomes

## Scope
### In Scope
### Out of Scope

## Technology Summary

## System Architecture

## Domains

## Runtime Entry Points

## External Systems

## System-wide Invariants

## Current Risks / Legacy / Migration

## Active Changes

## Where To Start
```

The page should favor orientation over exhaustive detail.

Detailed knowledge belongs in linked architecture/domain/node pages.

---

## 7. Architecture Contract

Architecture documentation explains how the system fits together at a level above individual capabilities and source files.

### `architecture/overview.md`

Must describe:

- major applications/services/processes,
- major system boundaries,
- major communication paths,
- high-level domain placement,
- system-context or container-style diagram where useful,
- links to deeper architecture pages.

### `architecture/technology.md`

Describe important technologies by role rather than as an unstructured dependency list:

- frontend/client,
- backend/runtime,
- persistence,
- cache,
- queue/event system,
- testing,
- build/tooling,
- infrastructure.

### `architecture/runtime.md`

Describe processes and runtime topology:

- servers,
- workers,
- schedulers,
- CLI processes,
- event consumers,
- runtime boundaries.

### `architecture/data.md`

Describe:

- primary databases,
- major data stores,
- ownership boundaries,
- caches,
- derived data,
- critical data movement rules.

### `architecture/deployment.md`

Describe environments, deployment topology, and operational boundaries when known.

### `architecture/integrations.md`

Describe external systems and why they exist, not merely SDK imports.

Architecture pages should be narrative maps, not a collection of tiny technology nodes.

---

## 8. Domain Contract

A domain represents a major area of business or system responsibility.

A domain page should prioritize responsibility boundaries before implementation detail.

Recommended order:

```md
# <Domain>

## Responsibility

## Owns

## Does Not Own

## Depends On

## Used By

## Core Concepts

## Capabilities

## Core Flows

## Data Ownership

## Entry Points

## Invariants

## Legacy / Migration

## Risks

## Source Areas

## Open Questions
```

`Owns`, `Does Not Own`, and `Depends On` are especially important because folder boundaries do not reliably represent responsibility boundaries.

Domain boundaries may initially be human-defined, source-derived, inferred, or mixed. Provenance must be preserved.

---

## 9. Knowledge Map Detail Levels

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

The existing detailed node families remain useful:

- capability,
- concept,
- flow,
- layer,
- engine,
- adapter,
- data model,
- API,
- UI,
- runtime behavior,
- state,
- decision,
- caveat/risk,
- legacy area,
- migration state.

They should be treated as deeper knowledge, not a substitute for project-level architecture.

---

## 10. Progressive Mapping for Large Projects

Kode Brain must not try to deeply document every source file before producing useful project knowledge.

Brownfield onboarding should progress approximately as follows:

1. inventory,
2. project intent,
3. architecture skeleton,
4. domain map,
5. runtime entry points,
6. high-value capabilities and flows,
7. frequently changed or highly connected areas,
8. task-relevant areas,
9. remaining unmapped areas.

For large repositories, process incrementally and persist progress.

A partially mapped KB is acceptable if its gaps are explicit.

`reports/knowledge-gaps.md` should make incomplete coverage visible.

---

## 11. Harvest and Source Reading Policy

The deterministic harvest remains the preferred first step for source inspection because it lowers cost and provides reproducible evidence.

However, the rule **"LLM never reads raw source files" is no longer canonical**.

Use an escalation model:

```text
Level 0 — file and project inventory
Level 1 — deterministic harvest
Level 2 — manifests/configuration/document inspection
Level 3 — targeted source reading
Level 4 — human clarification
```

Source reading is appropriate when:

- harvest output is insufficient to determine semantics,
- a supported language has weak extraction coverage,
- dynamic wiring cannot be resolved statically,
- project/domain boundaries are ambiguous,
- a critical runtime flow needs verification,
- source and existing KB contradict each other.

Do not read an entire large codebase without reason. Read targeted source based on expected information gain.

---

## 12. Intended Truth vs Observed Truth

Kode Brain must preserve the distinction between intent and observation.

Examples:

```text
Intent:
  "Stripe is the current payment provider."

Observed:
  "Stripe and Omise adapters both exist in source."
```

Both facts may be correct.

Authority rules:

- human-approved project intent is authoritative for **what should be true**,
- canonical project documents are authoritative for documented intent unless superseded,
- source code and configuration are authoritative evidence for **what implementation exists**,
- runtime evidence is authoritative for **what executed in the observed runtime context**,
- generated inference is never allowed to silently override stronger authority.

When intent and observation disagree, create a drift record.

---

## 13. Provenance and Confidence Are Separate

Current confidence semantics should evolve so that **how sure we are** is not confused with **where the claim came from**.

### Provenance / authority examples

```text
human
project_document
source_code
configuration
runtime
test
git
generated
```

### Confidence examples

```text
verified
supported
inferred
ambiguous
stale
needs_human_review
```

A human statement can be authoritative intent without being verified implementation.
A source-supported observation can be accurate implementation without representing intended design.

Schema implementation details may evolve, but this conceptual separation is required.

---

## 14. Change-First Workflow

Kode Brain should be updated **before implementation begins** when a task materially changes project behavior, architecture, domain responsibility, invariants, or public contracts.

Do not edit current-state architecture to pretend an unimplemented future already exists.

Instead create an active change record:

```text
changes/active/YYYY-MM-DD-<slug>.md
```

### Change Lifecycle States

Change lifecycle is separate from generic KB `status` (which remains `active` while the record exists):

| change_state | Meaning |
|---|---|
| `planned` | Intent recorded, implementation not yet started |
| `in_progress` | Implementation underway |
| `implemented` | Code complete, not yet reconciled with KB |
| `reconciled` | KB updated, drift checked, lessons captured |

After reconciliation, the change moves to `changes/completed/`.

### Change Record Structure

```md
# <Change>

State: planned | in_progress | implemented | reconciled
Outcome: success | partial | abandoned | rolled_back

## Intent
## Why
## Affected Domains
## Architecture Impact
## Expected Behavior Changes
## Invariants
## Compatibility / Migration
## Expected Source Areas

## Progress Log
### YYYY-MM-DD
...
### YYYY-MM-DD
...

## Implementation Evidence
## Outcome (filled after reconciliation)
## Deviations From Plan
## Lessons Learned
## Follow-ups
## Regressions / Problems Introduced
## Open Questions
```

### Lifecycle

```text
Task arrives
  ↓
Read Project Contract + relevant domains
  ↓
Retrieve relevant history (past decisions, similar changes, incidents)
  ↓
Create/update active change with change_state: planned
  ↓
Record architecture/decision impact
  ↓
Implement code (change_state: in_progress)
  ↓
Progress Log entries accumulate during implementation
  ↓
Harvest/review changed evidence
  ↓
Compare intended change vs implementation
  ↓
Reconcile canonical current-state docs
  ↓
Fill Outcome, Deviations, Lessons Learned
  ↓
Mark reconciled, move to completed
  ↓
Regenerate timeline + events
```

History retrieval before implementation ensures agents learn from past decisions, similar changes, and incidents touching the same domains or nodes.

---

## 14.1 Status vs Lifecycle State

Generic KB `status` describes knowledge quality (`active`, `stale`, `needs_review`). Lifecycle state is separate and type-specific:

| Record type | Lifecycle field | Values |
|---|---|---|
| Change | `change_state` | planned, in_progress, implemented, reconciled |
| Incident | `incident_state` | ongoing, mitigated, resolved |
| Decision | `decision_state` | active, superseded, deprecated |

A completed change has `status: active` (knowledge is valid) and `change_state: reconciled` (lifecycle is complete). A superseded decision has `status: active` (knowledge preserved intentionally) and `decision_state: superseded` (no longer current direction).

This separation is enforced in `schema/node.schema.json` and all templates.

---

## 15. Project History (The Fourth Question)

Project History is the semantic time axis — it answers **HOW DID WE GET HERE?**

History records are **append-oriented**. Once recorded, they are not rewritten. If understanding changes, a new record supersedes the old one — the old record remains as evidence of the path taken.

History is **not current truth**. If a lesson must constrain future behavior, it must be promoted:

```
Incident → lesson extracted → Decision → codified as → Invariant
```

### Record Types

Four semantic record types carry project history:

**Change (completed):** Records of what was intentionally changed. After reconciliation, captures outcome, deviations from plan, lessons learned, follow-ups, and regressions introduced. Progress log entries within active changes become temporal events.

**Decision:** Why a direction was chosen or changed. Decisions have lineage: a new decision may `supersede` an older one. `superseded_by` is derived by the compiler — only `supersedes` is stored on the new decision. The old decision is not rewritten.

**Incident:** Something that went wrong and was learned from. Includes architectural mistakes, data corruption, migration problems, performance disasters, security near misses, dependency problems, and failed implementation approaches. Records: what happened, root cause, why existing design allowed it, lesson, guardrail introduced, and affected knowledge nodes (enabling task → node → incident traversal).

**Milestone:** A significant project inflection point that changed the mental model — MVP launch, monolith split, provider migration, legacy removal, multi-tenant architecture. Not every release; only events that changed how contributors think about the system.

### Generated Artifacts

History records are the source of truth. Two artifacts are generated from them:

| Artifact | Generator | Purpose |
|---|---|---|
| `history/timeline.md` | `timeline.py` | Human-readable chronological timeline |
| `history/events.json` | `timeline.py` | Temporal index for agent retrieval |

### Agent Workflow Integration

Before a material change, agents must:

1. Identify affected nodes (domains, capabilities, flows)
2. Load `history/events.json`
3. Find relevant history: past decisions affecting same nodes, similar completed changes, incidents touching affected nodes, previous rollbacks
4. Surface historical warnings in the active change
5. Reading packs include a **Relevant History** section

This makes Kode Brain more valuable as the project ages — accumulated history prevents repeated mistakes.

---

## 16. Drift

A drift item records a meaningful disagreement between intended and observed reality.

Examples:

- intended architecture says only Stripe is active, but an Omise path appears live,
- domain contract says Orders owns cancellation, but runtime routes delegate it to Fulfillment,
- a completed change says an old API was removed, but routes still expose it,
- source changed a system invariant without a corresponding decision/change record.

Drift must be surfaced, not silently resolved.

Write drift to:

```text
reports/drift.md
```

Important drift may also become a risk/caveat node.

---

## 17. Markdown and Generated Graph Artifacts

Human-readable project knowledge is canonical.

Kode Brain should move toward:

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

The graph files are derived machine indexes and must not become a second independently edited source of truth.

Implementation may transition toward this model in phases, but new design work must not introduce additional dual-write authority.

---

## 18. Reading Behavior for Agents

A Kode Brain-enabled coding agent should start at the highest useful level rather than blindly reading source.

Normal task startup:

1. read project hub,
2. identify relevant domain(s),
3. read active change if one exists,
4. generate/read a focused reading pack,
5. inspect detailed KB nodes,
6. open targeted source files required for the actual edit or verification.

The rule is **KB first, source when needed**, not **KB instead of source**.

---

## 19. Source of Truth Update Rule

For material changes, agents must keep Kode Brain aligned as part of the development workflow.

Before implementation:

- create/update the active change,
- update intended decisions/specification if the decision itself has changed.

After implementation:

- update observed knowledge from changed source,
- reconcile affected project/domain/architecture pages,
- surface drift or uncertainty,
- update indexes,
- complete the change only when documentation and implementation agree sufficiently.

Refactors that do not change behavior may use a lighter update path.

---

## 20. Greenfield Project Definition Workflow

When `/kodebrain onboard` runs on an empty or nearly empty new project, Kode Brain must not attempt to infer domains from nonexistent source.

Instead:

```text
Detect Greenfield
      ↓
Intent Interview
      ↓
Project Contract Draft
      ↓
Architecture Skeleton
      ↓
Initial Domain Contracts
      ↓
Initial Decisions / Invariants
      ↓
Agent Instructions Installed
      ↓
Implementation Begins
```

At minimum, the resulting KB should tell an implementation agent:

- what is being built,
- who it is for,
- what is in and out of scope,
- core outcomes/workflows,
- current technology/architecture decisions or unresolved choices,
- initial domains and responsibilities,
- critical constraints and invariants,
- what remains undecided.

Unknowns must remain explicit rather than being filled with invented architecture.

---

## 21. Partial and Re-Onboarding Workflow

If Kode Brain already exists, onboarding should inspect completeness instead of starting over.

Example gap state:

```text
Purpose              complete
Technology           complete
Architecture         missing
Domains              partial
External systems     missing
Core workflows       complete
Domain boundaries    partial
```

Kode Brain should ask only for high-value missing human knowledge, then discover what it can from evidence.

Existing human notes and verified content must be preserved.

No page should be deleted merely because a new onboarding pass cannot confirm it.

---

## 22. Canonical Naming Direction

The vNext implementation must normalize naming and eliminate contradictory contracts across documentation, schemas, templates, and skill instructions.

Target direction:

- Product name: `Kode Brain`
- Package / CLI: `kodebrain`
- Primary command surface: `/kodebrain ...`
- Primary onboarding command: `/kodebrain onboard`
- KB location: `docs/brain/projects/<project>/`
- Domain hub filename: `<domain>.md`

Node ID format is flat, hyphen-separated: `<domain-slug>-<type-slug>` (e.g. `auth-login-flow`). Enforced in all schemas, templates, and compilers. The hierarchical format (`auth/login-flow`) is legacy — migrated by `migrate_kb.py` to flat format.

---

## 23. Compatibility and Migration Principles

vNext may evolve the current schemas and generated layout.

Migration rules:

1. preserve human-authored notes,
2. do not silently discard existing nodes/pages,
3. detect older KB format/version,
4. migrate deterministically where possible,
5. report ambiguous migration cases,
6. keep backwards compatibility only where it does not preserve contradictory authority models indefinitely.

Compatibility is useful; permanent ambiguity is not.

---

## 24. Non-Goals

Kode Brain is not intended to:

- automatically rewrite an entire project architecture without human intent,
- replace source code as implementation evidence,
- guarantee runtime behavior from static analysis alone,
- auto-delete suspected legacy code,
- make product decisions that are genuinely unknown,
- generate exhaustive documentation for every trivial function,
- require Obsidian to function,
- require a database service to function.

---

## 25. Success Criteria

Kode Brain succeeds when:

### For a new project

A coding agent can begin implementation from Kode Brain and correctly explain the project's purpose, architecture direction, core domains, constraints, and unresolved decisions before meaningful source code exists.

### For an existing project

A new human or agent can orient itself quickly, understand the intended architecture, distinguish current implementation from legacy or drift, and navigate to the correct source area without rediscovering the entire codebase.

### During development

Material changes leave a trace from intent → implementation → reconciled project knowledge.

### Over time

The project knowledge base becomes more accurate through work rather than steadily becoming stale documentation.

---

## 26. Precedence Rule

Kode Brain follows **specification authority**: every concept has exactly one canonical owner.

### Authority hierarchy

1. `docs/design/spec.md` (this document) — canonical product and knowledge root
2. `schema/node.schema.json` — canonical field contract for all node types
3. `kodebrain/skill/SKILL.md` — agent behavioral contract (derived from this spec)
4. `docs/design/implementation-plan-vnext.md` — migration execution order (plan, not spec)
5. `docs/design/project-history.md` — design rationale for Project History (historical, not current spec)
6. `docs/design/taxonomy.md`, `skills.md`, `agents.md`, `workflows.md` — older design input, superseded where they conflict
7. `docs/design/open-decisions.md` — resolved decision records, not current spec

### Rule

When a new concept is introduced:

1. Locate the canonical owner in this spec
2. Modify that section — do not create a competing document
3. If no owner exists, add one canonical section and link it from the root diagram
4. Record rationale in a Decision, not a parallel spec

The anti-pattern is: new idea → create another design document → implement from that document → leave the canonical spec unchanged. This is specification drift.