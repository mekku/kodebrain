---
id: {{YYYY-MM-DD}}-{{change-slug}}
type: change
status: active
change_state: planned
outcome: null
confidence: verified
provenance: human
knowledge_role: intent
started_at: "{{YYYY-MM-DD}}"
completed_at: null
last_updated: {{date}}
tags:
  - type/change
  - change_state/planned
---

# Change: {{Short Change Title}}

**State:** planned | in_progress | implemented | reconciled
**Outcome:** success | partial | abandoned | rolled_back
**Started:** {{YYYY-MM-DD}}
**Completed:** {{date or "—"}}

## Intent

{{What this change is meant to accomplish. One paragraph.}}

## Why

{{The problem or opportunity that drives this change.}}

## Affected Domains

- [[{{domain-slug}}|{{Domain Name}}]] — {{how it is affected}}
- ...

## Architecture Impact

{{How system structure, boundaries, or communication paths change.}}

## Expected Behavior Changes

- {{Before → After}}
- ...

## Invariants

- {{Constraint that must remain true during and after this change}}
- ...

## Compatibility / Migration

{{Breaking changes, migration steps, dual-write periods, backward compatibility.}}

## Expected Source Areas

- `{{file}}` — {{what will change}}
- ...

## Implementation Evidence

<!-- Filled in after implementation -->

- `{{commit}}` — {{what was done}}

## Outcome

<!-- Filled in after reconciliation -->

{{What actually happened? Compare intent vs result.}}

## Progress Log

<!-- Append-only entries. Compiler derives events from these. -->

### {{YYYY-MM-DD}}
{{What was done today. What was discovered. What changed.}}

### {{YYYY-MM-DD}}
{{...}}

## Deviations From Plan

<!-- What changed from the original intent during implementation? Summarized from progress log. -->

## Lessons Learned

<!-- What did this change teach us? What would we do differently? -->

## Follow-ups

<!-- What work remains that this change didn't address? -->

## Regressions / Problems Introduced

<!-- Did this change cause any issues later? Link to incidents if relevant. -->

## Open Questions

- {{Unresolved item}}
