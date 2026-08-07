---
id: kb-core-provenance
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-core
source_files:
  - docs/design/spec/knowledge-model.md
  - schema/node.schema.json
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-core
  - status/active
---

# Provenance

Part of [[kb-core|Core domain]].

## Short Summary

Provenance records **where a knowledge claim came from** — its origin. It is separate from confidence (how trustworthy it is) and must never be conflated with it.

## Why This Concept Exists

A human statement can be authoritative intent without being verified implementation. A source-supported observation can be accurate implementation without representing intended design. Without provenance, a reader cannot distinguish between "the architect said this" and "the code happens to do this" — both look like facts.

## How It Works

Every KB node carries a `provenance` field with one of eight values:

| Value | Origin |
|---|---|
| `human` | Direct human input (interview, explicit instruction) |
| `project_document` | README, ADR, spec, design doc |
| `source_code` | Source file symbols, imports, routes |
| `configuration` | Config files, env vars, build manifests |
| `runtime` | Observed runtime behavior, logs, traces |
| `test` | Test files, test coverage data |
| `git` | Git history, commit messages, diff data |
| `generated` | Machine-generated inference (lowest authority) |

## Where It Appears

Used by:
- Every KB page — `provenance` is a required frontmatter field
- [[kb-core-drift-detection|Drift Detection]] — provenance identifies which side of a drift is which
- [[kb-workflow-onboard|Onboard]] — provenance distinguishes intent from observation during mapping

Also relevant in [[kb-governance]] — spec authority hierarchy aligns with provenance strength.

## Common Misunderstanding

**Provenance is not confidence.** A `provenance: human` claim might have `confidence: needs_human_review` if the human was uncertain. A `provenance: source_code` claim typically has `confidence: supported` because the code is evidence.

**Generated inference never overrides stronger authority.** If a harvest script infers a domain boundary but a human explicitly defined it differently, the human provenance wins — and the disagreement becomes a drift item.

## Source Evidence

- `docs/design/spec/knowledge-model.md` — "Provenance and Confidence Are Separate" section
- `schema/node.schema.json` — `provenance` field definition with enum values

## Status Notes

Current design. No migration needed.

## Open Questions

None.
