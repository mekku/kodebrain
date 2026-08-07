# Context Infrastructure Roadmap

**Status:** DRAFT v0.1 — design and implementation roadmap
**Created:** 2026-08-07
**Scope:** Kode Brain context construction, repo-local semantic recall, Git evidence, historical reconstruction
**Related experiment:** `mekku/git-rag`

---

## 1. Purpose

Kode Brain is evolving from a project documentation system into **context infrastructure for humans and coding agents**.

The current hierarchy is valuable because it gives project knowledge structure, ownership, and a deterministic reading path. However, hierarchy alone can create a narrow reading frame: an agent may route correctly into one domain or capability, drill down, and fail to recall related decisions, risks, active changes, historical context, or cross-domain knowledge that uses different language.

Semantic retrieval solves a different problem. It can surface information that is plausibly related to the current task even when that information is not on the structural path selected by the hierarchy.

The target system therefore combines both:

```text
Hierarchy answers:
"Where does this belong?"

Semantic recall answers:
"What else might matter?"

History answers:
"How did the current state get here?"

Evidence answers:
"What can we verify from the repository?"
```

The primary goal of this roadmap is to build a **repo-local context assembly layer** that combines these signals without introducing a separate RAG server or making a vector store another source of truth.

---

## 2. Non-Negotiable Principles

### 2.1 Git is the repository file authority

Kode Brain must not maintain independent hard-coded ignore rules in every scanner.

For a Git-backed project, the canonical working file universe is derived from Git semantics:

```bash
git ls-files --cached --others --exclude-standard
```

This includes:

- tracked files,
- new untracked files that are not ignored,
- excludes files ignored by repository, info/exclude, and configured Git ignore rules.

Tracked files remain part of the project even if an ignore rule later matches them.

All modules that need the project file universe should consume the same deterministic primitive rather than independently traversing `project_root`.

### 2.2 Knowledge travels with the repository; retrieval indexes do not need to

The project must remain self-contained in Git.

Committed/project-distributed state includes:

- Project Contract and canonical knowledge,
- Knowledge Map,
- Decisions / Changes / Incidents / History,
- retrieval configuration and schema,
- provenance and stable identifiers.

Machine-local derived state may include:

- vector embeddings,
- local vector database,
- query cache,
- downloaded embedding model.

Deleting all local retrieval state must never destroy project knowledge. It must be rebuildable from repository content.

### 2.3 No retrieval server is required

Repo-local retrieval is an embedded capability of Kode Brain.

The default architecture must not require a separately deployed Qdrant, PostgreSQL, Pinecone, Elasticsearch, or other retrieval service merely to work with one repository.

A local embedded store such as LanceDB is acceptable as an implementation detail, but the knowledge model must not depend on a specific storage engine.

### 2.4 Vector search is recall, not authority

A vector hit means:

> "This knowledge unit may be relevant."

It does not mean:

> "This text is true."

Retrieval entries must point back to canonical or evidential sources. The agent should read the current source material after retrieval instead of treating a stale embedded copy as authoritative.

### 2.5 Structural routing and semantic recall are complementary

Context construction should use both:

```text
Context = Structural Route + Semantic Recall + Relevant History + Targeted Evidence
```

Neither structural hierarchy nor vector retrieval should independently decide the full agent context.

### 2.6 History is reconstructed only as deeply as current understanding requires

For brownfield projects Kode Brain must not require chronological reconstruction from the repository's first commit.

Historical investigation starts from **current concepts and unresolved knowledge gaps**, searches backward for relevant evidence, fills missing provenance/history slots, and stops when current knowledge is sufficiently explained or when a design boundary makes older history irrelevant to the current concern.

### 2.7 Historical uncertainty must remain explicit

Git proves implementation changes. Commit messages may provide stated rationale. LLM interpretation is inference.

These must remain distinguishable.

If rationale cannot be recovered, store `unknown`; do not fabricate a Decision from the current source layout.

---

## 3. Target Architecture

