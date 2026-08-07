# Kode Brain vNext — Implementation Plan

**Status:** Execution plan
**Depends on:** `docs/design/spec.md`
**Last aligned:** 2026-08-07

> This document is written for an implementation agent. Execute phases in order. Do not redesign the product while implementing unless the spec is internally impossible; surface contradictions instead.

---

## 0. Goal

Migrate the current Kode Brain implementation from a codebase-first knowledge mapper into the vNext model defined in `docs/design/spec.md`:

- greenfield + brownfield onboarding,
- project-level contract and architecture,
- gap-driven/resumable onboarding,
- human intent alignment when needed,
- progressive mapping,
- intent vs observed reality,
- drift detection,
- change-first workflow,
- Markdown-first canonical knowledge with generated indexes.

Do not attempt to implement every future optimization in one pass. Preserve working behavior where possible while moving the authority model and onboarding workflow first.

---

## 1. Known Current Inconsistencies To Resolve

Before adding behavior, normalize contradictory contracts across the repo.

Known examples:

- README title/references still use `kb-builder` in places while package/product is Kode Brain.
- `pyproject.toml` Homepage points to the old repository path.
- README says the project is still design-only although implementation exists.
- taxonomy/schema use hierarchical IDs such as `auth/login-flow` while current `SKILL.md` and templates use flat IDs such as `auth-login-flow`.
- older workflows use `/brain-init` and `overview.md`; current skill uses `/kodebrain init` and `<domain>.md`.
- JSON schema uses fields such as `sourceFiles`/`lastUpdated`; Markdown frontmatter uses `source_files`/`last_reviewed`.
- generated graph files and Markdown currently behave like parallel write authorities.

### Acceptance criteria

- one canonical name for every command/path/field introduced by vNext,
- schema, templates, examples, and skill instructions agree,
- no vNext code relies on conflicting legacy wording,
- historical docs may remain but must be clearly marked superseded where necessary.

---

## 2. Phase A — Canonical Data Model

### Objective

Define the minimum machine-readable model required by vNext before workflow changes.

### Work

1. Add/modify schemas for project-level knowledge.
2. Separate provenance from confidence.
3. Add enough structure to represent intended vs observed claims and drift.
4. Add KB/schema version metadata for migration detection.
5. Choose and enforce one node ID format globally.

### Recommended schema concepts

#### Provenance

At minimum support:

```text
human
project_document
source_code
configuration
runtime
test
git
generated
```

#### Confidence

At minimum support:

```text
verified
supported
inferred
ambiguous
stale
needs_human_review
```

If maintaining legacy confidence values temporarily, provide deterministic conversion rules.

#### Knowledge role

Where useful, distinguish:

```text
intent
observed
mixed
```

Do not force every Markdown paragraph into a claim object in the first implementation. Keep the first schema practical.

#### Drift item

Minimum fields:

```text
id
summary
expected
observed
severity
status
related_nodes
sources
last_updated
```

#### KB metadata

Minimum:

```text
schema_version
project
last_onboarded
onboarding_state
```

### Files likely affected

- `schema/node.schema.json`
- `schema/edge.schema.json`
- `schema/knowledge-base.schema.json`
- new schema files if cleaner
- tests validating schema consistency

### Acceptance criteria

- schemas can represent project/domain knowledge before source code exists,
- source-derived knowledge still works,
- provenance and confidence are not the same field,
- existing KB can be recognized as legacy format,
- chosen ID rule is documented and tested.

---

## 3. Phase B — New Canonical Templates

### Objective

Create the Markdown structure defined by the vNext spec.

### Add templates

```text
templates/project.md
templates/architecture-overview.md
templates/architecture-technology.md
templates/architecture-runtime.md
templates/architecture-data.md
templates/architecture-deployment.md
templates/architecture-integrations.md
templates/change.md
templates/drift-report.md
templates/knowledge-gaps.md
```

### Update domain template

Reorder it around responsibility boundaries:

1. Responsibility
2. Owns
3. Does Not Own
4. Depends On
5. Used By
6. Core Concepts
7. Capabilities
8. Core Flows
9. Data Ownership
10. Entry Points
11. Invariants
12. Legacy / Migration
13. Risks
14. Source Areas
15. Open Questions

### Existing detail templates

Preserve capability/flow/concept/model/risk templates where useful, but normalize:

- frontmatter fields,
- provenance/confidence,
- IDs,
- links,
- source evidence naming.

