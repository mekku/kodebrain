---
type: change
project: {{project-slug}}
status: planned
confidence: verified
provenance: human
knowledge_role: intent
last_updated: {{date}}
---

# Change: {{Short Change Title}}

**Status:** planned | in_progress | implemented | reconciled

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

## Open Questions

- {{Unresolved item}}
