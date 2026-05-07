---
name: kodebrain
description: "Kode Brain — living knowledge system for evolving codebases. Converts a project into a structured knowledge map: domains, capabilities, flows, concepts, legacy areas, and source evidence. Use when user asks questions about a codebase via /kodebrain."
trigger: /kodebrain
---

# /kodebrain

Convert any codebase into a living knowledge map — domains, capabilities, flows, concepts, legacy areas, and source evidence — so humans and AI agents can understand and modify it without rediscovering everything from scratch.

## Usage

```
/kodebrain init [path]                     # first-time scan → scaffold docs/brain/ and write knowledge map
/kodebrain scan [path]                     # re-scan, update changed nodes, flag stale pages
/kodebrain query "<task or symptom>"       # answer a question using the knowledge base
/kodebrain reading-pack "<task>"           # generate + save a context pack for a task
/kodebrain detect-legacy [--domain slug]   # surface suspected dead, duplicate, or migrated code
/kodebrain review [--page path]            # check whether KB pages match current source
/kodebrain update [--diff] [--files f1 f2] # update KB pages from recent code changes
/kodebrain install [path] [--platform all|claude|cursor|copilot|windsurf|cline]
                                           # write agent instructions to platform config files
/kodebrain uninstall [path]               # remove all kodebrain blocks from platform config files
```

## What /kodebrain is for

Point `/kodebrain` at any software project to get a structured, navigable knowledge map. Persistent across sessions. Honest confidence labels (source_supported / inferred / needs_human_review). Built for projects that grew organically — not perfect systems.

---

## What You Must Do When Invoked

Parse the sub-command from the argument. If no sub-command is given, print the usage block above and stop.

If no path is given for `init` or `scan`, use `.` (current working directory).

Follow the steps for each sub-command below. Do not skip steps.

---

## Knowledge Base Location

All knowledge lives under `docs/brain/` in the target project. The KB doubles as an **Obsidian vault** — open `docs/brain/` as a vault and you get a live graph view of the entire codebase knowledge map.

```
docs/brain/projects/<name>/
  <name>.md                     ← project hub (links to all domains)
  domains/<domain>/
    <domain>.md                 ← domain hub (NOT overview.md — filename = domain slug)
    capabilities/<cap-slug>.md
    flows/<flow-slug>.md
    concepts/<concept-slug>.md
    models/<model-slug>.md
    apis/<api-slug>.md
    decisions/<YYYY-MM-DD>-<slug>.md
    risks/<risk-slug>.md
  graph/
    nodes.json
    edges.json
    file-index.json
    file-hashes.json          ← SHA256 per source file; drives hash-based update detection
  reports/
    unmapped-files.md
    suspected-legacy.md
    stale-docs.md
    needs-review.md
    reading-packs/
  .obsidian/
    graph.json                  ← graph coloring config (copy from kb-builder/obsidian-vault-config/)
    app.json                    ← link resolution: "shortest unambiguous path"
```

**Domain file naming:** domain hub file is `<domain-slug>.md` (not `overview.md`). This makes `[[auth]]` resolve directly to the auth domain hub in Obsidian.

**Node ID = file slug:** a node with `id: auth-login-flow` lives at `flows/auth-login-flow.md` and is linked as `[[auth-login-flow]]`.

**ID format:** `<domain-slug>-<type-slug>` (flat, hyphen-separated). No nested slashes in IDs — they map cleanly to filenames.
- Domain hub: `auth` → `domains/auth/auth.md`
- Capability: `auth-login` → `domains/auth/capabilities/auth-login.md`
- Flow: `auth-login-flow` → `domains/auth/flows/auth-login-flow.md`
- Concept: `auth-session` → `domains/auth/concepts/auth-session.md`
- Model: `auth-user-model` → `domains/auth/models/auth-user-model.md`
- Risk: `auth-stale-session-risk` → `domains/auth/risks/auth-stale-session-risk.md`

**Frontmatter tags** (required on every page — used for Obsidian graph coloring):
```yaml
tags:
  - type/<domain|capability|flow|concept|model|risk|decision>
  - domain/<domain-slug>
  - status/<active|legacy|deprecated|partially_migrated|unused|experimental|unknown|needs_review>
```

