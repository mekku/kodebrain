---
spec_id: governance
spec_role: canonical
parent: root
owns:
  - governance.precedence
  - governance.compatibility
  - governance.non-goals
  - governance.success-criteria
  - governance.spec-authority
---

# Governance

Canonical owner for: precedence rules, compatibility/migration, non-goals, success criteria, specification authority.

## Precedence Rule

Kode Brain follows **specification authority**: every concept has exactly one canonical owner.

### Authority hierarchy

1. `docs/design/spec.md` — canonical root (diagram + links to children)
2. `docs/design/spec/*.md` — canonical child specs
3. `schema/node.schema.json` — canonical field contract for all node types
4. `kodebrain/skill/SKILL.md` — agent behavioral contract (derived from specs)
5. `docs/design/implementation-plan-vnext.md` — migration execution order (plan, not spec)
6. `docs/design/project-history.md` — design rationale (historical, not current spec)
7. `docs/design/taxonomy.md`, `skills.md`, `agents.md`, `workflows.md` — older design input, superseded where they conflict
8. `docs/design/open-decisions.md` — resolved decision records

### Rule

When a new concept is introduced:

1. Locate the canonical owner in the spec tree
2. Modify that section — do not create a competing document
3. If no owner exists, add one canonical child and link it from the root
4. Record rationale in a Decision, not a parallel spec

The anti-pattern is: new idea → create another design document → implement from that document → leave the canonical spec unchanged. This is specification drift.

## Spec Boundary Rules

When a new question arises, route it to one canonical owner using this framework:

| Question pattern | Owner | Example |
|---|---|---|
| What does X *mean*? | Knowledge | "What is provenance?" |
| What is the *shape/structure* of X? | Project | "Where do domain pages live?" |
| What *process* creates/modifies X? | Workflow | "When is a change created?" |
| What *temporal record* does X produce? | History | "What does a completed change contain?" |
| What *rule* constrains X? | Governance | "Can old specs be deleted?" |
| What is the *machine form* of X? | Schema (derived) | "What fields does a node have?" |

The boundary between Workflow and History:

- **Workflow** owns active development processes: when to create a change, how change lifecycle progresses (planned → in_progress → implemented → reconciled), how reconciliation works.
- **History** owns temporal records AND their lifecycle semantics: what a completed change contains, Decision lifecycle (active/superseded/deprecated), Incident lifecycle (ongoing/mitigated/resolved), lineage derivation, event generation, retrieval.
- Workflow owns Change lifecycle because Change is both a development process AND a historical record. History owns the completed Change record. History owns Decision and Incident lifecycle semantics fully.
- Neither spec independently redefines record semantics owned by the other.

---

## Specification Authority

Separate artifact classes with different roles:

| Artifact class | Role |
|---|---|
| **Specification** | What is true now |
| **Decision** | Why that truth was chosen or changed |
| **History** | What happened along the way |
| **Implementation Plan** | How the spec will be implemented or migrated |
| **Code / Runtime** | What currently exists in implementation |

A Decision must not become a second copy of the spec. An implementation plan must not become a future canonical spec by accident. A historical design document must not remain equally authoritative after the canonical model has changed.

## Compatibility and Migration Principles

vNext may evolve the current schemas and generated layout.

Migration rules: preserve human-authored notes, do not silently discard existing nodes/pages, detect older KB format/version, migrate deterministically where possible, report ambiguous migration cases, keep backwards compatibility only where it does not preserve contradictory authority models indefinitely.

Compatibility is useful; permanent ambiguity is not.

## Non-Goals

Kode Brain is not intended to: automatically rewrite an entire project architecture without human intent, replace source code as implementation evidence, guarantee runtime behavior from static analysis alone, auto-delete suspected legacy code, make product decisions that are genuinely unknown, generate exhaustive documentation for every trivial function, require Obsidian to function, require a database service to function.

## Success Criteria

Kode Brain succeeds when:

**For a new project:** A coding agent can begin implementation from Kode Brain and correctly explain the project's purpose, architecture direction, core domains, constraints, and unresolved decisions before meaningful source code exists.

**For an existing project:** A new human or agent can orient itself quickly, understand the intended architecture, distinguish current implementation from legacy or drift, and navigate to the correct source area without rediscovering the entire codebase.

**During development:** Material changes leave a trace from intent → implementation → reconciled project knowledge. History retrieval warns about past incidents and superseded approaches before changes begin.

**Over time:** The project knowledge base becomes more accurate through work rather than steadily becoming stale documentation. Accumulated history prevents repeated mistakes.
