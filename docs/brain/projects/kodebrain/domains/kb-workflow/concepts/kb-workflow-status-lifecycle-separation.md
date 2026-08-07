---
id: kb-workflow-status-lifecycle-separation
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: reference
project: kodebrain
domain: kb-workflow
canonical_source:
  path: docs/design/spec/workflow-model.md
  anchor: status-lifecycle-separation
source_files: []
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-workflow
  - status/active
---

# Status vs Lifecycle Separation

Part of [[kb-workflow|Workflow domain]].

## Short Summary

Generic KB `status` describes knowledge quality (`active`, `stale`, `needs_review`). Lifecycle state is separate and type-specific (`change_state`, `decision_state`, `incident_state`). They must never be conflated.

## Why This Concept Exists

A knowledge page can be `status: active` (the knowledge is current) while the thing it describes is in any lifecycle state. A completed change page has `status: active` (its knowledge is accurate) even though the change itself is done. Conflating the two would mean you cannot tell whether a page is stale knowledge or a completed process.

## How It Works

| Record type | Lifecycle field | Canonical owner | Values |
|---|---|---|---|
| Change | `change_state` | Workflow | `planned`, `in_progress`, `implemented`, `reconciled` |
| Decision | `decision_state` | History | `active`, `superseded`, `deprecated` |
| Incident | `incident_state` | History | `ongoing`, `mitigated`, `resolved` |

Generic KB `status` uses: `active`, `legacy`, `deprecated`, `partially_migrated`, `unused`, `experimental`, `unknown`, `needs_review`.

A page can be `status: active` + `change_state: in_progress` — the KB page is current, the change is underway.

A page can be `status: stale` + `decision_state: active` — the decision is still governing, but the page hasn't been reviewed recently.

## Where It Appears

Used by:
- Every record-type page that carries its own lifecycle
- Schema enforcement: `schema/node.schema.json` keeps these fields separate
- [[kb-workflow-change-lifecycle|Change Lifecycle]] — the change-specific lifecycle

Also relevant in [[kb-history-decision-lifecycle|Decision Lifecycle]] and [[kb-history-incident-lifecycle|Incident Lifecycle]] — both follow this separation.

## Common Misunderstanding

**Lifecycle state does not replace KB status.** They coexist. A page has both `status` and (if applicable) a lifecycle field. The lifecycle field tracks the process; the status field tracks knowledge quality.

## Source Evidence

- `docs/design/spec/workflow-model.md` — "Status vs Lifecycle State" section with ownership table
- `schema/node.schema.json` — separate `status` and lifecycle fields

## Status Notes

Current design. Enforced in vNext schema.

## Open Questions

None.
