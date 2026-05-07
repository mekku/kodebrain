# kb-builder

**Kode Brain** — a living knowledge system for evolving software projects.

Converts an imperfect, growing codebase into a structured, searchable knowledge map of domains, capabilities, concepts, flows, runtime behavior, dependencies, legacy areas, migration states, and source evidence — so humans and AI agents can understand and modify the system without rediscovering everything from scratch.

## Design Documents

| Document | Purpose |
|---|---|
| [Taxonomy](docs/design/taxonomy.md) | Finalized node types, edge types, status labels, confidence labels |
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

## Design Order

Per the Kode Brain spec (§20.7):

```
Taxonomy → Workflow → Skills → Agents → Plugin/CLI
```

This repository is currently at the **design phase**. Implementation comes after the design is validated.

## Commands

```
/kodebrain init [path]                     Scan project, scaffold docs/kodebrain/
/kodebrain scan [path]                     Re-scan and update knowledge graph
/kodebrain query "<task or symptom>"       Query the KB by task description
/kodebrain reading-pack "<task>"           Generate + save a context pack
/kodebrain detect-legacy [--domain slug]   Flag suspected dead code
/kodebrain review [--page path]            Review KB pages for stale claims
/kodebrain update [--diff] [--files ...]   Update KB from changed files
```

## Installation

The skill must be installed into Claude Code's skills directory:

```bash
# From the repo root
ln -s "$(pwd)" ~/.claude/skills/kodebrain
```

After symlinking, `SKILL.md` is discoverable by Claude Code and `/kodebrain` becomes available in any Claude Code session.
