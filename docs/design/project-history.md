# Project History — Semantic Time Axis

**Status:** Design rationale (historical)
**Canonical owner:** `docs/design/spec.md` §15 (Project History)
**Depends on:** `docs/design/spec.md`
**Date:** 2026-08-07

> **This document is design rationale, not current specification.**
> The canonical definition of Project History lives in `docs/design/spec.md` §15.
> This document preserves the original design thinking and motivation. When it
> conflicts with `spec.md`, the spec wins.

---

Kode Brain must accumulate value as a project ages. Git tells *what code changed*. Project History tells *why the world of the project changed*.

---

## 1. The Fourth Question

Kode Brain currently answers three questions:

1. What SHOULD the system be? — Project Contract / Decisions / Invariants
2. What IS the system? — Architecture / Domains / Source / Runtime
3. What are we CHANGING? — Active Changes / Drift

The fourth question:

4. HOW DID WE GET HERE? — Completed Changes / Superseded Decisions / Incidents / Milestones / Lessons

This is the **semantic time axis** — a dimension that cuts through all knowledge layers.

```
              TIME →
          ─────────────────────

Architecture   V1 ───── V2 ───── V3
                   ↑        ↑
Decision           D1       D2 supersedes D1
                   │
Change             C1 ───── C2
                   │
Incident           I1
                   │
Lesson             "don't do X because..."
```

---

## 2. Four Semantic Record Types

### 2.1 Change (enhanced)

We already have change records. Completed changes must additionally capture:

- **Outcome** — success, partial, abandoned, rolled_back
- **Deviations From Plan** — what changed from original intent
- **Lessons Learned** — what this taught us
- **Follow-ups** — what remains
- **Regressions / Problems Introduced** — did this cause anything later

Frontmatter additions:

```yaml
started_at: "2026-08-01"
completed_at: "2026-08-07"
outcome: success | partial | abandoned | rolled_back
```

### 2.2 Decision (enhanced)

Decisions already exist. They need **lineage**:

- `supersedes` — this decision replaces an older one
- `superseded_by` — this decision was replaced by a newer one
- `decision_state: active | superseded | deprecated`

Rule: never edit an old decision to make it look correct. Keep both.

```
2026-01 — Decision D1 (superseded)
  Use MongoDB transactions

       ↓ supersedes

2026-08 — Decision D2 (active)
  Use event-driven reconciliation instead
  supersedes: D1
  reason: assumption X proved false
```

### 2.3 Incident (new)

A record of something that went wrong. Not only production outages — includes architectural mistakes, data corruption, migration problems, performance disasters, security near misses, dependency problems, failed implementation approaches, and hard-to-reproduce high-impact bugs.

```yaml
---
id: <domain>-<YYYY-MM-DD>-<incident-slug>
type: incident
severity: critical | high | medium | low
status: resolved | mitigated | ongoing
started_at: "2026-07-18"
resolved_at: "2026-07-19"
domain: <domain-slug>
tags:
  - type/incident
  - domain/<domain-slug>
---
```

Sections: What Happened, Impact, Root Cause, Why Existing Design Allowed It, Resolution, Lesson, Guardrail Introduced, Related Changes, Related Decisions.

### 2.4 Milestone (new)

Major events that changed the project's mental model — not every release, only inflection points:

- MVP launched
- Monolith split into worker + API
- Migrated Stripe → Adyen
- Removed legacy v1
- Reached multi-tenant architecture
- Mobile client introduced

```yaml
---
id: <YYYY-MM-DD>-<milestone-slug>
type: milestone
date: "2026-06-15"
significance: architectural | product | operational | organizational
tags:
  - type/milestone
---
```

---

## 3. Immutability Rule

History records are **append-oriented**. Once a change is completed, a decision is made, an incident is resolved, or a milestone is recorded — it should not be rewritten.

If understanding changes:

- **Don't**: edit Decision A to make it correct
- **Do**: create Decision B that supersedes A, with reason

A wrong past decision contains more information than a correct present one — it marks the boundary of the solution space.

---

## 4. Timeline — Generated, Not Maintained

```
docs/brain/projects/<project>/
  decisions/         ← source of truth (individual records)
  changes/
    active/
    completed/       ← source of truth
  incidents/         ← source of truth
  milestones/        ← source of truth
  history/
    timeline.md      ← generated view (compile_graph or timeline compiler)
```

The compiler reads all history records and produces:

```markdown
# Project Timeline — <Project>

## 2026

### August

2026-08-07 — Decision
Switched graph authority to Markdown-first.
[[decision-markdown-authority]]

2026-08-05 — Change
Completed deterministic graph compiler.
[[change-graph-compiler]]

### July

2026-07-18 — Incident
Legacy migration overwrote human intent.
[[incident-legacy-migration-intent-loss]]
```

Records are source of truth. Timeline is a view — like graph JSON.

---

## 5. History Is Not Current Truth

An incident that says "Redis caused consistency problems" does NOT mean "never use Redis."

If a lesson must constrain future behavior, promote it:

```
Incident
   ↓ lesson extracted
Decision
   ↓ codified as
Invariant

Example:

Historical lesson:
  "Cache invalidation caused stale permissions."

Current invariant:
  "Authorization decisions must not depend solely
   on eventually-consistent cache."
```

This prevents agents from being haunted by ghosts of old architecture.

---

## 6. Agent Workflow Integration

Before a material change, the agent follows:

```
Read Current Truth
      ↓
Identify affected nodes
      ↓
Find Related History
      ↓
  - Decisions (active + superseded)
  - Past Changes (similar scope)
  - Incidents (same domain/pattern)
  - Previous Rollbacks
      ↓
Create Active Change
      ↓
Implement
```

Reading packs gain a new section:

```markdown
## Relevant History

### Previous Decisions
- ...

### Similar Past Changes
- ...

### Incidents / Lessons
- ...

### Superseded Approaches
- ...

### Historical Warnings
⚠ This change touches payment retry behavior.
A previous retry redesign caused duplicate captures.
Read [[incident-payment-duplicate-capture]] before editing.
```

---

## 7. Record Count Over Time

Unlike current-state docs (which should stay concise), history records grow linearly with project age. This is intentional:

- A 5-year project has more history than a 6-month project
- More history = more accumulated lessons = agents make fewer repeated mistakes
- The reading-pack history section acts as a relevance filter

---

## 8. Schema Extensions

### New node types

- `incident` — something that went wrong and was learned from
- `milestone` — a significant project inflection point

### New frontmatter fields on existing types

**Change:**
- `started_at`, `completed_at` (dates)
- `outcome` (success | partial | abandoned | rolled_back)

**Decision:**
- `decision_state` (active | superseded | deprecated)
- `supersedes` (list of decision IDs)
- `superseded_by` (list of decision IDs)

### Template additions

- `templates/incident.md`
- `templates/milestone.md`
- Update `templates/change.md` with outcome/lessons sections
- Update `templates/decision.md` with lineage fields

---

## 9. Compiler Support

`compile_graph` must:

- Read incident and milestone pages as graph nodes
- Build edges from wiki-links (same as other node types)
- Generate `history/timeline.md` from all history records, sorted by date

---

## 10. Success Criteria

- A 3-year-old project's KB can warn an agent about a pattern that caused an incident 2 years ago
- Superseded decisions are preserved and explainable — not erased
- Timeline is rebuildable from records
- History records are append-only in practice
- Reading packs surface relevant history without overwhelming
