# Taxonomy

Finalized types, labels, and their precise semantics.

---

## 1. Node Types

Each node represents one meaningful, independently explainable unit of the system.

| Type | What it represents | Typical source evidence |
|---|---|---|
| `project` | The top-level product or application | Root config, package.json, main README |
| `domain` | A major area of business/system responsibility | Folder clusters, service boundaries, team ownership |
| `capability` | One thing the system can do (behavior-first, not folder-first) | Route + service + model triad |
| `concept` | A mental model required to understand part of the system | Not always a feature — sometimes a rule or invariant |
| `flow` | A step-by-step runtime path from trigger to outcome | Traces through routes → services → repos → adapters |
| `layer` | A technical responsibility boundary | Controller layer, service layer, repo layer |
| `engine` | A reusable mechanism serving multiple capabilities | Query engine, rule engine, workflow engine |
| `adapter` | A boundary between core and a specific implementation | Database adapter, broker API adapter, payment gateway |
| `data_model` | A structure used to store or transfer data | ORM models, DTOs, Zod/Yup schemas |
| `api` | An external or internal interface | REST routes, GraphQL operations, CLI commands, MQTT topics |
| `ui` | A screen, page, or interaction surface | React pages, modals, wizards |
| `runtime_behavior` | Important behavior that only exists at runtime | Cache-first reads, pub/sub invalidation, retry loops |
| `state` | A meaningful lifecycle state for an entity | draft, submitted, approved, failed |
| `decision` | A recorded reason behind an architectural or product choice | ADRs, commit notes, design docs |
| `caveat` | A known limitation, bug risk, or dangerous area | TODO comments, post-mortems, known issues |
| `legacy_area` | A part of the system that is old and may or may not be active | Old module folders, superseded APIs |
| `migration_state` | A part of the system moving from one design to another | Migration scripts, dual-write periods |

### Node Type Rules

- A **capability** must be phrased as a verb phrase from the user/system perspective ("Create approval request"), not as a folder name ("approvals/").
- A **concept** answers "what must I understand before touching X?" A capability answers "what can X do?"
- A **flow** must have a named entry point (route, event, scheduler, CLI call) and a named outcome.
- A **runtime_behavior** describes something that cannot be read from a single file — it only becomes visible by tracing execution.
- A **decision** records the **why**, not the what. The what is in the code.
- A **caveat** is actionable: it should say what breaks, under what condition, and what the safe path is.

---

## 2. Edge Types

Edges describe directed relationships between nodes.

| Type | Meaning | Direction |
|---|---|---|
| `contains` | A structural parent/child relationship | parent → child |
| `implements` | A node provides the concrete logic for an abstraction | implementation → abstraction |
| `uses` | A node depends on another at runtime | caller → callee |
| `depends_on` | A node requires another to exist or function | dependent → dependency |
| `calls` | Direct function or method invocation | caller → callee |
| `reads_from` | A node reads data from a source | reader → source |
| `writes_to` | A node persists data to a target | writer → target |
| `invalidates` | A node signals that cached or derived data is stale | writer → cache/derived |
| `exposes` | A node makes another accessible through an interface | interface → implementation |
| `renders` | A UI node displays data from a domain node | ui → data/capability |
| `part_of_flow` | A node participates in a flow | node → flow |
| `replaces` | A node supersedes another (new replaces old) | new → old |
| `replaced_by` | A node has been superseded (old → new) | old → new |
| `related_to` | A semantic relationship without a more specific type | bidirectional by convention |
| `risky_for` | A change to this node risks breaking another | risky node → vulnerable node |
| `supported_by` | A claim or node is evidenced by a source | claim → evidence |

### Edge Rules

- Every edge **must** have at least one evidence item when confidence is `source_supported` or higher.
- `replaces` and `replaced_by` are mirrors. Only one direction should be stored; the inverse is computed.
- `related_to` is a last resort. If a more specific type fits, use it.
- `risky_for` should link to a `caveat` node as the intermediate when the risk is documented.

---

## 3. Status Labels

Applied to nodes. Describes the current life-cycle state of the thing being described.

| Label | Meaning |
|---|---|
| `active` | Currently used. Part of the intended system. |
| `legacy` | Old design or implementation. Still exists. May or may not be called. |
| `deprecated` | Known to be replaced or discouraged. Should not be used for new work. |
| `partially_migrated` | Some parts moved to a newer design. Old path remains. Both paths may be live. |
| `unused` | No known active caller or runtime path. **Must be verified before deletion.** |
| `experimental` | Built for exploration. Not production-intended. |
| `unknown` | System cannot confidently determine status. |
| `needs_review` | Requires human review before being trusted. |

### Status Transition Rules

- `unknown` → any other status requires at least one evidence item.
- `unused` → deletion requires human review (never automated).
- `partially_migrated` requires a linked `migration_state` node describing what has and has not moved.
- `legacy` does not imply `unused`. A legacy path may be the only live path.

---

## 4. Confidence Labels

Applied to nodes and edges. Describes how trustworthy the claim is.

| Label | Meaning |
|---|---|
| `verified` | Confirmed by source evidence AND human review. |
| `source_supported` | Supported by source files, exports, routes, tests. Not yet human-reviewed. |
| `inferred` | Reasonable interpretation. Supporting evidence exists but is indirect. |
| `ambiguous` | Multiple contradictory interpretations exist. |
| `stale` | Was accurate at some point. Source code may have changed since. |
| `needs_human_review` | Requires a human decision or clarification before being trusted. |

### Confidence Rules

- Only a human can upgrade confidence to `verified`.
- AI agents may set `source_supported`, `inferred`, `ambiguous`, or `needs_human_review`.
- A node that was `source_supported` and then the underlying source file changes should drop to `stale`.
- `ambiguous` must have at least two evidence items pointing in different directions.

---

## 5. Evidence Types

Evidence items ground claims in reality.

| Type | Examples |
|---|---|
| `file` | Source file path |
| `symbol` | Function name, class name, export name |
| `route` | `POST /api/orders`, `GET /users/:id` |
| `test` | Test file path or test name |
| `config` | Config key or config file |
| `migration` | Migration file name |
| `comment` | Inline code comment |
| `commit` | Commit SHA or PR reference |
| `human_note` | Explanation added by a human reviewer |

---

## 6. Naming Conventions

### Node IDs

Format: `{domain}/{type-slug}` or `{domain}/{subdomain}/{type-slug}`

- Lowercase, hyphen-separated
- Stable: do not change an ID after it is referenced by edges
- Unique within the project graph
- Examples: `auth/login-flow`, `billing/invoice-model`, `notification/send-email-capability`

### Page File Names

Match the node ID slug. Examples:
- `domains/auth/capabilities/login.md`
- `domains/billing/models/invoice.md`
- `domains/notification/flows/send-email.md`

### Decision File Names

Format: `YYYY-MM-DD-short-decision-name.md`

Example: `2026-05-07-use-adapter-pattern-for-datasources.md`
