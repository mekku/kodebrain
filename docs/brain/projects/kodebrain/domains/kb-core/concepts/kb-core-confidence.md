---
id: kb-core-confidence
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

# Confidence

Part of [[kb-core|Core domain]].

## Short Summary

Confidence records **how trustworthy a knowledge claim is** — separate from provenance (where it came from). A `provenance: human` claim might be uncertain; a `provenance: source_code` claim is usually well-supported.

## Why This Concept Exists

Without confidence labels, every claim looks equally certain. A reader (human or agent) needs to know whether to trust a claim or verify it independently. Confidence prevents stale docs from masquerading as current truth.

## How It Works

Every KB node carries a `confidence` field with one of six values:

| Value | Meaning | Who can set |
|---|---|---|
| `verified` | Human-reviewed and confirmed | Human only |
| `supported` | Backed by clear source evidence | Agent or human |
| `inferred` | Reasonable deduction, not directly observed | Agent |
| `ambiguous` | Evidence supports multiple interpretations | Agent |
| `stale` | Once valid, now outdated vs current source | Agent (scan/review) |
| `needs_human_review` | Cannot resolve without human judgment | Agent |

## Where It Appears

Used by:
- Every KB page — `confidence` is a required frontmatter field
- [[kb-workflow-onboard-flow|Onboard Flow]] — pages written from harvest get `confidence: supported`; inferred claims get `confidence: inferred`
- [[kb-workflow-scan|Scan]] — changed files trigger re-evaluation of confidence
- Reading packs — low-confidence nodes are flagged as warnings

Also relevant in [[kb-governance]] — confidence gates certain actions (only `supported` or `verified` pages should drive implementation decisions).

## Common Misunderstanding

**`inferred` is not a failure state.** It is honest: "this is our best understanding from available evidence, but verify before acting on it." Many useful KB pages will carry `confidence: inferred` for areas where source evidence is thin.

**`needs_human_review` is a blocking state.** Pages with this confidence should never drive implementation decisions without human confirmation.

## Source Evidence

- `docs/design/spec/knowledge-model.md` — "Provenance and Confidence Are Separate"
- `schema/node.schema.json` — `confidence` field definition with enum values

## Status Notes

Current design. No migration needed.

## Open Questions

None.
