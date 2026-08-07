---
status: draft
domain: product
---

# Product Specification

**Status:** DRAFT v0.1 — awaiting user confirmation

## Purpose

A simple counter API.

## Non-Negotiable Principles

- All counters start at 0
- Increment is atomic
- Max value is 999999

## State Machine

```
idle → counting → done
```

## Data Model

Counter:
  id: string
  value: number
