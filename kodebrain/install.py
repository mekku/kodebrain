"""
Write/remove Kode Brain agent instruction blocks in platform config files.

Two install modes:
  project-level  kodebrain install .        writes to project root config files
  user-level     kodebrain install          writes to global user config dirs

Each block is tagged for idempotent update and clean removal:
  <!-- kodebrain:start -->
  ...instructions...
  <!-- kodebrain:end -->
"""

from __future__ import annotations
import re
from pathlib import Path

BLOCK_START = "<!-- kodebrain:start -->"
BLOCK_END = "<!-- kodebrain:end -->"
_BLOCK_RE = re.compile(
    r"\n?" + re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END) + r"\n?",
    re.DOTALL,
)

# ---------------------------------------------------------------------------
# Platform definitions — project level
# ---------------------------------------------------------------------------

PROJECT_PLATFORMS = {
    "claude": {
        "file": "CLAUDE.md",
        "label": "Claude Code",
    },
    "cursor": {
        "file": ".cursor/rules/kodebrain.mdc",
        "label": "Cursor",
    },
    "copilot": {
        "file": ".github/copilot-instructions.md",
        "label": "GitHub Copilot",
    },
    "windsurf": {
        "file": ".windsurfrules",
        "label": "Windsurf",
    },
    "cline": {
        "file": ".clinerules",
        "label": "Cline",
    },
}

# User-level global config paths (relative to $HOME).
# Copilot excluded — it has no user-level global config.
USER_PLATFORMS = {
    "claude": {
        "file": ".claude/CLAUDE.md",
        "label": "Claude Code (global)",
    },
    "cursor": {
        "file": ".cursor/rules/kodebrain.mdc",
        "label": "Cursor (global)",
    },
    "windsurf": {
        "file": ".windsurf/rules/kodebrain.mdc",
        "label": "Windsurf (global)",
    },
    "cline": {
        "file": ".clinerules",
        "label": "Cline (global)",
    },
}

# ---------------------------------------------------------------------------
# Block content — project level (project name is known)
# ---------------------------------------------------------------------------

def _project_claude_block(name: str) -> str:
    return f"""{BLOCK_START}
## Kode Brain — Knowledge Base

This project has a structured knowledge map at `docs/brain/projects/{name}/`.

**Session start:** Run `/kodebrain reading-pack "<task>"` before touching any code.
It returns the relevant domain pages, source file hints, and active warnings — 3–25× cheaper than navigating source files cold.

**After editing source files:** Run `/kodebrain update --files <f1> <f2>` to keep the KB current.
Subsequent queries return fresh data, not pre-edit state.

**For questions:** Run `/kodebrain query "<question>"` instead of reading raw source files.

**KB-first rule:** Use KB pages as primary source of truth.
Read source files directly only when making a targeted edit or when a node is `confidence: stale`.

KB location:  `docs/brain/projects/{name}/`
Graph view:   Open `docs/brain/` as an Obsidian vault.
{BLOCK_END}"""


def _project_generic_block(name: str) -> str:
    return f"""{BLOCK_START}
## Kode Brain — Knowledge Base

This project has a structured knowledge map at `docs/brain/projects/{name}/`.

**Before starting any task:**
1. Read `docs/brain/projects/{name}/{name}.md` — project hub with all domains.
2. Read the domain hub(s) for areas you'll touch: `docs/brain/projects/{name}/domains/<domain>/<domain>.md`.
3. Check `docs/brain/projects/{name}/reports/reading-packs/` for a pre-built context pack matching your task.

**KB-first rule:** Use KB pages as primary source of truth.
Read source files directly only for targeted edits or when a page shows `confidence: stale`.

**After editing source files:**
The KB may drift from source. Check `docs/brain/projects/{name}/graph/file-hashes.json`
to identify which files changed. Run `/kodebrain scan` in Claude Code to refresh the KB.

KB location:  `docs/brain/projects/{name}/`
{BLOCK_END}"""


