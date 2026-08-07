---
type: report
project: kodebrain
confidence: supported
provenance: generated
last_updated: "2026-08-07"
---

# Suspected Legacy

Generated during onboard 2026-08-07.

## Suspected Unused

Harvest classified the following as `suspected_unused` — no other file imports them:

| File | Signals |
|---|---|
| `kodebrain/__init__.py` | Empty init; no imports from other files |
| `kodebrain/hook.py` | `install`, `uninstall`, `status` exports; no `imported_by` detected |
| `kodebrain/install.py` | Multiple exports; no `imported_by` detected (likely called via CLI, not import) |
| `kodebrain/skill/scripts/compile_graph.py` | `compile_graph`, `main`; no `imported_by` (called as subprocess) |
| `kodebrain/skill/scripts/frontmatter.py` | `_parse_yaml_list`; no `imported_by` (utility, imported by compile_graph) |
| `kodebrain/skill/scripts/migrate_kb.py` | No `imported_by` (called as subprocess) |
| `kodebrain/skill/scripts/project_inventory.py` | No `imported_by` (called as subprocess) |
| `kodebrain/skill/scripts/project_state.py` | No `imported_by` (called as subprocess) |
| `kodebrain/skill/scripts/spec_validator.py` | No `imported_by` (called as subprocess) |

## Analysis

Most `suspected_unused` classifications are false positives: substrate scripts are called as **subprocesses** (via `python3 script.py`), not as Python imports. The harvest importer cannot detect subprocess calls.

`kodebrain/install.py` is called from `kodebrain/cli.py` but harvest may not have resolved the import chain fully.

`kodebrain/hook.py` is called by the CLI or by Claude Code's hook system, not by Python import.

## Action

No action required. All files are in active use via subprocess or CLI invocation. The `suspected_unused` classification is a harvest limitation, not an actual legacy signal.

## Historical Design Docs

The following design docs are superseded historical input, not current specs:

| File | Status | Superseded By |
|---|---|---|
| `docs/design/taxonomy.md` | Historical | `spec/knowledge-model.md`, `spec/project-model.md` |
| `docs/design/skills.md` | Historical | `spec/workflow-model.md` |
| `docs/design/agents.md` | Historical | `spec/workflow-model.md` |
| `docs/design/workflows.md` | Historical | `spec/workflow-model.md` |
| `docs/design/project-history.md` | Historical | `spec/history-model.md` |

These are preserved for design rationale but are not canonical specifications.
