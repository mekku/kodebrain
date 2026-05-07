---
id: {{domain-slug}}-{{capability-slug}}
type: capability
status: active
confidence: source_supported
project: {{project-name}}
domain: {{domain-slug}}
source_files: []
last_reviewed: null
tags:
  - type/capability
  - domain/{{domain-slug}}
  - status/active
---

# {{Capability Name}}

<!-- Capability names must be verb phrases: "Create order", "Send notification", "Validate session" -->

Part of [[{{domain-slug}}|{{Domain Name}} domain]].

## Short Summary

{{One sentence: what the system can do here, from the user/caller perspective.}}

## Why It Exists

{{The product requirement or system need this capability satisfies.}}

## How It Works

{{Practical explanation. Entry point → what it does → result.}}

## Runtime Path

See [[{{domain-slug}}-{{flow-slug}}|{{Flow Name}}]] for the full flow.

1. {{Entry point — route, event, CLI call}}
2. {{Key service method}}
3. {{Data read/write}}
4. {{Response or side effect}}

## API Entry Point

`{{METHOD}} {{/path}}`

## Related Concepts

- [[{{domain-slug}}-{{concept-slug}}|{{Concept Name}}]] — {{why it matters here}}

## Related Models

- [[{{domain-slug}}-{{model-slug}}|{{Model Name}}]] — {{read / written / validated}}

## Known Risks

- [[{{domain-slug}}-{{risk-slug}}|{{Risk Name}}]]

## Source Evidence

- `{{file path}}` — `{{symbol}}` — {{what it does}}

## Status Notes

{{Is this capability fully active? Legacy? Partially migrated?}}

## Open Questions

{{Anything unclear that needs review.}}
