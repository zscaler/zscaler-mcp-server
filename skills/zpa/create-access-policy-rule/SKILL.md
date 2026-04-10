---
name: zpa-create-access-policy-rule
description: "Create ZPA access policy rules with v2 conditions. Supports all condition object types: APP, APP_GROUP, SAML, SCIM, SCIM_GROUP, PLATFORM, COUNTRY_CODE, POSTURE, TRUSTED_NETWORK, RISK_FACTOR_TYPE, CLIENT_TYPE, MACHINE_GRP, LOCATION, and CHROME_ENTERPRISE. Walks through: (1) gathering requirements, (2) looking up identity attributes (SAML/SCIM), (3) building the conditions payload, (4) creating the rule. Includes ready-to-use examples for common scenarios: SCIM group access, SAML attribute matching, platform restrictions, country-based access, posture checks, and combined conditions."
---

# ZPA: Create Access Policy Rule

## Keywords

access policy, access rule, allow rule, deny rule, zpa policy, scim group policy, saml policy, platform restriction, country restriction, posture check, require approval, zero trust policy, conditional access

## Overview

Create ZPA access policy rules that control who can access private applications. Access policies use the v2 condition format and support a rich set of condition types: identity-based (SAML/SCIM), device-based (platform, posture, Chrome Enterprise), network-based (trusted networks, country codes), and risk-based (ZIA risk factors).

**Use this skill when:** An administrator asks to create an access policy rule, grant or deny application access based on user identity, device posture, location, or any combination of conditions.

---

## Condition Object Type Reference

Each condition block must contain a **single object type**. Multiple condition blocks are ANDed together. Within a condition block, multiple operands or entry_values are ORed.

### Value-Based Object Types (use `values`)

| Object Type | Description | Values |
|---|---|---|
| `APP` | Application segments | Application segment IDs |
| `APP_GROUP` | Segment groups | Segment group IDs |
| `CLIENT_TYPE` | Client connector type | `zpn_client_type_zapp`, `zpn_client_type_exporter`, `zpn_client_type_machine_tunnel`, `zpn_client_type_browser_isolation`, `zpn_client_type_ip_anchoring`, `zpn_client_type_edge_connector`, `zpn_client_type_branch_connector`, `zpn_client_type_zapp_partner` |
| `MACHINE_GRP` | Machine groups | Machine group IDs |
| `LOCATION` | Locations | Location IDs |
| `EDGE_CONNECTOR_GROUP` | Edge connector groups | Edge connector group IDs |
| `BRANCH_CONNECTOR_GROUP` | Branch connector groups | Branch connector group IDs |

### Entry-Values Object Types (use `entry_values` with `lhs`/`rhs`)

| Object Type | LHS | RHS |
|---|---|---|
| `SAML` | SAML attribute ID | Attribute value to match (email, group name, etc.) |
| `SCIM` | SCIM attribute header ID | Attribute value to match |
| `SCIM_GROUP` | Identity Provider ID | SCIM group ID |
| `PLATFORM` | `linux`, `android`, `ios`, `mac`, `windows` | `"true"` or `"false"` |
| `COUNTRY_CODE` | ISO 3166 Alpha-2 code (`US`, `CA`, `GB`) | `"true"` or `"false"` |
| `POSTURE` | Posture profile `posture_udid` | `"true"` or `"false"` |
| `TRUSTED_NETWORK` | Trusted network `network_id` | `"true"` or `"false"` |
| `RISK_FACTOR_TYPE` | `ZIA` | `UNKNOWN`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `CHROME_ENTERPRISE` | `managed` | `"true"` or `"false"` |

### Action Types

| Action | Description |
|---|---|
| `ALLOW` | Permit access |
| `DENY` | Block access |
| `REQUIRE_APPROVAL` | Require explicit approval before access |

---

## Workflow

### Step 1: Gather Requirements

Ask the administrator:

**Required:**

- Rule name
- Action: `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`
- What conditions determine access (identity, platform, location, etc.)

**Optional:**

- Description
- Which application segments or segment groups to scope to
- App connector group IDs or server group IDs

---

### Step 2: Look Up Identity Attributes

If the rule uses identity-based conditions (SAML, SCIM, SCIM_GROUP), look up the required IDs first.

**For SCIM groups:**

```text
get_zpa_scim_group(search="<group_name>")
```text

