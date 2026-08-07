---
id: {{domain-slug}}-{{YYYY-MM-DD}}-{{decision-slug}}
type: decision
decision_state: active
status: active
confidence: verified
provenance: human
knowledge_role: intent
project: {{project-slug}}
domain: {{domain-slug}}
source_files: []
supersedes: []
superseded_by: []
last_updated: {{YYYY-MM-DD}}
last_reviewed: {{YYYY-MM-DD}}
tags:
  - type/decision
  - domain/{{domain-slug}}
  - decision_state/active
---

# Decision: {{Short Decision Title}}

**Date:** {{YYYY-MM-DD}}
**Author:** {{name or "unknown"}}
**State:** active | superseded | deprecated

<!-- If superseded_by is populated, this decision is no longer current. -->
<!-- If supersedes is populated, this decision replaces the listed decisions. -->

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

## Why Previous Decision Changed

<!-- Fill in when this decision supersedes an earlier one -->

{{At the time the previous decision was made, ... Later we discovered ... Therefore the original assumption no longer holds.}}

## When to Revisit

{{Under what conditions should this decision be reconsidered?}}
