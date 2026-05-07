---
id: {{domain-slug}}-{{YYYY-MM-DD}}-{{decision-slug}}
type: decision
status: active
confidence: verified
project: {{project-name}}
domain: {{domain-slug}}
source_files: []
last_reviewed: {{YYYY-MM-DD}}
tags:
  - type/decision
  - domain/{{domain-slug}}
  - status/active
---

# Decision: {{Short Decision Title}}

**Date:** {{YYYY-MM-DD}}
**Author:** {{name or "unknown"}}

Justifies [[{{domain-slug}}-{{concept-slug}}|{{Concept}}]] / affects [[{{domain-slug}}-{{capability-slug}}|{{Capability}}]].

## Context

{{What situation or problem prompted this? What constraints existed?}}

## Decision

{{What was decided, stated plainly.}}

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| {{option}} | {{reason}} |

## Consequences

{{What does this enable? What does it constrain? What debt does it create?}}

## When to Revisit

{{Under what conditions should this decision be reconsidered?}}