```text
                          USER / AGENT TASK
                                 │
                                 ▼
                         CONTEXT ASSEMBLER
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            ▼                    ▼                    ▼
   STRUCTURAL ROUTING      SEMANTIC RECALL      HISTORY RECALL
   hierarchy / graph       local vector index   episodic lineage
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                                 ▼
                      TARGETED EVIDENCE EXPANSION
                         source / tests / config / Git
                                 │
                                 ▼
                         WORKING CONTEXT PACK
                                 │
                                 ▼
                               AGENT
```

The underlying project information model remains:

```text
Intended / Canonical Knowledge
            ↓
      Knowledge Map
            ↓
Evidence: current Git tree / source / runtime / tests

Temporal axis:
Current knowledge ← historical lineage ← older designs
```

---

## 4. Ownership Boundaries in Existing Canonical Specs

This document is a cross-cutting implementation/design roadmap. It does **not** become a new canonical root child.

When the design stabilizes, normative semantics are incorporated into existing owners:

| Concern | Canonical owner |
|---|---|
| Git/project file universe as evidence input | `spec/knowledge-model.md` |
| semantic recall meaning and non-authority | `spec/knowledge-model.md` |
| context assembly / agent pre-work process | `spec/workflow-model.md` |
| backward history tracing / history retrieval | `spec/history-model.md` |
| repo layout/config for retrieval | `spec/project-model.md` |
| validation of committed vs derived artifacts | `spec/onboard-validation-gate.md` where necessary |

Implementation plans and SKILL instructions derive from those specs after promotion.

---

## 5. Component A — Git Project File Universe

### 5.1 Problem

Current scanners can independently recurse over the repository and maintain their own ignore lists. This produces inconsistent project boundaries and has already caused comparison logic to scan nested dependencies such as `web/node_modules/...`.

### 5.2 Required primitive

Add one shared module, conceptually:

```text
project_files.py
```

Minimum API:

```python
get_project_files(root)       # tracked + non-ignored untracked files
get_tracked_files(root)       # files in Git index
get_untracked_files(root)     # non-ignored working tree files
get_changed_files(root)       # working tree/index changes when needed
get_repo_head(root)           # current HEAD identity
```

`get_project_files()` should use Git semantics when `.git` is available.

For non-Git directories, Kode Brain may use a clearly separate fallback policy. Fallback behavior must not redefine Git semantics for Git-backed projects.

### 5.3 Required consumers

At minimum, migrate these to the shared file universe:

- deterministic inventory / harvest,
- intent↔observed comparison,
- source mapping,
- benchmark coverage,
- future semantic indexing,
- future history candidate extraction where current-tree files are relevant.

### 5.4 Acceptance

Given a monorepo containing:

```text
src/
web/src/
web/node_modules/
packages/app/dist/
```

where dependencies/build outputs are ignored by Git, every Kode Brain source consumer must observe the same project file set and must not include ignored nested paths.

---

## 6. Component B — Repo-Local Semantic Recall

### 6.1 Purpose

Semantic recall complements the deterministic hierarchy and reduces tunnel vision.

The first retrieval corpus should be **Kode Brain knowledge itself**, not raw source and not all Git commits.

This tests the smallest useful hypothesis:

> Does semantic recall of current project knowledge improve agent context beyond hierarchy-only navigation?

### 6.2 Initial corpus

Index knowledge units from:

- Project Contract,
- architecture pages,
- domain hubs,
- capabilities,
- flows,
- concepts,
- models,
- risks/caveats,
- Decisions,
- Active Changes,
- Incidents,
- durable History documents.

Reports and machine-generated indexes should not become semantic truth merely because they are searchable.

### 6.3 Knowledge unit granularity

Do not default to arbitrary fixed-token chunking.

Prefer semantic sections tied to a canonical identity:

```json
{
  "key": "ai-transcription#constraints",
  "node_id": "ai-transcription",
  "document": "domains/ai/capabilities/ai-transcription.md",
  "section": "Constraints",
  "type": "capability",
  "domain": "ai",
  "content_hash": "..."
}
```