### Acceptance criteria

- a new project can have useful Project/Architecture/Domain docs with zero source files,
- templates do not require fake source evidence,
- existing source-derived pages remain representable,
- all templates follow one field convention.

---

## 4. Phase C — Project State and Knowledge Gap Detection

### Objective

Implement the first step of `/kodebrain onboard`.

### Add deterministic project-state detection

Classify at least:

```text
greenfield
new_brownfield
partial_kb
legacy_kb
stale_kb
onboarded
```

Do not base this only on whether `docs/brain/` exists.

Signals should include:

- source file count,
- project manifests,
- existing KB version,
- presence/completeness of project hub,
- architecture pages,
- domain pages,
- graph/index state,
- old schema markers.

### Knowledge Gap Map

Produce structured gaps for at least:

```text
purpose
actors
core_outcomes
scope
technology
architecture
runtime
external_integrations
domains
domain_boundaries
invariants
legacy_migration
```

Each gap should indicate whether it can likely be:

```text
found_in_docs
inferred_from_project
needs_human
unknown
```

### Acceptance criteria

- rerunning onboard does not start from scratch,
- partial KBs lead to targeted enrichment,
- greenfield is recognized without error,
- user interview is triggered by meaningful gaps, not missing filenames.

---

## 5. Phase D — Intent Discovery and Alignment Interview

### Objective

Gather project intent before deep inference.

### Existing-intent discovery

Inspect, in priority order:

1. current Project Contract,
2. human notes,
3. ADR/architecture docs,
4. README/project docs,
5. other likely product/spec docs.

Do not treat arbitrary old docs as current truth without provenance/confidence.

### Interview behavior

When material intent gaps remain, ask a short adaptive interview covering only necessary items.

Minimum dimensions:

- purpose/users,
- core outcomes/workflows,
- known system shape,
- critical external systems,
- known legacy/migration.

Greenfield may additionally ask about:

- technology constraints,
- deployment constraints,
- security/privacy constraints,
- non-functional requirements,
- initial domains.

Unknown is a valid answer.

### Important rule

The agent must not infer business intent from folder names if the user can cheaply resolve a material ambiguity.

### Acceptance criteria

- a greenfield project exits the interview with enough information to produce a Project Contract draft,
- a brownfield project does not ask redundant questions already answered by canonical docs,
- interview output records provenance as human-provided intent,
- unverified implementation claims are not created from interview answers.

---

## 6. Phase E — Project Contract Generation

### Objective

Generate useful high-level knowledge before deep mapping.

### Generate/populate

```text
<project>.md
architecture/overview.md
architecture/technology.md
architecture/runtime.md
architecture/data.md
architecture/deployment.md
architecture/integrations.md
```

Only populate sections supported by current knowledge. Keep unknowns explicit.

For greenfield, architecture may be planned/intended.
For brownfield, architecture may include both intended and observed notes.

### Project hub must contain

- Purpose
- Primary Users / Actors
- Core Outcomes
- Scope
- Technology Summary
- System Architecture
- Domains
- Runtime Entry Points
- External Systems
- System-wide Invariants
- Current Risks / Legacy / Migration
- Active Changes
- Where To Start

### Acceptance criteria

- project hub is usable before detailed graph generation,
- a coding agent can orient itself from project + architecture pages,
- unknowns are explicit,
- human-authored content is preserved on rerun.

---

## 7. Phase F — Architecture-Aware Harvest

### Objective

Retain deterministic harvest, but make it useful for project architecture discovery.

### Extend harvest to inventory more than source symbols

Add detection where practical for:

- language/runtime manifests,
- package managers,
- frontend/backend frameworks,
- DB clients/ORMs,
- cache clients,
- queues/event systems,
- infrastructure/deployment files,
- Docker/container files,
- CI configuration,
- environment/config conventions,
- API styles,
- worker/scheduler entry points.

Do not pretend regex extraction provides full semantic understanding.

### Source-reading escalation

Update skill instructions to use:

```text
inventory
→ harvest
→ config/docs
→ targeted source
→ human clarification
```

Remove the hard rule that raw source is never read.

### Acceptance criteria

- harvest output can support a useful technology/runtime skeleton,
- unsupported/weak language extraction is reported rather than treated as empty truth,
- agent may inspect targeted source when needed,
- whole-repo raw reading is not the default.

---

## 8. Phase G — Domain Mapping vNext

