# ZMS (Zscaler Microsegmentation) Steering

## Overview

ZMS provides **agent-based microsegmentation** to prevent lateral movement inside data center and cloud environments. Lightweight agents on each workload classify processes, observe traffic, and enforce identity-based segmentation policies. ZMS is the canonical Zero Trust answer for **east-west** workload-to-workload traffic — distinct from ZTW (Zscaler Workload Segmentation), which operates at the network IP-group / network-service layer.

All ZMS MCP tools today are **read-only** Query operations on the ZMS GraphQL endpoint. The underlying API also exposes Mutation operations (create/update/delete agents, groups, policy rules, resource groups), but those are not yet wired into MCP.

## Available Skills

Kiro should prefer **guided skills** over ad-hoc workflows whenever a user's intent matches one of the skills below. Each skill is a multi-step playbook that auto-activates on description match. When a request maps cleanly to a skill, load the SKILL.md and follow it; otherwise fall back to the ad-hoc workflows further down.

| Skill | Path | When to use |
|-------|------|-------------|
| Audit microsegmentation posture | `skills/zms/audit-microsegmentation-posture/SKILL.md` | "Review our microsegmentation posture", "What is our ZMS coverage?", "Audit agents + policies + resources" |
| Assess workload protection | `skills/zms/assess-workload-protection/SKILL.md` | "Which workloads are unprotected?", "Show me protection gaps by resource group", "Coverage breakdown" |
| Analyze policy rules | `skills/zms/analyze-policy-rules/SKILL.md` | "Review my ZMS segmentation policies", "Find shadowed or overly-permissive rules", "Policy optimization" |
| Review tag classification | `skills/zms/review-tag-classification/SKILL.md` | "How are workloads tagged?", "Review ML / external / custom tag classifications", "Tag → resource-group mapping" |
| Troubleshoot agent deployment | `skills/zms/troubleshoot-agent-deployment/SKILL.md` | "ZMS agents won't connect", "Agent fleet health", "Why is this workload showing as unprotected?" |

## Critical: `ZSCALER_CUSTOMER_ID` Is Mandatory

Every ZMS tool requires `ZSCALER_CUSTOMER_ID` to be set as an environment variable on the MCP server. The tools auto-resolve it from env and inject it into every GraphQL query — if it is missing, tools return an error immediately. Don't try to pass it as a positional parameter.

## Key Concepts

- **Agents**: Lightweight software running on each workload (VM / container / bare metal). Identified by `eyez_id` (the canonical ZMS identifier — not a numeric ID).
- **Agent Groups**: Logical groupings of agents used to associate workloads with deployment / lifecycle policies. Identified by `eyez_id`.
- **Resources**: Discovered workloads — VMs, containers, FQDNs, CIDR blocks. Each has a `protection_status` (`PROTECTED`, `UNPROTECTED`, etc.) and cloud-provider metadata.
- **Resource Groups**: Two distinct subtypes that share one list endpoint:
  - **`ManagedResourceGroup`** — tag-based membership; workloads with matching tags are auto-enrolled.
  - **`UnmanagedResourceGroup`** — explicit CIDR / FQDN membership.
- **Policy Rules**: Segmentation rules between resource groups (allow / deny / inspect). `fetchAll=true` bypasses pagination but should be used sparingly on large tenants.
- **App Zones**: Logical perimeter boundaries used to group resource groups for policy scoping.
- **App Catalog**: Classified-application inventory (the apps ZMS has identified running on agents).
- **Tags**: A three-level hierarchy — `namespace → key → value`. To list values, navigate top-down (namespace → tag key → tag values).
  - `namespace_origin` is one of `CUSTOM`, `EXTERNAL` (cloud-provider tags), `ML` (ZMS classifier), or `UNKNOWN`.
- **Nonces**: Pre-shared one-time tokens used during agent enrollment.

## ZMS vs ZTW vs ZPA — Choose the Right Surface

