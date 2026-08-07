---
type: architecture_integrations
project: {{project-slug}}
confidence: {{confidence}}
provenance: {{provenance}}
knowledge_role: {{knowledge_role}}
last_updated: {{date}}
---

# External Integrations — {{Project Name}}

## Active Integrations

| System | Purpose | Protocol | Criticality | Failure Mode |
|---|---|---|---|---|
| {{name}} | {{why this project talks to it}} | HTTP / gRPC / queue / webhook | high / medium / low | {{what breaks if unavailable}} |

## Integration Details

### {{System Name}}

**Why:** {{Business reason, not just technical.}}

**How:**
- Direction: {{outbound / inbound / bidirectional}}
- Auth: {{method}}
- Retry: {{policy}}
- Timeout: {{duration}}

**Owned by:** {{domain / team}}

**Key code paths:**
- `{{file}}` — `{{symbol}}` — {{what it calls}}

## Deprecated / Legacy Integrations

| System | Status | Migration Plan |
|---|---|---|
| {{name}} | deprecated / partially_migrated | {{plan}} |

## Known Risks

- {{integration-specific risk}}
