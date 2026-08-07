---
type: architecture_deployment
project: {{project-slug}}
confidence: {{confidence}}
provenance: {{provenance}}
knowledge_role: {{knowledge_role}}
last_updated: {{date}}
---

# Deployment — {{Project Name}}

## Environments

| Environment | Purpose | URL / Endpoint |
|---|---|---|
| production | {{live traffic}} | {{url}} |
| staging | {{pre-release validation}} | {{url}} |
| development | {{local / shared dev}} | {{url}} |

## Deployment Topology

| Component | Host | Scaling | Region |
|---|---|---|---|
| {{name}} | {{platform / VM / container}} | {{fixed / auto}} | {{region}} |

## CI/CD

| Stage | Tool | Trigger |
|---|---|---|
| Build | {{tool}} | {{push / PR}} |
| Test | {{tool}} | {{push / PR}} |
| Deploy | {{tool}} | {{merge / manual}} |

## Operational Boundaries

- {{Constraint or policy about how deployment works}}
- {{Known deployment risks or limitations}}
