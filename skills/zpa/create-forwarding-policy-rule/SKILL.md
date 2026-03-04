---
name: zpa-create-forwarding-policy-rule
description: "Create ZPA client forwarding policy rules that control how traffic is routed from the Zscaler Client Connector. Supports actions: BYPASS (direct internet), INTERCEPT (route through ZPA), INTERCEPT_ACCESSIBLE (route only if reachable). Conditions support APP, APP_GROUP, SAML, SCIM, SCIM_GROUP, PLATFORM, COUNTRY_CODE, POSTURE, TRUSTED_NETWORK, and CLIENT_TYPE. Use when an administrator asks: 'Bypass ZPA for specific apps', 'Route traffic directly', or 'Create a forwarding exception.'"
---

# ZPA: Create Forwarding Policy Rule

## Keywords
forwarding policy, forwarding rule, bypass zpa, intercept traffic, direct access, client forwarding, traffic routing, bypass rule, split tunnel, forwarding exception, zpa bypass

## Overview

Create ZPA client forwarding policy rules that control how the Zscaler Client Connector routes traffic. Forwarding policies determine whether traffic for specific applications is intercepted by ZPA (tunneled through the Zscaler cloud), bypassed (sent directly to the internet), or conditionally intercepted.

**Use this skill when:** An administrator asks to bypass ZPA for certain applications, create split-tunnel exceptions, route traffic directly for specific users or platforms, or configure conditional forwarding rules.

---

## Action Types

| Action | Description | Use Case |
|---|---|---|
| `BYPASS` | Traffic goes directly to the destination, skipping ZPA entirely | Apps that don't need ZPA tunneling (e.g., video conferencing, local printers) |
| `INTERCEPT` | Traffic is routed through ZPA (tunneled via the Zscaler cloud) | Default for private applications that need ZPA access |
| `INTERCEPT_ACCESSIBLE` | Traffic is intercepted only if the destination is reachable through ZPA | Hybrid apps that may or may not be behind ZPA depending on the user's location |

---

## Condition Object Type Reference

Forwarding policies support the same condition object types as access policies. Each condition block must contain a **single object type**. Multiple condition blocks are ANDed together.

### Value-Based Object Types (use `values`)

| Object Type | Description | Values |
|---|---|---|
| `APP` | Application segments | Application segment IDs |
| `APP_GROUP` | Segment groups | Segment group IDs |
| `CLIENT_TYPE` | Client connector type | `zpn_client_type_zapp`, `zpn_client_type_exporter`, `zpn_client_type_browser_isolation`, `zpn_client_type_ip_anchoring`, `zpn_client_type_edge_connector`, `zpn_client_type_branch_connector`, `zpn_client_type_zapp_partner` |
| `MACHINE_GRP` | Machine groups | Machine group IDs |
| `LOCATION` | Locations | Location IDs |

### Entry-Values Object Types (use `entry_values` with `lhs`/`rhs`)

| Object Type | LHS | RHS |
|---|---|---|
| `SAML` | SAML attribute ID | Attribute value to match |
| `SCIM` | SCIM attribute header ID | Attribute value to match |
| `SCIM_GROUP` | Identity Provider ID | SCIM group ID |
| `PLATFORM` | `linux`, `android`, `ios`, `mac`, `windows` | `"true"` or `"false"` |
| `COUNTRY_CODE` | ISO 3166 Alpha-2 code (`US`, `CA`, `GB`) | `"true"` or `"false"` |
| `POSTURE` | Posture profile `posture_udid` | `"true"` or `"false"` |
| `TRUSTED_NETWORK` | Trusted network `network_id` | `"true"` or `"false"` |

---

## Workflow

### Step 1: Gather Requirements

Ask the administrator:

**Required:**
- Rule name
- Action: `BYPASS`, `INTERCEPT`, or `INTERCEPT_ACCESSIBLE`
- Which applications or application groups should this rule apply to?

