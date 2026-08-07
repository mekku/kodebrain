---
type: report
project: kodebrain
confidence: supported
provenance: generated
last_updated: "2026-08-07"
---

# Drift Report

Derived from `graph/validation-result.json`.

## Active Drift Items

### DRF-INT-001: kb-workflow-onboard — intended vs observed flattened

Node `kb-workflow-onboard` (`knowledge_role: intent`) describes a deterministic 12-step substrate pipeline (harvest → compile → timeline), but Status Notes indicates substrate scripts are not yet integrated and default path is LLM-driven. The page presents intended architecture as current runtime.

**Source:** `domains/kb-workflow/capabilities/kb-workflow-onboard.md`
**Validation rule:** `intent-observed-mismatch`

### DRF-INT-002: kb-workflow-change-reconciliation — intended vs observed flattened

Node `kb-workflow-change-reconciliation` (`knowledge_role: intent`) describes reconciliation steps referencing substrate scripts, but the reconciliation flow is not yet automated.

**Source:** `domains/kb-workflow/capabilities/kb-workflow-change-reconciliation.md`
**Validation rule:** `intent-observed-mismatch`

### DRF-INT-003: kb-workflow-onboard-flow — deterministic step table with progress disclaimer

Node `kb-workflow-onboard-flow` (`knowledge_role: intent`) contains a full 12-step deterministic flow table, but Status Notes says the substrate integration is still in progress (vNext implementation). Intended flow presented as current flow.

**Source:** `domains/kb-workflow/flows/kb-workflow-onboard-flow.md`
**Validation rule:** `intent-observed-mismatch`

### DRF-INT-004: kb-workflow-change-reconciliation-flow — deterministic step table with progress disclaimer

Node `kb-workflow-change-reconciliation-flow` (`knowledge_role: intent`) contains a full 11-step reconciliation flow table, but the reconciliation process is partially manual.

**Source:** `domains/kb-workflow/flows/kb-workflow-change-reconciliation-flow.md`
**Validation rule:** `intent-observed-mismatch`

## Resolution

These drift items are genuine — substrate integration is tracked in `docs/design/implementation-plan-vnext.md`. The KB pages should be changed to `knowledge_role: mixed` to acknowledge that they describe intended design, not current runtime. Resolution deferred to vNext substrate integration.

## Resolved Drift Items

None yet.

## How Drift Is Detected

Drift is surfaced during:
- Onboard validation gate (`validate.py`) — deterministic checks after `compile_graph`
- `/kodebrain scan` — re-scan may surface stale claims
- Change reconciliation — comparing intended change vs implementation
- `/kodebrain review` — checking KB pages against current source

When drift is found, a new item is appended to this report. The relevant KB node is marked `confidence: stale`. Neither side is silently overwritten.