Note both the SCIM group ID (used as `rhs`) and the Identity Provider ID (used as `lhs`).

**For SAML attributes:**

```text
get_zpa_saml_attribute(search="<attribute_name>")
```text

Note the SAML attribute ID (used as `lhs`). The `rhs` is the value to match (e.g., an email address or group name string).

**For SCIM attributes:**

```text
get_zpa_scim_attribute(search="<attribute_name>")
```text

**For segment groups (APP_GROUP):**

```text
zpa_list_segment_groups()
```text

**For posture profiles:**

```text
get_zpa_posture_profile(search="<profile_name>")
```text

Note the `posture_udid` value (used as `lhs`).

**For trusted networks:**

```text
get_zpa_trusted_network(search="<network_name>")
```text

Note the `network_id` value (used as `lhs`).

---

### Step 3: Build the Conditions Payload

Conditions use a list of dictionaries. Each dictionary represents one condition block with an `operator` and `operands`. **Separate condition blocks for each object type.**

**Format:**

```json
[
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "<OBJECT_TYPE>",
        "values": ["<id1>", "<id2>"]
      }
    ]
  },
  {
    "operator": "OR",
    "operands": [
      {
        "object_type": "<OBJECT_TYPE>",
        "entry_values": [
          {"lhs": "<lhs_value>", "rhs": "<rhs_value>"}
        ]
      }
    ]
  }
]
```text

**Rules:**

- Each condition block contains **one object type only**
- Multiple condition blocks are **ANDed** together (all must match)
- Within a block, multiple `entry_values` or multiple `values` are **ORed** (any can match)
- Value-based types (`APP`, `APP_GROUP`, `CLIENT_TYPE`, etc.) use `values`
- Entry-based types (`SAML`, `SCIM_GROUP`, `PLATFORM`, etc.) use `entry_values`

---

### Step 4: Create the Rule

```text
zpa_create_access_policy_rule(
  name="<rule_name>",
  action_type="ALLOW",
  description="<description>",
  conditions=<conditions_payload>,
  app_connector_group_ids=["<optional_connector_group_ids>"],
  app_server_group_ids=["<optional_server_group_ids>"]
)
```text

---

### Step 5: Verify

```text
zpa_get_access_policy_rule(rule_id="<returned_rule_id>")
```text

---

## Ready-to-Use Examples

### Example 1: Allow SCIM Groups to Access a Segment Group

Allow members of "Engineering" or "DevOps" SCIM groups to access an application segment group.

**Step 1: Look up IDs**

```text
get_zpa_scim_group(search="Engineering")
get_zpa_scim_group(search="DevOps")
zpa_list_segment_groups()
```text

**Step 2: Create rule**

```text
zpa_create_access_policy_rule(
  name="Allow Engineering and DevOps",
  action_type="ALLOW",
  description="Grants Engineering and DevOps teams access to internal apps",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<segment_group_id>"]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "SCIM_GROUP",
          "entry_values": [
            {"lhs": "<idp_id>", "rhs": "<engineering_scim_group_id>"},
            {"lhs": "<idp_id>", "rhs": "<devops_scim_group_id>"}
          ]
        }
      ]
    }
  ]
)
```text

**Logic:** User must be in the segment group's apps AND be a member of Engineering OR DevOps.

---

### Example 2: Allow SAML Users with Platform Restriction

Allow specific SAML-identified users, but only from macOS and Windows devices.

**Step 1: Look up SAML attribute**

```text
get_zpa_saml_attribute(search="Email_Users")
```text

**Step 2: Create rule**

```text
zpa_create_access_policy_rule(
  name="Allow Specific Users on Mac/Windows",
  action_type="ALLOW",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "SAML",
          "entry_values": [
            {"lhs": "<saml_email_attribute_id>", "rhs": "alice@company.com"},
            {"lhs": "<saml_email_attribute_id>", "rhs": "bob@company.com"}
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
            {"lhs": "mac", "rhs": "true"},
            {"lhs": "windows", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```text

**Logic:** User must match a SAML email AND be on macOS OR Windows.

---

### Example 3: Country-Based Access Restriction

Allow access only from the United States and Canada.

```text
zpa_create_access_policy_rule(
  name="US and Canada Only",
  action_type="ALLOW",
  description="Restrict access to US and Canadian locations",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<segment_group_id>"]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "COUNTRY_CODE",
          "entry_values": [
            {"lhs": "US", "rhs": "true"},
            {"lhs": "CA", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```text

