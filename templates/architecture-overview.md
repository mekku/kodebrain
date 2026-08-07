---
type: architecture_overview
project: {{project-slug}}
confidence: {{confidence}}
provenance: {{provenance}}
knowledge_role: {{knowledge_role}}
last_updated: {{date}}
---

# Architecture Overview — {{Project Name}}

## System Context

{{High-level description of what the system is, what it talks to, and who uses it. Include a system-context or container diagram where useful (ASCII or Mermaid).}}

## Applications & Services

| Component | Type | Role | Runtime |
|---|---|---|---|
| {{name}} | web / api / worker / scheduler / cli | {{what it does}} | {{runtime env}} |

## Boundaries

### Internal Boundaries

- {{domain A}} ⇄ {{domain B}} via {{mechanism}}

### External Boundaries

- {{system}} → {{external service}} via {{protocol}}

## Communication Paths

| From | To | Protocol | Purpose |
|---|---|---|---|
| {{component}} | {{component}} | HTTP / gRPC / queue / event | {{why}} |

## Domain Placement

{{Which domains live in which components. Cross-reference with domain pages.}}

## Deployment Topology (when known)

{{Environments, regions, scaling groups. Link to architecture/deployment.md.}}

## See Also

- [[architecture-technology|Technology Stack]]
- [[architecture-runtime|Runtime Topology]]
- [[architecture-data|Data Architecture]]
- [[architecture-deployment|Deployment]]
- [[architecture-integrations|External Integrations]]
