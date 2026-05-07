# Skill API Contracts

Skills are stateless, single-responsibility functions. Each skill does one job and returns structured output. Skills are composed by agents into workflows.

Skills do not call other skills directly. Agents orchestrate skill composition.

---

## Conventions

```
Input:  parameters the skill receives
Output: guaranteed fields the skill always returns
Side effects: files written, none, or described
Errors: named failure cases
```

All file paths are relative to the project root unless noted otherwise.

---

## skill: scan_project_files

**Purpose:** Build a complete inventory of project files with type classification.

```
Input:
  projectRoot:      string   — absolute path to project root
  ignorePatterns:   string[] — glob patterns to exclude (e.g. ["node_modules/**", ".git/**"])
  includeExtensions?: string[] — if set, only include these extensions
  maxDepth?:        number   — max directory depth (default: unlimited)

Output:
  files: Array<{
    path:     string  — relative to projectRoot
    type:     "source" | "config" | "test" | "migration" | "doc" | "asset" | "unknown"
    language: string | null  — e.g. "typescript", "python", "yaml"
    sizeBytes: number
  }>
  entryPoints: string[]  — suspected entry points (main files, index files, CLI roots)
  summary: {
    totalFiles:  number
    byType:      Record<string, number>
    byLanguage:  Record<string, number>
    totalSizeBytes: number
  }

Side effects: none

Errors:
  PROJECT_ROOT_NOT_FOUND  — projectRoot does not exist
  PERMISSION_DENIED       — cannot read one or more directories
```

---

## skill: extract_symbols

**Purpose:** Extract exported functions, classes, routes, models, and import/export relationships from source files.

```
Input:
  files: Array<{ path: string, language: string }>
  projectRoot: string

Output:
  symbols: Array<{
    file:     string
    name:     string
    kind:     "function" | "class" | "constant" | "type" | "interface" | "route" | "model" | "component" | "export"
    exported: boolean
    line:     number
  }>
  imports: Array<{
    file:   string
    from:   string  — the import source path or module name
    names:  string[]
  }>
  routes: Array<{
    file:   string
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | string
    path:   string
    handler: string | null  — handler function name if detectable
    line:   number
  }>
  summary: {
    totalSymbols: number
    totalRoutes:  number
    byKind:       Record<string, number>
  }

Side effects: none

Errors:
  PARSE_ERROR  — file could not be parsed. File is included in errors[], not symbols[].
  errors: Array<{ file: string, reason: string }>
```

---

## skill: detect_domains

**Purpose:** Identify major domain candidates from file structure, symbol clustering, and folder semantics.

```
Input:
  files:     Array<{ path: string, type: string, language: string | null }>
  symbols:   Array<{ file: string, name: string, kind: string }>
  routes:    Array<{ file: string, method: string, path: string }>
  existingDocs?: string[]  — paths to any existing documentation files

Output:
  domains: Array<{
    name:       string       — proposed domain name (e.g. "Auth", "Billing")
    slug:       string       — lowercase hyphenated (e.g. "auth", "billing")
    confidence: "source_supported" | "inferred"
    evidence:   Array<{ file?: string, symbol?: string, note?: string }>
    rootPaths:  string[]     — folder paths associated with this domain
    routePrefixes: string[]  — route prefixes associated (e.g. ["/auth", "/users"])
    notes:      string       — brief reasoning
  }>
  unmappedFiles: string[]    — files not assigned to any domain candidate

Side effects: none
```

---

## skill: detect_capabilities

**Purpose:** Identify what the system can do within each domain.

```
Input:
  domains:  Array<{ slug: string, rootPaths: string[], routePrefixes: string[] }>
  routes:   Array<{ file: string, method: string, path: string, handler: string | null }>
  symbols:  Array<{ file: string, name: string, kind: string, exported: boolean }>
  files:    Array<{ path: string, type: string }>

Output:
  capabilities: Array<{
    name:       string   — verb phrase (e.g. "Create approval request")
    slug:       string   — lowercase hyphenated
    domain:     string   — domain slug
    confidence: "source_supported" | "inferred"
    evidence:   Array<{ file?: string, symbol?: string, route?: string, note?: string }>
    sourceFiles: string[]
    notes:      string
  }>

Side effects: none
```

---

## skill: extract_flows

**Purpose:** Describe step-by-step runtime paths for key capabilities.

```
Input:
  capabilities: Array<{ slug: string, domain: string, sourceFiles: string[] }>
  symbols:      Array<{ file: string, name: string, kind: string }>
  imports:      Array<{ file: string, from: string, names: string[] }>
  routes:       Array<{ file: string, method: string, path: string, handler: string | null }>

Output:
  flows: Array<{
    name:        string   — e.g. "Update collection data flow"
    slug:        string
    domain:      string
    capability:  string   — linked capability slug
    confidence:  "source_supported" | "inferred"
    entryPoint:  { type: "route" | "event" | "scheduler" | "cli", value: string }
    steps: Array<{
      order:       number
      description: string
      file?:       string
      symbol?:     string
      sideEffects: string[]  — e.g. ["writes to database", "publishes cache invalidation event"]
    }>
    dataMovement: Array<{
      from:  string   — source (e.g. "HTTP request body")
      to:    string   — destination (e.g. "orders table")
      via:   string   — mechanism (e.g. "OrderRepository.save()")
    }>
    evidence:    Array<{ file?: string, symbol?: string, note?: string }>
    notes:       string
  }>

Side effects: none
```

