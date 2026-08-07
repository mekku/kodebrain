---
id: kb-core-knowledge-edge-model
type: model
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-core
source_files:
  - schema/edge.schema.json
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/model
  - domain/kb-core
  - status/active
---

# Knowledge Edge

Part of [[kb-core|Core domain]].

## Schema

Defined in `schema/edge.schema.json`. Edges represent relationships between knowledge nodes. They are compiled from `[[wiki-links]]` in Markdown page bodies — edges are derived, not manually authored.

### Edge Fields

| Field | Type | Description |
|---|---|---|
| `source` | string | Source node ID |
| `target` | string | Target node ID |
| `type` | enum | Relationship type |
| `provenance` | enum | Origin of the edge |

### Edge Types

| Type | Meaning | Inferred From |
|---|---|---|
| `contains` | Source contains target (domain → child node) | Domain hub lists child under Capabilities/Flows/Concepts |
| `depends_on` | Source depends on target | Listed under "Depends On" heading |
| `used_by` | Source is used by target | Listed under "Used By" heading |
| `references` | Source references target | Listed under "Core Concepts", "Related Concepts", or fallback |
| `implements` | Source implements target (flow → capability) | Listed under "Core Flows" with "Implements" context |
| `part_of_flow` | Node is part of a flow | Listed in flow step table or flow page references |
| `supersedes` | Source supersedes target (decision lineage) | `supersedes` frontmatter field |
| `has_caveat` | Source has a risk/caveat | Listed under "Known Risks" or "Risks" heading |

## Inference Rules

The compiler (`compile_graph.py`) infers edge types from section context:

1. Wiki-link under "Depends On" → `depends_on`
2. Wiki-link under "Used By" → `used_by`
3. Wiki-link under "Core Concepts" / "Related Concepts" → `references`
4. Wiki-link under "Core Flows" with "Implements" → `implements`
5. Wiki-link under "Known Risks" / "Risks" → `has_caveat`
6. Domain hub listing child under typed section → `contains`
7. Fallback → `references`

## Compilation

Edges are compiled by `compile_graph.py` from Markdown wiki-links. The same relationship expressed as `[[target|label]]` in the body becomes an edge `{source: <page-id>, target: <target>, type: <inferred>}` in `edges.json`.

## Source Evidence

- `schema/edge.schema.json` — full JSON Schema definition
- `kodebrain/skill/scripts/compile_graph.py` — `_infer_edge_type_from_section()`, `_infer_edge_type_fallback()`
- `docs/design/spec/knowledge-model.md` — "Markdown-First Graph Compilation"

## Status Notes

vNext schema current. Edge types aligned with flat node IDs.
