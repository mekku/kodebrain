---
name: kodebrain
description: "Kode Brain — living knowledge system for evolving codebases. Converts a project into a structured knowledge map: domains, capabilities, flows, concepts, legacy areas, and source evidence. Use when user asks questions about a codebase via /kodebrain."
trigger: /kodebrain
---

# /kodebrain

Convert any codebase into a living knowledge map — domains, capabilities, flows, concepts, legacy areas, and source evidence — so humans and AI agents can understand and modify it without rediscovering everything from scratch.

## Usage

```
/kodebrain onboard [path]                    # unified onboarding — greenfield, brownfield, partial, legacy
/kodebrain init [path]                       # first-time scan → scaffold docs/brain/ and write knowledge map
/kodebrain scan [path]                       # re-scan, update changed nodes, flag stale pages
/kodebrain query "<task or symptom>"         # answer a question using the knowledge base
/kodebrain reading-pack "<task>"             # generate + save a context pack for a task
/kodebrain detect-legacy [--domain slug]     # surface suspected dead, duplicate, or migrated code
/kodebrain review [--page path]              # check whether KB pages match current source
/kodebrain update [--diff] [--files f1 f2]   # update KB pages from recent code changes
/kodebrain install [path] [--platform ...]   # write agent instructions to platform config files
/kodebrain uninstall [path]                  # remove all kodebrain blocks from platform config files
```

## What /kodebrain is for

Point `/kodebrain` at any software project to get a structured, navigable knowledge map. Persistent across sessions. Honest confidence labels. Built for projects that grew organically — not perfect systems.

Kode Brain has three jobs:
1. **Define intended reality** — what the project is for, what it should do, constraints.
2. **Map observed reality** — what source, config, runtime, tests show the system actually does.
3. **Detect and manage drift** — surface disagreements between intent and observation.

---

## Core Concepts

### Three Knowledge Layers

```
Project Contract (intended/canonical knowledge)
       ↓ guides
Knowledge Map (explanation + navigation)
       ↓ grounded by
Evidence (observed reality — source, config, runtime, tests, git)
```

### Provenance vs Confidence

**Provenance** = where the claim came from:
`human` `project_document` `source_code` `configuration` `runtime` `test` `git` `generated`

**Confidence** = how trustworthy the claim is:
`verified` `supported` `inferred` `ambiguous` `stale` `needs_human_review`

A human statement can be authoritative intent without being verified implementation.
A source-supported observation can be accurate implementation without representing intended design.

### Knowledge Role

Each node carries a `knowledge_role`:
- `intent` — what should be true (from human, project docs, architecture decisions)
- `observed` — what implementation exists (from source, config, runtime)
- `mixed` — both intent and observation

### Drift

When intent and observed reality disagree, create a drift record — never silently resolve to one side.

---

## What You Must Do When Invoked

Parse the sub-command from the argument. If no sub-command is given, print the usage block above and stop.

If no path is given for `init`, `scan`, or `onboard`, use `.` (current working directory).

Follow the steps for each sub-command below. Do not skip steps.

---

## Knowledge Base Location

All knowledge lives under `docs/brain/` in the target project. The KB doubles as an **Obsidian vault**.

```
docs/brain/projects/<project>/
  <project>.md                  ← project hub (START HERE)

  architecture/
    overview.md
    technology.md
    runtime.md
    data.md
    deployment.md
    integrations.md

  domains/<domain>/
    <domain>.md                 ← domain hub (NOT overview.md — filename = domain slug)
    capabilities/<cap-slug>.md
    flows/<flow-slug>.md
    concepts/<concept-slug>.md
    models/<model-slug>.md
    apis/<api-slug>.md
    decisions/<YYYY-MM-DD>-<slug>.md
    risks/<risk-slug>.md

  decisions/

  changes/
    active/
    completed/

  graph/
    nodes.json
    edges.json
    file-index.json
    file-hashes.json            ← SHA256 per source file; drives hash-based update detection

  reports/
    knowledge-gaps.md
    drift.md
    unmapped-files.md
    suspected-legacy.md
    stale-docs.md
    needs-review.md
    reading-packs/

  .obsidian/
    graph.json                  ← graph coloring config
    app.json                    ← link resolution
```

**Domain file naming:** domain hub file is `<domain-slug>.md` (not `overview.md`). This makes `[[auth]]` resolve directly to the auth domain hub in Obsidian.

