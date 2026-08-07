---
id: kb-core-knowledge-node-model
type: model
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-core
source_files:
  - schema/node.schema.json
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/model
  - domain/kb-core
  - status/active
---

# Knowledge Node

Part of [[kb-core|Core domain]].

## Schema

Defined in `schema/node.schema.json`. Every KB page is a Knowledge Node.

### Common Fields (all types)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Flat, hyphen-separated: `<domain-slug>-<type-slug>` |
| `type` | enum | yes | `domain`, `capability`, `flow`, `concept`, `model`, `risk`, `decision`, `incident`, `milestone`, `change`, `project`, `architecture_*` |
| `status` | enum | yes | `active`, `legacy`, `deprecated`, `partially_migrated`, `unused`, `experimental`, `unknown`, `needs_review` |
| `confidence` | enum | yes | `verified`, `supported`, `inferred`, `ambiguous`, `stale`, `needs_human_review` |
| `provenance` | enum | yes | `human`, `project_document`, `source_code`, `configuration`, `runtime`, `test`, `git`, `generated` |
| `knowledge_role` | enum | yes | `intent`, `observed`, `mixed` |
| `project` | string | yes | Project slug |
| `domain` | string | conditional | Required for domain-scoped types |
| `source_files` | string[] | yes | Source file paths that provide evidence |
| `last_updated` | date | yes | ISO date |
| `last_reviewed` | date | no | Last human review date |
| `tags` | string[] | yes | `type/<type>`, `domain/<slug>`, `status/<status>` |

### Lifecycle Fields (type-specific)

| Field | Applies to | Owner |
|---|---|---|
| `change_state` | Change | Workflow |
| `decision_state` | Decision | History |
| `incident_state` | Incident | History |

Lifecycle fields are separate from `status` — see [[kb-workflow-status-lifecycle-separation|Status vs Lifecycle Separation]].

### Decision-Specific Fields

| Field | Type | Description |
|---|---|---|
| `supersedes` | string[] | IDs of decisions this one replaces |
| `superseded_by` | string[] | Derived by compiler — not stored |

## File Location

A node with `id: kb-core-provenance` lives at:
`domains/kb-core/concepts/kb-core-provenance.md`

Domain hub: `id: kb-core` → `domains/kb-core/kb-core.md`

## Wiki-Link Representation

Every relationship between nodes must appear as a `[[node-id|Display Name]]` wiki-link in the body. The compiler extracts these to build `edges.json`.

## Source Evidence

- `schema/node.schema.json` — full JSON Schema definition
- `docs/design/spec/knowledge-model.md` — field semantics
- `docs/design/spec/project-model.md` — node ID format, file layout

## Status Notes

vNext schema current. Older KBs may use hierarchical IDs (`auth/login-flow`) — migrated by `migrate_kb.py`.
