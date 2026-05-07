# Open Decisions

Architectural decisions that have not been finalized. Each item has a status, the options being considered, and the constraint that makes it hard to resolve.

Decisions here are unresolved. Resolved decisions live as `decision` nodes in the KB itself.

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

**Status:** Open

**Question:** Should confidence automatically degrade if source files change but a node is not re-reviewed?

**Option A: No automatic degradation**
- Simple
- Problem: nodes accumulate stale confidence without anyone noticing

**Option B: Time-based degradation**
- After N days without a scan, `source_supported` → `stale`
- Problem: a stable, unchanged file should not degrade just because time passed

**Option C: Change-triggered degradation**
- When `/brain-scan` or git diff detects a changed file, nodes that reference that file are flagged as `stale`
- No time-based decay; only triggered by actual changes

**Constraint:** KB nodes track `lastUpdated`. Git diffs provide the change signal. This decision is really about when the file-index to node-staleness mapping runs.

**Leaning toward:** Option C — change-triggered via file-index, not time-based.

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

**Status:** Open

**Question:** Should KB pages be freeform Markdown or strictly validated against the template in the spec (§12)?

**Option A: Freeform Markdown**
- Easy for humans to write
- Problem: agents cannot reliably parse pages to extract structured data

**Option B: Frontmatter + required sections**
- YAML frontmatter for machine-readable fields
- Markdown sections (`## Short Summary`, `## How It Works`, etc.) for human content
- Agent reads frontmatter; human reads Markdown
- Problem: sections may be missing or inconsistently named

**Option C: Frontmatter only (all structured)**
- Entire page is YAML/JSON
- Fully machine-readable
- Problem: violates the spec's principle that pages must be human-readable

**Constraint:** Spec §7.4 says "Markdown alone is too loose for agents. JSON alone is too dry for humans. Both are needed."

**Leaning toward:** Option B — YAML frontmatter for machine fields, required Markdown sections validated by a linter (review_claims skill checks for missing sections).

---

## OD-009 — Edge Directionality and Inverse Edges

**Status:** Open

**Question:** Should both directions of a relationship be stored explicitly (e.g., `A uses B` and `B used_by A`), or only one direction with inverse computed at query time?

**Option A: Store only canonical direction**
- Canonical: `A uses B` (never `B used_by A`)
- Inverse is computed at query time by reversing the edge
- Simpler graph files; fewer edges to maintain

**Option B: Store both directions**
- `A uses B` stored explicitly
- `B used_by A` also stored, labeled as inverse
- Faster queries (no traversal reversal needed)
- Problem: doubles the edge count; sync risk if one direction is updated but not the other

**Leaning toward:** Option A — store canonical direction only. Query engine computes inverses. If traversal performance becomes a problem, add a derived inverse index.

---

## OD-010 — Handling of Dynamically Referenced Code

**Status:** Open

**Question:** How should the builder handle code that is referenced dynamically (e.g., loaded by string name, dependency injection, `require(variable)`, plugin systems)?

**Option A: Ignore dynamic references**
- Only track statically resolvable imports
- Problem: large portions of some systems are dynamically wired; the graph will miss them

**Option B: Flag as `inferred` with a note**
- Detect dynamic patterns (e.g., `require()` with a variable, DI containers, plugin loaders)
- Create an edge with `confidence: inferred` and a note: "dynamic reference detected — manual verification required"
- Problem: many false positives in framework-heavy codebases

**Option C: Surface in `unmapped-files.md` with a dynamic-reference annotation**
- Files that are never statically imported get flagged
- Agent notes which of those files match dynamic patterns
- Problem: not all unmapped files are dynamically referenced

**Leaning toward:** Option B — detect and annotate dynamic patterns with `inferred` confidence rather than silently missing them. Better a low-confidence edge than no edge.
