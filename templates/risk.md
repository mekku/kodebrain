---
id: {{domain-slug}}-{{risk-slug}}
type: caveat
status: needs_review
confidence: source_supported
project: {{project-name}}
domain: {{domain-slug}}
source_files: []
last_reviewed: null
tags:
  - type/risk
  - domain/{{domain-slug}}
  - status/needs_review
  - severity/{{high|medium|low}}
---

# Risk: {{Short Risk Title}}

<!-- Risk nodes appear as red leaf nodes in the graph, clustered around what they threaten. -->

**Severity:** high / medium / low
**Category:** data-loss / staleness / security / correctness / performance / legacy

Affects:
- [[{{domain-slug}}-{{capability-slug}}|{{Capability Name}}]]
- [[{{domain-slug}}-{{flow-slug}}|{{Flow Name}}]]

## What Can Go Wrong

{{Describe the failure mode clearly. What breaks, under what condition?}}

## When It Triggers

{{The specific scenario. Not just "if X fails" — be precise.}}

## Current Mitigation

{{What is already in place? If nothing, say "none".}}

## Safe Path

{{What should a developer do to avoid triggering this?}}

## Source Evidence

- `{{file}}` — {{what in the code demonstrates or causes this risk}}

## Status

{{Known and accepted / being addressed / unknown.}}