**Wiki-link rule:** Every relationship between nodes MUST appear as a `[[node-id|Display Name]]` wiki-link somewhere in the page body. This is what creates the edge in the Obsidian graph. The `edges.json` file is a machine-readable mirror of the same links.

**Write rule:**
- `source_supported` → write draft page immediately
- `inferred` → write with `<!-- draft: inferred — not human-reviewed -->` banner
- `ambiguous` or `needs_human_review` → add to needs-review.md report, do NOT write a page

**Valid `status`:** `active` `legacy` `deprecated` `partially_migrated` `unused` `experimental` `unknown` `needs_review`

**Valid `confidence`:** `verified` (human only) `source_supported` `inferred` `ambiguous` `stale` `needs_human_review`

**Risk node `severity` field:** Every `type: caveat` node in `nodes.json` **must** include a top-level `"severity"` field with value `"low"`, `"med"`, or `"high"`. This field is read by `--benchmark` to compute the risk surface score. Do not rely on markdown frontmatter tags for severity — the script reads `nodes.json` directly.

```json
{
  "id": "payment-webhook-idempotency-risk",
  "type": "caveat",
  "severity": "high",
  "name": "Stripe Webhook Idempotency Risk",
  ...
}
```

---

## Harvest Phase

The harvest phase extracts structured data from source files using a deterministic Python script. The LLM **never reads raw source files** — it reads the JSON output instead. This reduces init token cost by ~5–10x and makes update detection exact.

### Running the script

```bash
# Full harvest (init — all files)
python3 <skill_base_dir>/scripts/harvest.py <root>

# Incremental harvest (scan — dirty files only)
python3 <skill_base_dir>/scripts/harvest.py <root> \
  --hashes docs/brain/projects/<name>/graph/file-hashes.json

# Targeted harvest (update — specific files only)
python3 <skill_base_dir>/scripts/harvest.py <root> \
  --files src/services/TaskService.ts src/api/tasks/tasks.controller.ts
```

`<skill_base_dir>` is the base directory shown at the top of the skill when invoked (e.g. `/Users/you/.claude/skills/kodebrain`).

### Output schema

```json
{
  "root": "/path/to/project",
  "hashes": { "src/file.ts": "sha256hex..." },
  "dirty": ["src/file.ts"],
  "files": {
    "src/file.ts": {
      "path": "src/file.ts",
      "exports": ["AuthService"],
      "routes": ["loginRouter.post()"],
      "imports": ["./UserRepository", "jsonwebtoken"],
      "imported_by": ["src/api/auth/login.ts"],
      "status_signals": [{"line": 3, "text": "// DEPRECATED"}],
      "status": "deprecated",
      "has_test": false,
      "is_test": false
    }
  }
}
```

**`dirty`** — files whose SHA-256 hash changed since `--hashes` was last saved (or all files on first run). Only dirty files appear in `files`. This is the only input needed for all init and update steps.

### Status classification (deterministic — no LLM judgment)

| Signal | → `status` |
|---|---|
| `@deprecated` / `// DEPRECATED` in file | `deprecated` |
| `TODO.*(remov\|migrat\|replac)` comment | `partially_migrated` |
| Filename stem matches V1/Old/Legacy/Backup | `suspected_legacy` |
| Zero importers AND zero routes | `suspected_unused` |
| File is a test file (`*.test.*`, `tests/`) | `active` (not unused) |
| File is an entry point (`server`, `main`, `index`) with no importers | `active` (not unused) |
| None of above | `active` |

### What Claude does with the output

Read the JSON, build harvest briefs mentally per file, then proceed to domain/capability/flow narration. Do not read any raw source files — the JSON contains all the signal needed.

---

## Sub-command: init

**Purpose:** Scan a project for the first time and produce the initial knowledge map.

### Steps

