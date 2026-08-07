---
spec_id: history-model
spec_role: canonical
parent: root
owns:
  - decision.record
  - decision.lineage
  - incident.record
  - incident.lifecycle
  - milestone.record
  - change.record
  - temporal.events
  - temporal.timeline
  - temporal.retrieval
exports:
  decision.record: Decision Lifecycle
  incident.lifecycle: Incident Lifecycle
---

# Project History Model

Canonical owner for: the 4th Kode Brain question (HOW DID WE GET HERE?), semantic record types, decision lineage, incident records, milestone records, change history, timeline/events generation, history retrieval in agent workflow.

## The Fourth Question

Project History is the semantic time axis — it answers **HOW DID WE GET HERE?**

> **Boundary:** History owns the record schemas AND lifecycle semantics of decisions, incidents, milestones, and completed changes. The active Change process lifecycle (planned → in_progress → implemented → reconciled) is owned by [`workflow-model`](workflow-model.md) because Change is both a development process and a historical record. History owns the completed Change record. For project structure conventions, see [`project-model`](project-model.md).

History records are **append-oriented**. Once recorded, they are not rewritten. If understanding changes, a new record supersedes the old one — the old record remains as evidence of the path taken.

History is **not current truth**. If a lesson must constrain future behavior, it must be promoted:

```
Incident → lesson extracted → Decision → codified as → Invariant
```

## Four Semantic Record Types

**Change (completed):** Records of what was intentionally changed. After reconciliation, captures outcome, deviations from plan, lessons learned, follow-ups, and regressions introduced. Progress log entries within active changes become temporal events.

**Decision:** Why a direction was chosen or changed. Decisions have lineage: a new decision may `supersede` an older one. `superseded_by` is derived by the compiler — only `supersedes` is stored on the new decision. The old decision is not rewritten.

**Incident:** Something that went wrong and was learned from. Includes architectural mistakes, data corruption, migration problems, performance disasters, security near misses, dependency problems, and failed implementation approaches. Records: what happened, root cause, why existing design allowed it, lesson, guardrail introduced, and affected knowledge nodes (enabling task → node → incident traversal).

**Milestone:** A significant project inflection point that changed the mental model — MVP launch, monolith split, provider migration, legacy removal, multi-tenant architecture. Not every release; only events that changed how contributors think about the system.

## Decision Lineage

Decisions support lineage through `supersedes`:

```yaml
# New decision (active)
decision_state: active
supersedes:
  - old-decision-id
```

The compiler derives `superseded_by` on the old decision and sets its effective state to `superseded`. The old decision is never rewritten.

### Decision Lifecycle

| decision_state | Meaning |
|---|---|
| `active` | Current governing decision for this concern |
| `superseded` | Replaced by a newer decision via lineage; preserved for historical trace |
| `deprecated` | Intentionally retired without a direct replacement; the concern itself may no longer apply |

### Incident Lifecycle

| incident_state | Meaning |
|---|---|
| `ongoing` | Problem still active or unresolved |
| `mitigated` | Immediate impact contained; root cause or permanent fix incomplete |
| `resolved` | Incident concluded; resolution implemented and lesson captured |

## Generated Artifacts

History records are the source of truth. Two artifacts are generated:

| Artifact | Generator | Purpose |
|---|---|---|
| `history/timeline.md` | `timeline.py` | Human-readable chronological timeline |
| `history/events.json` | `timeline.py` | Temporal index for agent retrieval |

Both are compiled from the same enriched records (with derived lineage).

## Agent Workflow Integration

Before a material change, agents must:

1. Identify affected nodes (domains, capabilities, flows)
2. Load `history/events.json`
3. Find relevant history: past decisions affecting same nodes, similar completed changes, incidents touching affected nodes, previous rollbacks
4. Surface historical warnings in the active change
5. Reading packs include a **Relevant History** section

This makes Kode Brain more valuable as the project ages — accumulated history prevents repeated mistakes.

## Record Count Over Time

Unlike current-state docs (which should stay concise), history records grow linearly with project age. This is intentional: a 5-year project has more history than a 6-month project. More history = more accumulated lessons = agents make fewer repeated mistakes.