The vector representation is derived from the section text. The pointer and identity allow the current canonical source to be re-read after retrieval.

### 6.4 Query contract

Add a primitive conceptually equivalent to:

```text
kodebrain index
kodebrain recall "<query>"
```

`recall` returns ranked candidates, not a generated answer.

Expected result shape:

```json
{
  "query": "change voice transcription provider",
  "hits": [
    {
      "node_id": "ai-transcription",
      "section": "Constraints",
      "document": "...",
      "score": 0.82,
      "type": "capability",
      "domain": "ai"
    }
  ]
}
```

### 6.5 Local distribution model

Example layout:

```text
repo/
  docs/brain/                     # committed knowledge
  .kodebrain/
    retrieval.yaml                # committed configuration
  .kodebrain/cache/               # ignored derived state
    retrieval/
      ... local vector index ...
```

The exact path may change, but the invariant is:

```text
source + config = portable
index = rebuildable local cache
```

### 6.6 Embedding configuration

Embedding model identity must be recorded in the local index manifest/config.

Changing model or embedding dimensions invalidates the index and triggers rebuild.

The model itself should be installed/cached globally per developer machine rather than committed into each repository.

Example conceptual configuration:

```yaml
retrieval:
  schema_version: 1
  embedding_model: bge-m3
  chunking: semantic-section
  index_scope:
    - project_contract
    - architecture
    - domains
    - decisions
    - active_changes
    - history
```

Implementation may initially reuse the LanceDB approach proven in `mekku/git-rag`, but storage remains replaceable.

---

## 7. Component C — Context Assembly

### 7.1 Problem

Agents currently depend heavily on the hierarchy / reading instructions. Correct routing is useful, but agents can miss semantically relevant side-context outside the selected branch.

### 7.2 Required process

Before a material task, construct context in stages:

```text
1. Structural Route
   Find canonical owner / relevant domain / capability / flow.

2. Semantic Recall
   Retrieve related current knowledge outside the structural path.

3. Relevant History
   Retrieve known Decisions, Incidents, historical lineage, previous changes.

4. Evidence Expansion
   Open source/config/tests/Git only where verification is needed.

5. Context Pack
   Merge, deduplicate, prioritize, and pass to agent.
```

### 7.3 Context pack provenance

Every context item should preserve why it was included:

```yaml
source: domains/ai/capabilities/ai-transcription.md
reason: semantic_recall
score: 0.82
canonical: true
```

or:

```yaml
source: domains/interview/interview.md
reason: structural_route
```

This makes the retrieval path inspectable and benchmarkable.

### 7.4 Ranking principle

Structural relevance has priority for authoritative task framing. Semantic recall broadens the context.

Do not let a high vector score displace the canonical owner of the concern.

Conceptually:

```text
Primary context = canonical route
Supplemental context = semantic + temporal recall
```

---

## 8. Component D — Backward Historical Tracing

### 8.1 Purpose

Brownfield onboarding should recover enough semantic history to explain current knowledge without reconstructing the entire Git timeline.

The process begins from current concepts and knowledge gaps.

### 8.2 Example

Current observation:

```text
Transcription provider = Whisper
```

Accepted/current project intent may say:

```text
Voice transcription = Wispr local
```

Knowledge gaps:

```text
- Was Whisper an intentional replacement?
- When did the change happen?
- Why did it happen?
- Is the current spec stale or is source temporary drift?
```

Historical tracing searches backward for commits related to transcription, Wispr, Whisper, or the affected source paths.

Once it finds a transition such as:

```text
Wispr → Whisper
```

with sufficient evidence, it records the lineage and can stop unless older history is still material.

### 8.3 History-needed slots

Historical tracing should be driven by explicit unresolved slots rather than "read history until it feels enough".

Example:

```yaml
concept: ai-transcription
history_needed:
  introduced_by: unknown
  predecessor: unknown
  transition_commit: unknown
  rationale: unknown
  supersedes: unknown
```

Each inspected commit may fill zero or more slots.

### 8.4 Stop conditions

