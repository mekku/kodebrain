# Agent Role Boundaries

Agents are orchestrators. They call skills, make decisions about ordering and retry, and write outputs to the knowledge base. They are not skills themselves.

Each agent has a narrow responsibility. Agents should not grow beyond their defined scope.

---

## Design Rules

- An agent must state which skills it uses.
- An agent must state what it cannot do.
- An agent must state what requires human review before proceeding.
- Agents do not call other agents directly. They produce outputs that other agents can read.
- An agent may read any KB page. It may only write pages within its defined scope.

---

## 1. Knowledge Builder Agent

**Trigger:** `/brain-init`, `/brain-scan`

**Responsibility:** Scan a project and produce the initial or updated draft knowledge map.

**Allowed skills:**
- `scan_project_files`
- `extract_symbols`
- `detect_domains`
- `detect_capabilities`
- `extract_flows`
- `map_dependencies`
- `classify_status`
- `generate_knowledge_page`

**Allowed writes:**
- `docs/brain/projects/<name>/domains/**`
- `docs/brain/projects/<name>/graph/nodes.json`
- `docs/brain/projects/<name>/graph/edges.json`
- `docs/brain/projects/<name>/graph/file-index.json`
- `docs/brain/projects/<name>/reports/unmapped-files.md`
- `docs/brain/projects/<name>/reports/suspected-legacy.md`

**Forbidden:**
- Marking any node `verified` (only humans can)
- Deleting existing KB pages
- Overwriting human-authored notes or decisions without a conflict marker
- Modifying source code
- Upgrading inferred confidence to source_supported without source evidence

**Conflict behavior:** If a page already exists, the builder diffs its existing content against the new draft. If human notes exist in the page (flagged by `<!-- human-note -->`), those sections are preserved unchanged and the rest is updated. The builder writes a diff summary alongside the update.

**Outputs:**
```
- Draft domain overview pages
- Draft capability pages
- Draft concept pages (top 5-10 inferred concepts)
- Draft flow pages
- nodes.json + edges.json + file-index.json
- unmapped-files.md
- suspected-legacy.md
```

---

## 2. Knowledge Architect Agent

**Trigger:** Called by Knowledge Builder when domain boundaries are ambiguous, or invoked manually via `/brain-review --taxonomy`

**Responsibility:** Resolve taxonomy decisions — domain boundaries, concept naming, page splits/merges.

**Allowed skills:**
- `detect_domains` (re-run with revised parameters)
- `generate_knowledge_page` (for naming/boundary updates)

**Allowed writes:**
- Domain `overview.md` files (structure only, not content)
- `docs/brain/projects/<name>/graph/nodes.json` (rename or reclassify nodes)

**Forbidden:**
- Adding or removing source evidence
- Changing status or confidence labels
- Modifying flow or capability page content
- Modifying source code

**Required human review before:**
- Renaming a domain (ID change breaks all edges pointing to it)
- Splitting a capability into two (may hide a real coupling)
- Merging two concepts into one (may lose nuance)
- Changing a node's type (e.g., `concept` → `capability`)

**Outputs:**
```
- Revised domain list with justification
- Renamed/merged/split node proposals (pending human approval)
- Taxonomy decision notes
```

---

## 3. Knowledge Reviewer Agent

**Trigger:** `/brain-review`, post-code-change hook (when implemented)

**Responsibility:** Check whether existing KB pages accurately reflect current source code.

**Allowed skills:**
- `review_claims`
- `classify_status`
- `extract_symbols` (re-run to get current state)

**Allowed writes:**
- `docs/brain/projects/<name>/reports/stale-docs.md`
- `docs/brain/projects/<name>/reports/missing-evidence.md`
- `docs/brain/projects/<name>/reports/needs-review.md`
- Adding `confidence: stale` or `needs_human_review` to existing page frontmatter

**Forbidden:**
- Deleting KB pages (can only flag them)
- Changing a node's status label from `active` to `unused` (requires human review)
- Removing source evidence (can only add review notes)
- Marking anything `verified`
- Automatically rewriting page content

**Required human review before:**
- Marking a legacy path as safe to delete
- Changing any `verified` node's status
- Marking a migration as `completed`

**Outputs:**
```
- stale-docs.md  — pages where claims contradict current source
- missing-evidence.md  — pages with claims that lack source support
- needs-review.md  — items requiring human decision
```

---

## 4. Retrieval Agent

**Trigger:** `/brain-query <task>`, `/brain-reading-pack <task>`

**Responsibility:** Answer project questions and produce context packs for tasks.

**Allowed skills:**
- `build_reading_pack`

**Allowed reads:** All KB pages, nodes.json, edges.json, file-index.json

**Allowed writes:** None. This agent is read-only.

**Forbidden:**
- Answering from memory or training data when KB/source evidence exists
- Treating `inferred` or `ambiguous` pages as authoritative
- Creating or modifying any KB content

**Behavior when KB is incomplete:**
- Always state confidence level of the answer
- Flag when relevant KB pages are `stale`, `inferred`, or `needs_human_review`
- Recommend re-running `/brain-scan` when coverage is insufficient

**Outputs:**
```
Required reading list (ordered by priority)
Likely source files
Risk warnings (legacy paths, migration states, stale cache behavior)
Recommended investigation order
```

---

## 5. Coding Agent

**Trigger:** Before modifying source code (manual query or future pre-edit hook)

**Responsibility:** Query the KB before editing, and flag KB pages that need updating after changes.

**Allowed skills:**
- `build_reading_pack` (to get context before editing)
- `review_claims` (to check what changed after editing)

**Allowed reads:** All KB pages

**Allowed writes:**
- `docs/brain/projects/<name>/reports/needs-review.md` — flag pages that may be stale after its changes

**Forbidden:**
- Editing blindly from search results without reading required KB pages
- Ignoring `legacy` or `migration` warnings in the reading pack
- Creating architecture-level changes without a corresponding `decision` node proposal
- Marking pages as `stale` without having actually read them

**Required behavior before editing:**
1. Query KB with task description
2. Read all `required` priority pages from the reading pack
3. Read listed source files
4. Note any `legacy` or `partially_migrated` warnings

**Required behavior after editing:**
1. Identify which KB pages reference the changed files (via file-index.json)
2. Flag those pages for review in needs-review.md
3. If behavior changed: draft updated content for the relevant flow or capability page

**Outputs:**
```
Pre-edit: reading pack (via Retrieval Agent)
Post-edit: needs-review.md entries for affected KB pages
Post-edit (optional): draft updated KB page content
```

---

## Agent Interaction Map

```
User / CLI
  │
  ├─ /brain-init, /brain-scan
  │     └─ Knowledge Builder Agent
  │           └─ [when taxonomy ambiguous] → Knowledge Architect Agent
  │
  ├─ /brain-review
  │     └─ Knowledge Reviewer Agent
  │
  ├─ /brain-query, /brain-reading-pack
  │     └─ Retrieval Agent
  │
  └─ [before code change]
        └─ Coding Agent
              ├─ Retrieval Agent (pre-edit context)
              └─ Knowledge Reviewer Agent (post-edit flagging)
```

---

## What No Agent Can Do

These actions are reserved for humans:

| Action | Reason |
|---|---|
| Set `confidence: verified` on any node | Only humans can verify |
| Delete a KB page | May contain non-obvious value |
| Delete source code | Unused ≠ safe to delete |
| Mark a migration `completed` | Requires human confirmation |
| Rename a domain after initial mapping | ID stability required |
| Approve architecture decisions | Human judgment required |
| Upgrade a `needs_human_review` node | Requires explicit human sign-off |
