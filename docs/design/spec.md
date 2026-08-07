---
spec_id: root
spec_role: canonical-root
owns:
  - kodebrain.product-definition
  - kodebrain.system-architecture
---

# Kode Brain — Canonical Specification Root

**Status:** Canonical
**Last aligned:** 2026-08-07 (spec tree decomposition)

> This document is the navigational root of the Kode Brain specification. Every concept has exactly one canonical owner. Follow the links to find the authoritative definition.

---

## Product Definition

Kode Brain is a **living project knowledge and coordination system for software projects**.

It is not only a codebase documentation generator. It must support a project from the moment the project is conceived, through implementation, maintenance, migration, and long-term evolution.

Kode Brain answers four questions:

1. **What SHOULD the system be?** — Project Contract, architecture direction, domain responsibilities, decisions, invariants. Intended reality.
2. **What IS the system?** — Source code, configuration, runtime behavior, tests, infrastructure. Observed reality.
3. **What are we CHANGING?** — Active changes, drift between intent and observation.
4. **HOW DID WE GET HERE?** — Completed changes, superseded decisions, incidents, milestones, lessons. Semantic project memory that accumulates value as the project ages.

The primary users are: human developers and project owners, coding agents, review and maintenance agents, future contributors who need to understand the project without rediscovering it from scratch.

---

## System Architecture

```text
                         KODE BRAIN
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
   KNOWLEDGE MODEL       WORKFLOW MODEL       MEMORY MODEL
         │                    │                    │
         ▼                    ▼                    ▼
  [knowledge-model]     [workflow-model]     [history-model]
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │    │    │          │    │    │          │    │    │
    ▼    ▼    ▼          ▼    ▼    ▼          ▼    ▼    ▼
  Layers Truth Graph  Onboard Change Agent  Decision Incident
  Harvest Drift       Lifecycle Behavior   Change Events
         │                                      Timeline
         ▼
   [project-model]
         │
    ┌────┴────┐
    │    │    │
    ▼    ▼    ▼
 Structure Arch Domains
   Naming IDs

                    [governance]
                         │
                    ┌────┴────┐
                    │    │    │
                    ▼    ▼    ▼
                Precedence Compat Non-Goals
```

Each `[bracket]` links to a canonical child specification below.

---

## Canonical Child Specifications

| Spec | File | Owns |
|---|---|---|
| **Knowledge Model** | [`spec/knowledge-model.md`](spec/knowledge-model.md) | Layers, truth model, provenance/confidence, harvest policy, drift, graph compilation |
| **Project Model** | [`spec/project-model.md`](spec/project-model.md) | Project structure, layout, hub, architecture, domains, naming, IDs |
| **Workflow Model** | [`spec/workflow-model.md`](spec/workflow-model.md) | Onboarding (greenfield/brownfield), change lifecycle, status/lifecycle, agent behavior |
| **History Model** | [`spec/history-model.md`](spec/history-model.md) | 4th question, record types, decision lineage, incidents, milestones, events, timeline, retrieval |
| **Governance** | [`spec/governance.md`](spec/governance.md) | Precedence, compatibility, non-goals, success criteria, spec authority |

### Other Design Documents

| Document | Role | References |
|---|---|---|
| `schema/node.schema.json` | Machine contract | Field definitions for all node types |
| `kodebrain/skill/SKILL.md` | Agent contract | Derived operational behavior |
| `docs/design/implementation-plan-vnext.md` | Implementation plan | References canonical specs |
| `docs/design/project-history.md` | Design rationale | Historical — superseded by spec/history-model.md |
| `docs/design/taxonomy.md` | Historical design | Superseded in part |
| `docs/design/open-decisions.md` | Decision records | Resolved architectural decisions |

---

## Specification Authority

One concept → one canonical owner → zero duplicated definitions.

- **Specification** defines what is true now
- **Decision** explains why that truth was chosen or changed
- **History** records what happened along the way
- **Implementation Plan** references the spec; never defines product truth independently
- **SKILL.md** derives operational behavior from spec

When adding a new concept: locate the canonical owner → modify that spec → record rationale in a Decision. Do not create a competing document.

Full governance rules: see [`spec/governance.md`](spec/governance.md).