Stop tracing backward when any applicable condition is met:

1. Required history slots are fulfilled.
2. A clear design boundary is reached and older design is not relevant to the current question.
3. Older commits no longer belong to the current lineage.
4. Search depth/cost threshold is reached; unresolved values remain explicitly `unknown`.
5. An authoritative Decision already explains the transition.

### 8.5 Design boundary

A design transition is a natural lazy-history boundary.

```text
Current Design C
       ↑
   B → C transition
       ↑
Older Design B
```

For current work, Kode Brain may materialize only C and the B→C transition.

Older B history remains expandable later if a future task requires it.

### 8.6 Evidence model

Historical extraction must distinguish:

```text
Observed change     ← commit diff
Stated rationale    ← commit title/body / PR/ADR if available
Inferred impact     ← model interpretation
```

Example:

```yaml
observed_change:
  value: "WhisperTranscriber introduced"
  provenance: git_diff

rationale:
  value: "reduce local deployment dependency"
  provenance: commit_message

impact:
  value: "changes the voice transcription integration boundary"
  provenance: generated
  confidence: inferred
```

Never upgrade generated rationale into an authoritative Decision without supporting evidence or human confirmation.

---

## 9. Component E — Semantic Git Retrieval as a Candidate Selector

The `mekku/git-rag` experiment demonstrates a useful primitive:

```text
commit diff
   ↓
topic extraction
   ↓
embedding
   ↓
semantic commit/topic candidates
```

Kode Brain should reuse the **concept**, not necessarily the standalone application architecture.

Git semantic retrieval is not historical truth storage. It is a candidate-selection accelerator for backward tracing.

Example:

```text
Knowledge gap:
"Why does InterviewSchema have no lifecycle?"
        ↓
Semantic history query
        ↓
Candidate commits:
- schema refactor
- remove schema status
- initial builder implementation
        ↓
Inspect actual Git evidence
        ↓
Fill history slots / stop
```

Raw retrieval results never directly become a Decision or current truth.

---

## 10. Component F — Historical Accumulation

### 10.1 New / already-onboarded projects

Once Kode Brain is active in a project, semantic history should accumulate incrementally.

Instead of repeatedly reconstructing the full past:

```text
Historical Knowledge(t+1)
  = Historical Knowledge(t)
  + relevant new changes
```

A local model may classify and summarize changes as part of normal project reconciliation.

### 10.2 Historical significance filter

Not every commit deserves durable semantic history.

Likely durable categories:

- architecture/design transition,
- technology/provider migration,
- important feature introduction/removal,
- Decision change,
- migration,
- significant incident/root cause,
- failed approach worth remembering,
- new invariant/constraint,
- major runtime/data behavior change.

Likely ephemeral categories:

- formatting,
- typo fixes,
- mechanical rename without semantic change,
- routine dependency patch with no relevant impact,
- generated artifacts.

### 10.3 Durable output

Durable history should become repository knowledge (record or history document), not remain only in a vector DB.

```text
Git evidence
   ↓
historical interpretation
   ↓
durable Kode Brain history record
   ↓
commit to repo
   ↓
local semantic index includes it automatically
```

---

## 11. Brownfield Onboarding Flow vNext

Target brownfield flow after these components mature:

```text
1. Resolve Git project file universe
        ↓
2. Discover and resolve intent sources
        ↓
3. Map current architecture/domains/capabilities
        ↓
4. Build current canonical Knowledge Map
        ↓
5. Detect material knowledge gaps / intent-observed disagreements
        ↓
6. Semantic recall over current KB
        ↓
7. Backward trace selected concepts through Git history
        │
        ├─ retrieve candidate commits/topics
        ├─ inspect actual diffs/messages
        ├─ fill provenance/history slots
        └─ stop at fulfilment / design boundary
        ↓
8. Persist durable historical lineage
        ↓
9. Ask human only for remaining material ambiguity
        ↓
10. Validate and finish onboarding
```

Human questions should become evidence-backed.

Bad:

```text
"Why does this project use Whisper?"
```

