"""
kodebrain platform install/uninstall.

Two levels:

  Global (skill install) — `kodebrain install`
    Claude Code : copies SKILL.md + scripts/ → ~/.claude/skills/kodebrain/
                  writes ## Kode Brain to ~/.claude/CLAUDE.md
    Cursor      : writes rule → ~/.cursor/rules/kodebrain.mdc
    Windsurf    : writes rule → ~/.windsurf/rules/kodebrain.mdc
    Cline       : writes rule → ~/.clinerules
    Codex CLI   : writes rule → ~/.codex/AGENTS.md
    OpenCode    : writes agent → ~/.config/opencode/agents/kodebrain.md

  Project (config install) — `kodebrain <platform> install [path]`
    Claude Code : writes ## Kode Brain to ./CLAUDE.md
    Cursor      : writes rule to ./.cursor/rules/kodebrain.mdc
    Copilot     : writes rule to ./.github/copilot-instructions.md
    Windsurf    : writes rule to ./.windsurfrules
    Cline       : writes rule to ./.clinerules
    Codex CLI   : writes rule to ./AGENTS.md
    OpenCode    : writes rule to ./opencode-instructions.md
"""

from __future__ import annotations
import re
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Skill bundle path (installed alongside this module)
# ---------------------------------------------------------------------------

SKILL_DIR = Path(__file__).parent / "skill"

# ---------------------------------------------------------------------------
# Section markers — use heading-based markers like graphify (## Kode Brain)
# so the section is human-readable and platform-agnostic.
# ---------------------------------------------------------------------------

_SECTION_HEADER = "## Kode Brain"
_SECTION_RE = re.compile(
    r"\n*" + re.escape(_SECTION_HEADER) + r"[^\n]*\n.*?(?=\n## |\Z)",
    re.DOTALL,
)

# ---------------------------------------------------------------------------
# Block content
# ---------------------------------------------------------------------------

def _claude_project_block(name: str) -> str:
    return f"""{_SECTION_HEADER}

This project has a Kode Brain knowledge map at `docs/brain/projects/{name}/`.

**Session start:** Run `/kodebrain reading-pack "<task>"` before touching any code.
It returns the relevant domain pages, source hints, and active warnings — 3–25× cheaper than reading source files cold.

**After editing files:** Run `/kodebrain update --files <f1> <f2>` to keep the KB current.

**For questions:** Run `/kodebrain query "<question>"` instead of reading raw source files.

**KB-first rule:** Use KB pages as primary source of truth.
Read source files directly only for targeted edits or when a node is `confidence: stale`.

KB: `docs/brain/projects/{name}/` — open `docs/brain/` in Obsidian for graph view."""


def _claude_global_block() -> str:
    return f"""{_SECTION_HEADER}

If the current project has `docs/brain/projects/`, it has a Kode Brain knowledge map.
Use `/kodebrain reading-pack "<task>"` before reading source files — 3–25× cheaper per query.
After editing files, run `/kodebrain update --files <changed>` to keep the KB current.
For questions, run `/kodebrain query "<question>"` before opening source files."""


def _generic_project_block(name: str) -> str:
    return f"""{_SECTION_HEADER}

This project has a Kode Brain knowledge map at `docs/brain/projects/{name}/`.

Before starting: read `docs/brain/projects/{name}/{name}.md` (project hub) and the
relevant domain pages under `docs/brain/projects/{name}/domains/`.
Check `docs/brain/projects/{name}/reports/reading-packs/` for a pre-built context pack.

KB-first rule: use KB pages as primary source of truth before reading source files.
After editing, note that KB may drift — run `/kodebrain scan` in Claude Code to refresh."""


def _generic_global_block() -> str:
    return f"""{_SECTION_HEADER}

If the current project has `docs/brain/projects/`, it has a Kode Brain knowledge map.
Before starting, read the project hub and relevant domain pages in `docs/brain/projects/`.
Check `docs/brain/projects/*/reports/reading-packs/` for pre-built context packs.
KB-first rule: use KB pages as primary source of truth before reading source files."""


# ---------------------------------------------------------------------------
# Shared file helpers
# ---------------------------------------------------------------------------

def _write_section(target: Path, block: str) -> None:
    """Append or replace the ## Kode Brain section in target file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""

    if _SECTION_HEADER in existing:
        new_content = _SECTION_RE.sub("", existing).rstrip("\n") + "\n\n" + block + "\n"
    elif existing.strip():
        new_content = existing.rstrip("\n") + "\n\n" + block + "\n"
    else:
        new_content = block + "\n"

    target.write_text(new_content, encoding="utf-8")


def _remove_section(target: Path) -> bool:
    """Remove the ## Kode Brain section. Returns True if anything changed."""
    if not target.exists():
        return False
    original = target.read_text(encoding="utf-8")
    if _SECTION_HEADER not in original:
        return False
    cleaned = _SECTION_RE.sub("", original).rstrip("\n")
    if cleaned:
        target.write_text(cleaned + "\n", encoding="utf-8")
    else:
        target.unlink()
    return True


# ---------------------------------------------------------------------------
# KB discovery
# ---------------------------------------------------------------------------

