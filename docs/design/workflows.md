# Workflows

Core workflow sequence diagrams. All diagrams use Mermaid syntax.

---

## 1. Initial Mapping Workflow

**Trigger:** `/brain-init <project-root>`

**Purpose:** Produce the first knowledge map for a project.

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant Builder as Knowledge Builder Agent
    participant Architect as Knowledge Architect Agent
    participant Reviewer as Knowledge Reviewer Agent
    participant KB as Knowledge Base (files)

    User->>CLI: /brain-init <project-root>
    CLI->>Builder: projectRoot, ignorePatterns

    Builder->>Builder: scan_project_files()
    Builder->>Builder: extract_symbols()

    Builder->>Architect: file inventory + symbol map
    Architect->>Architect: detect_domains()
    note over Architect: Resolves ambiguous domain boundaries.<br/>Flags conflicts for human review.
    Architect->>Builder: confirmed domain list

    loop per domain
        Builder->>Builder: detect_capabilities()
        Builder->>Builder: extract_flows()
        Builder->>Builder: classify_status() per candidate node
    end

    Builder->>Builder: map_dependencies()
    note over Builder: Builds nodes[] + edges[] + file-index

    loop per node
        Builder->>KB: generate_knowledge_page() → write draft .md
    end

    Builder->>KB: write nodes.json
    Builder->>KB: write edges.json
    Builder->>KB: write file-index.json

    Builder->>Reviewer: all draft pages + source evidence

    loop per draft page
        Reviewer->>Reviewer: review_claims()
    end

    Reviewer->>KB: write reports/unmapped-files.md
    Reviewer->>KB: write reports/suspected-legacy.md
    Reviewer->>KB: write reports/needs-review.md

    KB->>CLI: summary + report paths
    CLI->>User: "Mapped N domains, M capabilities. Review needed-review.md."
```

**Outputs:**
- Domain overview pages
- Capability, concept, flow pages
- `nodes.json` + `edges.json` + `file-index.json`
- `reports/unmapped-files.md`
- `reports/suspected-legacy.md`
- `reports/needs-review.md`

---

## 2. Debugging / Investigation Workflow

**Trigger:** `/brain-query "symptom description"`

**Purpose:** Help a human or coding agent understand where to start for a given problem.

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant Retrieval as Retrieval Agent
    participant KB as Knowledge Base

    User->>CLI: /brain-query "symptom or task"
    CLI->>Retrieval: taskDescription

    Retrieval->>KB: load nodes.json + edges.json + file-index.json
    Retrieval->>Retrieval: match taskDescription → candidate domains + capabilities

    loop per candidate node
        Retrieval->>KB: read page (summary, status, confidence, risks)
    end

    Retrieval->>Retrieval: traverse edges: capability → flows → concepts → models → APIs
    Retrieval->>Retrieval: collect legacy/migration warnings for traversed nodes
    Retrieval->>Retrieval: build_reading_pack()

    Retrieval->>CLI: reading pack
    CLI->>User: Required reading + source files + risks + investigation order
```

**Output shape:**
```
Required reading (ordered):
  1. domain/auth/overview.md         [required]   — domain context
  2. domain/auth/flows/login.md      [required]   — runtime path
  3. domain/auth/concepts/session.md [recommended] — key concept
  4. domain/auth/models/user.md      [optional]   — data shape

Likely source files:
  - src/api/auth/login.ts
  - src/services/AuthService.ts
  - src/repositories/UserRepository.ts
  - src/cache/SessionCache.ts

Risks:
  [HIGH] legacy auth path still active — see caveat: legacy-basic-auth
  [MED]  cache invalidation may not fire on partial updates

Investigation order:
  1. Confirm which route is actually called
  2. Trace service method
  3. Check cache invalidation
  4. Check legacy path
```

---

## 3. Code Change Workflow

**Trigger:** Developer or agent is about to modify source files.

**Purpose:** Ensure KB is read before changes and flagged after changes.

```mermaid
sequenceDiagram
    actor Dev as Developer / Coding Agent
    participant Retrieval as Retrieval Agent
    participant Reviewer as Knowledge Reviewer Agent
    participant KB as Knowledge Base

    Dev->>Retrieval: "I'm about to change: src/services/OrderService.ts"
    Retrieval->>KB: look up file-index.json for OrderService.ts
    Retrieval->>KB: read all referenced KB nodes
    Retrieval->>Dev: reading pack (required reading, risks, warnings)

    Dev->>Dev: reads required KB pages
    Dev->>Dev: reads source files
    Dev->>Dev: makes code changes

    Dev->>Reviewer: changed files + change type
    note over Dev,Reviewer: Change types: behavior_change | refactor | migration | removal | addition

    Reviewer->>KB: re-run extract_symbols() on changed files
    Reviewer->>KB: look up affected nodes via file-index.json

    loop per affected node
        Reviewer->>Reviewer: review_claims() — new source vs. existing page
    end

    alt claims still valid
        Reviewer->>KB: update lastUpdated on node, no other changes
    else claims changed
        Reviewer->>KB: set confidence: stale on affected nodes
        Reviewer->>KB: write reports/needs-review.md entry
    end

    Reviewer->>Dev: summary of affected KB pages + stale flags
```

