# ZPA (Zscaler Private Access) Steering

## Overview

ZPA provides zero trust network access (ZTNA) to private applications without exposing them to the internet. It replaces traditional VPNs with a direct-to-app architecture using app connectors and service edges.

## Key Concepts

- **Application Segments**: Define which private applications are accessible (domains, IPs, ports)
- **Segment Groups**: Logical groupings of application segments for policy assignment
- **Server Groups**: Define backend servers and link them to app connector groups
- **App Connectors**: Lightweight software deployed near applications that broker connections
- **App Connector Groups**: Logical groupings of connectors (by datacenter, cloud region, etc.)
- **Service Edges**: Provide local breakout points for users (edge locations)
- **Access Policies**: Control who can access which applications (evaluated top-to-bottom)
- **Forwarding Policies**: Control whether traffic is intercepted by ZPA or bypassed
- **Timeout Policies**: Set session and idle timeout durations per app/user
- **Isolation Policies**: Route sessions through browser isolation
- **PRA (Privileged Remote Access)**: Portals and credentials for privileged access to servers

## Critical: Dependency Chain

ZPA resources have strict dependencies. Creating them out of order causes 400 errors.

### Application Onboarding Order
```
1. App Connector Group (zpa_create_app_connector_group)
   ↓
2. Server Group — references connector group (zpa_create_server_group)
   ↓
3. Segment Group (zpa_create_segment_group)
   ↓
4. Application Segment — references server group + segment group (zpa_create_application_segment)
   ↓
5. Access Policy Rule — references application/segment group + identity conditions (zpa_create_access_policy_rule)
```

Always check for existing resources before creating new ones. Use `zpa_list_*` tools first.

## Common Workflows

### Application Discovery
```
1. zpa_list_application_segments → Get all configured apps
2. zpa_get_application_segment   → Get details for specific app (domains, ports, server groups)
3. zpa_list_segment_groups       → See how apps are organized
4. zpa_list_server_groups        → View backend server configurations
5. zpa_list_app_connector_groups → Check connector group assignments
```

### End-to-End Application Onboarding
```
1. Gather requirements: app name, domains/IPs, ports, protocols, who needs access
2. zpa_list_app_connector_groups → Check for existing connector group in the target datacenter
3. zpa_create_app_connector_group → Create one if needed
4. zpa_create_server_group       → Create server group referencing the connector group
5. zpa_list_segment_groups       → Check for existing segment group
6. zpa_create_segment_group      → Create one if needed
7. zpa_create_application_segment → Create the app segment with domains, ports, protocol, server/segment group IDs
8. zpa_create_access_policy_rule → Create policy rule granting access (see condition types below)
9. Verify: zpa_get_application_segment + zpa_get_access_policy_rule
```

### Access Policy Review
```
1. zpa_list_access_policy_rules     → List all access rules (evaluated top-to-bottom)
2. zpa_get_access_policy_rule       → Get specific rule details including conditions
3. posture_profile_manager          → Check device posture requirements (action="read")
4. trusted_network_manager          → View trusted network definitions (action="read")
5. saml_attribute_manager           → List SAML attributes for identity conditions (action="read")
6. scim_group_manager               → List SCIM groups for group-based access (action="read")
```

### Infrastructure Status
```
1. zpa_list_app_connector_groups → List connector groups and their health
2. zpa_list_service_edge_groups  → List service edge groups
3. zpa_list_provisioning_keys    → Check available provisioning keys
4. zpa_list_application_servers  → View individual application servers
```

### PRA (Privileged Remote Access)
```
1. zpa_list_pra_portals     → List PRA portals
2. zpa_get_pra_portal       → Get portal details
3. zpa_create_pra_portal    → Create a PRA portal
4. zpa_list_pra_credentials → List PRA credentials
5. zpa_create_pra_credential → Create privileged access credentials
```

### Browser Access Certificates
```
1. zpa_list_ba_certificates → List browser access certificates
2. zpa_get_ba_certificate   → Get certificate details
3. zpa_create_ba_certificate → Upload a new certificate
```

## Access Policy Condition Types

Access policy rules use conditions to determine who gets access. Each condition block uses a single object type. Multiple blocks are ANDed. Within a block, values are ORed.

### Value-Based (use `values`)
| Object Type | What It Matches |
|---|---|
| `APP` | Specific application segment IDs |
| `APP_GROUP` | Segment group IDs |
| `CLIENT_TYPE` | Client type: `zpn_client_type_zapp`, `zpn_client_type_exporter`, etc. |
| `MACHINE_GRP` | Machine group IDs |
| `LOCATION` | Location IDs |

