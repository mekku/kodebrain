---
spec_id: workflow-model
spec_role: canonical
parent: root
owns:
  - onboarding.process
  - greenfield.workflow
  - brownfield.workflow
  - change.lifecycle
  - status-lifecycle.separation
  - agent.behavior
---

# Workflow Model

Canonical owner for: onboarding (greenfield/brownfield), change lifecycle, status vs lifecycle separation, agent reading behavior.

## Two First-Class Project Modes

### Greenfield Mode — before meaningful code exists

Kode Brain may be initialized before implementation begins. It must: interview the user to understand intent, create the initial Project Contract, define initial architecture and technology choices when known, define domain boundaries and responsibilities, record important decisions and invariants, create an implementation-ready project knowledge skeleton, make that knowledge available to coding agents before they write code.

The absence of source code is not an error and must not prevent onboarding.

### Brownfield Mode — an existing codebase

Kode Brain must also onboard existing projects, including large legacy projects. It must: discover existing project documents and prior KB content, determine how much project intent is already known, interview the user only for important missing or conflicting intent, build or repair the Project Contract, scan observed implementation evidence, build architecture and domain maps progressively, surface drift, uncertainty, legacy areas, and unmapped areas.

A large repository must not require a complete deep scan before the KB becomes useful.

## Unified Onboarding Command

The preferred user-facing operation is:

```bash
/kodebrain onboard [path]
```

`onboard` is **idempotent, resumable, and gap-driven**. The user should not need to know whether they need `init`, `scan`, `resume`, `migrate`, or `repair`.

Kode Brain determines the project state itself: fresh project / no code, new codebase / no KB, partial KB, existing KB with missing project-level knowledge, stale KB, older schema / older Kode Brain format, well-onboarded project.

## Onboarding Workflow

**Phase 0 — Detect Project and KB State:** Inspect repository and file topology, existing `docs/brain/`, README and project docs, manifests and build files, existing Kode Brain schema/version, current completeness of project-level knowledge. Produce an internal **Knowledge Gap Map**.

**Phase 1 — Discover Existing Intent:** Before inferring project purpose from code, search for intent in: Project Contract / existing Kode Brain pages, README, ADRs, product or design documentation, architecture documentation, explicit human notes.

**Phase 2 — Intent Alignment Interview:** If project-level intent is absent, materially incomplete, ambiguous, or contradictory, interview the user before deep mapping. Do not interview merely because a particular file is missing. Interview only for knowledge that materially improves project interpretation.

**Phase 3 — Create or Repair the Project Contract:** Create a project-level knowledge skeleton before deep mapping following the canonical structure.

**Phases 4–6 — Harvest, Domain Mapping, Progressive Deep Mapping:** Populate architecture evidence, map domains from both intent and observed evidence, progressively deep-map by priority.

## Greenfield Project Definition Workflow

When `/kodebrain onboard` runs on an empty or nearly empty new project:

```text
Detect Greenfield → Intent Interview → Project Contract Draft → Architecture Skeleton → Initial Domain Contracts → Initial Decisions / Invariants → Agent Instructions Installed → Implementation Begins
```

The resulting KB should tell an implementation agent: what is being built, who it is for, what is in and out of scope, core outcomes/workflows, current technology/architecture decisions or unresolved choices, initial domains and responsibilities, critical constraints and invariants, what remains undecided. Unknowns must remain explicit.

## Partial and Re-Onboarding Workflow

If Kode Brain already exists, onboarding should inspect completeness instead of starting over. Kode Brain should ask only for high-value missing human knowledge, then discover what it can from evidence. Existing human notes and verified content must be preserved. No page should be deleted merely because a new onboarding pass cannot confirm it.

---

## Change-First Workflow

Kode Brain should be updated **before implementation begins** when a task materially changes project behavior, architecture, domain responsibility, invariants, or public contracts.

Do not edit current-state architecture to pretend an unimplemented future already exists. Instead create an active change record in `changes/active/YYYY-MM-DD-<slug>.md`.

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

Required sections: Intent, Why, Affected Domains, Architecture Impact, Expected Behavior Changes, Invariants, Compatibility / Migration, Expected Source Areas, **Progress Log** (append-only dated entries), Implementation Evidence, **Outcome** (success / partial / abandoned / rolled_back), Deviations From Plan, Lessons Learned, Follow-ups, Regressions / Problems Introduced, Open Questions.

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

## Status vs Lifecycle State

Generic KB `status` describes knowledge quality (`active`, `stale`, `needs_review`). Lifecycle state is separate and type-specific.

The canonical record owner defines that record's lifecycle semantics:

| Record type | Lifecycle field | Canonical owner |
|---|---|---|
| Change | `change_state` | Workflow (this spec) — [Change Lifecycle](#change-lifecycle-states) |
| Incident | `incident_state` | [`history-model`](history-model.md) — Incident Lifecycle |
| Decision | `decision_state` | [`history-model`](history-model.md) — Decision Lifecycle |

Workflow owns Change lifecycle because Change is both an active development process and a historical record. History owns Decision and Incident lifecycle semantics.

This separation is enforced in `schema/node.schema.json` and all templates.

---

## Agent Reading Behavior

A Kode Brain-enabled coding agent should start at the highest useful level rather than blindly reading source.

Normal task startup: read project hub → identify relevant domain(s) → read active change if one exists → generate/read a focused reading pack → inspect detailed KB nodes → open targeted source files required for the actual edit or verification.

The rule is **KB first, source when needed**, not **KB instead of source**.

## Source of Truth Update Rule

For material changes, agents must keep Kode Brain aligned:

Before implementation: create/update the active change, update intended decisions/specification if the decision itself has changed.

After implementation: update observed knowledge from changed source, reconcile affected project/domain/architecture pages, surface drift or uncertainty, update indexes, complete the change only when documentation and implementation agree sufficiently.

Refactors that do not change behavior may use a lighter update path.