**1. Confirm project root.** Look for `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, or a `src/` directory. If none found, warn and ask for confirmation.

**2. Run harvest phase.** Run `python3 <skill_base_dir>/scripts/harvest.py <root>` (no `--hashes` flag on first init). Parse the JSON output. This produces: file hashes, export map, route map, import/importer map, status signals, and per-file briefs for every source file. Do not read raw source files — all subsequent steps use the JSON output.

**3. Classify domains.** From harvest briefs: a domain candidate is a folder whose briefs collectively include a service export, a model/repository export, and at least one route reference. Name domains after the folder (title-cased). Always check for: Auth, User, Billing/Payment, Notification, Admin, Core/Shared. Flag anything unclusterable as `unmapped`.

**4. Detect capabilities.** Per domain: derive from route patterns and service export names in briefs. Phrase as verb phrases: "Create order", "Send notification", "Validate user session". Aim for 5–10 per domain.

**5. Trace flows.** For the top 3–5 capabilities per domain, trace the runtime path using the import graph from H4: entry route → service methods → downstream imports → side effects (cache writes, queue, email). Use brief data only — do not read source files.

**6. Identify concepts.** A concept is a non-obvious mental model needed before working with the domain. Look for: terms that appear across multiple file exports that aren't self-explanatory, adapter patterns, caching strategies, state machines, dual-write periods. Target 3–7 per domain.

**7. Identify risks.** From status signals (H5): deprecated files still imported by active code, V1 routes still registered alongside V2, `TODO: migrate` comments with no timeline. Write a risk node for each.

**8. Find entry points.** From route grep (H3) and import graph: identify `main.ts` `app.ts` `server.ts` `index.ts` or equivalent. Record in project hub.

**9. Write pages.** For each `source_supported` node: generate using the matching template from `templates/`. For each `inferred` node: same but add the draft banner. Write to the correct path under `docs/brain/projects/<name>/`.

  File naming rules:
  - Domain hub: `domains/<slug>/<slug>.md` (e.g., `domains/auth/auth.md`) — enables `[[auth]]` links
  - All other pages: `<type-folder>/<domain-slug>-<node-slug>.md` (e.g., `flows/auth-login-flow.md`)

  Wiki-link rules (applied in every page):
  - Every relationship in "Related" or "Used by" sections must be a `[[node-id|Display Name]]` link
  - Domain hub links: `[[auth|Auth domain]]`
  - Cross-type links: `[[auth-login-flow|Login Flow]]`, `[[auth-user-model|User Model]]`
  - These wiki-links create the Obsidian graph edges — they are the graph

**10. Write Obsidian config.** Copy `obsidian-vault-config/graph.json` and `app.json` to `docs/brain/.obsidian/`. Only do this on first init (don't overwrite if already present).

**11. Write graph files.**

Write `nodes.json` and `edges.json` manually. Then generate `file-index.json` deterministically — **do not write it by hand**:

```bash
python3 <skill_base_dir>/scripts/harvest.py \
  --build-index docs/brain/projects/<name>/graph/nodes.json
```

This inverts `source_files` fields in `nodes.json` → `{ "src/file.ts": ["node-id", ...] }`. Every file listed in any node's `source_files` appears in the index automatically. Save `file-hashes.json` from the harvest output's `hashes` field.

```
docs/brain/projects/<name>/graph/nodes.json       — all nodes (written by Claude)
docs/brain/projects/<name>/graph/edges.json       — all edges (written by Claude)
docs/brain/projects/<name>/graph/file-index.json  — generated by --build-index (never hand-written)
docs/brain/projects/<name>/graph/file-hashes.json — from harvest output hashes field
```

**12. Write reports.**
```
reports/unmapped-files.md    — files not assigned to any domain
reports/suspected-legacy.md — nodes flagged legacy or unused
reports/needs-review.md      — ambiguous or needs_human_review items
```

**13. Write project-level platform configs.** Run the kodebrain CLI to write agent instruction files for this project automatically — this is part of init, not a separate step:

```bash
kodebrain project install <root> 2>/dev/null \
  && echo "Platform configs written." \
  || echo "Tip: pip install kodebrain && kodebrain project install . to set up platform configs."
```

This writes `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/kodebrain.mdc`, `.github/copilot-instructions.md`, `.windsurfrules`, `.clinerules`, and `opencode-instructions.md` with KB-specific instructions for each platform. If the package is not installed, print the tip and continue — do not fail.

**14. Print summary.**
```
Kode Brain init complete — <project name>
Domains:        N
Capabilities:   N
Flows:          N
Concepts:       N
Models:         N
Risks:          N
Unmapped files: N  (see reports/unmapped-files.md)
Needs review:   N  (see reports/needs-review.md)

KB location:    docs/brain/projects/<name>/
Graph view:     Open docs/brain/ as an Obsidian vault → Graph view
                Nodes colored by type. Filter by #domain/<name> or #status/legacy.