| If the user is asking about… | Use this service |
|---|---|
| **Process-aware, agent-based east-west segmentation** between workloads inside a DC / cloud | **ZMS** (this file) |
| **IP-group / network-service** based segmentation, cloud account discovery, GRE/IPSec branch | **ZTW** (`ztw.md`) |
| **User → private application** access (ZTNA) over the internet | **ZPA** (`zpa.md`) |

When in doubt: "*Is there a Zscaler agent installed on the workload itself?*" → ZMS. "*Are we routing branch traffic through Zscaler with IP/CIDR rules?*" → ZTW.

## GraphQL Idiosyncrasies

- **Status codes lie.** GraphQL endpoints return **HTTP 200 even on errors** — the error detail lives in the response body. Always check for an `errors` field, not just the HTTP status, when handling a raw API call.
- **Two pagination patterns coexist** (the SDK papers over this, but worth knowing):
  - `page` + `pageSize`: agents, agent groups, nonces.
  - `pageNum` + `pageSize`: resources, resource groups, policy rules, app zones, app catalog, tags.
- **Connection envelope**: list responses are shaped `{ "nodes": [...], "page_info": { page_number, page_size, total_count, total_pages } }`. JMESPath expressions (the optional `query` parameter on each list tool) operate **inside** that envelope, so prefer e.g. `nodes[?cloud_provider=='AWS']` rather than `[?cloud_provider=='AWS']`.
- **Inline fragments**: `zms_list_resource_groups` returns a heterogeneous list of `ManagedResourceGroup` and `UnmanagedResourceGroup`. Their fields differ — check the `__typename` (or the unique fields like `tag_filters` vs `cidr_blocks`) before treating two rows as interchangeable.

## Common Workflows

### Microsegmentation Posture Review
```
1. zms_list_agents                         → Agent fleet inventory (count, OS mix, versions)
2. zms_get_agent_connection_status_statistics → Online / offline / disconnected breakdown
3. zms_get_agent_version_statistics        → Version distribution (upgrade backlog)
4. zms_list_resources                      → Discovered workloads with protection_status
5. zms_get_resource_protection_status      → Protection summary for the inventory
6. zms_list_resource_groups                → Managed vs Unmanaged group structure
7. zms_list_policy_rules                   → Custom segmentation rules
8. zms_list_default_policy_rules           → Built-in baseline rules
9. zms_list_app_zones                      → Policy-scope perimeters
10. zms_list_app_catalog                   → Classified applications inventory
```

### Workload Protection Gap Analysis
```
1. zms_list_resources                      → All discovered workloads
2. zms_get_resource_protection_status      → Identify UNPROTECTED workloads
3. For each unprotected workload:
   a. zms_get_metadata                     → Cloud provider, tags, environment
   b. zms_list_resource_groups             → Which groups (if any) cover this workload?
4. Cross-reference with zms_list_policy_rules to confirm no policy applies
5. Recommend tag updates or new resource-group memberships
```

### Policy Rule Audit
```
1. zms_list_policy_rules(fetchAll=false, page_num=1, page_size=50)
   → Walk pages; reserve fetchAll=true for small tenants
2. zms_list_default_policy_rules            → Capture baseline behaviour
3. zms_list_app_zones                       → Understand policy scoping
4. zms_list_resource_groups                 → Resolve source / destination references
5. Identify: shadowed rules, overly-permissive allow-all, missing deny-by-default
```

### Tag Classification Review
```
1. zms_list_tag_namespaces                  → CUSTOM / EXTERNAL / ML / UNKNOWN
2. For each namespace of interest:
   zms_list_tag_keys(namespace_origin=...)  → All keys in that namespace
3. For each key:
   zms_list_tag_values(namespace_origin=..., tag_key_id=...) → Values + workload counts
4. zms_list_resource_groups                 → Tag-filter rules used by ManagedResourceGroups
5. Identify ML-suggested tags awaiting adoption vs stale custom tags
```

