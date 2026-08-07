---
id: kb-governance-spec-authority
type: concept
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
  - type/concept
  - domain/kb-governance
  - status/active
---

# Spec Authority

Part of [[kb-governance|Governance domain]].

## Short Summary

Every concept in Kode Brain has exactly one canonical specification owner. When a new concept is introduced, it must be routed to the correct owner — never left as a free-floating document. This prevents specification drift.

## Why This Concept Exists

Without spec authority, new ideas spawn competing documents. The canonical spec stays unchanged while implementation follows the new document. Over time, nobody knows which document is authoritative. Spec authority makes ownership explicit and enforceable.

## How It Works

**Authority hierarchy (8 levels):**

1. `docs/design/spec.md` — canonical root
2. `docs/design/spec/*.md` — 5 canonical child specs
3. `schema/node.schema.json` — canonical field contract
4. `kodebrain/skill/SKILL.md` — agent behavioral contract (derived)
5. `docs/design/implementation-plan-vnext.md` — migration execution order
6. `docs/design/project-history.md` — design rationale (historical)
7. `docs/design/taxonomy.md`, `skills.md`, `agents.md`, `workflows.md` — historical input, superseded
8. `docs/design/open-decisions.md` — resolved decision records

**When introducing a new concept:**
1. Locate the canonical owner in the spec tree
2. Modify that section — do not create a competing document
3. If no owner exists, add one canonical child and link it from the root
4. Record rationale in a Decision, not a parallel spec

**Routing framework:**

| Question pattern | Owner |
|---|---|
| What does X *mean*? | Knowledge |
| What is the *shape/structure* of X? | Project |
| What *process* creates/modifies X? | Workflow |
| What *temporal record* does X produce? | History |
| What *rule* constrains X? | Governance |
| What is the *machine form* of X? | Schema (derived) |

## Where It Appears

Used by:
- [[kb-governance-precedence|Precedence]] — spec authority drives the precedence hierarchy
- [[kb-workflow-onboard|Onboard]] — onboarding creates pages under the correct spec owner
- All domain specs — each domain's spec declares what it owns

## Common Misunderstanding

**Spec authority does not mean "specs never change."** It means changes happen at the canonical owner, not in competing documents. A spec can be modified — but the modification replaces the old truth, it does not create a parallel truth.

**Schema is derived, not independent.** `schema/node.schema.json` is a machine contract derived from all five specs. It does not define semantics independently — if schema and spec disagree, spec wins.

## Source Evidence

- `docs/design/spec/governance.md` — "Specification Authority" section with hierarchy
- `docs/design/spec.md` — "Specification Authority" section with artifact class separation

## Status Notes

Current design. The vNext spec tree (root + 5 children) implements this authority model.

## Open Questions

None.