**Node ID = file slug:** a node with `id: auth-login-flow` lives at `flows/auth-login-flow.md` and is linked as `[[auth-login-flow]]`.

**ID format:** `<domain-slug>-<type-slug>` (flat, hyphen-separated). No nested slashes in IDs.
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
- `supported` → write draft page immediately
- `inferred` → write with `<!-- draft: inferred — not human-reviewed -->` banner
- `ambiguous` or `needs_human_review` → add to needs-review.md report, do NOT write a page

**Valid `status`:** `active` `legacy` `deprecated` `partially_migrated` `unused` `experimental` `unknown` `needs_review`

**Valid `confidence`:** `verified` (human only) `supported` `inferred` `ambiguous` `stale` `needs_human_review`

**Valid `provenance`:** `human` `project_document` `source_code` `configuration` `runtime` `test` `git` `generated`

**Valid `knowledge_role`:** `intent` `observed` `mixed`

---

## Harvest Phase

The harvest phase extracts structured data from source files using a deterministic Python script. It is the preferred first step for source inspection because it lowers cost and provides reproducible evidence.

### Source-reading escalation

```
Level 0 — file and project inventory
Level 1 — deterministic harvest
Level 2 — manifests/configuration/document inspection
Level 3 — targeted source reading (LLM reads specific files)
Level 4 — human clarification
```

Source reading is appropriate when:
- harvest output is insufficient to determine semantics,
- a supported language has weak extraction coverage,
- dynamic wiring cannot be resolved statically,
- project/domain boundaries are ambiguous,
- a critical runtime flow needs verification,
- source and existing KB contradict each other.

Do not read an entire large codebase without reason. Read targeted source based on expected information gain.

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

`<skill_base_dir>` is the base directory shown at the top of the skill when invoked.

### Output schema

```json
{
  "root": "/path/to/project",
  "hashes": { "src/file.ts": "sha256hex..." },
  "dirty": ["src/file.ts"],
  "files": {
    "src/file.ts": {
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

---

## Sub-command: onboard

**Purpose:** Unified onboarding command. Works on greenfield projects, existing codebases, partial KBs, and legacy KBs. Idempotent, resumable, gap-driven.

### Steps

**1. Detect project state.** Inspect:
- repository and file topology,
- existing `docs/brain/`,
- README and project docs,
- manifests and build files,
- existing KB schema version,
- current completeness of project-level knowledge.

Classify state as one of:
```
greenfield      — no meaningful source code, no KB
new_brownfield  — source exists, no KB
partial_kb      — KB exists but missing project-level knowledge
legacy_kb       — older KB format detected
stale_kb        — KB exists but outdated vs source
onboarded       — KB is current and complete at project level
```

Produce an internal **Knowledge Gap Map** across these dimensions:
```
purpose, actors, core_outcomes, scope, technology, architecture,
runtime, external_integrations, domains, domain_boundaries,
invariants, legacy_migration
```

Each gap marked: `found_in_docs` / `inferred_from_project` / `needs_human` / `unknown`.

**2. Discover existing intent.** Before inferring project purpose from code, search for intent in:
1. current Project Contract / existing KB pages,
2. human notes,
3. ADRs,
4. README and architecture docs,
5. other likely product/spec docs.

Distinguish current/active documentation from historical/stale documentation when possible.

**3. Interview if necessary.** If project-level intent is absent, materially incomplete, ambiguous, or contradictory, interview the user before deep mapping.

Do not interview merely because a particular file is missing. Interview only for knowledge that materially improves project interpretation.

Minimum interview dimensions:
- Purpose and users — what the project is and who it serves.
- Core outcomes/workflows — the few things the system fundamentally must accomplish.
- Known system shape — apps, services, workers, major components.
- Critical external systems — important third-party dependencies.
- Known legacy/migration areas.

For greenfield, additionally establish: technology constraints, deployment constraints, security/privacy constraints, initial domains, non-functional requirements.

Interview output gets `provenance: human`, `knowledge_role: intent`.

**4. Create or repair the Project Contract.** Generate `<project>.md` with all required sections. Only populate sections supported by current knowledge. Keep unknowns explicit.

Also generate architecture pages for which evidence exists:
- `architecture/overview.md`
- `architecture/technology.md`
- `architecture/runtime.md`
- `architecture/data.md`
- `architecture/deployment.md`
- `architecture/integrations.md`

**5. Run harvest and map architecture.** Run harvest script. Use output to populate technology/runtime skeleton. Extend harvest detection to include: language/runtime manifests, package managers, frameworks, DB clients, cache clients, queues, infrastructure files, Docker files, CI config, API styles, worker/scheduler entry points.

**6. Map domains.** Discover domains from: human/project contract, architecture components, file/folder clusters, routes, services/models, runtime entry points, existing KB domains.

For each domain, write domain hub with: Responsibility, Owns, Does Not Own, Depends On, Used By, Core Concepts, Capabilities, Core Flows, Data Ownership, Entry Points, Invariants, Legacy/Migration, Risks, Source Areas, Open Questions.

If code clustering conflicts with intended domain boundaries, preserve both and surface drift.

**7. Progressive deep mapping.** Map in priority order:
1. runtime entry points,
2. high-connectivity domains,
3. core outcomes/workflows from Project Contract,
4. frequently changed areas (if git evidence available),
5. task-relevant areas,
6. remaining unmapped areas.

Persist progress. Partial mapping is acceptable if gaps are explicit.

**8. Write reports.**
- `reports/knowledge-gaps.md` — what is still unknown
- `reports/drift.md` — intent vs observation disagreements
- `reports/unmapped-files.md` — files not assigned to any domain
- `reports/suspected-legacy.md` — nodes flagged legacy or unused
- `reports/needs-review.md` — ambiguous or needs_human_review items

**9. Compile graph indexes.** Write `nodes.json` and `edges.json`. Generate `file-index.json`:
```bash
python3 <skill_base_dir>/scripts/harvest.py \
  --build-index docs/brain/projects/<name>/graph/nodes.json