# ---------------------------------------------------------------------------
# Block content — user level (no project name, detects KB dynamically)
# ---------------------------------------------------------------------------

_USER_CLAUDE_BLOCK = f"""{BLOCK_START}
## Kode Brain

If the current project has `docs/brain/projects/`, it has a Kode Brain knowledge map.
Use it before reading source files — it's 3–25× cheaper per query.

**Session start:** Check for `docs/brain/projects/` and run `/kodebrain reading-pack "<task>"`.
**After editing files:** Run `/kodebrain update --files <changed-files>`.
**For questions:** Run `/kodebrain query "<question>"` before opening source files.
**KB-first rule:** Read source files directly only for targeted edits or when a node is `confidence: stale`.
{BLOCK_END}"""

_USER_GENERIC_BLOCK = f"""{BLOCK_START}
## Kode Brain

If the current project has `docs/brain/projects/`, it has a Kode Brain knowledge map.
Use it before reading source files.

**Before starting:** Check for `docs/brain/projects/*/` and read the project hub and relevant domain pages.
**Check for reading packs:** `docs/brain/projects/*/reports/reading-packs/` may have a pre-built context pack.
**KB-first rule:** Use KB pages as primary source of truth before reading source files.
{BLOCK_END}"""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _write_block(target: Path, block: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""

    if BLOCK_START in existing:
        new_content = _BLOCK_RE.sub("", existing).rstrip("\n") + "\n\n" + block + "\n"
    elif existing.strip():
        new_content = existing.rstrip("\n") + "\n\n" + block + "\n"
    else:
        new_content = block + "\n"

    target.write_text(new_content, encoding="utf-8")


def _remove_block(target: Path) -> bool:
    if not target.exists():
        return False
    original = target.read_text(encoding="utf-8")
    if BLOCK_START not in original:
        return False
    cleaned = _BLOCK_RE.sub("", original).rstrip("\n")
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
# Project-level install / uninstall
# ---------------------------------------------------------------------------

def install_project(root: Path, platforms: list[str]) -> list[str]:
    """Write project-specific KB blocks. Returns list of relative paths written."""
    name = find_kb_name(root)
    if name is None:
        raise RuntimeError(
            "No Kode Brain KB found in docs/brain/projects/. "
            "Run /kodebrain init first."
        )

    written: list[str] = []
    for platform in platforms:
        cfg = PROJECT_PLATFORMS[platform]
        target = root / cfg["file"]
        block = _project_claude_block(name) if platform == "claude" else _project_generic_block(name)
        _write_block(target, block)
        written.append(str(target.relative_to(root)))

    return written


def uninstall_project(root: Path) -> list[str]:
    """Remove project KB blocks. Returns list of relative paths changed."""
    changed: list[str] = []
    for cfg in PROJECT_PLATFORMS.values():
        target = root / cfg["file"]
        if _remove_block(target):
            changed.append(str(target.relative_to(root)))
    return changed


# ---------------------------------------------------------------------------
# User-level install / uninstall
# ---------------------------------------------------------------------------

def install_user(platforms: list[str]) -> list[str]:
    """Write user-level KB blocks to global config dirs. Returns list of absolute paths written."""
    home = Path.home()
    written: list[str] = []

    for platform in platforms:
        if platform not in USER_PLATFORMS:
            continue  # e.g. copilot has no user-level config
        cfg = USER_PLATFORMS[platform]
        target = home / cfg["file"]
        block = _USER_CLAUDE_BLOCK if platform == "claude" else _USER_GENERIC_BLOCK
        _write_block(target, block)
        written.append(str(target))

    return written


def uninstall_user() -> list[str]:
    """Remove user-level KB blocks. Returns list of absolute paths changed."""
    home = Path.home()
    changed: list[str] = []
    for cfg in USER_PLATFORMS.values():
        target = home / cfg["file"]
        if _remove_block(target):
            changed.append(str(target))
    return changed
