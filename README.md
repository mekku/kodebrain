# Kode Brain

**Kode Brain** — a living knowledge system for evolving software projects.

Converts an imperfect, growing codebase into a structured, searchable knowledge map of domains, capabilities, concepts, flows, runtime behavior, dependencies, legacy areas, migration states, and source evidence — so humans and AI agents can understand and modify the system without rediscovering everything from scratch.

## Design Documents

| Document | Purpose |
|---|---|
| [Spec](docs/design/spec.md) | Canonical product & knowledge spec (vNext) |
| [Implementation Plan](docs/design/implementation-plan-vnext.md) | vNext migration execution plan |
| [Taxonomy](docs/design/taxonomy.md) | Node types, edge types, status labels, confidence labels |
| [Skills](docs/design/skills.md) | Skill API contracts — inputs, outputs, guarantees |
| [Agents](docs/design/agents.md) | Agent role boundaries — responsibilities, allowed skills, forbidden actions |
| [Workflows](docs/design/workflows.md) | Core workflow sequence diagrams |
| [Open Decisions](docs/design/open-decisions.md) | Unresolved architectural decisions |

## Schemas

| File | Purpose |
|---|---|
| [schema/node.schema.json](schema/node.schema.json) | JSON Schema for KnowledgeNode |
| [schema/edge.schema.json](schema/edge.schema.json) | JSON Schema for KnowledgeEdge |
| [schema/knowledge-base.schema.json](schema/knowledge-base.schema.json) | Top-level graph container schema |

## Templates

| File | Purpose |
|---|---|
| [templates/project.md](templates/project.md) | Project hub page |
| [templates/domain.md](templates/domain.md) | Domain hub page |
| [templates/capability.md](templates/capability.md) | Capability page |
| [templates/flow.md](templates/flow.md) | Flow page |
| [templates/concept.md](templates/concept.md) | Concept page |
| [templates/model.md](templates/model.md) | Data model page |
| [templates/decision.md](templates/decision.md) | Decision record |
| [templates/risk.md](templates/risk.md) | Risk/caveat page |
| [templates/change.md](templates/change.md) | Active change record |
| [templates/architecture-overview.md](templates/architecture-overview.md) | Architecture overview |
| [templates/architecture-technology.md](templates/architecture-technology.md) | Technology stack |
| [templates/architecture-runtime.md](templates/architecture-runtime.md) | Runtime topology |
| [templates/architecture-data.md](templates/architecture-data.md) | Data architecture |
| [templates/architecture-deployment.md](templates/architecture-deployment.md) | Deployment |
| [templates/architecture-integrations.md](templates/architecture-integrations.md) | External integrations |
| [templates/drift-report.md](templates/drift-report.md) | Intent vs observed drift |
| [templates/knowledge-gaps.md](templates/knowledge-gaps.md) | Knowledge gap tracking |

## Commands

```
/kodebrain onboard [path]                    Unified onboarding — works on empty, existing, and legacy projects
/kodebrain init [path]                       Scan project, scaffold docs/brain/
/kodebrain scan [path]                       Re-scan and update knowledge graph
/kodebrain query "<task or symptom>"         Query the KB by task description
/kodebrain reading-pack "<task>"             Generate + save a context pack
/kodebrain detect-legacy [--domain slug]     Flag suspected dead code
/kodebrain review [--page path]              Review KB pages for stale claims
/kodebrain update [--diff] [--files ...]     Update KB from changed files
```

## Installation

```bash
pip install kodebrain
kodebrain install        # installs skill + platform configs globally
```

`/kodebrain` is then available in every Claude Code session.

### Developing the skill

The skill definition lives in `kodebrain/skill/` — `SKILL.md` and `scripts/harvest.py`. To have changes take effect immediately without reinstalling:

```bash
# Symlink the skill dir directly (dev mode)
ln -s "$(pwd)/kodebrain/skill" ~/.claude/skills/kodebrain
```

Or install the package in editable mode so `kodebrain install` always picks up local changes:

```bash
pip install -e .
kodebrain install
```