---

### Example 4: Posture-Based Access with Risk Factor

Allow access only from devices that pass a posture check and have a ZIA risk score of LOW or below.

**Step 1: Look up posture profile**

```text
get_zpa_posture_profile(search="CrowdStrike_ZTA")
```text

**Step 2: Create rule**

```text
zpa_create_access_policy_rule(
  name="Posture and Risk Check",
  action_type="ALLOW",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "POSTURE",
          "entry_values": [
            {"lhs": "<posture_udid>", "rhs": "true"}
          ]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "RISK_FACTOR_TYPE",
          "entry_values": [
            {"lhs": "ZIA", "rhs": "UNKNOWN"},
            {"lhs": "ZIA", "rhs": "LOW"}
          ]
        }
      ]
    }
  ]
)
```text

**Logic:** Device must pass posture check AND have a ZIA risk score of UNKNOWN or LOW.

---

### Example 5: Combined SCIM + SAML + Platform + Country

A comprehensive rule combining identity, device, and location conditions.

```text
zpa_create_access_policy_rule(
  name="Comprehensive Access Rule",
  action_type="ALLOW",
  description="Engineering team, Mac/Linux only, from US/CA",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<segment_group_id>"]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "SCIM_GROUP",
          "entry_values": [
            {"lhs": "<idp_id>", "rhs": "<engineering_group_id>"}
          ]
        },
        {
          "object_type": "SAML",
          "entry_values": [
            {"lhs": "<saml_email_attr_id>", "rhs": "admin@company.com"}
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
            {"lhs": "mac", "rhs": "true"},
            {"lhs": "linux", "rhs": "true"}
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
            {"lhs": "US", "rhs": "true"},
            {"lhs": "CA", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```text

**Logic:** Must access apps in the segment group AND (be in Engineering SCIM group OR be <admin@company.com>) AND (be on macOS OR Linux) AND (be in US OR Canada).

---

### Example 6: Deny Rule

Block access from specific platforms.

```text
zpa_create_access_policy_rule(
  name="Deny Android and iOS",
  action_type="DENY",
  description="Block mobile device access to sensitive applications",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<sensitive_apps_segment_group_id>"]
        }
      ]
    },
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "PLATFORM",
          "entry_values": [
            {"lhs": "android", "rhs": "true"},
            {"lhs": "ios", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```text

---

## Edge Cases

### No Conditions (Global Rule)

A rule with no conditions applies to all users and all applications:

```text
zpa_create_access_policy_rule(
  name="Default Allow All",
  action_type="ALLOW",
  conditions=[]
)
```text

### Mixing SAML and SCIM in the Same Condition Block

SAML and SCIM_GROUP operands can share a condition block since they are identity types. They are ORed within the block:

```json
{
  "operator": "OR",
  "operands": [
    {
      "object_type": "SAML",
      "entry_values": [{"lhs": "<saml_attr_id>", "rhs": "user@company.com"}]
    },
    {
      "object_type": "SCIM_GROUP",
      "entry_values": [{"lhs": "<idp_id>", "rhs": "<scim_group_id>"}]
    }
  ]
}
```text

### Trusted Network Condition

```json
{
  "operator": "OR",
  "operands": [
    {
      "object_type": "TRUSTED_NETWORK",
      "entry_values": [{"lhs": "<network_id>", "rhs": "true"}]
    }
  ]
}
```text

---

## Quick Reference

**Tools used:**

- `get_zpa_scim_group(search)` -- look up SCIM group IDs
- `get_zpa_saml_attribute(search)` -- look up SAML attribute IDs
- `get_zpa_scim_attribute(search)` -- look up SCIM attribute IDs
- `get_zpa_posture_profile(search)` -- look up posture profile UDIDs
- `get_zpa_trusted_network(search)` -- look up trusted network IDs
- `zpa_list_segment_groups()` -- look up segment group IDs
- `zpa_create_access_policy_rule(name, action_type, conditions, ...)` -- create the rule
- `zpa_get_access_policy_rule(rule_id)` -- verify the rule

**Condition logic:**

- Multiple condition blocks = AND (all must match)
- Multiple entry_values within a block = OR (any can match)
- Separate condition blocks per object type

**Actions:** `ALLOW`, `DENY`, `REQUIRE_APPROVAL`