---

## 4. Legacy Detection Workflow

**Trigger:** `/brain-detect-legacy [--domain <slug>]`

**Purpose:** Surface code that may be unused, duplicated, or partially migrated.

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant Builder as Knowledge Builder Agent
    participant Reviewer as Knowledge Reviewer Agent
    participant KB as Knowledge Base

    User->>CLI: /brain-detect-legacy [--domain auth]
    CLI->>Builder: scope (all or domain slug)

    Builder->>Builder: scan_project_files() — current file list
    Builder->>Builder: extract_symbols() — current symbol usage
    Builder->>Builder: check import graph — find unreferenced symbols/files
    Builder->>Builder: check for signals:
    note over Builder: Signals checked:<br/>- no importers<br/>- no route reference<br/>- TODO/deprecated comments<br/>- duplicate responsibility patterns<br/>- old naming conventions<br/>- missing/failing tests<br/>- no recent git changes

    loop per suspect
        Builder->>Builder: classify_status() — inferred status + confidence
    end

    Builder->>Reviewer: suspect list with signals

    loop per suspect
        Reviewer->>Reviewer: review_claims() — cross-check with existing KB
        Reviewer->>KB: read existing node if mapped
    end

    Reviewer->>KB: write reports/suspected-legacy.md
    note over Reviewer,KB: NEVER auto-delete.<br/>Always write to report for human review.

    KB->>CLI: report path
    CLI->>User: "Found N suspects. Review reports/suspected-legacy.md"
```

**Report format for each suspect:**
```
## src/services/OldPaymentService.ts

Status: suspected_unused
Confidence: inferred
Signals:
  - No files import this module
  - Replaced by: src/services/PaymentV2Service.ts (inferred)
  - Last modified: 2024-11-03
  - No tests reference this service

Action required: Human must confirm before deletion
```

---

## 5. Reading Pack Workflow

**Trigger:** `/brain-reading-pack "task description"`

**Purpose:** Generate a focused context bundle for a specific task.

This is similar to the Debugging workflow but always produces a structured, saveable output rather than just an investigation guide.

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant Retrieval as Retrieval Agent
    participant KB as Knowledge Base

    User->>CLI: /brain-reading-pack "Add due date to approval request"
    CLI->>Retrieval: taskDescription

    Retrieval->>KB: load graph (nodes + edges)
    Retrieval->>Retrieval: parse task → extract entity names + action verbs
    Retrieval->>Retrieval: match to domain/capability nodes

    Retrieval->>KB: load matched domain overview page
    Retrieval->>KB: traverse: capability → flows → models → apis → concepts
    Retrieval->>Retrieval: filter by: required | recommended | optional

    Retrieval->>KB: collect source files from all required nodes
    Retrieval->>Retrieval: collect risks, legacy warnings, migration states

    Retrieval->>CLI: structured reading pack (JSON + Markdown)
    CLI->>User: saves to .brain/reading-packs/<date>-<slug>.md
```

**Reading pack file format:**
```md
---
task: Add due date to approval request
generated: 2026-05-07
domain: workflow
confidence: source_supported
---

## Required Reading

1. [Workflow Domain Overview](domains/workflow/overview.md) — required
2. [Create Approval Request](domains/workflow/capabilities/create-approval-request.md) — required
3. [Approval Request Model](domains/workflow/models/approval-request.md) — required
4. [Approval Request Flow](domains/workflow/flows/create-approval-request.md) — required

## Source Files

- src/models/ApprovalRequest.ts
- src/services/ApprovalService.ts
- src/api/routes/approval.ts
- src/repositories/ApprovalRepository.ts
- tests/approval/create.test.ts

## Warnings

- [HIGH] Approval model is partially migrated — old schema still in use for legacy forms
- [MED] due_date field may interact with auto-close scheduler (see: AutoCloseFlow)

## Recommended Investigation Order

1. Read model to understand current schema
2. Check migration state for old approval schema
3. Confirm API route accepts and validates date fields
4. Check if due_date needs to propagate to notification flow
```

---

## 6. KB Update From Diff Workflow

**Trigger:** `/brain-update --diff <git-diff-output>` or post-merge hook (future)

**Purpose:** Detect which KB pages are affected by a set of file changes and flag them for update.

```mermaid
sequenceDiagram
    participant CLI
    participant Reviewer as Knowledge Reviewer Agent
    participant KB as Knowledge Base

    CLI->>Reviewer: list of changed files (from git diff or hook)
    Reviewer->>KB: look up file-index.json → affected node IDs
    Reviewer->>KB: read affected node pages

    loop per affected node
        Reviewer->>Reviewer: review_claims() with new source evidence
        alt no claim conflict
            Reviewer->>KB: update lastUpdated
        else claim conflict detected
            Reviewer->>KB: set confidence: stale
            Reviewer->>KB: append to reports/stale-docs.md
        end
    end

    Reviewer->>KB: write reports/needs-review.md
    KB->>CLI: summary of affected + stale nodes
```
