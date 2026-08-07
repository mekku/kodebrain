---
id: kb-project
type: domain
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-project
source_files:
  - docs/design/spec/project-model.md
  - templates/
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/domain
  - domain/kb-project
  - status/active
---

# Project Domain

## Responsibility

Define the *shape* of project knowledge — structure, layout, hub contract, architecture contract, domain contract, naming conventions, node ID format.

## Owns

- Project hub contract (`<project>.md`): required sections, orientation-first design
- KB directory layout: `docs/brain/projects/<project>/`
- Architecture page contracts: overview, technology, runtime, data, deployment, integrations
- Domain hub contract: Responsibility, Owns, Does Not Own, Depends On, Used By, Core Concepts, Capabilities, Core Flows, Data Ownership, Entry Points, Invariants, Legacy/Migration, Risks, Source Areas, Open Questions
- Node ID format: flat, hyphen-separated `<domain-slug>-<type-slug>`
- File naming: domain hub is `<domain>.md` (not overview.md)
- Tag taxonomy: `type/<type>`, `domain/<slug>`, `status/<status>`
- Template files for all page types

## Does Not Own

- What knowledge means — see [[kb-core|Core domain]]
- What processes mutate knowledge — see [[kb-workflow|Workflow domain]]
- Record lifecycle semantics — see [[kb-history|History domain]]
- Spec authority and governance — see [[kb-governance|Governance domain]]

## Depends On

- [[kb-core|Core domain]] — node types drive page templates
- [[kb-governance|Governance domain]] — spec authority for canonical naming

## Used By

- All domains — every domain follows this domain's layout and naming rules
- [[kb-substrate|Substrate domain]] — compile_graph expects flat IDs and standard paths

## Core Concepts

- [[kb-project-node-id-format|Node ID Format]] — flat, hyphen-separated
- [[kb-project-hub-contract|Project Hub Contract]] — required sections
- [[kb-project-domain-contract|Domain Contract]] — domain hub structure
- [[kb-project-architecture-contract|Architecture Contract]] — architecture page structure
- [[kb-project-page-layout|Page Layout]] — directory structure

## Capabilities

This domain is structural — it defines contracts, not executable capabilities.

## Core Flows

None — structural domain.

## Data Ownership

| Model | Ownership | Shared With |
|---|---|---|
| Project layout spec | owned | all domains (follow it) |

## Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `templates/` | Files | Page templates for all node types |
| `docs/brain/projects/<project>/<project>.md` | File | Project hub |

## Invariants

- Node IDs are flat: `<domain-slug>-<type-slug>` — no nested slashes
- Domain hub filename is `<domain>.md` — not `overview.md`
- Every relationship between nodes appears as a `[[wiki-link]]` in the body
- Tags on every page: `type/<type>`, `domain/<domain>`, `status/<status>`
- Project hub favors orientation over exhaustive detail

## Legacy / Migration

- Hierarchical node IDs (`auth/login-flow`) → flat (`auth-login-flow`) handled by migrate_kb.py
- Older design docs (taxonomy.md, skills.md, agents.md, workflows.md) are historical

## Risks

None currently flagged.

## Source Areas

| Path | Purpose |
|---|---|
| `docs/design/spec/project-model.md` | Canonical project model spec |
| `templates/` | Page templates (project, domain, capability, flow, concept, model, decision, risk, change, architecture-*) |
| `schema/node.schema.json` | Node field contract (derived from all specs) |

## Open Questions

None at this time.
