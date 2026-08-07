---
id: {{domain-slug}}-{{YYYY-MM-DD}}-{{incident-slug}}
type: incident
severity: {{severity}}
status: {{status}}
started_at: "{{YYYY-MM-DD}}"
resolved_at: {{YYYY-MM-DD or null}}
domain: {{domain-slug}}
project: {{project-slug}}
confidence: verified
provenance: human
knowledge_role: observed
last_updated: "{{date}}"
tags:
  - type/incident
  - domain/{{domain-slug}}
  - severity/{{severity}}
---

# Incident: {{Short Incident Title}}

**Severity:** critical / high / medium / low
**Status:** resolved | mitigated | ongoing
**Started:** {{YYYY-MM-DD}}
**Resolved:** {{YYYY-MM-DD or "ongoing"}}

## What Happened

{{Describe the incident clearly. What broke, under what conditions? One paragraph.}}

## Impact

{{What was affected? Users, data, revenue, trust? Quantify if possible.}}

## Timeline

| Time | Event |
|---|---|
| {{HH:MM}} | {{What was observed}} |
| {{HH:MM}} | {{Action taken}} |
| {{HH:MM}} | {{Resolution confirmed}} |

## Root Cause

{{The fundamental reason this happened. Not the symptom — the cause.}}

## Why Existing Design Allowed It

{{What assumption, missing guardrail, or architectural gap permitted this?}}

## Resolution

{{What was done to fix the immediate problem?}}

## Lesson

{{What must be different going forward? One clear, actionable lesson.}}

## Guardrail Introduced

{{What check, invariant, test, or monitor now prevents recurrence? Link to invariant/decision if promoted.}}

## Affected Knowledge

<!-- Nodes touched by this incident — enables traversal: task → node → incident -->

- [[{{node-id}}|{{Node Name}}]]
- [[{{node-id}}|{{Node Name}}]]

## Related Changes

- [[{{change-id}}|{{Change Title}}]]

## Related Decisions

- [[{{decision-id}}|{{Decision Title}}]]

## Related Incidents

- [[{{incident-id}}|{{Incident Title}}]]