---

## skill: map_dependencies

**Purpose:** Build the graph nodes and edges from all discovered knowledge units.

```
Input:
  domains:      Array<{ slug: string, name: string, ... }>
  capabilities: Array<{ slug: string, name: string, domain: string, sourceFiles: string[], ... }>
  flows:        Array<{ slug: string, domain: string, capability: string, steps: [...], ... }>
  symbols:      Array<{ file: string, name: string, kind: string }>
  imports:      Array<{ file: string, from: string, names: string[] }>
  routes:       Array<{ ... }>

Output:
  nodes: KnowledgeNode[]   — see node.schema.json
  edges: KnowledgeEdge[]   — see edge.schema.json
  fileIndex: Record<string, string[]>
    — maps file path → node IDs that reference this file (reverse index for change detection)

Side effects: none
```

---

## skill: classify_status

**Purpose:** Determine whether a node is active, legacy, deprecated, partially migrated, unused, or unknown.

```
Input:
  node: KnowledgeNode
  usageEvidence: {
    importedBy:    string[]  — files that import from this node's source files
    referencedIn:  string[]  — files containing symbol references
    hasTests:      boolean
    hasRouteRef:   boolean
    hasUIRef:      boolean
    hasComments:   string[]  — relevant inline comments (TODO, DEPRECATED, etc.)
    humanNotes:    string[]  — notes from human reviewers
  }

Output:
  status:     "active" | "legacy" | "deprecated" | "partially_migrated" | "unused" | "experimental" | "unknown" | "needs_review"
  confidence: "source_supported" | "inferred" | "needs_human_review"
  reasoning:  string    — explanation of how status was determined
  requiresHumanReview: boolean
  reviewReason?: string — why human review is required

Side effects: none
```

---

## skill: generate_knowledge_page

**Purpose:** Write or update a Markdown knowledge page for a node.

```
Input:
  node:            KnowledgeNode
  relatedNodes:    Array<{ id: string, name: string, type: string }>
  evidence:        Array<{ type: string, value: string, note?: string }>
  existingPage?:   string   — current file content if updating
  template:        "domain" | "capability" | "concept" | "flow" | "model" | "api" | "decision" | "risk"

Output:
  content:  string   — full Markdown page content with frontmatter
  path:     string   — recommended relative file path within docs/brain/
  isNew:    boolean
  changes:  string[] — human-readable list of what changed vs. existingPage

Side effects: none  — caller is responsible for writing the file
```

---

## skill: review_claims

**Purpose:** Check whether the claims in a knowledge page are supported by current source evidence.

```
Input:
  page:          { path: string, content: string }
  sourceEvidence: {
    files:   Array<{ path: string, contentSnippets: string[] }>
    symbols: Array<{ name: string, kind: string, file: string }>
    routes:  Array<{ method: string, path: string, file: string }>
  }

Output:
  unsupportedClaims: Array<{
    claim:    string   — the claim text
    reason:   string   — why it lacks support
    location: string   — section or line in the page
  }>
  ambiguousClaims: Array<{
    claim:          string
    interpretations: string[]
  }>
  staleClaims: Array<{
    claim:       string
    priorEvidence: string
    currentState:  string
  }>
  confidenceUpdates: Array<{
    field:       string
    currentValue: string
    suggestedValue: string
    reason:      string
  }>
  reviewNotes: string   — overall assessment

Side effects: none
```

---

## skill: build_reading_pack

**Purpose:** Given a task description, produce a focused context pack for a human or coding agent.

```
Input:
  taskDescription: string
  nodes:           KnowledgeNode[]
  edges:           KnowledgeEdge[]
  fileIndex:       Record<string, string[]>
  pageSummaries:   Array<{ id: string, path: string, summary: string, status: string, confidence: string }>

Output:
  requiredReading: Array<{
    nodeId:   string
    name:     string
    type:     string
    path:     string   — file path to the KB page
    reason:   string   — why this is required reading for this task
    priority: "required" | "recommended" | "optional"
  }>
  likelySourceFiles: Array<{
    path:   string
    reason: string
  }>
  risks: Array<{
    description: string
    nodeId?:     string
    severity:    "high" | "medium" | "low"
  }>
  investigationOrder: string[]   — ordered list of steps for the task
  warnings: string[]             — legacy/migration/ambiguity warnings relevant to this task

Side effects: none
```