### Objective

Map responsibilities using both intent and observed evidence.

### Domain discovery inputs

Use:

- human/project contract domains,
- architecture components,
- file/folder clusters,
- routes,
- services/models,
- runtime entry points,
- existing KB domains.

Do not require a service+model+route triad for every legitimate domain.

### Domain reconciliation

Possible outcomes:

```text
confirmed
discovered
inferred
ambiguous
drifted
```

If code clustering conflicts with intended domain boundaries, preserve both and surface drift.

### Acceptance criteria

- greenfield domains can exist without source files,
- brownfield domain detection uses source evidence,
- domain responsibility is not equated with folder ownership,
- domain pages include owns/does-not-own/depends-on.

---

## 9. Phase H — Progressive Deep Mapping

### Objective

Replace all-at-once mapping with prioritised/resumable mapping.

### Priority order

1. runtime entry points,
2. high-connectivity domains,
3. core outcomes/workflows from Project Contract,
4. frequently changed areas if git evidence is available,
5. task-relevant areas,
6. remaining unmapped areas.

### Persist progress

The KB must record enough state for onboard to resume.

Do not use "0 capability nodes = total failure" as the only completeness rule. Completeness must be gap-based.

### Reports

Maintain:

```text
reports/knowledge-gaps.md
reports/unmapped-files.md
reports/needs-review.md
reports/suspected-legacy.md
```

### Acceptance criteria

- 5,000+ file repos can produce a useful project/domain map before full deep mapping,
- onboarding can be interrupted and rerun without discarding work,
- incomplete mapping is visible and honest.

---

## 10. Phase I — Change-First Workflow

### Objective

Make Kode Brain useful during implementation, not only before/after scanning.

### Add change records

Path:

```text
changes/active/YYYY-MM-DD-<slug>.md
changes/completed/
```

Status:

```text
planned
in_progress
implemented
reconciled
```

### Agent rule

Before a material behavior/architecture/domain/API/invariant change:

1. read relevant Project Contract/domain pages,
2. create/update active change,
3. record intended impact,
4. then implement.

After implementation:

1. harvest/review changed files,
2. compare with intended change,
3. update current-state KB,
4. surface drift,
5. mark reconciled and move to completed.

### Acceptance criteria

- current-state architecture is not rewritten as if unfinished work already exists,
- material implementation has an intent record,
- completed change points to implementation evidence,
- agents can find current active work from project hub.

---

## 11. Phase J — Drift Detection

### Objective

Turn intent-vs-code disagreement into first-class output.

### Initial drift types

At least detect/report:

- intended component absent from implementation,
- observed component contradicts intended current architecture,
- intended migration/removal not reflected in source,
- domain ownership mismatch,
- material code change without corresponding KB/change update where detectable,
- stale completed-change assumptions.

Do not auto-resolve drift.

### Output

```text
reports/drift.md
```

High-risk drift may also produce caveat/risk nodes.

### Acceptance criteria

- source-vs-intent contradictions are explicit,
- no "trust source" global rule silently destroys intended truth,
- no "trust docs" global rule hides observed implementation.

---

## 12. Phase K — Markdown-First Graph Compilation

### Objective

Remove independent dual-write authority between Markdown and graph JSON.

### Direction

```text
Markdown/frontmatter/wiki-links
       ↓ compile
nodes.json
edges.json
file-index.json
```

Implement deterministic index generation as much as practical.

During migration, old JSON may be read for compatibility, but new writes should move toward Markdown-first authority.

### Acceptance criteria

- normal agent workflow does not manually maintain the same relationship in Markdown and JSON independently,
- generated indexes can be rebuilt,
- rebuild is covered by tests,
- human-authored Markdown remains readable without tooling.

---

## 13. Phase L — `/kodebrain onboard`

### Objective

Expose the complete workflow under one user-facing command.

### Expected behavior

```text
/kodebrain onboard [path]
```

internally:

1. detect state,
2. load/migrate old KB if necessary,
3. build knowledge gap map,
4. discover intent,
5. interview if necessary,
6. create/repair Project Contract,
7. harvest architecture evidence,
8. map/reconcile domains,
9. progressively deep-map according to priority,
10. compile indexes,
11. write gap/drift/review reports,
12. install/update agent project instructions,
13. print concise status and next gaps.

### Compatibility

Keep `/kodebrain init` and `/kodebrain scan` temporarily if useful, but implement them as narrower wrappers or aliases rather than separate competing lifecycle models.