Platform configs written to: CLAUDE.md, AGENTS.md, .cursor/rules/, ...

If you haven't already:
  pip install kodebrain    # install once globally
  kodebrain install        # register with all AI platforms (user-level, run once)
  kodebrain hook install   # git hook — keeps KB drift detection current
```

---

## Sub-command: scan

**Purpose:** Re-scan a project that already has a KB. Update changed nodes, add new ones, flag stale ones.

### Steps

1. Load `nodes.json`, `edges.json`, `file-index.json`.
2. Run `python3 <skill_base_dir>/scripts/harvest.py <root> --hashes graph/file-hashes.json`. The script compares SHA-256 hashes and returns only dirty/new files in `files`. Deleted files (in hashes but not on disk) are not in `hashes` output.
3. For dirty files: look up node IDs in `file-index.json`. Re-narrate affected nodes from the JSON briefs. Set `confidence: source_supported`.
4. For deleted files (in old hashes but absent from new `hashes`): mark all referenced nodes `confidence: stale`. Add to `reports/needs-review.md`.
5. For new files (in `dirty` but not in `file-index.json`): run domain/capability detection from brief. Write new node if `source_supported`. Add the new file to the new node's `source_files` field.
6. Update `nodes.json`. Regenerate `file-index.json` from `nodes.json` using `--build-index`. Save updated `file-hashes.json`. Print change summary.

---

## Sub-command: query

**Purpose:** Answer a question about the project using the knowledge base.

**Input:** Natural language task description, symptom, or question.

### Steps

1. Load `nodes.json` and `edges.json` from `docs/brain/projects/<name>/graph/`.
2. **Find seed nodes.** Extract entity names and action keywords from the query. Find nodes whose `name` or `summary` contains any of these terms. If no matches, fall back to domain-level nodes for the most relevant domain.
3. **BFS traversal.** Starting from seed nodes, traverse edges outward to depth 2. Follow edge types: `contains`, `calls`, `reads_from`, `writes_to`, `invalidates`, `part_of_flow`. Collect all reached nodes. Always include nodes linked via `has_caveat` regardless of depth.
4. Read the Markdown page for each collected node (summary + status sections).
5. Collect risks: `caveat` nodes connected to collected nodes, nodes with `legacy` or `partially_migrated` status.
6. Print:
   ```
   ## Relevant to: "<query>"

   ### Required Reading
   - [type: domain] path/to/page.md — reason
   - [type: flow]   path/to/page.md — reason

   ### Likely Source Files
   - src/file.ts — reason

   ### Warnings
   ⚠ [HIGH] description — (node: node-id)
   ⚠ [MED]  description

   ### Investigation Order
   1. ...
   2. ...
   ```
7. Note confidence of each referenced node. Explicitly call out any that are `stale`, `inferred`, or `needs_human_review`.

---

## Sub-command: reading-pack

**Purpose:** Same as `query` but saves the output as a Markdown file.

### Steps

1–6. Same as `query`.
7. Write to `docs/brain/projects/<name>/reports/reading-packs/<YYYY-MM-DD>-<slug>.md`.
8. Print: `Reading pack saved to: <path>`

---

## Sub-command: detect-legacy

**Purpose:** Surface suspected dead, duplicate, or partially migrated code.

### Steps

1. Determine scope: all domains or `--domain <slug>`.
2. For each source file in scope, check:
   - Imported by any other file? `grep -r "from.*<filename>" <root> --include="*.ts" --include="*.py" -l`
   - Referenced in routes? `grep -r "<export-name>" <root>/routes -l 2>/dev/null`
   - Has tests? Check test file naming patterns
   - Contains `TODO` `DEPRECATED` `@deprecated` `// old` `// legacy` comments?
   - Name suggests old version? (`*Old.*` `*V1.*` `*Legacy.*` `*Backup.*`)
   - Newer replacement exists? (same base name with V2, or same exports in newer module)
3. Classify suspects: `suspected_unused` / `suspected_legacy` / `partially_migrated`
4. Write `reports/suspected-legacy.md`. Format per suspect:
   ```
   ## src/services/OldPaymentService.ts
   Classification: suspected_unused
   Confidence: inferred
   Signals:
     - No files import this module
     - Possible replacement: src/services/PaymentV2Service.ts (inferred)
   Action: Human review required before any deletion.
   ```
