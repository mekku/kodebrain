---
type: architecture_overview
project: kodebrain
confidence: supported
provenance: project_document
knowledge_role: intent
last_updated: "2026-08-07"
---

# Architecture Overview — Kode Brain

## System Context

Kode Brain is a CLI tool + Claude Code skill that converts any software project into a living knowledge map. It operates on local files only — no server, no database, no network dependency at runtime. Users interact via the `/kodebrain` slash command in Claude Code or via the `kodebrain` CLI for installation. The primary consumers are human developers and AI coding agents.

```text
┌──────────────────────┐
│   Human Developer    │
│   + AI Coding Agent  │
└──────────┬───────────┘
           │ /kodebrain commands (Claude Code skill)
           ▼
┌──────────────────────┐
│     Kode Brain       │
│                      │
│  SKILL.md (agent)    │──── reads/writes ────▶ docs/brain/ (Markdown KB)
│  harvest.py          │──── scans ──────────▶ project source files
│  compile_graph.py    │──── compiles ───────▶ graph/*.json
│  timeline.py         │──── generates ──────▶ history/*
│  kodebrain CLI       │──── installs ───────▶ platform configs
└──────────────────────┘
           │
           │ Optional: Obsidian for graph visualization
           ▼
    ┌──────────────┐
    │   Obsidian   │ (external, not required)
    └──────────────┘
```

## Applications & Services

| Component | Type | Role | Runtime |
|---|---|---|---|
| `/kodebrain` skill | Skill | Agent behavior definition for Claude Code | Claude Code session |
| `harvest.py` | Script | Deterministic source extraction (exports, routes, imports, status signals) | Python 3.9+ |
| `compile_graph.py` | Script | Markdown → graph JSON compiler (nodes.json, edges.json, file-index.json) | Python 3.9+ |
| `timeline.py` | Script | History timeline + events.json generation | Python 3.9+ |
| `project_state.py` | Script | Project state classifier + gap map | Python 3.9+ |
| `project_inventory.py` | Script | File inventory + topology | Python 3.9+ |
| `migrate_kb.py` | Script | Legacy KB format migration | Python 3.9+ |
| `spec_validator.py` | Script | Validate KB against schema | Python 3.9+ |
| `frontmatter.py` | Script | YAML frontmatter parser | Python 3.9+ |
| `kodebrain` CLI | CLI | Install/uninstall skill + platform configs | Python 3.9+ |

## Boundaries

### Internal Boundaries

- **Skill ⇄ Scripts:** SKILL.md defines agent behavior; scripts provide deterministic substrate. Scripts are called by the agent during skill execution, not by end users directly.
- **Markdown ⇄ JSON:** Markdown knowledge pages are canonical; graph JSON (nodes.json, edges.json) is derived and rebuildable.
- **Spec ⇄ Implementation:** `docs/design/spec.md` (root) + 5 child specs define intent; `kodebrain/skill/` implements it. Drift between them is surfaced, never silently resolved.

### External Boundaries

- **Claude Code:** Kode Brain skill runs inside Claude Code sessions. No other runtime dependency.
- **Obsidian:** Optional graph visualization. Kode Brain generates Obsidian-compatible vault structure but does not require Obsidian.
- **pip:** Distribution channel. `pip install kodebrain` makes the CLI + skill available.

## Communication Paths

| From | To | Protocol | Purpose |
|---|---|---|---|
| Claude Code session | `/kodebrain` skill | Skill invocation | User triggers onboard/scan/query/etc. |
| SKILL.md agent | harvest.py | Subprocess (Python) | Extract source evidence |
| SKILL.md agent | compile_graph.py | Subprocess (Python) | Compile graph indexes |
| SKILL.md agent | Markdown files | File read/write | Read/write KB pages |
| `kodebrain` CLI | Platform config files | File write | Install agent instructions |

## Domain Placement

```text
kb-core        — knowledge meaning: layers, truth model, provenance, confidence, drift, harvest
kb-project     — knowledge shape: project structure, layout, hub, architecture, domains, naming, IDs
kb-workflow    — processes: onboarding, change lifecycle, status/lifecycle separation, agent behavior
kb-history     — temporal records: decisions, incidents, milestones, timeline, events, retrieval
kb-governance  — rules: precedence, compatibility, non-goals, success criteria, spec authority
kb-substrate   — deterministic scripts: harvest, compile, inventory, migrate, timeline
```

All domains are implemented in the same repository. No domain has its own deployable.

## See Also

- [[kodebrain|Project Hub]] — START HERE
- [[architecture-technology|Technology Stack]]
- [[architecture-runtime|Runtime Topology]]
- [[architecture-data|Data Architecture]]
- [[architecture-deployment|Deployment]]
- [[architecture-integrations|External Integrations]]
