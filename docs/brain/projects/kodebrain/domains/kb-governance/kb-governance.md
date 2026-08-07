---
id: kb-governance
type: domain
status: active
confidence: supported
provenance: project_document
knowledge_role: intent
project: kodebrain
domain: kb-governance
source_files:
  - docs/design/spec/governance.md
  - docs/design/spec.md
last_updated: "2026-08-07"
last_reviewed: null
tags:
  - type/domain
  - domain/kb-governance
  - status/active
---

# Governance Domain

## Responsibility

Define the *rules* that govern the KB itself — precedence hierarchy, spec authority, compatibility/migration principles, non-goals, success criteria.

## Owns

- Spec authority tree: `spec.md` (root) → 5 child specs → schema → SKILL.md → implementation plan
- One concept → one canonical owner rule
- Artifact class separation: Specification, Decision, History, Implementation Plan, Code/Runtime
- Precedence hierarchy (8 levels)
- Spec boundary routing: which spec owns which question pattern
- Workflow ↔ History boundary: Change lifecycle vs Decision/Incident lifecycle
- Compatibility principles: preserve human notes, detect legacy format, migrate deterministically
- Non-goals: what Kode Brain is not intended to do
- Success criteria: for new projects, existing projects, during development, over time

## Does Not Own

- Any domain's substantive content — governance owns the RULES, not the content
- Implementation details — see [[kb-substrate|Substrate domain]]

## Depends On

- All 4 other specs (knowledge, project, workflow, history) — governance rules apply to them
- [[kb-core|Core domain]] — drift rules (governance enforces, core defines)

## Used By

- All domains — every spec change follows governance rules
- [[kb-workflow|Workflow domain]] — onboard follows compatibility rules
- [[kb-substrate|Substrate domain]] — migrate_kb.py follows migration rules

## Core Concepts

- [[kb-governance-spec-authority|Spec Authority]] — one concept, one owner
- [[kb-governance-precedence|Precedence]] — 8-level authority hierarchy
- [[kb-governance-artifact-classes|Artifact Classes]] — spec, decision, history, plan, code
- [[kb-governance-compatibility|Compatibility]] — preserve, detect, migrate, report
- [[kb-governance-non-goals|Non-Goals]] — explicit boundaries
- [[kb-governance-success-criteria|Success Criteria]] — how Kode Brain succeeds

## Capabilities

This domain is regulatory — it defines rules, not executable capabilities.

## Core Flows

None — regulatory domain.

## Data Ownership

None — governance owns rules, not data.

## Entry Points

None — governance is enforced by process, not code.

## Invariants

- Every concept has exactly one canonical specification owner
- When introducing a new concept: locate owner → modify that spec → record rationale in Decision
- Anti-pattern: new idea → create another doc → implement from it → leave canonical spec unchanged
- A Decision must not become a second copy of the spec
- An implementation plan must not become a future canonical spec by accident
- Historical design docs must not remain equally authoritative after canonical model has changed

## Legacy / Migration

- vNext spec tree (root + 5 children) replaces older flat design docs
- `docs/design/taxonomy.md`, `skills.md`, `agents.md`, `workflows.md` are superseded historical input

## Risks

None currently flagged.

## Source Areas

| Path | Purpose |
|---|---|
| `docs/design/spec/governance.md` | Canonical governance spec |
| `docs/design/spec.md` | Canonical root — defines spec tree |
| `docs/design/open-decisions.md` | Resolved architectural decisions |

## Open Questions

None at this time.
