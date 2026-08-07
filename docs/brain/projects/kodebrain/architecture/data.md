---
type: architecture_data
project: kodebrain
confidence: supported
provenance: project_document
knowledge_role: mixed
last_updated: "2026-08-07"
---

# Data Architecture — Kode Brain

## Storage Model

Kode Brain uses a file-based storage model. No database. No cache service.

```text
docs/brain/projects/<project>/
  ├── Markdown pages (canonical)     ← human-authored + agent-authored knowledge
  ├── graph/*.json (derived)         ← compiled from Markdown wiki-links
  ├── history/* (generated)          ← timeline + events from record pages
  ├── reports/*.md                  ← gap/drift/stale tracking
  └── changes/                       ← active + completed change records
```

## Data Ownership

| Data | Canonical Format | Owned By | Derived Formats |
|---|---|---|---|
| Knowledge pages | Markdown + YAML frontmatter | Each domain | — |
| Graph nodes | `graph/nodes.json` | Compiler (compile_graph.py) | — |
| Graph edges | `graph/edges.json` | Compiler (compile_graph.py) | — |
| File index | `graph/file-index.json` | Compiler (compile_graph.py) | — |
| File hashes | `graph/file-hashes.json` | Harvest (harvest.py) | — |
| Timeline | `history/timeline.md` | Timeline (timeline.py) | — |
| Events | `history/events.json` | Timeline (timeline.py) | — |

## Canonical vs Derived Rule

**Markdown knowledge pages are canonical.** Graph JSON files are derived and must be rebuildable from Markdown alone. If they disagree, Markdown wins. No agent should manually maintain the same relationship in both Markdown and JSON.

## Node Identity

Node IDs are flat, hyphen-separated: `<domain-slug>-<type-slug>`. Example: `kb-core-provenance`.

A node with ID `kb-core-provenance` lives at `domains/kb-core/concepts/kb-core-provenance.md`.

## Frontmatter Fields

Every KB page carries YAML frontmatter. Required fields vary by node type. Common fields: `id`, `type`, `status`, `confidence`, `provenance`, `knowledge_role`, `project`, `domain`, `source_files`, `last_updated`, `tags`.

Full field definitions: `schema/node.schema.json`.

## Wiki-Link Rule

Every relationship between nodes must appear as a `[[node-id|Display Name]]` wiki-link in the page body. The compiler extracts these to build `edges.json`. A relationship not expressed as a wiki-link is invisible to the graph.

## History Data

History records (decisions, incidents, milestones, completed changes) are append-oriented. Once recorded, they are not rewritten. Superseded decisions are preserved with derived `superseded_by` — the old record remains.

## Source Evidence

- `schema/node.schema.json` — node field contract
- `schema/edge.schema.json` — edge field contract
- `kodebrain/skill/scripts/compile_graph.py` — wiki-link extraction, graph compilation
- `docs/design/spec/project-model.md` — project layout spec