Better:

```text
"The current implementation uses Whisper while the accepted spec still says Wispr.
Git history shows the change was introduced in commit X, but no rationale is recorded.
Was this an intentional replacement of the spec or a temporary implementation?"
```

---

## 12. Greenfield Flow

Greenfield starts differently:

```text
1. Establish Project Contract
2. Define architecture/domains/constraints
3. Begin implementation
4. Current KB + active changes travel with repo
5. Local semantic index is built from current KB
6. History accumulates from meaningful changes from day one
```

No historical reconstruction is needed because history begins accumulating at project birth.

---

## 13. Roadmap

### Phase 0 — Correct the Substrate

**Goal:** one trustworthy project file universe and correct graph typing before adding retrieval complexity.

Work:

- implement shared Git-backed `project_files` primitive;
- migrate source scanners/comparison to it;
- remove independent recursive source traversal where unnecessary;
- complete explicit node `type:` contract + legacy tag fallback/mismatch validation from the external dogfood fix;
- reduce current intent comparator false-positive behavior enough that external dogfood is usable.

Exit gate:

```text
sampard-ai comparison contains no ignored dependency paths;
node types compile correctly;
current validation output is small enough to inspect meaningfully.
```

### Phase 1 — Semantic Recall MVP

**Goal:** prove that local semantic recall adds useful context to hierarchy-only navigation.

Work:

- define semantic knowledge-unit extraction from `docs/brain`;
- add local retrieval manifest;
- add embedded index implementation;
- implement `kodebrain index`;
- implement `kodebrain recall <query>`;
- return canonical pointers and metadata, not answers;
- implement stale-content hash/reindex behavior.

Exit gate:

- clone repo + build local index without server;
- deleting local cache and rebuilding yields equivalent retrievable units;
- retrieval never becomes required canonical state.

### Phase 2 — Context Assembler

**Goal:** combine hierarchy and semantic recall before agent work.

Work:

- structural route output format;
- semantic recall output format;
- merge/dedup/ranking;
- context-pack provenance;
- agent workflow integration;
- add `Relevant Semantic Context` alongside structural reading pack.

Experiment:

```text
Agent A = hierarchy only
Agent B = hierarchy + semantic recall
```

Measure:

- relevant docs discovered,
- missed cross-domain constraints,
- wrong-domain edits,
- source files opened before correct edit,
- rework / reviewer correction,
- total context cost.

Do not continue expanding retrieval if B does not materially improve downstream task quality.

### Phase 3 — Git History Candidate Retrieval

**Goal:** use semantic retrieval to identify likely historical evidence, not to build full history.

Work:

- extract Git commits/diffs using Git-authoritative paths;
- adapt useful primitives from `mekku/git-rag`;
- decompose relevant commits into semantic topics where useful;
- build local history retrieval corpus;
- keep links to exact commit SHA and affected files;
- support history queries scoped by node/domain/file/time.

Exit gate:

Given a known historical change, the system should retrieve the relevant commit/topic in a small candidate set and always preserve the commit SHA for verification.

### Phase 4 — Backward Historical Tracer

**Goal:** recover only the ancestry required to explain current concepts/gaps.

Work:

- history-needed slot model;
- backward candidate inspection;
- evidence extraction;
- design-boundary recognition;
- explicit stop conditions;
- persist lineage and unresolved unknowns;
- human escalation only after evidence search.

Exit gate:

For selected brownfield concepts, tracing produces an explainable current lineage without processing the repository's complete history.

### Phase 5 — Incremental Historical Accumulation

**Goal:** make future projects cheaper to understand as they age.

Work:

- classify historical significance at Change reconciliation / commit intervals;
- local model support for constrained extraction;
- update durable history/Decision/Incident/Milestone records where appropriate;
- maintain last-processed history marker;
- process only new relevant history incrementally.

Exit gate:

Once initialized, normal project evolution does not require full-history reconstruction again.

### Phase 6 — Brownfield Onboard Integration

**Goal:** integrate backward tracing into onboarding only after the primitives are proven.

