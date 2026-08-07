---
type: architecture_data
project: {{project-slug}}
confidence: {{confidence}}
provenance: {{provenance}}
knowledge_role: {{knowledge_role}}
last_updated: {{date}}
---

# Data Architecture — {{Project Name}}

## Primary Databases

| Database | Technology | Purpose | Owned By |
|---|---|---|---|
| {{name}} | {{tech}} | {{what it stores}} | {{domain / service}} |

## Major Data Stores

| Store | Type | Purpose | Ownership |
|---|---|---|---|
| {{name}} | relational / document / key-value / blob | {{what it holds}} | {{domain}} |

## Ownership Boundaries

- **{{Domain A}}** owns tables/collections: {{list}}
- **{{Domain B}}** owns tables/collections: {{list}}
- Cross-domain access: {{which domains read others' data, and how}}

## Caches

| Cache | Backs | TTL | Invalidation |
|---|---|---|---|
| {{cache key}} | {{data source}} | {{duration}} | {{trigger}} |

## Derived Data

| Source | Derived Form | Purpose | Refresh |
|---|---|---|---|
| {{table}} | {{view / materialized / projection}} | {{why}} | {{how often}} |

## Critical Data Movement Rules

- {{Rule about how data flows between stores}}
- {{Constraint on data duplication or consistency}}
