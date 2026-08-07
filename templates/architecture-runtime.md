---
type: architecture_runtime
project: {{project-slug}}
confidence: {{confidence}}
provenance: {{provenance}}
knowledge_role: {{knowledge_role}}
last_updated: {{date}}
---

# Runtime Topology — {{Project Name}}

## Processes

| Process | Type | Entry Point | Runs As |
|---|---|---|---|
| {{name}} | server / worker / scheduler / cli | `{{file}}` | {{user / systemd / container}} |

## Servers

| Server | Port | Protocol | Purpose |
|---|---|---|---|
| {{name}} | {{port}} | HTTP / gRPC | {{what it serves}} |

## Workers

| Worker | Queue/Topic | Concurrency | Purpose |
|---|---|---|---|
| {{name}} | {{queue}} | {{N}} | {{job type}} |

## Schedulers

| Scheduler | Schedule | Purpose |
|---|---|---|
| {{name}} | {{cron}} | {{what it triggers}} |

## Event Consumers

| Consumer | Event | Purpose |
|---|---|---|
| {{name}} | {{event name}} | {{what it does on receipt}} |

## CLI Processes

| Command | Entry Point | Purpose |
|---|---|---|
| `{{command}}` | `{{file}}` | {{one-time / utility}} |

## Runtime Boundaries

- {{process A}} ⇄ {{process B}}: {{protocol}}, {{timeout}}, {{retry policy}}
