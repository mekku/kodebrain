---
type: report
project: kodebrain
confidence: supported
provenance: generated
last_updated: "2026-08-07"
---

# Drift Report

Generated during onboard 2026-08-07.

## Active Drift Items

None detected. The KB was onboarded fresh from canonical specs + source harvest — intent and observation are aligned at this point.

## Resolved Drift Items

None yet.

## How Drift Is Detected

Drift is surfaced during:
- `/kodebrain onboard` (brownfield) — comparing existing docs vs source
- `/kodebrain scan` — re-scan may surface stale claims
- Change reconciliation — comparing intended change vs implementation
- `/kodebrain review` — checking KB pages against current source

When drift is found, a new item is appended to this report. The relevant KB node is marked `confidence: stale`. Neither side is silently overwritten.
