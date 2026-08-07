---
id: {{project-slug}}
type: project
status: active
confidence: {{confidence}}
provenance: {{provenance}}
knowledge_role: {{knowledge_role}}
project: {{project-slug}}
source_files: []
last_updated: {{date}}
last_reviewed: null
tags:
  - type/project
  - status/active
---

# {{Project Name}}

## Purpose

{{What this project is for, who it serves. One paragraph.}}

## Primary Users / Actors

- **{{Actor}}** — {{what they do, why they use this system}}
- ...

## Core Outcomes

1. {{The system lets users do X}}
2. {{The system lets users do Y}}
3. ...

## Scope

### In Scope

- ...

### Out of Scope

- ...

## Technology Summary

| Role | Technology |
|---|---|
| Frontend | {{framework}} |
| Backend | {{runtime}} |
| Persistence | {{database}} |
| Cache | {{cache}} |
| Queue/Events | {{queue}} |
| Testing | {{test framework}} |
| Build/Tooling | {{build tool}} |
| Infrastructure | {{infra}} |

## System Architecture

{{High-level description of apps, services, processes, boundaries, and communication paths. Link to architecture/overview.md for details.}}

## Domains

- [[{{domain-slug}}|{{Domain Name}}]] — {{one-line responsibility}}
- ...

## Runtime Entry Points

| Entry Point | Type | Description |
|---|---|---|
| `{{command}}` | CLI | {{what it starts}} |
| `{{path}}` | HTTP | {{what it serves}} |
| `{{topic}}` | Event | {{what it consumes}} |

## External Systems

| System | Purpose | Criticality |
|---|---|---|
| {{name}} | {{why it exists in this project}} | high / medium / low |

## System-wide Invariants

- {{Constraint that must remain true across all domains}}
- ...

## Current Risks / Legacy / Migration

- [[{{risk-slug}}|{{Risk}}]]
- {{Known legacy subsystem}} — {{status}}

## Active Changes

- [[changes/active/{{YYYY-MM-DD}}-{{change-slug}}|{{Change Title}}]]

## Where To Start

1. Read this page for project orientation.
2. Read `architecture/overview.md` for system structure.
3. Pick a domain from [[#Domains]] relevant to your task.
4. Read the domain hub page for responsibility boundaries.
5. Check [[#Active Changes]] for in-progress work.
6. Use `/kodebrain reading-pack "<task>"` for focused context.