**Optional:**
- Description
- Who should this apply to? (specific users/groups or everyone)
- Platform restrictions (e.g., only bypass on Windows)
- Location or network conditions

**Common scenarios:**
- "Bypass ZPA for Zoom/Teams traffic" -> `BYPASS` with specific APP or APP_GROUP
- "Route all traffic through ZPA for contractors" -> `INTERCEPT` with SCIM_GROUP condition
- "Direct access when on corporate network" -> `BYPASS` with TRUSTED_NETWORK condition

---

### Step 2: Look Up Required IDs

**For application scoping:**
```
zpa_list_application_segments()
zpa_list_segment_groups()
```

**For identity conditions:**
```
get_zpa_scim_group(search="<group_name>")
get_zpa_saml_attribute(search="<attribute_name>")
```

**For trusted networks:**
```
get_zpa_trusted_network(search="<network_name>")
```

**For posture profiles:**
```
get_zpa_posture_profile(search="<profile_name>")
```

---

### Step 3: Build Conditions and Create the Rule

```
zpa_create_forwarding_policy_rule(
  name="<rule_name>",
  action_type="BYPASS",
  description="<description>",
  conditions=<conditions_payload>
)
```

The conditions format is identical to access policy rules. See the examples below.

---

### Step 4: Verify

```
zpa_get_forwarding_policy_rule(rule_id="<returned_rule_id>")
```

Present the rule summary including action, conditions, and scope.

---

## Ready-to-Use Examples

### Example 1: Bypass ZPA for a Segment Group

Bypass ZPA tunneling for all applications in a segment group (e.g., video conferencing apps).

**Step 1: Find the segment group**
```
zpa_list_segment_groups()
```

**Step 2: Create rule**
```
zpa_create_forwarding_policy_rule(
  name="Bypass Video Conferencing",
  action_type="BYPASS",
  description="Send video conferencing traffic directly, bypassing ZPA tunnel",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<video_conferencing_segment_group_id>"]
        }
      ]
    }
  ]
)
```

---

### Example 2: Bypass for Specific Users on Trusted Network

When users are on the corporate trusted network, bypass ZPA and go direct.

**Step 1: Look up IDs**
```
get_zpa_trusted_network(search="Corporate_WiFi")
get_zpa_scim_group(search="Office_Workers")
```

**Step 2: Create rule**
```
zpa_create_forwarding_policy_rule(
  name="Direct Access on Corporate Network",
  action_type="BYPASS",
  description="Bypass ZPA when on corporate trusted network",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "TRUSTED_NETWORK",
          "entry_values": [
            {"lhs": "<corporate_wifi_network_id>", "rhs": "true"}
          ]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "SCIM_GROUP",
          "entry_values": [
            {"lhs": "<idp_id>", "rhs": "<office_workers_group_id>"}
          ]
        }
      ]
    }
  ]
)
```

**Logic:** User must be on the corporate trusted network AND be in the Office_Workers group.

---

### Example 3: Intercept All Traffic for Contractors

Force all contractor traffic through ZPA regardless of application.

**Step 1: Look up contractor group**
```
get_zpa_scim_group(search="Contractors")
```

**Step 2: Create rule**
```
zpa_create_forwarding_policy_rule(
  name="Intercept Contractor Traffic",
  action_type="INTERCEPT",
  description="Route all contractor traffic through ZPA for security",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "SCIM_GROUP",
          "entry_values": [
            {"lhs": "<idp_id>", "rhs": "<contractors_group_id>"}
          ]
        }
      ]
    }
  ]
)
```

---

### Example 4: Platform-Specific Bypass

Bypass ZPA for specific applications only on Linux and Android devices.

```
zpa_create_forwarding_policy_rule(
  name="Bypass Dev Tools on Linux/Android",
  action_type="BYPASS",
  description="Development tools bypass ZPA on Linux and Android",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<dev_tools_segment_group_id>"]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "PLATFORM",
          "entry_values": [
            {"lhs": "linux", "rhs": "true"},
            {"lhs": "android", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```

