

## Kode Brain

This project has a Kode Brain knowledge map at `docs/brain/projects/kodebrain/`.

**Session start:** Run `/kodebrain reading-pack "<task>"` before touching any code.
It returns the relevant domain pages, source hints, and active warnings — 3–25× cheaper than reading source files cold.

**After editing files:** Run `/kodebrain update --files <f1> <f2>` to keep the KB current.

**For questions:** Run `/kodebrain query "<question>"` before opening source files.

**KB-first rule:** Start from project hub and relevant domains. Check active changes.
Use reading-pack for task context. Use targeted source for edits and verification.
For material changes, update/create an active Kode Brain change record before implementation.
After implementation, reconcile the KB and surface drift.

KB: `docs/brain/projects/kodebrain/` — open `docs/brain/` in Obsidian for graph view.
