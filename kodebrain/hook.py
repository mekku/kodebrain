"""
Git post-commit hook that marks KB-tracked source files as dirty
after each commit, so the next /kodebrain scan knows what changed.

The hook does NOT run the LLM — it only updates file-hashes.json
so scan can detect drift deterministically.
"""

from __future__ import annotations
import os
import re
import stat
import subprocess
from pathlib import Path

HOOK_START = "# kodebrain:start"
HOOK_END = "# kodebrain:end"
HOOK_FILE = ".git/hooks/post-commit"
_HOOK_RE = re.compile(
    r"\n?" + re.escape(HOOK_START) + r".*?" + re.escape(HOOK_END) + r"\n?",
    re.DOTALL,
)

_HOOK_BODY = """\
# kodebrain:start
# Kode Brain — mark changed source files as dirty in file-hashes.json
# Run /kodebrain scan in Claude Code to refresh KB pages after significant changes.
_KB_HASHES=$(ls docs/brain/projects/*/graph/file-hashes.json 2>/dev/null | head -1)
if [ -n "$_KB_HASHES" ]; then
  _CHANGED=$(git diff --name-only HEAD~1 2>/dev/null | grep -E '\\.(ts|tsx|js|jsx|py|go|rs|java|rb|swift|kt)$' | head -30)
  if [ -n "$_CHANGED" ]; then
    python3 -c "
import json, hashlib, sys
from pathlib import Path
hashes_path = Path('$_KB_HASHES')
if not hashes_path.exists():
    sys.exit(0)
hashes = json.loads(hashes_path.read_text())
changed = [f for f in '''$_CHANGED'''.strip().split() if f]
for f in changed:
    p = Path(f)
    if p.exists():
        hashes[f] = hashlib.sha256(p.read_bytes()).hexdigest()
    elif f in hashes:
        del hashes[f]
hashes_path.write_text(json.dumps(hashes, indent=2))
" 2>/dev/null || true
  fi
fi
# kodebrain:end"""


def install(root: Path) -> str:
    hook_path = root / HOOK_FILE
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    existing = hook_path.read_text(encoding="utf-8") if hook_path.exists() else ""

    if HOOK_START in existing:
        new_content = _HOOK_RE.sub("", existing).rstrip("\n") + "\n\n" + _HOOK_BODY + "\n"
    elif existing.strip():
        new_content = existing.rstrip("\n") + "\n\n" + _HOOK_BODY + "\n"
    else:
        new_content = "#!/bin/sh\n\n" + _HOOK_BODY + "\n"

    hook_path.write_text(new_content, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return HOOK_FILE


def uninstall(root: Path) -> bool:
    hook_path = root / HOOK_FILE
    if not hook_path.exists():
        return False
    original = hook_path.read_text(encoding="utf-8")
    if HOOK_START not in original:
        return False
    cleaned = _HOOK_RE.sub("", original).rstrip("\n")
    if cleaned and cleaned.strip() != "#!/bin/sh":
        hook_path.write_text(cleaned + "\n", encoding="utf-8")
    else:
        hook_path.unlink()
    return True


def status(root: Path) -> bool:
    hook_path = root / HOOK_FILE
    if not hook_path.exists():
        return False
    return HOOK_START in hook_path.read_text(encoding="utf-8")