5. Do NOT delete or modify source code.
6. Print: `Found N suspects. Review reports/suspected-legacy.md`

---

## Sub-command: review

**Purpose:** Check whether KB pages accurately reflect current source code.

**Input:** Optional `--page <path>`. Default: review all pages.

### Steps

1. For each KB page:
   a. Read frontmatter: get `source_files`, `status`, `confidence`.
   b. Check each source file still exists.
   c. Check key claims in the body against source: do listed symbols still exist? Does the described flow still match?
   d. Rate: `still_valid` / `likely_stale` / `contradicted` / `unverifiable`
2. For pages with contradicted or stale claims: set `confidence: stale` in frontmatter. Add to `reports/stale-docs.md`. Do NOT rewrite the body.
3. For pages where source files are gone: add to `reports/needs-review.md`.
4. Print: `Reviewed N pages. Stale: N. Needs review: N.`

---

## Sub-command: update

**Purpose:** Update KB pages affected by recent code changes. Designed to be called by an agent after editing source files — keeps the KB current within a session.

### Steps

1. Get changed files:
   - `--diff`: run `git diff --name-only HEAD`
   - `--files f1 f2 ...`: use provided list
2. Run `python3 <skill_base_dir>/scripts/harvest.py <root> --files <f1> <f2> ...`. Parse the JSON briefs for each changed file. Compare new `status` field against the existing node's `status`.
3. Load `file-index.json`. Find node IDs referencing each changed file.
4. For each affected node, re-narrate from the updated harvest brief:
   - Behavior changed (new/removed exports or routes) → rewrite relevant page sections, set `confidence: source_supported`
   - Refactor only (no export/route changes) → update `source_files` and `last_reviewed`, no content change
   - File deleted → set `status: unused`, `confidence: needs_human_review`, add to needs-review.md
5. Update `file-hashes.json` with new hashes for changed files.
6. Update `nodes.json`. Regenerate `file-index.json` via `--build-index`. Print summary: files changed, nodes affected, sections rewritten.

---

## Agent Working Pattern

An agent working in a KB-enabled codebase should use KB pages as its primary source of truth instead of reading source files. This eliminates repeated navigation overhead and keeps token cost low across a multi-file edit session.

**Session start — load context before touching any code:**
```
/kodebrain reading-pack "<task description>"
```
Read the saved reading pack. It contains: relevant domain hubs, flow paths, source file hints, and active warnings. Do not read source files not listed in the pack until you need to make a targeted edit.

**After editing source files — keep the KB current:**
```
/kodebrain update --files src/services/TaskService.ts src/api/tasks/tasks.controller.ts
```
Call this after each batch of edits. The KB re-harvests the changed files and re-narrates affected nodes. Subsequent queries return fresh KB data, not stale pre-edit state.

**Answering questions during the session:**
```
/kodebrain query "<question>"
```
Answer from KB pages. Read source files directly only when the KB reports `confidence: stale` or `needs_human_review` on a node directly relevant to your answer.

**Rule of thumb:** KB first. Source file only when KB is stale or you are making a targeted edit to that file.

---

## Behavior Rules

**Never:**
- Delete any KB page or source file
- Set `confidence: verified` (human only)
- Mark a migration `completed`
- Overwrite text inside `<!-- human-note --> ... <!-- /human-note -->` blocks — preserve verbatim
- Claim behavior without source evidence — use `inferred` instead

**Always:**
- State confidence level in every answer
- Warn when a referenced node is `stale`, `inferred`, or `needs_human_review`
- List source file evidence for every non-trivial claim
- Suggest `/kodebrain scan` when KB appears outdated

**When source contradicts KB:** Trust the source code. Mark the KB node `stale`. Report the contradiction — do not silently resolve it.

**On rename:** Update `id` in nodes.json, update `from`/`to` in all referencing edges in edges.json, update keys and values in file-index.json. No backward-compat stubs.

---

## Sub-command: benchmark

**Purpose:** Read the generated KB and produce a metrics report — coverage, confidence quality, graph density, risk surface, and an overall health score. Read-only. Does not modify any KB content.

**Input:** Optional project path. Default: current directory.

