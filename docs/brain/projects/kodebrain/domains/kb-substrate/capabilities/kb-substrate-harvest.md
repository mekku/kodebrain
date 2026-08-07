---
id: kb-substrate-harvest
type: capability
status: active
confidence: supported
provenance: source_code
knowledge_role: observed
project: kodebrain
domain: kb-substrate
source_files:
  - kodebrain/skill/scripts/harvest.py
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/capability
  - domain/kb-substrate
  - status/active
---

# Source Harvest

Part of [[kb-substrate|Substrate domain]].

## Short Summary

Deterministic Python script that extracts structured evidence from source files: exports, routes, imports, imported_by, status signals (TODO, DEPRECATED, @deprecated), test detection, and status classification. Supports full, incremental (hash-based), and targeted (specific files) harvest modes.

## Why It Exists

LLMs reading raw source files is expensive and non-deterministic. Harvest provides reproducible, cached evidence at lower cost. It is the preferred first step for source inspection in the escalation model (Level 1).

## How It Works

1. Scan project root for source files
2. For each file, extract: exports (functions, classes), routes (HTTP method + path patterns), imports (local + external), status signals (DEPRECATED, TODO, @deprecated comments)
3. Compute SHA-256 hash per file for change detection
4. Determine imported_by relationships across files
5. Classify status: `active`, `deprecated`, `suspected_unused`, `needs_review`
6. Output JSON with root, hashes, dirty list, per-file briefs

Modes:
- **Full:** `harvest.py <root>` — scan all files
- **Incremental:** `harvest.py <root> --hashes <file>` — only dirty files
- **Targeted:** `harvest.py <root> --files f1 f2` — specific files
- **Index build:** `harvest.py --build-index <nodes.json>` — build file-index.json
- **Benchmark:** `harvest.py --benchmark <kb_dir> --source-root <root>` — metrics

## Runtime Path

1. `harvest.py <root>` — subprocess call from agent
2. JSON output on stdout — agent parses and uses

## API Entry Point

`python3 harvest.py <root> [--hashes <file>] [--files f1 f2] [--build-index <nodes.json>] [--benchmark ...]`

## Related Concepts

- [[kb-core-harvest-policy|Harvest Policy]] — escalation model (Level 0–4)
- [[kb-substrate-sha-detection|SHA-256 Change Detection]] — hash-based incremental harvest

## Known Risks

- Harvest may miss dynamically wired routes or exports — Level 3 (targeted source reading) is the fallback

## Source Evidence

- `kodebrain/skill/scripts/harvest.py` — full harvest implementation

## Status Notes

Active. Core substrate module.

## Open Questions

None.
