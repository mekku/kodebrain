---
type: architecture_integrations
project: kodebrain
confidence: supported
provenance: project_document
knowledge_role: mixed
last_updated: "2026-08-07"
---

# External Integrations — Kode Brain

## Integration Philosophy

Kode Brain operates on local files only. It has no runtime network dependencies. External integrations are optional value-adds, not required for operation.

## Integrations

| System | Type | Required? | Purpose |
|---|---|---|---|
| Claude Code | Host platform | Required | Skill execution environment |
| Obsidian | Graph visualization | Optional | Visual knowledge graph browsing |
| Git | Version control | Recommended | SHA-256 change detection, diff-based updates |
| Cursor | IDE | Optional | Agent instruction installation target |
| Windsurf | IDE | Optional | Agent instruction installation target |

## Claude Code Integration

Kode Brain is primarily a **Claude Code skill**. The skill file (`SKILL.md`) is installed to `~/.claude/skills/kodebrain/`. Platform config blocks in `~/.claude/settings.json` register the skill and its hooks.

The skill defines 8 sub-commands: `onboard`, `init`, `scan`, `query`, `reading-pack`, `detect-legacy`, `review`, `update`.

## Obsidian Integration

Kode Brain's `docs/brain/` directory is structured as an Obsidian vault:

- `.obsidian/graph.json` — graph coloring config (node type colors)
- `.obsidian/app.json` — link resolution settings
- Wiki-links (`[[node-id]]`) resolve to Markdown pages
- Frontmatter `tags` drive graph coloring

Obsidian is never required. The graph view is a convenience. All Kode Brain functionality works without it.

## Git Integration

Harvest uses SHA-256 file hashes for change detection. `harvest.py --hashes <file>` compares stored hashes against current files to identify dirty files. This enables incremental scanning — only changed files are re-harvested.

`/kodebrain update --diff` uses `git diff --name-only HEAD` to identify changed files.

## Platform Config Installation

`kodebrain install` writes agent instruction blocks to platform config files:

| Platform | Config File | Block Marker |
|---|---|---|
| Claude Code (global) | `~/.claude/settings.json` | `<!-- KODEBRAIN:START -->` |
| Claude Code (project) | `.claude/settings.json` | `<!-- KODEBRAIN:START -->` |
| Cursor | `.cursorrules` | `<!-- KODEBRAIN:START -->` |
| Windsurf | `.windsurfrules` | `<!-- KODEBRAIN:START -->` |
| Generic | `CLAUDE.md` | `<!-- KODEBRAIN:START -->` |

`kodebrain uninstall` removes these blocks cleanly via `_remove_section()`.

## Source Evidence

- `kodebrain/install.py` — `_claude_project_block`, `_claude_global_block`, `_generic_project_block`, `_generic_global_block`, `_write_section`, `_remove_section`
- `kodebrain/hook.py` — platform detection, install, uninstall
- `kodebrain/cli.py` — CLI commands for install/uninstall
- `kodebrain/skill/SKILL.md` — full skill definition