**All numeric metrics are computed by the harvest script — not by the LLM.** The LLM's role is to interpret the JSON output, write a narrative summary, draw ASCII graph topology, and produce improvement recommendations.

### Steps

1. Locate `docs/brain/projects/<name>/graph/nodes.json`, `edges.json`, `file-index.json`, `file-hashes.json`. If missing, tell the user to run `/kodebrain init` first.

2. **Run the benchmark script.**
   ```bash
   python3 <skill_base_dir>/scripts/harvest.py \
     --benchmark docs/brain/projects/<name>/ \
     --source-root <project-root>
   ```
   Parse the JSON output. All counts, percentages, quality scores, degree calculations, and token estimates come from this output — do not recompute them.

   Output schema:
   ```json
   {
     "coverage":        { "total_source_files": N, "mapped_files": N, "unmapped_files": N, "pct": N },
     "nodes":           { "total": N, "by_type": {...}, "by_status": {...}, "by_confidence": {...} },
     "edges":           { "total": N, "by_type": {...}, "cross_domain": N },
     "graph":           { "avg_degree": N, "orphan_count": N, "top_hubs": [{"id":..,"degree":..,"type":..}] },
     "risk_surface":    { "risk_nodes": [...], "legacy_count": N, "needs_review_count": N, "suspected_legacy_count": N },
     "scores":          { "coverage": N, "confidence": N, "connectedness": N, "risk_awareness": N, "overall": N },
     "token_efficiency":{ "source_bytes": N, "kb_bytes": N, "source_tokens_est": N, "kb_tokens_est": N, "ratio": N }
   }
   ```

3. **Build ASCII graph topology.** Using the node and edge data from the script output, draw a cluster map showing domains, their child node counts, and cross-domain edges as arrows. This is the one step that requires spatial layout judgment.

4. **Write improvement recommendations.** Based on gaps surfaced by the script (uncovered files, orphan nodes, missing risk nodes, inferred-confidence nodes), write a prioritized list of HIGH / MED / LOW recommendations.

5. **Write report** to `docs/brain/projects/<name>/reports/benchmark.md` using the format below.

6. **Print summary** — the full benchmark report to the terminal.

### Benchmark Report Format

```md
# Kode Brain Benchmark — <project>
Generated: <date>

## Coverage
Total source files:   N
Mapped to KB:         N  (NN%)
Unmapped:             N  (NN%)

## Knowledge Map
| Type         | Count |
|---|---|
| Domains      | N |
| Capabilities | N |
| Flows        | N |
| Concepts     | N |
| Models       | N |
| Risks        | N |
| Legacy areas | N |
| **Total nodes** | **N** |
| **Total edges** | **N** |

## Confidence
| Level              | Nodes | % |
|---|---|---|
| source_supported   | N | NN% |
| inferred           | N | NN% |
| ambiguous          | N | NN% |
| needs_human_review | N | NN% |
| verified           | N | NN% |

## Status
| Status             | Nodes |
|---|---|
| active             | N |
| partially_migrated | N |
| legacy             | N |
| needs_review       | N |

## Graph Metrics
Avg edges per node:    N.N
Cross-domain edges:    N
Orphan nodes:          N  (no edges — may need wiki-links)

Top hubs:
  1. <node-id> — N edges  (<type>)
  2. <node-id> — N edges
  3. <node-id> — N edges

## Risk & Legacy Surface
Risk nodes (HIGH):     N
Risk nodes (MED/LOW):  N
Legacy/deprecated:     N files
Needs review:          N items
Suspected legacy:      N files

## Graph Topology
<ASCII cluster map>

## Quality Scores
Coverage:       NN/100
Confidence:     NN/100
Connectedness:  NN/100
Risk awareness: NN/100
─────────────────────
Overall:        NN/100  [grade]

Grade scale: 90+ = Excellent · 75+ = Good · 60+ = Fair · <60 = Needs work
```

---

## Templates

Page templates are in `templates/` relative to this SKILL.md:
- `templates/domain.md`
- `templates/capability.md`
- `templates/flow.md`
- `templates/concept.md`
- `templates/model.md`
- `templates/decision.md`
- `templates/risk.md`

## Schemas

- `schema/node.schema.json` — KnowledgeNode field definitions
- `schema/edge.schema.json` — KnowledgeEdge field definitions
- `schema/knowledge-base.schema.json` — top-level graph container
