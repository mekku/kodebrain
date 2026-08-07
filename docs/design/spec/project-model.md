---
spec_id: project-model
spec_role: canonical
parent: root
owns:
  - project.structure
  - project.layout
  - project.hub
  - project.architecture
  - project.domains
  - project.naming
  - project.ids
---

# Project Model

Canonical owner for: project structure, layout, hub contract, architecture contract, domain contract, naming conventions, ID format.

## Project Hub Contract

`<project>.md` is the required **START HERE** page for both humans and agents. It should allow a contributor to form a useful mental model of the system within roughly one or two minutes.

Required sections: Purpose, Primary Users / Actors, Core Outcomes, Scope, Technology Summary, System Architecture, Domains, Runtime Entry Points, External Systems, System-wide Invariants, Current Risks / Legacy / Migration, Active Changes, Where To Start.

The page should favor orientation over exhaustive detail. Detailed knowledge belongs in linked architecture/domain/node pages.

## Project Layout

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

  domains/<domain>/
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
    timeline.md       ← generated
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

## Architecture Contract

Architecture documentation explains how the system fits together at a level above individual capabilities and source files.

### `architecture/overview.md`

Must describe: major applications/services/processes, major system boundaries, major communication paths, high-level domain placement, system-context or container-style diagram where useful, links to deeper architecture pages.

### `architecture/technology.md`

Describe important technologies by role rather than as an unstructured dependency list: frontend/client, backend/runtime, persistence, cache, queue/event system, testing, build/tooling, infrastructure.

### `architecture/runtime.md`

Describe processes and runtime topology: servers, workers, schedulers, CLI processes, event consumers, runtime boundaries.

### `architecture/data.md`

Describe: primary databases, major data stores, ownership boundaries, caches, derived data, critical data movement rules.

### `architecture/deployment.md`

Describe environments, deployment topology, and operational boundaries when known.

### `architecture/integrations.md`

Describe external systems and why they exist, not merely SDK imports.

Architecture pages should be narrative maps, not a collection of tiny technology nodes.

## Domain Contract

A domain represents a major area of business or system responsibility. A domain page should prioritize responsibility boundaries before implementation detail.

Recommended order: Responsibility, Owns, Does Not Own, Depends On, Used By, Core Concepts, Capabilities, Core Flows, Data Ownership, Entry Points, Invariants, Legacy / Migration, Risks, Source Areas, Open Questions.

`Owns`, `Does Not Own`, and `Depends On` are especially important because folder boundaries do not reliably represent responsibility boundaries. Domain boundaries may initially be human-defined, source-derived, inferred, or mixed. Provenance must be preserved.

## Canonical Naming Direction

- Product name: `Kode Brain`
- Package / CLI: `kodebrain`
- Primary command surface: `/kodebrain ...`
- Primary onboarding command: `/kodebrain onboard`
- KB location: `docs/brain/projects/<project>/`
- Domain hub filename: `<domain>.md`

Node ID format is flat, hyphen-separated: `<domain-slug>-<type-slug>` (e.g. `auth-login-flow`). Enforced in all schemas, templates, and compilers. The hierarchical format (`auth/login-flow`) is legacy — migrated by `migrate_kb.py` to flat format.