Work:

- gap-driven historical investigation after current map;
- evidence-backed adaptive interview;
- cost/depth limits;
- onboarding reports for resolved/unknown historical slots;
- explicit distinction between recovered evidence and inferred interpretation.

Exit gate:

Active legacy repositories can gain useful current + historical context without requiring chronological ingestion of every commit.

---

## 14. What We Are Explicitly Not Building Yet

- a centralized Kode Brain cloud vector service;
- a mandatory RAG server;
- a vector DB as canonical project memory;
- full-repository raw-source embedding as the first retrieval corpus;
- chronological LLM summarization of every historical commit;
- automatic conversion of Git changes into authoritative Decisions;
- autonomous semantic drift resolution;
- perfect historical reconstruction for inactive/archived projects;
- complex multi-agent memory orchestration before context assembly is proven useful.

---

## 15. Evaluation Strategy

Each phase must be evaluated on downstream usefulness rather than internal elegance.

### Retrieval quality

Measure:

- precision of top-k current-KB retrieval,
- useful context recalled outside structural route,
- irrelevant context added,
- stale index behavior,
- deterministic rebuildability.

### Agent effectiveness

Compare same model and task with/without semantic context assembly.

Measure:

- files/docs opened,
- turns before correct mental model,
- architecture/domain mistakes,
- rework,
- tests/reviewer feedback,
- ability to explain why surrounding context matters.

### Historical tracing

Measure:

- candidate commits inspected versus total history,
- recovered `introduced_by` / predecessor / transition / rationale slots,
- false rationale invention rate,
- number/quality of human questions remaining,
- whether the tracer stops at sensible design boundaries.

The desired property is not maximum recall. It is **minimum sufficient trustworthy context**.

---

## 16. Initial Implementation Sequence

The next implementation work should proceed in this order:

```text
1. Git file authority
2. Finish node-type/compiler substrate
3. Stabilize current intent comparison enough for external dogfood
4. Semantic KB indexing
5. `recall` primitive
6. context assembler experiment
7. Git history semantic candidate retrieval
8. backward historical tracing
9. incremental historical accumulation
10. brownfield onboard integration
```

Do not start with historical reconstruction. First prove that repo-local semantic recall improves context assembly on current knowledge.

---

## 17. Definition of Done for This Initiative

This initiative is mature when all of the following are true:

- [ ] Every Git-backed source consumer uses a shared Git-authoritative project file universe.
- [ ] Kode Brain requires no external retrieval server for normal repository use.
- [ ] Retrieval indexes are machine-local, rebuildable, and non-canonical.
- [ ] Repo-distributed knowledge/config is sufficient to reconstruct retrieval state.
- [ ] Semantic recall returns canonical pointers with provenance, not independent truth.
- [ ] Agent context combines structural routing and semantic recall.
- [ ] A/B dogfood demonstrates measurable benefit from semantic recall.
- [ ] Git history retrieval returns candidate evidence with exact commit identity.
- [ ] Brownfield history tracing starts from current gaps and moves backward selectively.
- [ ] Historical tracing has explicit stop conditions and preserves unknowns.
- [ ] Design changes act as lazy history boundaries unless older lineage is requested.
- [ ] Durable historical findings are committed as Kode Brain knowledge, not trapped in the vector cache.
- [ ] Ongoing projects accumulate semantic history incrementally after onboarding.
- [ ] Human onboarding questions are materially reduced and become evidence-backed.

---

## 18. Guiding Mental Model

The compact model for future implementation decisions is:

```text
Git Tree
  = what belongs to the working project

Canonical Kode Brain
  = what the project means / what should be true

Hierarchy
  = where to start reading

Semantic Recall
  = what else may matter

Git History
  = evidence of how implementation evolved

Historical Knowledge
  = durable interpretation of meaningful evolution

Context Assembler
  = the layer that combines enough of the above before an agent acts
```

The objective is not to give an agent all available context.

The objective is to give it **the smallest trustworthy context that is sufficient to make the next decision well**.