def find_kb_name(root: Path) -> str | None:
    """Return the project name by scanning docs/brain/projects/."""
    projects_dir = root / "docs" / "brain" / "projects"
    if not projects_dir.is_dir():
        return None
    for child in sorted(projects_dir.iterdir()):
        if child.is_dir() and (child / "graph" / "nodes.json").exists():
            return child.name
    return None


# ---------------------------------------------------------------------------
# Global skill install — copies SKILL.md + scripts to platform dirs
# ---------------------------------------------------------------------------

def install_global(platforms: list[str]) -> list[tuple[str, str]]:
    """
    Install skill/rules globally for each platform.
    Returns list of (description, path) tuples.
    """
    home = Path.home()
    results: list[tuple[str, str]] = []

    for platform in platforms:
        if platform == "claude":
            # Copy skill bundle to ~/.claude/skills/kodebrain/
            dest = home / ".claude" / "skills" / "kodebrain"
            if dest.is_symlink():
                dest.unlink()
            elif dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(SKILL_DIR, dest)
            results.append(("skill installed", str(dest)))

            # Write global instructions to ~/.claude/CLAUDE.md
            global_md = home / ".claude" / "CLAUDE.md"
            _write_section(global_md, _claude_global_block())
            results.append(("global config", str(global_md)))

        elif platform == "cursor":
            target = home / ".cursor" / "rules" / "kodebrain.mdc"
            _write_section(target, _generic_global_block())
            results.append(("global rule", str(target)))

        elif platform == "windsurf":
            target = home / ".windsurf" / "rules" / "kodebrain.mdc"
            _write_section(target, _generic_global_block())
            results.append(("global rule", str(target)))

        elif platform == "cline":
            target = home / ".clinerules"
            _write_section(target, _generic_global_block())
            results.append(("global rule", str(target)))

        elif platform == "codex":
            target = home / ".codex" / "AGENTS.md"
            _write_section(target, _generic_global_block())
            results.append(("global rule", str(target)))

        elif platform == "opencode":
            target = home / ".config" / "opencode" / "agents" / "kodebrain.md"
            _write_section(target, _generic_global_block())
            results.append(("global agent", str(target)))

    return results


def uninstall_global(platforms: list[str]) -> list[str]:
    """Remove global skill/rules. Returns list of paths changed."""
    home = Path.home()
    changed: list[str] = []

    for platform in platforms:
        if platform == "claude":
            skill_dir = home / ".claude" / "skills" / "kodebrain"
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
                changed.append(str(skill_dir))
            global_md = home / ".claude" / "CLAUDE.md"
            if _remove_section(global_md):
                changed.append(str(global_md))

        elif platform == "cursor":
            if _remove_section(home / ".cursor" / "rules" / "kodebrain.mdc"):
                changed.append(str(home / ".cursor" / "rules" / "kodebrain.mdc"))

        elif platform == "windsurf":
            if _remove_section(home / ".windsurf" / "rules" / "kodebrain.mdc"):
                changed.append(str(home / ".windsurf" / "rules" / "kodebrain.mdc"))

        elif platform == "cline":
            if _remove_section(home / ".clinerules"):
                changed.append(str(home / ".clinerules"))

        elif platform == "codex":
            if _remove_section(home / ".codex" / "AGENTS.md"):
                changed.append(str(home / ".codex" / "AGENTS.md"))

        elif platform == "opencode":
            if _remove_section(home / ".config" / "opencode" / "agents" / "kodebrain.md"):
                changed.append(str(home / ".config" / "opencode" / "agents" / "kodebrain.md"))

    return changed


# ---------------------------------------------------------------------------
# Project config install — writes platform section to project config files
# ---------------------------------------------------------------------------

_PROJECT_CONFIGS = {
    "claude":    ("CLAUDE.md",                        _claude_project_block),
    "cursor":    (".cursor/rules/kodebrain.mdc",      _generic_project_block),
    "copilot":   (".github/copilot-instructions.md",  _generic_project_block),
    "windsurf":  (".windsurfrules",                   _generic_project_block),
    "cline":     (".clinerules",                      _generic_project_block),
    "codex":     ("AGENTS.md",                        _generic_project_block),
    "opencode":  ("opencode-instructions.md",         _generic_project_block),
}

_OPENCODE_NOTE = (
    "Add to opencode.jsonc:\n"
    '  "instructions": ["opencode-instructions.md"]'
)


def install_project(root: Path, platform: str) -> tuple[str, str | None]:
    """
    Write project-level KB config for one platform.
    Returns (relative_path, optional_note).
    """
    name = find_kb_name(root)
    if name is None:
        raise RuntimeError(
            "No Kode Brain KB found in docs/brain/projects/. "
            "Run /kodebrain init first."
        )

    rel_path, block_fn = _PROJECT_CONFIGS[platform]
    target = root / rel_path
    _write_section(target, block_fn(name))
    note = _OPENCODE_NOTE if platform == "opencode" else None
    return str(target.relative_to(root)), note


def uninstall_project(root: Path, platform: str) -> str | None:
    """Remove project-level KB config for one platform. Returns path if changed."""
    if platform not in _PROJECT_CONFIGS:
        return None
    rel_path, _ = _PROJECT_CONFIGS[platform]
    target = root / rel_path
    return str(target.relative_to(root)) if _remove_section(target) else None