```
Save `file-hashes.json` from harvest output.

**10. Write Obsidian config.** Copy `obsidian-vault-config/graph.json` and `app.json` to `docs/brain/.obsidian/`. Only on first onboard (don't overwrite if already present).

**11. Install project-level platform configs.**
```bash
kodebrain project install <root> 2>/dev/null \
  && echo "Platform configs written." \
  || echo "Tip: pip install kodebrain && kodebrain project install . to set up platform configs."
```

**12. Print summary.**
```
Kode Brain onboard complete — <project name>
State:            <onboarding_state>
Domains:          N
Capabilities:     N
Flows:            N
Concepts:         N
Models:           N
Risks:            N
Unmapped files:   N  (see reports/unmapped-files.md)
Drift items:      N  (see reports/drift.md)
Knowledge gaps:   N  (see reports/knowledge-gaps.md)

KB location:      docs/brain/projects/<name>/
Graph view:       Open docs/brain/ as an Obsidian vault → Graph view
```

---

## Sub-command: init

**Purpose:** Scan a project for the first time and produce the initial knowledge map. (Legacy alias — delegates to onboard internally.)

### Steps

Run the same flow as `onboard`. If user specifically requested `init` rather than `onboard`, proceed but mention that `onboard` is the preferred command.

---

## Sub-command: scan

**Purpose:** Re-scan a project that already has a KB. Update changed nodes, add new ones, flag stale ones.

### Steps

1. Load `nodes.json`, `edges.json`, `file-index.json`.
2. Run `python3 <skill_base_dir>/scripts/harvest.py <root> --hashes graph/file-hashes.json`. The script compares SHA-256 hashes and returns only dirty/new files in `files`.
3. For dirty files: look up node IDs in `file-index.json`. Re-narrate affected nodes from the JSON briefs. Set `confidence: supported`.
4. For deleted files (in old hashes but absent from new `hashes`): mark all referenced nodes `confidence: stale`. Add to `reports/needs-review.md`.
5. For new files (in `dirty` but not in `file-index.json`): run domain/capability detection from brief. Write new node if `supported`.
6. Update `nodes.json`. Regenerate `file-index.json` via `--build-index`. Save updated `file-hashes.json`. Print change summary.

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
7. Note confidence and provenance of each referenced node. Explicitly call out any that are `stale`, `inferred`, or `needs_human_review`.

---

## Sub-command: reading-pack

**Purpose:** Generate a focused context pack for a task — includes relevant knowledge, source hints, warnings, AND relevant history.

### Steps

1. Run `/kodebrain query "<task>"` to get seed nodes, required reading, and source files.
2. **Retrieve relevant history:**
   a. Load `history/events.json`. If missing, generate: `python3 <skill_base_dir>/scripts/timeline.py <kb_dir>`
   b. For each affected node from step 1, find events where `linked_nodes` intersects.
   c. Also find: decisions touching same domain, similar past changes, incidents with matching linked_nodes, superseded approaches.
3. Build the reading pack file with sections:
   ```
   ## Required Reading
   ...
   ## Likely Source Files
   ...
   ## Warnings
   ...
   ## Relevant History
   ### Previous Decisions
   ### Similar Past Changes
   ### Incidents / Lessons
   ### Superseded Approaches
   ### Historical Warnings
   ```
4. Write to `docs/brain/projects/<name>/reports/reading-packs/<YYYY-MM-DD>-<slug>.md`.
5. Print: `Reading pack saved to: <path>`

---

## Sub-command: detect-legacy

**Purpose:** Surface suspected dead, duplicate, or partially migrated code.

### Steps

1. Determine scope: all domains or `--domain <slug>`.
2. For each source file in scope, check:
   - Imported by any other file?
   - Referenced in routes?
   - Has tests?
   - Contains `TODO` `DEPRECATED` `@deprecated` comments?
   - Name suggests old version? (`*Old.*` `*V1.*` `*Legacy.*` `*Backup.*`)
   - Newer replacement exists?
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
   a. Read frontmatter: get `source_files`, `status`, `confidence`, `provenance`.
   b. Check each source file still exists.
   c. Check key claims in the body against source: do listed symbols still exist? Does the described flow still match?
   d. Rate: `still_valid` / `likely_stale` / `contradicted` / `unverifiable`
2. For pages with contradicted or stale claims: set `confidence: stale` in frontmatter. Add to `reports/stale-docs.md`. Do NOT rewrite the body.
3. If intent (`knowledge_role: intent`) contradicts observed source, create a drift item in `reports/drift.md`. Do not silently resolve to either side.
4. For pages where source files are gone: add to `reports/needs-review.md`.
5. Print: `Reviewed N pages. Stale: N. Drift: N. Needs review: N.`

---

## Sub-command: update

**Purpose:** Update KB pages affected by recent code changes. Designed to be called by an agent after editing source files — keeps the KB current within a session.

### Steps

1. Get changed files:
   - `--diff`: run `git diff --name-only HEAD`
   - `--files f1 f2 ...`: use provided list
2. Run `python3 <skill_base_dir>/scripts/harvest.py <root> --files <f1> <f2> ...`. Parse the JSON briefs for each changed file.
3. Load `file-index.json`. Find node IDs referencing each changed file.
4. For each affected node, re-narrate from the updated harvest brief:
   - Behavior changed (new/removed exports or routes) → rewrite relevant page sections, set `confidence: supported`
   - Refactor only (no export/route changes) → update `source_files` and `last_updated`, no content change
   - File deleted → set `status: unused`, `confidence: needs_human_review`, add to needs-review.md
5. If this was a material change (behavior, architecture, domain, API, invariant), check for an active change record. If none exists, note that one should be created.
6. Update `file-hashes.json` with new hashes for changed files.
7. Update `nodes.json`. Regenerate `file-index.json` via `--build-index`. Print summary.

---

## Agent Working Pattern (vNext)

An agent working in a KB-enabled codebase must consult history before making material changes:

**Session start — load context:**
```
/kodebrain reading-pack "<task description>"
```
Read the saved reading pack. It contains: relevant domain pages, flow paths, source hints, active warnings, AND relevant history (past decisions, similar changes, incidents, rollbacks).

**Before material changes — consult history, then record intent:**
```
1. Read Project Contract + relevant domain pages
2. Identify affected nodes (domains, capabilities, flows)
3. Load history/events.json (or generate via timeline.py)
4. Find relevant history:
   - Decisions touching same domain/nodes (active AND superseded)
   - Similar past changes (same domain, related architecture)
   - Incidents touching affected nodes or similar patterns
   - Previous rollbacks
