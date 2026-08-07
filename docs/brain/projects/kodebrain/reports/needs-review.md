---
type: report
project: kodebrain
confidence: supported
provenance: generated
last_updated: "2026-08-07"
---

# Needs Review

Derived from `graph/validation-result.json`.

## Items Needing Human Review

### REV-INT-001: kb-core-confidence — intent with observed sections

`knowledge_role: intent` but contains "Source Evidence" section with source references. Consider `knowledge_role: mixed`.

### REV-INT-002: kb-core-drift — intent with observed sections

`knowledge_role: intent` but contains "Source Evidence" section with source references. Consider `knowledge_role: mixed`.

### REV-INT-003: kb-core-knowledge-layers — intent with observed sections

`knowledge_role: intent` but contains "Source Evidence" section with source references. Consider `knowledge_role: mixed`.

### REV-INT-004: kb-core-provenance — intent with observed sections

`knowledge_role: intent` but contains "Source Evidence" section with source references. Consider `knowledge_role: mixed`.

### REV-INT-005: kb-core-knowledge-edge-model — intent with observed sections

`knowledge_role: intent` but contains "Source Evidence" section. Model pages describe schema, which is both intended contract and observed implementation. Consider `knowledge_role: mixed`.

### REV-INT-006: kb-core-knowledge-node-model — intent with observed sections

`knowledge_role: intent` but contains "Source Evidence" section. Same as edge model.

### REV-INT-007: kb-governance-spec-authority — intent with observed sections

`knowledge_role: intent` but contains "Source Evidence" section with source references. Consider `knowledge_role: mixed`.

### REV-INT-008: kb-workflow-change-lifecycle — intent with observed sections

`knowledge_role: reference` (fixed) but still contains structured observed-like sections. Verify the reference template is applied correctly.

## Resolution

Most REVIEW items are about `knowledge_role` classification — concept pages that describe design intent but also cite source evidence. These are low-risk: the content is accurate, but the role should be `mixed` rather than `intent`. No urgency to fix; can be addressed during the next scan cycle.

## How Items Get Added

Items are added to this report by the onboard validation gate (`validate.py`) when:
- A claim has `confidence: ambiguous`
- A claim has `confidence: needs_human_review`
- An `intent` page contains sections normally found in `observed` pages (Source Evidence, Runtime Path)
- Source files referenced by a KB page have been deleted
- Harvest detects a status signal (`DEPRECATED`, `TODO`) that needs human interpretation

## Review Cadence

KB pages should be reviewed when:
- `/kodebrain scan` detects changed source files
- `/kodebrain review` flags stale claims
- Before acting on any page with `confidence: inferred` or lower