---

### Example 5: INTERCEPT_ACCESSIBLE for Hybrid Apps

Use `INTERCEPT_ACCESSIBLE` for applications that may or may not be reachable through ZPA depending on the user's location.

```
zpa_create_forwarding_policy_rule(
  name="Conditional Intercept for Hybrid Apps",
  action_type="INTERCEPT_ACCESSIBLE",
  description="Route through ZPA only if destination is reachable via ZPA connectors",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<hybrid_apps_segment_group_id>"]
        }
      ]
    }
  ]
)
```

**When to use:** The application exists both on the corporate network (reachable via ZPA) and on the public internet. `INTERCEPT_ACCESSIBLE` routes through ZPA if connectors can reach it, otherwise falls back to direct access.

---

### Example 6: Combined SAML + Platform + Country

Bypass ZPA for a SAML-identified group, only on Windows, only from the US.

```
zpa_create_forwarding_policy_rule(
  name="US Windows Bypass for Finance",
  action_type="BYPASS",
  description="Finance team on Windows in the US bypasses ZPA for specific apps",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<finance_apps_segment_group_id>"]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "SAML",
          "entry_values": [
            {"lhs": "<saml_group_attr_id>", "rhs": "Finance"}
          ]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "PLATFORM",
          "entry_values": [
            {"lhs": "windows", "rhs": "true"}
          ]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "COUNTRY_CODE",
          "entry_values": [
            {"lhs": "US", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```

**Logic:** App must be in the Finance segment group AND user has SAML group "Finance" AND platform is Windows AND country is US.

---

## Forwarding vs Access Policy Comparison

| Aspect | Access Policy | Forwarding Policy |
|---|---|---|
| **Purpose** | Who can access apps | How traffic reaches apps |
| **Actions** | `ALLOW`, `DENY`, `REQUIRE_APPROVAL` | `BYPASS`, `INTERCEPT`, `INTERCEPT_ACCESSIBLE` |
| **Evaluated when** | After forwarding decision | Before access decision |
| **Tool** | `zpa_create_access_policy_rule` | `zpa_create_forwarding_policy_rule` |
| **Condition types** | Same | Same |

**Evaluation order:** Forwarding policy is evaluated first (determines routing), then access policy is evaluated (determines authorization).

---

## Edge Cases

### Bypass with No Conditions

A forwarding rule with no conditions applies globally:

```
zpa_create_forwarding_policy_rule(
  name="Global Bypass",
  action_type="BYPASS",
  conditions=[]
)
```

This bypasses ZPA for ALL traffic, which is almost never desired. Always scope with conditions.

### Conflicting Forwarding and Access Rules

If traffic is bypassed by a forwarding rule, the access policy rule is never evaluated for that traffic. Be careful not to bypass traffic that requires access policy enforcement.

### Listing Existing Forwarding Rules

Before creating, check what rules already exist:
```
zpa_list_forwarding_policy_rules()
```

---

## Quick Reference

**Tools used:**
- `zpa_list_application_segments()` -- find application segments
- `zpa_list_segment_groups()` -- find segment groups
- `get_zpa_scim_group(search)` -- look up SCIM group IDs
- `get_zpa_saml_attribute(search)` -- look up SAML attribute IDs
- `get_zpa_trusted_network(search)` -- look up trusted network IDs
- `get_zpa_posture_profile(search)` -- look up posture profile UDIDs
- `zpa_list_forwarding_policy_rules()` -- list existing rules
- `zpa_create_forwarding_policy_rule(name, action_type, conditions)` -- create the rule
- `zpa_get_forwarding_policy_rule(rule_id)` -- verify the rule

**Condition logic:**
- Multiple condition blocks = AND (all must match)
- Multiple entry_values within a block = OR (any can match)
- Separate condition blocks per object type

**Actions:** `BYPASS`, `INTERCEPT`, `INTERCEPT_ACCESSIBLE`