### Entry-Value Based (use `entry_values` with `lhs`/`rhs`)
| Object Type | LHS | RHS |
|---|---|---|
| `SAML` | SAML attribute ID | Attribute value to match |
| `SCIM` | SCIM attribute header ID | Attribute value |
| `SCIM_GROUP` | Identity Provider ID | SCIM group ID |
| `PLATFORM` | `linux`, `android`, `ios`, `mac`, `windows` | `"true"` or `"false"` |
| `COUNTRY_CODE` | ISO 3166 Alpha-2 code (e.g., `US`) | `"true"` or `"false"` |
| `POSTURE` | Posture profile `posture_udid` | `"true"` (required) or `"false"` (not required) |
| `TRUSTED_NETWORK` | Trusted network `network_id` | `"true"` or `"false"` |
| `RISK_FACTOR_TYPE` | `ZIA` | `UNKNOWN`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |

### Action Types
- `ALLOW` — Grant access
- `DENY` — Block access
- `REQUIRE_APPROVAL` — Require admin approval

## Available Tools

### Read Operations
| Tool | Description |
|------|-------------|
| `zpa_list_application_segments` | List all application segments |
| `zpa_get_application_segment` | Get specific application segment |
| `zpa_list_segment_groups` | List segment groups |
| `zpa_get_segment_group` | Get specific segment group |
| `zpa_list_server_groups` | List server groups |
| `zpa_get_server_group` | Get specific server group |
| `zpa_list_app_connector_groups` | List app connector groups |
| `zpa_get_app_connector_group` | Get specific connector group |
| `zpa_list_service_edge_groups` | List service edge groups |
| `zpa_get_service_edge_group` | Get specific service edge group |
| `zpa_list_application_servers` | List application servers |
| `zpa_get_application_server` | Get specific application server |
| `zpa_list_provisioning_keys` | List provisioning keys |
| `zpa_get_provisioning_key` | Get specific provisioning key |
| `zpa_list_access_policy_rules` | List access policy rules |
| `zpa_get_access_policy_rule` | Get specific access policy rule |
| `zpa_list_forwarding_policy_rules` | List forwarding policy rules |
| `zpa_get_forwarding_policy_rule` | Get specific forwarding rule |
| `zpa_list_timeout_policy_rules` | List timeout policy rules |
| `zpa_get_timeout_policy_rule` | Get specific timeout rule |
| `zpa_list_isolation_policy_rules` | List isolation policy rules |
| `zpa_get_isolation_policy_rule` | Get specific isolation rule |
| `zpa_list_app_protection_rules` | List app protection rules |
| `zpa_get_app_protection_rule` | Get specific app protection rule |
| `zpa_list_pra_portals` | List PRA portals |
| `zpa_get_pra_portal` | Get specific PRA portal |
| `zpa_list_pra_credentials` | List PRA credentials |
| `zpa_get_pra_credential` | Get specific PRA credential |
| `zpa_list_ba_certificates` | List browser access certificates |
| `zpa_get_ba_certificate` | Get specific BA certificate |
| `posture_profile_manager` | Retrieve posture profiles (action="read") |
| `trusted_network_manager` | Retrieve trusted networks (action="read") |
| `saml_attribute_manager` | Retrieve SAML attributes (action="read") |
| `scim_group_manager` | Retrieve SCIM groups (action="read") |
| `scim_attribute_manager` | Retrieve SCIM attributes (action="read") |
| `enrollment_certificate_manager` | Retrieve enrollment certificates (action="read") |
| `isolation_profile_manager` | Retrieve isolation profiles (action="read") |
| `app_protection_profile_manager` | Retrieve app protection profiles (action="read") |
| `app_segments_by_type_manager` | Retrieve app segments by type (BROWSER_ACCESS, INSPECT, SECURE_REMOTE_ACCESS) |

