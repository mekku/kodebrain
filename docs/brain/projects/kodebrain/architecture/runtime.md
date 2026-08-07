---
type: architecture_runtime
project: kodebrain
confidence: supported
provenance: source_code
knowledge_role: observed
last_updated: "2026-08-07"
---

# Runtime Topology — Kode Brain

## Processes

Kode Brain has no persistent processes. All execution is request-driven:

| Process | Type | Trigger | Lifetime |
|---|---|---|---|
| Claude Code session | Host | User invokes `/kodebrain` | Session duration |
| `harvest.py` | Subprocess | Agent calls harvest during onboard/scan/update | Single invocation |
| `compile_graph.py` | Subprocess | Agent calls compile after page writes | Single invocation |
| `timeline.py` | Subprocess | Agent calls timeline for history generation | Single invocation |
| `project_state.py` | Subprocess | Agent calls during onboard | Single invocation |
| `project_inventory.py` | Subprocess | Agent calls during onboard | Single invocation |
| `migrate_kb.py` | Subprocess | Agent calls when legacy KB format detected | Single invocation |
| `kodebrain` CLI | CLI process | User runs `kodebrain install` | Single invocation |

## Runtime Boundaries

```text
┌─────────────────────────────────────────┐
│         Claude Code Session              │
│                                          │
│  /kodebrain skill (SKILL.md)            │
│       │                                  │
│       │ subprocess (Python)              │
│       ▼                                  │
│  ┌─────────────────────────────────┐    │
│  │  kodebrain/skill/scripts/       │    │
│  │  harvest.py                     │    │
│  │  compile_graph.py               │    │
│  │  timeline.py                    │    │
│  │  project_state.py               │    │
│  │  project_inventory.py           │    │
│  │  migrate_kb.py                  │    │
│  │  spec_validator.py              │    │
│  │  frontmatter.py                 │    │
│  └─────────────────────────────────┘    │
│                                          │
│  File I/O: docs/brain/ (Markdown, JSON) │
│  Source scanning: project source files   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Terminal (user-driven)           │
│                                          │
│  kodebrain install                       │
│  kodebrain uninstall                     │
│  kodebrain project install .             │
│  kodebrain project uninstall .           │
└─────────────────────────────────────────┘
```

## Entry Points Summary

| Entry Point | Type | Invocation |
|---|---|---|
| `/kodebrain onboard` | Skill command | User in Claude Code |
| `/kodebrain scan` | Skill command | User in Claude Code |
| `/kodebrain query` | Skill command | User in Claude Code |
| `/kodebrain reading-pack` | Skill command | User in Claude Code |
| `/kodebrain update` | Skill command | User in Claude Code |
| `/kodebrain detect-legacy` | Skill command | User in Claude Code |
| `/kodebrain review` | Skill command | User in Claude Code |
| `kodebrain install` | CLI | Terminal |
| `python3 harvest.py <root>` | Script (direct) | Agent internal only |

## Source Evidence

- `kodebrain/cli.py` — `main()` entry point for CLI
- `kodebrain/skill/SKILL.md` — skill definition with all sub-commands
- `kodebrain/skill/scripts/harvest.py` — harvest script with `__main__` block
- `kodebrain/skill/scripts/compile_graph.py` — `main()` function
