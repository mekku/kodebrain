# Open Decisions

> **Superseded in part by `docs/design/spec.md`.** vNext has resolved several items below.
> See individual OD items for current status.

Architectural decisions. Resolved decisions live as `decision` nodes in the KB itself.

---

## OD-001 — Node ID Stability vs. Readability

**Status:** Resolved — 2026-05-07

**Decision:** Hierarchical human-readable slugs. Renames just rename — update the ID in nodes.json and all referencing edges in edges.json. No backward-compatibility edges, no frozen IDs.

**Rationale:** Simplicity over stability. A rename is an explicit operation; the tool handles the file and edge update as part of the rename action. No hidden legacy IDs accumulating in the graph.

---

## OD-002 — Storage Backend

**Status:** Open

**Question:** Should the knowledge base be stored as flat Markdown + JSON files, or in a queryable database?

**Option A: Flat files** (current design)
- Human-readable, version-controlled with git
- No infrastructure required
- Problem: graph traversal at query time is O(N) scan of nodes.json; slow at scale

**Option B: SQLite with FTS**
- Local, file-based, queryable
- Fast traversal and full-text search
- Problem: not human-readable without tooling; requires migration if schema changes

**Option C: Dual** — canonical files + derived SQLite index
- Source of truth: Markdown + JSON files
- Fast query: SQLite rebuilt from files on demand
- Problem: must keep both in sync; adds implementation complexity

**Constraint:** The spec explicitly values human-readable output. A pure database would violate this.

**Status:** Resolved — 2026-05-07

**Decision:** Flat files only. Markdown pages + JSON graph files (nodes.json, edges.json, file-index.json). No database layer. Graph traversal is done by loading JSON into memory at query time.

---

## OD-003 — Multi-Project Cross-References

**Status:** Open

**Question:** Can a node in Project A reference (via an edge) a node in Project B?

**Option A: No cross-project edges**
- Projects are isolated knowledge graphs
- Simple graph model; no namespace collision
- Problem: real systems often depend on shared libraries or microservices across repos

**Option B: Cross-project edges with explicit namespace**
- Edge `from` or `to` uses `project:domain/slug` format
- Problem: requires resolving the foreign project's knowledge base at query time

**Option C: Cross-project references as unresolved stubs**
- A node can reference an external entity, but it is represented as a `stub` node with `confidence: needs_human_review`
- Stubs are not traversed during queries until manually linked

**Constraint:** The file structure puts each project under its own directory. A single file-index cannot span projects without a global index.

**Leaning toward:** Option C (stubs), as it keeps each project graph self-contained while acknowledging external dependencies.

---

## OD-004 — Automated vs. Assisted Generation

**Status:** Resolved — 2026-05-07

**Decision:** Confidence-tiered writes.
- `source_supported` → write draft immediately
- `inferred` → write with `<!-- draft: inferred — not reviewed -->` banner
- `ambiguous` → report only (needs-review.md), write only with `--include-ambiguous` flag
- `needs_human_review` → report only, never written as a page automatically

---

## OD-005 — Confidence Degradation Over Time

**Status:** Resolved — 2026-08-07 (by vNext spec)

**Decision:** Change-triggered degradation (Option C). Nodes referencing changed files drop to `stale`. No time-based decay. vNext adds provenance/confidence separation — a `stale` confidence marker is separate from provenance, so the source of the claim is preserved even when the claim is stale.

---

## OD-006 — Conflict Resolution Between Agents

**Status:** Open

**Question:** If two agents produce contradictory assessments of the same node (e.g., Builder says `active`, Reviewer says `legacy`), what wins?

**Option A: Last write wins**
- Simple
- Problem: an automated agent can silently overwrite a human-reviewed node

**Option B: Confidence hierarchy**
- Higher confidence wins. `verified` > `source_supported` > `inferred`
- Problem: two agents may both claim `source_supported` with different evidence

**Option C: Conflict is surfaced, not resolved**
- When a write conflicts with an existing node, write a conflict marker and add to needs-review.md
- Human resolves
- Problem: accumulates unresolved conflicts if humans don't review

**Constraint:** The spec states humans verify meaning. Agents should not silently overwrite.

**Leaning toward:** Option C — conflicts surface to needs-review.md. Automated agents may never overwrite a `verified` node without human sign-off.

---

## OD-007 — Claude Code Plugin vs. Standalone CLI

**Status:** Resolved — 2026-05-07

**Decision:** Claude Code plugin for MVP. SKILL.md + slash commands. Claude is the inference engine; Bash/Read/Write/Edit are the I/O tools. CLI and MCP server are post-MVP.

---

## OD-008 — Page Template Enforcement

**Status:** Resolved — 2026-08-07 (by vNext spec)

**Decision:** Frontmatter + required sections (Option B). YAML frontmatter for machine-readable fields, Markdown sections for human content. vNext templates define canonical section structure. Markdown-first: knowledge is authored in Markdown; graph JSON is compiled from it.

---

## OD-009 — Edge Directionality and Inverse Edges

**Status:** Resolved — 2026-08-07 (by vNext spec)

**Decision:** Store canonical direction only (Option A). Inverses computed at query time. `replaces`/`replaced_by` are the only mirrored pair — store one direction; the inverse is computed.

---

## OD-010 — Handling of Dynamically Referenced Code

**Status:** Resolved — 2026-08-07 (by vNext spec)

**Decision:** Flag as `inferred` with annotation (Option B). Dynamic patterns get `confidence: inferred` edges with notes. vNext source-reading escalation allows targeted LLM source inspection when harvest cannot resolve dynamic wiring. Not all unmapped files are errors — some are dynamically wired and surfaced as such.
