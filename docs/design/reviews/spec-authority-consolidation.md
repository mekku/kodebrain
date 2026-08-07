# Design Review — Spec Authority Consolidation

**Review target:** Kode Brain vNext at `f5a170cd90b38403efcfd6ccfc88ce307fdd4d8b`
**Status:** Feedback for next design/correctness pass
**Date:** 2026-08-07

## Summary

Kode Brain now has a strong Project Memory model, but its own design repository is demonstrating a failure mode that Kode Brain should explicitly prevent: new design truth is being added in child documents and implementation without being propagated back into the canonical specification.

`docs/design/spec.md` declares itself canonical and says it wins when older design documents conflict. However, several concepts implemented after that spec were introduced or redefined in separate documents such as `project-history.md`, `SKILL.md`, templates, and schemas without updating the canonical root. This means the repository can contain multiple partially-correct definitions of the same concept.

The next pass should focus on **specification authority**, not new features.

## Core Rule

> One concept may have exactly one canonical owner.
>
> Other documents may reference, justify, plan, or record the history of that concept, but they must not independently redefine its current truth.

This should become a first-class Kode Brain invariant.

## Current Failure Mode

The repository currently has multiple design documents that overlap in authority:

- `docs/design/spec.md`
- `docs/design/project-history.md`
- `docs/design/implementation-plan-vnext.md`
- `docs/design/taxonomy.md`
- `docs/design/workflows.md`
- `docs/design/skills.md`
- `docs/design/agents.md`
- `kodebrain/skill/SKILL.md`
- templates and JSON schemas

The problem is not that multiple documents exist. The problem is that several of them answer the same question.

Examples at the reviewed commit:

1. `spec.md` still presents Kode Brain using the older three-job model, while `project-history.md` introduces the fourth temporal question: **HOW DID WE GET HERE?**
2. `spec.md` project layout does not include `incidents/`, `milestones/`, or `history/`, although these are now implemented.
3. `spec.md` still describes the older Change lifecycle shape, while templates and schema now separate generic KB `status` from `change_state`, `incident_state`, and `decision_state`.
4. `spec.md` says a single ID convention still needs to be selected, while the implementation and skill have already standardized on flat IDs.
5. `project-history.md` itself is already partially stale relative to the latest implementation: it describes stored `superseded_by` and older incident lifecycle fields, while lineage is now derived and lifecycle state is separated.

This creates the exact behavior that large language models are prone to: when extending a design, they create a new specification fragment rather than editing the existing owner of the concept.

## Specification Should Be a Tree, Not a Pile of Documents

Do not solve this by making `spec.md` one enormous file.

Instead, define a **Canonical Spec Root** that owns the top-level model and delegates each concern to exactly one child specification.

Suggested shape:

```text
SPECIFICATION ROOT
        |
        +-- Product Model
        |
        +-- Knowledge Model
        |     +-- Project Contract
        |     +-- Architecture
        |     +-- Domains
        |     +-- Evidence / Drift
        |
        +-- Workflow Model
        |     +-- Onboarding
        |     +-- Reading Pack
        |     +-- Change / Reconcile
        |
        +-- Project Memory
        |     +-- Decision
        |     +-- Change History
        |     +-- Incident
        |     +-- Milestone
        |     +-- Event Timeline / Retrieval
        |
        +-- Schema / Identifier Contracts
```

Each node in this tree should have one canonical owner.

For example:

| Concern | Canonical owner |
|---|---|
| Product definition | `spec.md#product-definition` |
| Knowledge layers | `spec/knowledge-model.md` |
| Project structure | `spec/project-structure.md` |
| Onboarding | `spec/onboarding.md` |
| Change lifecycle | `spec/change-workflow.md` |
| Project History | `spec/history.md` |
| Agent reading behavior | `spec/agent-workflow.md` |
| Node field contract | `schema/node.schema.json` |

The exact filenames are less important than the ownership rule.

## Main Diagram Is Part of the Contract

The root specification should contain the primary system diagram showing how the major concepts relate and where each concept decomposes.

A contributor or agent should be able to read that diagram first and answer:

- What are the major subsystems of Kode Brain?
- Which specification owns each subsystem?
- How does Project Contract relate to Current Knowledge, Evidence, Active Change, and Project Memory?
- Where should a new requirement be incorporated?

A possible high-level model is:

```text
                 SPECIFICATION ROOT
              "What defines Kode Brain?"
                       |
          +------------+-------------+
          |            |             |
          v            v             v
     KNOWLEDGE      WORKFLOW       MEMORY
       MODEL          MODEL         MODEL
          |            |             |
          v            v             v
   Project Contract  Active       Decisions
   Architecture      Change       Completed Changes
   Domains           Reconcile    Incidents
   Invariants                    Milestones
          |                          |
          v                          v
   Current Knowledge          Temporal Events
          |
          v
       Evidence
```

The diagram should be navigational, not decorative. Each major box should link to its canonical child specification.

## Separate Current Truth From Why and How

Different artifact classes must have different authority roles.

```text
SPECIFICATION
What is true now.

DECISION
Why that truth was chosen or changed.

HISTORY
What happened along the way.

IMPLEMENTATION PLAN
How the current specification will be implemented or migrated.

CODE / RUNTIME
What currently exists in implementation.
```

A Decision must not become a second copy of the spec.
An implementation plan must not become a future canonical spec by accident.
A historical design document must not remain equally authoritative after the canonical model has changed.

## Required Change Workflow for Specifications

When a new product/design idea appears, the default workflow should be:

```text
New requirement / idea
        |
        v
Locate canonical owner
        |
        +-- owner exists --> MODIFY that canonical spec
        |
        +-- no owner ------> ADD one canonical child
                              and link it from the root
        |
        v
Record Decision / rationale if material
        |
        v
Create implementation Change
        |
        v
Implement + validate
```

The anti-pattern is:

```text
New idea
  -> create another design document
  -> implement from that document
  -> leave the original canonical spec unchanged
```

This should be considered specification drift.

## Canonical Ownership Metadata

Consider explicit metadata for canonical spec pages, for example:

```yaml
spec_id: history
spec_role: canonical
parent: project-memory
owns:
  - history.record-types
  - history.decision-lineage
  - history.event-model
  - history.retrieval
```

Root example:

```yaml
spec_id: root
spec_role: canonical-root
```

Historical or rationale documents should use a different role, e.g.:

```yaml
spec_role: historical
superseded_by: history
```

or simply be moved under a clearly non-canonical design-history area.

## Deterministic Structural Validation

Kode Brain should not rely only on an LLM to remember these rules.

A deterministic spec validator should be able to check at least:

- every canonical spec is reachable from the root,
- no canonical spec is orphaned,
- every owned concern has one canonical owner,
- no concern has multiple canonical owners,
- canonical child pages declare a parent,
- deprecated/superseded spec pages identify their replacement,
- implementation plans reference the canonical specs they implement,
- material Decisions reference the canonical area they changed,
- canonical docs do not depend on historical design notes for current truth.

Semantic contradiction detection may still require an LLM, but structural authority should not.

## Agent Reading Rule

Agents should not discover authority by broad text search alone.

Avoid:

```text
search "history"
  -> find project-history.md
  -> assume it is authoritative
```

Prefer:

```text
Read Canonical Spec Root
        |
        v
Resolve canonical owner for "Project History"
        |
        v
Read canonical History spec
        |
        +-- read Decisions / historical records only when rationale is needed
```

The structure should choose the document before the model reasons about its content.

## Recommended Consolidation Pass for This Repository

Before adding more vNext features:

1. Define the canonical spec decomposition and main diagram.
2. Merge the current implemented Project History model back into the canonical specification tree.
3. Update the root model from the old three-part view to include Project Memory / temporal history explicitly.
4. Normalize current project layout, lifecycle fields, ID convention, and agent reading behavior in their canonical owners.
5. Reclassify `project-history.md`, the vNext implementation plan, and older design docs as either:
   - rationale/history,
   - implementation plan,
   - superseded design input,
   rather than alternate current specifications.
6. Add structural spec-authority validation and regression tests.
7. Update agent workflow so a material spec change must locate and edit the canonical owner before implementation begins.

## Acceptance Criteria

This pass is successful when:

- asking "What is the current Project History model?" has one authoritative answer path,
- asking "What is the Change lifecycle?" has one authoritative definition,
- no child design document silently overrides a canonical parent,
- an agent can navigate from the root diagram to the correct spec owner without global search,
- adding a future feature causes modification of the existing canonical owner rather than creation of a competing spec fragment,
- a deterministic validator can report duplicate or orphaned specification authority.

## Principle

> A specification system becomes trustworthy not when it contains all design information, but when every piece of current truth has exactly one known home.
