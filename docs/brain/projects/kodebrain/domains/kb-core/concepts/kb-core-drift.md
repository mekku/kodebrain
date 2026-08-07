---
id: kb-core-drift
type: concept
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-core
source_files:
  - docs/design/spec/knowledge-model.md
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/concept
  - domain/kb-core
  - status/active
---

# Drift

Part of [[kb-core|Core domain]].

## Short Summary

Drift is a meaningful disagreement between intended reality (Project Contract) and observed reality (Evidence). A drift item records the disagreement without silently resolving it to either side.

## Why This Concept Exists

In real projects, docs say one thing and code does another. Most documentation tools either ignore the gap or overwrite one side. Kode Brain surfaces drift explicitly so a human can decide what to fix — the spec, the code, or both.

## How It Works

When intent and observation disagree:
1. A drift item is created in `reports/drift.md`
2. The relevant KB node is marked `confidence: stale`
3. Neither side is silently overwritten
4. A human decides the resolution

Examples of drift:
- Intended architecture says only Stripe is active, but an Omise code path appears live
- Domain contract says Orders owns cancellation, but runtime routes delegate it to Fulfillment
- A completed change says an old API was removed, but routes still expose it

Important drift may also become a risk/caveat node for that domain.

## Where It Appears

Used by:
- [[kb-core-drift-detection|Drift Detection]] — capability that finds drift
- [[kb-workflow-onboard|Onboard]] — brownfield onboarding surfaces drift between existing docs and code
- [[kb-workflow-change-reconciliation|Change Reconciliation]] — post-implementation check for drift
- [[kb-workflow-scan|Scan]] — re-scan may surface new drift

## Common Misunderstanding

**Drift is not a bug.** It is a signal. The code might be right and the spec outdated. Or the spec might be right and the code wrong. Or both might be partially right. Kode Brain does not decide — it surfaces.

**Drift items are not automatically resolved.** A human must determine the correct resolution and update either the spec, the code, or both.

## Source Evidence

- `docs/design/spec/knowledge-model.md` — "Drift" section
- `docs/design/spec/knowledge-model.md` — "Intended Truth vs Observed Truth" section

## Status Notes

Current design. No migration needed.

## Open Questions

None.
