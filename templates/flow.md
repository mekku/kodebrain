---
id: {{domain-slug}}-{{flow-slug}}
type: flow
status: active
confidence: source_supported
project: {{project-name}}
domain: {{domain-slug}}
source_files: []
last_reviewed: null
tags:
  - type/flow
  - domain/{{domain-slug}}
  - status/active
---

# {{Flow Name}}

<!-- Flow page = the path through the stack. Links here create the chain in the graph. -->

Part of [[{{domain-slug}}|{{Domain Name}} domain]]. Implements [[{{domain-slug}}-{{capability-slug}}|{{Capability Name}}]].

## Short Summary

{{One sentence: what triggers this flow and what it produces.}}

## Entry Point

| Field | Value |
|---|---|
| Type | `route` / `event` / `scheduler` / `cli` |
| Value | `{{METHOD /path}}` or `{{event-name}}` |
| Handler | `{{handlerFunction}}` |

## Steps

| # | Description | Symbol | Side Effects |
|---|---|---|---|
| 1 | Validate request | `{{validateFn}}` | — |
| 2 | Call service | `{{serviceFn}}` | — |
| 3 | Persist | `{{repoFn}}` | writes [[{{domain-slug}}-{{model-slug}}]] |
| 4 | Invalidate cache | `{{cacheFn}}` | publishes invalidation event |
| 5 | Return response | — | — |

## Data Movement

| From | To | Via |
|---|---|---|
| HTTP request | [[{{domain-slug}}-{{model-slug}}|{{Model}}]] | `{{validator}}` |
| [[{{domain-slug}}-{{model-slug}}|{{Model}}]] | database | `{{repositoryMethod}}` |

## Cache / State Behavior

{{Reads from cache first? Invalidates on write? Any locking?}}

## Concepts Required

- [[{{domain-slug}}-{{concept-slug}}|{{Concept Name}}]] — {{why it matters for this flow}}

## Error Paths

{{Validation failure? DB error? External service timeout?}}

## Source Evidence

- `{{file}}` — `{{symbol}}` — {{description}}

## Known Risks

- [[{{domain-slug}}-{{risk-slug}}|{{Risk Name}}]]

## Status Notes

{{Is this the current flow, a legacy flow, or partially migrated?}}

## Open Questions

{{Anything unclear about how this flow actually works.}}
