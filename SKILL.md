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

---

## Sub-command: init

**Purpose:** Scan a project for the first time and produce the initial knowledge map.

### Steps

**1. Confirm project root.** Look for `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, or a `src/` directory. If none found, warn and ask for confirmation.

**2. Scan files.**
```bash
find <root> -type f \
  ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/dist/*" \
  ! -path "*/build/*" ! -path "*/__pycache__/*" ! -path "*/.venv/*" \
  | sort
```
Classify each file:
- `source` — `.ts .tsx .js .jsx .py .go .rs .java .rb .php .cs .swift .kt`
- `config` — `.json .yaml .yml .toml .env .ini .xml` at root or in config/
- `test` — in `test/` `tests/` `spec/` `__tests__/` or named `*.test.*` `*.spec.*`
- `migration` — in `migrations/` `db/migrate/` or named `*_migration.*`
- `doc` — `.md .rst .txt` in docs/ or root

**3. Find entry points.** Look for: `main.ts` `main.py` `index.ts` `app.ts` `server.ts` `cmd/` `cli.ts`, and route registration files (files that call `app.use`, `router.add`, or `app.include_router`).

**4. Extract symbols.** For each source file, identify:
- Exported functions and classes — look for `export function` `export class` `export const` `def ` `func ` `pub fn` `public class`
- Route definitions — look for `.get(` `.post(` `.put(` `.delete(` `.patch(` `@app.route` `@router.` `r.Handle` `router.`
- Model/schema definitions — look for `@Entity` `Schema(` `model.define` `z.object` `BaseModel` `mongoose.model`
- Imports — what each file imports from where

**5. Detect domains.** A domain candidate is a folder containing a service file, a model/repository file, and at least one route or handler. Name domains after the folder (title-cased). Always check for: Auth, User, Billing/Payment, Notification, Admin, Core/Shared. Flag anything unclusterable as `unmapped`.

**6. Detect capabilities.** Per domain: derive from route handlers ("what does each route do?") and service method names ("what does each public method do?"). Phrase as verb phrases: "Create order", "Send notification", "Validate user session". Aim for 5–10 per domain.

**7. Extract flows.** For the top 3–5 capabilities per domain, trace the runtime path:
- Entry: which route or event?
- Steps: which service methods in which order?
- Data: what is read, what is written?
- Side effects: cache, events, queues, emails?

**8. Identify concepts.** A concept is a non-obvious mental model needed before working with the domain. Look for: terms used across multiple files that aren't self-explanatory, adapter patterns, multi-tenancy, caching strategies, state machines, dual-write periods. Target 3–7 per domain.

**9. Classify status.** For each node:
- `active` — has route refs, recent imports, tests
- `legacy` — old folder name, `TODO`/`DEPRECATED` comment, newer replacement exists
- `unused` — no imports, no route ref, no test (flag for human review — do NOT delete)
- `unknown` — insufficient signal

**10. Write pages.** For each `source_supported` node: generate using the matching template from `templates/`. For each `inferred` node: same but add the draft banner. Write to the correct path under `docs/brain/projects/<name>/`.

  File naming rules:
  - Domain hub: `domains/<slug>/<slug>.md` (e.g., `domains/auth/auth.md`) — enables `[[auth]]` links
  - All other pages: `<type-folder>/<domain-slug>-<node-slug>.md` (e.g., `flows/auth-login-flow.md`)

  Wiki-link rules (applied in every page):
  - Every relationship in "Related" or "Used by" sections must be a `[[node-id|Display Name]]` link
  - Domain hub links: `[[auth|Auth domain]]`
  - Cross-type links: `[[auth-login-flow|Login Flow]]`, `[[auth-user-model|User Model]]`
  - These wiki-links create the Obsidian graph edges — they are the graph

**10a. Write Obsidian config.** Copy `obsidian-vault-config/graph.json` and `app.json` to `docs/brain/.obsidian/`. Only do this on first init (don't overwrite if already present).

**11. Write graph files.**
```
docs/brain/projects/<name>/graph/nodes.json      — all nodes (see schema/node.schema.json)
docs/brain/projects/<name>/graph/edges.json      — all edges (see schema/edge.schema.json)
docs/brain/projects/<name>/graph/file-index.json — { "src/file.ts": ["node-id", ...] }
```

**12. Write reports.**
```
reports/unmapped-files.md    — files not assigned to any domain
reports/suspected-legacy.md — nodes flagged legacy or unused
reports/needs-review.md      — ambiguous or needs_human_review items
```

**13. Print summary.**
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
```

---

## Sub-command: scan

**Purpose:** Re-scan a project that already has a KB. Update changed nodes, add new ones, flag stale ones.

### Steps

1. Load `nodes.json`, `edges.json`, `file-index.json`.
2. Run current file scan (steps 2–9 of `init`).
3. Compare:
   - **New file not in file-index** → run capability/flow detection, write new node if confident
   - **Existing node's source files changed** → set `confidence: stale`, add to stale-docs.md
   - **File in file-index no longer exists** → mark referenced nodes `confidence: stale`, add to needs-review.md
4. Write updated pages for `source_supported` nodes only.
5. Set `confidence: stale` on changed nodes without rewriting body content.
6. Update graph files. Print change summary.

---

## Sub-command: query

**Purpose:** Answer a question about the project using the knowledge base.

**Input:** Natural language task description, symptom, or question.

### Steps

1. Load `nodes.json` and `edges.json` from `docs/brain/projects/<name>/graph/`.
2. Parse the query: extract entity names (nouns) and action words (verbs). Match against node `name` and `summary` fields.
3. Find candidate nodes. Traverse edges from candidates: follow `contains`, `calls`, `reads_from`, `writes_to`, `invalidates`, `part_of_flow` edges to collect related nodes.
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

**Purpose:** Update KB pages affected by recent code changes.

### Steps

1. Get changed files:
   - `--diff`: run `git diff --name-only HEAD`
   - `--files f1 f2 ...`: use provided list
2. Load `file-index.json`. For each changed file, find node IDs that reference it.
3. For each affected node:
   - Determine change type: `behavior_change` / `refactor` / `migration` / `removal` / `addition`
   - Behavior changed → update relevant page sections, set `confidence: source_supported`
   - Refactor only → update `source_files` list and `last_reviewed`, no content change
   - Removal → set `status: unused`, `confidence: needs_human_review`, add to needs-review.md
4. Update `nodes.json`. Print summary.

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

### Steps

1. Locate `docs/brain/projects/<name>/graph/nodes.json`, `edges.json`, `file-index.json`. If missing, tell the user to run `/kodebrain init` first.

2. **Count source files.** Run `find <root>` (same ignore rules as `init`). Classify as source/test/config.

3. **Compute coverage.**
   - `mapped_files` = files that appear as keys in `file-index.json` with at least one node ID
   - `unmapped_files` = source files not in file-index or with empty node list
   - `coverage_pct` = `mapped_files / total_source_files * 100`

4. **Count nodes by type and status.**
   Count how many nodes of each `type` exist. Count how many nodes have each `status` value.

5. **Count edges by type.**
   Count how many edges of each `type` exist. Also count cross-domain edges (where `from` and `to` nodes have different `domain` values).

6. **Confidence distribution.**
   Count nodes at each confidence level. Flag any `inferred` or `ambiguous` nodes — these need human review.

7. **Graph metrics.**
   - For each node, count its outbound + inbound edges → find the top 3 most-connected hub nodes
   - Orphan nodes = nodes with zero edges (disconnected — may need wiki-links added)
   - Avg edges per node = total edges / total nodes

8. **Legacy & risk surface.**
   - Count nodes with `status: legacy`, `deprecated`, `partially_migrated`, `unused`
   - Count `type: caveat` nodes, grouped by `severity` tag if present
   - Count items in `reports/needs-review.md` (count `## ` headings)
   - Count items in `reports/suspected-legacy.md`

9. **Compute quality scores (0–100).**

   | Dimension | Formula |
   |---|---|
   | Coverage | `mapped_source_files / total_source_files * 100` |
   | Confidence | `(verified*100 + source_supported*80 + inferred*40 + ambiguous*10) / total_nodes` |
   | Connectedness | `100 - (orphan_nodes / total_nodes * 100)` |
   | Risk awareness | `min(100, risk_nodes * 20 + legacy_nodes * 10)` — rewards finding problems |
   | Overall | `(coverage + confidence + connectedness + risk_awareness) / 4` |

10. **Build ASCII graph topology.** Show domains as cluster headers, list their child node types and counts, show cross-domain edges as arrows between cluster names.

11. **Write report** to `docs/brain/projects/<name>/reports/benchmark.md`.

12. **Print summary** — the full benchmark report to the terminal.

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
