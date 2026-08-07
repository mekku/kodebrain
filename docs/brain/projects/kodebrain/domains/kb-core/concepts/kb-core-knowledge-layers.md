---
id: kb-core-knowledge-layers
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

# Knowledge Layers

Part of [[kb-core|Core domain]].

## Short Summary

Kode Brain uses three layers of project knowledge: Project Contract (intended/canonical), Knowledge Map (explanation + navigation), and Evidence (observed reality). The layers are connected by guidance and grounding — the Contract guides the Map, which is grounded by Evidence.

## Why This Concept Exists

Without layers, a reader cannot distinguish "what we intend to build" from "what we built" from "what the code actually does." These three things disagree in every real project. Layers make the disagreement explicit and traceable instead of silently conflating them.

## How It Works

```text
Project Contract (intended/canonical)
  Purpose, Scope, Architecture, Domains, Invariants, Decisions
        │ guides
        ▼
Knowledge Map (explanation + navigation)
  Capabilities, Flows, Concepts, Models, APIs, Risks
        │ grounded by
        ▼
Evidence (observed reality)
  Source, Symbols, Tests, Config, Runtime, Git
```

- **Project Contract** answers "what SHOULD the system be?"
- **Knowledge Map** connects intent to observation and makes both navigable
- **Evidence** answers "what does the system ACTUALLY do?"

A disagreement between layers becomes a **drift item** — Kode Brain must never silently rewrite intended knowledge from observed code, or rewrite observed claims because a human intended something else.

## Where It Appears

Used by:
- [[kb-core-drift-detection|Drift Detection]] — drift is a disagreement between layers
- [[kb-workflow-onboard|Onboard]] — greenfield starts with Contract; brownfield builds up from Evidence
- [[kb-workflow-change-reconciliation|Change Reconciliation]] — reconcile Contract with post-implementation Evidence

## Common Misunderstanding

**The Contract is not "the spec doc."** It is the collection of all intended knowledge: purpose, architecture, domain responsibilities, invariants, decisions — regardless of which file they live in.

**Evidence is not "the source code."** It includes source, config, runtime behavior, tests, git history, and infrastructure — anything observable.

## Source Evidence

- `docs/design/spec/knowledge-model.md` — "Core Mental Model" section with three-layer diagram

## Status Notes

Current design. No migration needed.

## Open Questions

None.
