---
id: kb-core-graph-compilation
type: capability
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: kodebrain
domain: kb-core
source_files:
  - kodebrain/skill/scripts/compile_graph.py
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/capability
  - domain/kb-core
  - status/active
---

# Graph Compilation

Part of [[kb-core|Core domain]].

## Short Summary

Compile Markdown knowledge pages into machine-readable graph indexes: `nodes.json`, `edges.json`, and `file-index.json`. Wiki-links (`[[node-id]]`) in page bodies become graph edges. Markdown is canonical; JSON is derived.

## Why It Exists

Humans and agents read Markdown. Graph queries and tools need structured JSON. Rather than maintaining both manually (and having them drift), the compiler derives JSON from Markdown wiki-links deterministically — Markdown is the single source of truth.

## How It Works

1. Discover all KB pages under `docs/brain/projects/<project>/`
2. Parse YAML frontmatter from each page for node metadata
3. Extract `[[wiki-links]]` from page bodies
4. Infer edge types from section context and fallback heuristics
5. Build `nodes.json` — one entry per page with all frontmatter fields
6. Build `edges.json` — one entry per wiki-link with inferred type
7. Build `file-index.json` — maps source files to node IDs for fast lookup

Edge type inference:
- Wiki-link under "Depends On" → `depends_on`
- Wiki-link under "Used By" → `used_by`
- Wiki-link under "Core Concepts" / "Related Concepts" → `references`
- Wiki-link under "Core Flows" → `implements`
- Fallback → `references`

## Runtime Path

1. `compile_graph.py <kb_dir>` — discovers pages, parses frontmatter, extracts wiki-links
2. Outputs `graph/nodes.json`, `graph/edges.json`, `graph/file-index.json`

## API Entry Point

`python3 compile_graph.py <kb_dir>`

## Related Concepts

- [[kb-core-knowledge-layers|Knowledge Layers]] — compilation bridges Knowledge Map and Evidence
- [[kb-project-node-id-format|Node ID Format]] — flat IDs drive link resolution
- [[kb-substrate-compile-graph|Substrate: Compile Graph]] — the deterministic script

## Known Risks

None currently flagged.

## Source Evidence

- `kodebrain/skill/scripts/compile_graph.py` — `compile_graph()`, `_extract_wikilinks_with_sections()`, `_infer_edge_type_from_section()`, `_infer_edge_type_fallback()`, `main()`
- `docs/design/spec/knowledge-model.md` — "Markdown-First Graph Compilation" section

## Status Notes

Active. Script implemented; integration into onboard workflow tracked in vNext plan.

## Open Questions

None.