5. Surface historical warnings in the active change
6. Create/update active change record in changes/active/
```

**Reading pack must include a Relevant History section:**

```markdown
## Relevant History

### Previous Decisions
- [[decision-id|Decision Title]] — {{why relevant}}
- ...

### Similar Past Changes
- [[change-id|Change Title]] — outcome: {{success/partial/rolled_back}}
- ...

### Incidents / Lessons
- [[incident-id|Incident Title]] — {{lesson summary}}
- ...

### Superseded Approaches
- ...

### Historical Warnings
⚠ This change touches payment retry behavior.
A previous retry redesign caused duplicate captures.
Read [[incident-payment-duplicate-capture]] before editing.
```

**After editing source files — keep the KB current:**
```
/kodebrain update --files src/services/TaskService.ts src/api/tasks/tasks.controller.ts
```

**After implementation — reconcile + capture lessons:**
1. Harvest/review changed files.
2. Compare intended change vs implementation.
3. Update current-state KB pages.
4. Surface drift if intent and implementation diverge.
5. Fill in Outcome, Deviations From Plan, Lessons Learned in the change record.
6. If a new pattern of failure or risk emerged, create an incident record.
7. Mark change reconciled and move to `changes/completed/`.
8. Regenerate: `python3 <skill_base_dir>/scripts/timeline.py <kb_dir>`

**Recording incidents:**
When something goes wrong — architectural mistake, data corruption, migration problem, performance disaster, security near miss, dependency problem, or failed implementation approach — create an incident record in `incidents/`. Use `templates/incident.md`.

**Answering questions during the session:**
```
/kodebrain query "<question>"
```
Answer from KB pages. Read source files directly when: KB reports `confidence: stale`, harvest output is insufficient, dynamic wiring needs verification, or source and KB contradict.

**Rule of thumb:** KB first, source when needed — not KB instead of source. History first for patterns — not KB then surprise.

---

## Behavior Rules

**Never:**
- Delete any KB page or source file
- Set `confidence: verified` (human only)
- Mark a migration `completed`
- Overwrite text inside `<!-- human-note --> ... <!-- /human-note -->` blocks — preserve verbatim
- Claim behavior without source evidence — use `inferred` instead
- Silently resolve intent vs observed conflict — create a drift record
- Rewrite current-state architecture as if unfinished work already exists — use active change records

**Always:**
- State confidence AND provenance in every answer
- Warn when a referenced node is `stale`, `inferred`, or `needs_human_review`
- List source file evidence for every non-trivial claim
- Suggest `/kodebrain scan` when KB appears outdated
- Keep unknowns explicit — do not invent architecture to fill gaps

**When source contradicts KB:** Do not automatically trust either side. Surface as drift. Mark the KB node `stale`. If a human intent statement exists, preserve it — do not let source evidence silently destroy intended truth. If source evidence is clear, record it — do not let stale docs hide real implementation.

---

## Sub-command: benchmark

**Purpose:** Read the generated KB and produce a metrics report — coverage, confidence quality, graph density, risk surface, and an overall health score. Read-only.

**Input:** Optional project path. Default: current directory.

### Steps

1. Locate `docs/brain/projects/<name>/graph/nodes.json`, `edges.json`, `file-index.json`, `file-hashes.json`. If missing, tell the user to run `/kodebrain onboard` first.

2. **Run the benchmark script.**
   ```bash
   python3 <skill_base_dir>/scripts/harvest.py \
     --benchmark docs/brain/projects/<name>/ \
     --source-root <project-root>
   ```
   Parse the JSON output. All counts, percentages, quality scores, degree calculations, and token estimates come from this output — do not recompute them.

3. **Build ASCII graph topology.** Draw a cluster map showing domains, their child node counts, and cross-domain edges as arrows.

4. **Write improvement recommendations.** Based on gaps surfaced by the script, write a prioritized list of HIGH / MED / LOW recommendations.

5. **Write report** to `docs/brain/projects/<name>/reports/benchmark.md`.

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
| supported          | N | NN% |
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
Orphan nodes:          N

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
Drift items:           N

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
- `templates/project.md` — project hub
- `templates/domain.md` — domain hub (vNext order)
- `templates/capability.md`
- `templates/flow.md`
- `templates/concept.md`
- `templates/model.md`
- `templates/decision.md`
- `templates/risk.md`
- `templates/change.md` — active change record
- `templates/architecture-overview.md`
- `templates/architecture-technology.md`
- `templates/architecture-runtime.md`
- `templates/architecture-data.md`
- `templates/architecture-deployment.md`
- `templates/architecture-integrations.md`
- `templates/drift-report.md`
- `templates/knowledge-gaps.md`
- `templates/incident.md`
- `templates/milestone.md`

## History Scripts

- `scripts/timeline.py` — generate history/timeline.md + history/events.json

## Schemas

- `schema/node.schema.json` — KnowledgeNode field definitions (vNext: provenance, knowledge_role, flat IDs)
- `schema/edge.schema.json` — KnowledgeEdge field definitions (vNext: provenance)
- `schema/knowledge-base.schema.json` — top-level graph container (vNext: schema_version, onboarding_state)
