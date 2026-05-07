---
id: {{domain-slug}}-{{model-slug}}
type: data_model
status: active
confidence: source_supported
project: {{project-name}}
domain: {{domain-slug}}
source_files: []
last_reviewed: null
tags:
  - type/model
  - domain/{{domain-slug}}
  - status/active
---

# {{Model Name}}

<!-- Models are typically leaf nodes — many flows link in, few links out. -->

Part of [[{{domain-slug}}|{{Domain Name}} domain]].

## Short Summary

{{What this model represents. One sentence.}}

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | yes | Primary key |
| `{{field}}` | `{{type}}` | yes/no | {{description}} |

## Lifecycle States

<!-- Include this section only if this model has a state machine. -->

| State | Meaning | Transitions To |
|---|---|---|
| `{{state}}` | {{meaning}} | `{{next}}` on `{{event}}` |

## Where It Is Used

- [[{{domain-slug}}-{{capability-slug}}|{{Capability}}]] — {{written / read / validated}}
- [[{{domain-slug}}-{{flow-slug}}|{{Flow}}]] — {{step N}}
- ...

## Cross-Domain Usage

<!-- Include if this model is shared across domains — this is a graph bridge node. -->

Also referenced by [[{{other-domain-slug}}]] — {{why}}.

## Source Evidence

- `{{file}}` — `{{class or schema name}}` — ORM / Zod / Pydantic / etc.

## Status Notes

{{Current schema? V2 planned? Shared across unrelated flows (risky)?}}

## Known Risks

- [[{{domain-slug}}-{{risk-slug}}|{{Risk}}]]