### Write Operations (Require --enable-write-tools)
| Tool | Description |
|------|-------------|
| `zpa_create_application_segment` | Create application segment |
| `zpa_update_application_segment` | Update application segment |
| `zpa_delete_application_segment` | Delete application segment |
| `zpa_create_segment_group` | Create segment group |
| `zpa_update_segment_group` | Update segment group |
| `zpa_delete_segment_group` | Delete segment group |
| `zpa_create_server_group` | Create server group |
| `zpa_update_server_group` | Update server group |
| `zpa_delete_server_group` | Delete server group |
| `zpa_create_app_connector_group` | Create app connector group |
| `zpa_update_app_connector_group` | Update app connector group |
| `zpa_delete_app_connector_group` | Delete app connector group |
| `zpa_create_application_server` | Create application server |
| `zpa_update_application_server` | Update application server |
| `zpa_delete_application_server` | Delete application server |
| `zpa_create_service_edge_group` | Create service edge group |
| `zpa_update_service_edge_group` | Update service edge group |
| `zpa_delete_service_edge_group` | Delete service edge group |
| `zpa_create_provisioning_key` | Create provisioning key |
| `zpa_update_provisioning_key` | Update provisioning key |
| `zpa_delete_provisioning_key` | Delete provisioning key |
| `zpa_create_access_policy_rule` | Create access policy rule |
| `zpa_update_access_policy_rule` | Update access policy rule |
| `zpa_delete_access_policy_rule` | Delete access policy rule |
| `zpa_create_forwarding_policy_rule` | Create forwarding policy rule |
| `zpa_update_forwarding_policy_rule` | Update forwarding policy rule |
| `zpa_delete_forwarding_policy_rule` | Delete forwarding policy rule |
| `zpa_create_timeout_policy_rule` | Create timeout policy rule |
| `zpa_update_timeout_policy_rule` | Update timeout policy rule |
| `zpa_delete_timeout_policy_rule` | Delete timeout policy rule |
| `zpa_create_isolation_policy_rule` | Create isolation policy rule |
| `zpa_update_isolation_policy_rule` | Update isolation policy rule |
| `zpa_delete_isolation_policy_rule` | Delete isolation policy rule |
| `zpa_create_app_protection_rule` | Create app protection rule |
| `zpa_update_app_protection_rule` | Update app protection rule |
| `zpa_delete_app_protection_rule` | Delete app protection rule |
| `zpa_create_pra_portal` | Create PRA portal |
| `zpa_update_pra_portal` | Update PRA portal |
| `zpa_delete_pra_portal` | Delete PRA portal |
| `zpa_create_pra_credential` | Create PRA credential |
| `zpa_update_pra_credential` | Update PRA credential |
| `zpa_delete_pra_credential` | Delete PRA credential |
| `zpa_create_ba_certificate` | Create BA certificate |
| `zpa_delete_ba_certificate` | Delete BA certificate |

## Response Style — Don't Leak Implementation Details

When answering the admin, give the **business answer in plain language**. Tool plumbing — `search` keys, JMESPath, pagination, validation, retries — is internal optimization the user does not care about.

- **Plain-language answers only.** Translate tool output into the answer the admin actually wanted; don't paste back JMESPath expressions or projections.
- **Empty is authoritative — do not fan out retries.** A `zpa_list_*` call with `search="<exact name>"` is a server-side substring match on the resource's `name` field. An empty result means the resource does not exist by that name. **Stop.** Do NOT re-call the same tool with split keywords, broader JMESPath projections, larger `page_size`, or no filter "to double-check". Ask the admin to clarify the name instead. ❌ *Five calls (search → split keywords → unfiltered → "let me drop the projection in case it's too aggressive").* ✅ *One call → empty → "I can't find an application segment named `<name>`. Want me to use a different name?"*
- **Don't narrate strategy pivots.** If a retry is genuinely warranted, do it quietly and report the final answer. ❌ *"The `search` filter came back empty. Let me list without the filter and apply JMESPath instead so I'm not relying on server-side fuzzy matching."* ✅ *"I didn't find a connector group by that name. Here's what's in the tenant: …"*
- **Don't claim a tool doesn't exist without checking.** If `zpa_get_*` / `zpa_create_*` / `zpa_update_*` / `zpa_delete_*` are visible, the matching `zpa_list_*` almost certainly exists too — search by the `zpa_` prefix and the resource name before declaring a gap. Examples that have been wrongly mis-claimed missing: `zpa_list_app_connector_groups`, `zpa_list_segment_groups`, `zpa_list_application_segments`.
- **Don't expose internal field names or validators.** Pydantic messages, MCP output-validator errors, and SDK tuple shapes are noise — convert them into a one-line user-facing summary.

## Best Practices

1. **Respect the dependency chain** — Create connector groups before server groups, server groups before app segments, app segments before policy rules. Deleting follows the reverse order.
2. **Policy rule ordering matters** — Access policy rules are evaluated top-to-bottom. New rules are appended at the end. Verify placement after creation.
3. **Always start with discovery** — Use `zpa_list_*` tools to understand current state before making changes.
4. **Check dependencies before deletion** — Application segments referenced by policy rules cannot be deleted until the policy reference is removed.
5. **Look up identity attributes before creating policy rules** — Use `saml_attribute_manager`, `scim_group_manager`, and `posture_profile_manager` to get the correct IDs for conditions.
6. **Confirm before write operations** — Always explain proposed changes and get explicit user confirmation.
