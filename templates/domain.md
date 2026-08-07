---
id: {{domain-slug}}
type: domain
status: active
confidence: {{confidence}}
provenance: {{provenance}}
knowledge_role: {{knowledge_role}}
project: {{project-slug}}
domain: {{domain-slug}}
source_files: []
last_updated: {{date}}
last_reviewed: null
tags:
  - type/domain
  - domain/{{domain-slug}}
  - status/active
---

# {{Domain Name}}

## Responsibility

{{One paragraph: what this domain is responsible for. What business or system problem it solves.}}

## Owns

- {{Capability, data, or sub-domain this domain owns}}
- ...

## Does Not Own

- {{Thing this domain explicitly does NOT own}} — see [[{{other-domain-slug}}|{{Other Domain}}]]
- ...

## Depends On

- [[{{other-domain-slug}}|{{Other Domain}}]] — {{what this domain needs from it}}
- ...

## Used By

- [[{{other-domain-slug}}|{{Other Domain}}]] — {{why it uses this domain}}
- ...

## Core Concepts

- [[{{domain-slug}}-{{concept-slug}}|{{Concept Name}}]] — {{one-line description}}
- ...

## Capabilities

- [[{{domain-slug}}-{{capability-slug}}|{{Capability Name}}]]
- ...

## Core Flows

- [[{{domain-slug}}-{{flow-slug}}|{{Flow Name}}]]
- ...

## Data Ownership

| Model | Ownership | Shared With |
|---|---|---|
| [[{{domain-slug}}-{{model-slug}}|{{Model}}]] | owned / shared | {{domain}} |

## Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `{{METHOD}} {{/path}}` | HTTP | {{what it does}} |
| `{{command}}` | CLI | {{what it does}} |

## Invariants

- {{Constraint that must remain true in this domain}}
- ...

## Legacy / Migration

{{Known legacy code, partial migrations, or areas not representing intended architecture.}}

## Risks

- [[{{domain-slug}}-{{risk-slug}}|{{Risk Name}}]]

## Source Areas

| Path | Purpose |
|---|---|
| `{{directory}}` | {{what lives there}} |

## Open Questions

{{Anything that needs human review or clarification.}}
