"""
Write/remove Kode Brain agent instruction blocks in platform config files.

Each platform gets a tagged block:
  <!-- kodebrain:start -->
  ...instructions...
  <!-- kodebrain:end -->

The block is idempotent — install twice, update safely. Uninstall removes it cleanly.
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
# Platform definitions
# ---------------------------------------------------------------------------

PLATFORMS = {
    "claude": {
        "file": "CLAUDE.md",
        "label": "Claude Code",
        "create_if_missing": True,
    },
    "cursor": {
        "file": ".cursor/rules/kodebrain.mdc",
        "label": "Cursor",
        "create_if_missing": True,
    },
    "copilot": {
        "file": ".github/copilot-instructions.md",
        "label": "GitHub Copilot",
        "create_if_missing": True,
    },
    "windsurf": {
        "file": ".windsurfrules",
        "label": "Windsurf",
        "create_if_missing": True,
    },
    "cline": {
        "file": ".clinerules",
        "label": "Cline",
        "create_if_missing": True,
    },
}

# ---------------------------------------------------------------------------
# Block content
# ---------------------------------------------------------------------------

def _claude_block(name: str) -> str:
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


def _generic_block(name: str) -> str:
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


def _make_block(platform: str, name: str) -> str:
    if platform == "claude":
        return _claude_block(name)
    return _generic_block(name)


# ---------------------------------------------------------------------------
# KB discovery
# ---------------------------------------------------------------------------

def find_kb_name(root: Path) -> str | None:
    """Return the project name by scanning docs/brain/projects/."""
    projects_dir = root / "docs" / "brain" / "projects"
    if not projects_dir.is_dir():
        return None
    for child in projects_dir.iterdir():
        if child.is_dir() and (child / "graph" / "nodes.json").exists():
            return child.name
    return None


# ---------------------------------------------------------------------------
# Install / uninstall
# ---------------------------------------------------------------------------

def install(root: Path, platforms: list[str]) -> list[str]:
    """Write KB instruction blocks. Returns list of files written."""
    name = find_kb_name(root)
    if name is None:
        raise RuntimeError(
            "No Kode Brain KB found in docs/brain/projects/. "
            "Run /kodebrain init first."
        )

    written: list[str] = []
    for platform in platforms:
        cfg = PLATFORMS[platform]
        target = root / cfg["file"]

        target.parent.mkdir(parents=True, exist_ok=True)

        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        block = _make_block(platform, name)

        if BLOCK_START in existing:
            # Replace existing block
            new_content = _BLOCK_RE.sub("", existing).rstrip("\n") + "\n\n" + block + "\n"
        elif existing.strip():
            # Append to existing file
            new_content = existing.rstrip("\n") + "\n\n" + block + "\n"
        else:
            # New file
            new_content = block + "\n"

        target.write_text(new_content, encoding="utf-8")
        written.append(str(target.relative_to(root)))

    return written


def uninstall(root: Path) -> list[str]:
    """Remove KB blocks from all platform files. Returns list of files changed."""
    changed: list[str] = []
    for cfg in PLATFORMS.values():
        target = root / cfg["file"]
        if not target.exists():
            continue
        original = target.read_text(encoding="utf-8")
        if BLOCK_START not in original:
            continue
        cleaned = _BLOCK_RE.sub("", original).rstrip("\n")
        if cleaned:
            target.write_text(cleaned + "\n", encoding="utf-8")
        else:
            target.unlink()
        changed.append(str(target.relative_to(root)))
    return changed
