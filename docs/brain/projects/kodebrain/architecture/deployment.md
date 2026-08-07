---
type: architecture_deployment
project: kodebrain
confidence: supported
provenance: source_code
knowledge_role: observed
last_updated: "2026-08-07"
---

# Deployment — Kode Brain

## Distribution

Kode Brain is distributed as a pip package:

```bash
pip install kodebrain
```

The package installs:
1. `kodebrain` CLI entry point (`kodebrain/cli.py` → `main()`)
2. Skill files to `~/.claude/skills/kodebrain/` (via `kodebrain install`)
3. Platform config blocks to Claude Code settings (via `kodebrain install`)

## Environments

| Environment | Purpose |
|---|---|
| Local dev | `pip install -e .` + symlinked skill dir |
| User install | `pip install kodebrain && kodebrain install` |

No staging, no production server. Kode Brain runs entirely on the user's machine.

## Installation Paths

| What | Where |
|---|---|
| Package | pip site-packages |
| SKILL.md | `~/.claude/skills/kodebrain/SKILL.md` |
| Scripts | `~/.claude/skills/kodebrain/scripts/` |
| Claude Code config | `~/.claude/settings.json` (global) or `.claude/settings.json` (project) |
| Cursor config | `.cursorrules` |
| Windsurf config | `.windsurfrules` |

## Platform Support

`kodebrain install` writes agent instructions to platform-specific config files. Supported platforms: Claude Code (global + project), Cursor, Windsurf, and generic markdown include files.

Detection is handled by `kodebrain/hook.py` which checks for known platform markers in existing config files.

## Source Evidence

- `pyproject.toml` — package config, entry point `kodebrain = "kodebrain.cli:main"`
- `kodebrain/cli.py` — `cmd_global_install`, `cmd_global_uninstall`, `cmd_project_install`, `cmd_project_uninstall`
- `kodebrain/install.py` — `install_global`, `uninstall_global`, `install_project`, `uninstall_project`
- `kodebrain/hook.py` — `install`, `uninstall`, `status`