### Agent Troubleshooting
```
1. zms_list_agents(search="<host or eyez_id>") → Locate the agent
2. zms_get_agent_connection_status_statistics → Fleet-wide context — is the user's symptom an outlier or part of a wave?
3. zms_get_agent_version_statistics            → Is the affected agent on an unsupported version?
4. zms_list_agent_groups                       → Group membership / policy assignment
5. zms_get_agent_group_totp_secrets            → Rotate TOTP if re-enrollment is needed
6. zms_list_nonces / zms_get_nonce             → Confirm a valid enrollment nonce exists for the workload
```

## Available Tools

All ZMS tools are **read-only** (GraphQL Query operations).

### Agents
| Tool | Description |
|------|-------------|
| `zms_list_agents` | List agents in the tenant (paginated) |
| `zms_get_agent_connection_status_statistics` | Aggregate connection state across the fleet |
| `zms_get_agent_version_statistics` | Aggregate version distribution across the fleet |

### Agent Groups
| Tool | Description |
|------|-------------|
| `zms_list_agent_groups` | List agent groups (paginated) |
| `zms_get_agent_group_totp_secrets` | Retrieve TOTP secrets for an agent group (re-enrollment) |

### Resources
| Tool | Description |
|------|-------------|
| `zms_list_resources` | List discovered workloads with protection status |
| `zms_get_resource_protection_status` | Protection-status breakdown for a resource scope |
| `zms_get_metadata` | Cloud-provider, tag, and environment metadata for a resource |

### Resource Groups
| Tool | Description |
|------|-------------|
| `zms_list_resource_groups` | List Managed (tag-based) and Unmanaged (CIDR/FQDN) resource groups |
| `zms_get_resource_group_members` | List members of a specific resource group |
| `zms_get_resource_group_protection_status` | Protection breakdown for a specific resource group |

### Policy Rules
| Tool | Description |
|------|-------------|
| `zms_list_policy_rules` | List custom segmentation rules (use `fetchAll=true` sparingly) |
| `zms_list_default_policy_rules` | List built-in / baseline rules |

### App Zones / App Catalog
| Tool | Description |
|------|-------------|
| `zms_list_app_zones` | List policy-scope perimeters |
| `zms_list_app_catalog` | List classified applications inventory |

### Enrollment (Nonces)
| Tool | Description |
|------|-------------|
| `zms_list_nonces` | List enrollment nonces |
| `zms_get_nonce` | Get a specific enrollment nonce |

### Tags
| Tool | Description |
|------|-------------|
| `zms_list_tag_namespaces` | List tag namespaces (`CUSTOM`, `EXTERNAL`, `ML`, `UNKNOWN`) |
| `zms_list_tag_keys` | List tag keys within a namespace |
| `zms_list_tag_values` | List tag values for a specific namespace + key |

## Response Style — Don't Leak Implementation Details

When answering the user, give the **business answer in plain language**. Tool plumbing — JMESPath expressions, `nodes[]` envelopes, GraphQL response shapes, pagination — is internal optimization the user does not care about.

- *"How many ZMS agents are online?"* → **"412 out of 458 agents are online (89.9%)."** Not: *"`group_by_connection_status` returned `{ ONLINE: 412, OFFLINE: 46 }`."*
- *"Which workloads are unprotected?"* → list the workloads. Not: *"I filtered `nodes[?protection_status=='UNPROTECTED']`."*
- An empty `nodes[]` response is **authoritative** — do not fan out retries with broader filters. Ask the user to clarify the scope instead.

## Best Practices

1. **Always confirm `ZSCALER_CUSTOMER_ID` is set** before claiming ZMS is unavailable — most "tool returned an error" cases on ZMS are missing-env-var problems.
2. **Use `eyez_id` for agent / agent-group / nonce identity** — these are not numeric IDs.
3. **Check the resource-group `__typename`** when navigating membership — `ManagedResourceGroup` uses tag filters, `UnmanagedResourceGroup` uses CIDR/FQDN lists.
4. **Avoid `fetchAll=true` on large tenants** for `zms_list_policy_rules` — paginate instead.
5. **Don't treat ZMS as ZTW** — they're complementary, not interchangeable. ZMS is agent-based; ZTW is IP-group / network-service-based.
6. **GraphQL errors hide under HTTP 200** — always inspect the response body, not just the status.