### Acceptance criteria

- same command works on empty repo, small existing repo, huge legacy repo, and partial KB,
- rerun is safe,
- onboarding asks humans only when necessary,
- user does not need to choose init vs resume vs repair.

---

## 14. Phase M — Agent Instruction Update

Update project/global instruction blocks generated by `kodebrain install` / `kodebrain project install`.

Replace the current simplistic "KB first, source only if stale" wording with roughly:

```text
Start from project hub and relevant domains.
Check active changes.
Use reading-pack for task context.
Use targeted source for edits and verification.
For material changes, update/create an active Kode Brain change record before implementation.
After implementation, reconcile the KB and surface drift.
```

Do not force non-Claude platforms to invoke slash commands they cannot invoke.

### Acceptance criteria

- instructions reflect vNext workflow,
- supported platforms receive equivalent behavioral rules,
- generated instructions do not claim Kode Brain state that does not exist.

---

## 15. Phase N — Legacy KB Migration

### Objective

Allow current users to move forward without destroying existing knowledge.

### Migration behavior

- detect schema/version,
- normalize IDs/field names,
- preserve human notes verbatim,
- preserve pages that cannot be confidently migrated,
- create migration report for ambiguities,
- generate missing project/architecture skeleton,
- derive graph indexes under the new convention.

### Acceptance criteria

- existing KB can be onboarded into vNext,
- migration is rerunnable or clearly one-way with backup guidance,
- no silent deletion of unknown knowledge.

---

## 16. Tests Required

Add tests for at least:

### Greenfield

- empty git repo → greenfield state,
- interview data → project hub/architecture/domain skeleton,
- zero source files does not fail onboarding.

### Brownfield

- no KB → new brownfield,
- partial KB → only missing knowledge requested/generated,
- legacy KB → migration path,
- existing project docs reduce interview questions.

### Progressive mapping

- resumable state,
- gap report changes as knowledge improves.

### Drift

- intended vs observed mismatch creates drift,
- drift does not overwrite either side.

### Canonical generation

- Markdown/index compile reproducible,
- file-index rebuild works,
- IDs/fields match schemas.

### Preservation

- human-note blocks survive onboarding/update/migration unchanged.

---

## 17. Documentation Cleanup

After implementation stabilizes, update or mark superseded:

```text
README.md
docs/design/taxonomy.md
docs/design/skills.md
docs/design/agents.md
docs/design/workflows.md
docs/design/open-decisions.md
kodebrain/skill/SKILL.md
```

Do not leave old documents appearing equally canonical.

Recommended headers for historical docs during transition:

```md
> Superseded in part by `docs/design/spec.md`. See that document for vNext behavior.
```

Resolve old "open decisions" that vNext has now decided, especially canonical storage/authority and source-vs-KB conflict behavior.

---

## 18. Suggested Execution Order

An implementation agent should execute in this order:

```text
A  Data model normalization
B  Templates
C  Project state + gap detection
D  Intent discovery/interview
E  Project Contract generation
F  Architecture-aware harvest
G  Domain mapping
H  Progressive mapping
I  Change-first workflow
J  Drift
K  Markdown-first graph compilation
L  /kodebrain onboard orchestration
M  Agent instructions
N  Legacy migration
→  documentation cleanup
→  full regression tests
```

Do not start by rewriting the entire `SKILL.md`. Establish reusable implementation primitives and schemas first, then make the skill orchestrate them.

---

## 19. Definition of Done

vNext is functionally ready when all of the following are true:

1. `/kodebrain onboard` works on a new project with no meaningful code.
2. It creates a Project Contract from a short alignment interview.
3. A coding agent can use that contract before implementation begins.
4. The same command works on an existing codebase.
5. Existing intent is reused instead of redundantly re-questioned.
6. Large codebases can onboard progressively.
7. Architecture and domain maps exist above detailed capability/flow nodes.
8. Targeted raw source reading is allowed when deterministic evidence is insufficient.
9. Material changes have active change records before implementation.
10. Intent/implementation disagreement is surfaced as drift.
11. Human notes and canonical intent are not silently overwritten.
12. Graph/index artifacts are rebuildable from canonical knowledge rather than maintained as an independent truth.
13. Schemas, templates, docs, commands, paths, and IDs no longer contradict one another.
14. Existing Kode Brain projects have a documented migration path.
