---
id: {{YYYY-MM-DD}}-{{milestone-slug}}
type: milestone
date: "{{YYYY-MM-DD}}"
significance: {{significance}}
project: {{project-slug}}
confidence: verified
provenance: human
knowledge_role: intent
last_updated: "{{date}}"
tags:
  - type/milestone
  - significance/{{significance}}
---

# Milestone: {{Short Milestone Title}}

**Date:** {{YYYY-MM-DD}}
**Significance:** architectural / product / operational / organizational

## What Changed

{{One paragraph: what happened and why it matters.}}

## Why It Matters

{{How did this change the mental model of the project? What was different after?}}

## Before / After

| Before | After |
|---|---|
| {{old state}} | {{new state}} |

## Affected Domains

- [[{{domain-slug}}|{{Domain Name}}]]

## Related Changes

- [[{{change-id}}|{{Change Title}}]]

## Related Decisions

- [[{{decision-id}}|{{Decision Title}}]]
