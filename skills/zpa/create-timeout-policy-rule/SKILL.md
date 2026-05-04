---
name: zpa-create-timeout-policy-rule
description: "Create ZPA timeout policy rules that control session re-authentication and idle timeout behavior. Configures how long a user session remains active (reauth_timeout) and how long an idle session persists (reauth_idle_timeout) before requiring re-authentication. Supports conditions: APP, APP_GROUP, CLIENT_TYPE, SAML, SCIM, SCIM_GROUP, PLATFORM, and POSTURE. Use when an administrator asks: 'Set session timeout', 'Configure idle timeout', 'Require re-authentication after X hours', or 'Set different timeouts per app or user group.'"
---

# ZPA: Create Timeout Policy Rule

## Keywords

timeout policy, session timeout, idle timeout, reauth timeout, re-authentication, session expiry, idle disconnect, timeout rule, session duration, zpa timeout, reauth policy

## Overview

Create ZPA timeout policy rules that define session re-authentication and idle timeout behavior. Timeout policies control how long a user's authenticated session remains valid and how long an idle connection persists before requiring re-authentication. Different applications and user groups can have different timeout values.

**Use this skill when:** An administrator asks to configure session timeouts, set idle disconnect timers, require re-authentication after a specific period, or apply different timeout rules to different applications or user groups.

---

## Timeout Parameters

### `reauth_timeout` (Session Timeout)

How long a user session remains valid before requiring re-authentication, regardless of activity.

| Value Format | Examples | Description |
|---|---|---|
| `<number> Minutes` | `"30 Minutes"`, `"60 Minutes"` | Session expires after N minutes |
| `<number> Hours` | `"4 Hours"`, `"8 Hours"` | Session expires after N hours |
| `<number> Days` | `"1 Days"`, `"10 Days"`, `"30 Days"` | Session expires after N days |
| `Never` | `"Never"` | Session never expires (not recommended for sensitive apps) |

Minimum: 10 minutes. Default: `"172800"` (seconds, i.e., 2 days).

### `reauth_idle_timeout` (Idle Timeout)

How long an idle (inactive) connection persists before the session is terminated.

| Value Format | Examples | Description |
|---|---|---|
| `<number> Minutes` | `"10 Minutes"`, `"30 Minutes"` | Idle session expires after N minutes |
| `<number> Hours` | `"1 Hours"`, `"2 Hours"` | Idle session expires after N hours |
| `<number> Days` | `"1 Days"` | Idle session expires after N days |
| `Never` | `"Never"` | Idle sessions never expire |

Minimum: 10 minutes. Default: `"600"` (seconds, i.e., 10 minutes).

### Action

The only supported action is `RE_AUTH` -- when the timeout is reached, the user must re-authenticate.

---

## Condition Object Types

Timeout policies support a subset of condition types.

### Value-Based (use `values`)

| Object Type | Description | Values |
|---|---|---|
| `APP` | Application segments | Application segment IDs |
| `APP_GROUP` | Segment groups | Segment group IDs |
| `CLIENT_TYPE` | Client connector type | `zpn_client_type_zapp`, `zpn_client_type_exporter`, `zpn_client_type_browser_isolation`, `zpn_client_type_ip_anchoring`, `zpn_client_type_edge_connector`, `zpn_client_type_branch_connector`, `zpn_client_type_zapp_partner` |

### Entry-Values Based (use `entry_values` with `lhs`/`rhs`)

| Object Type | LHS | RHS |
|---|---|---|
| `SAML` | SAML attribute ID | Attribute value to match |
| `SCIM` | SCIM attribute header ID | Attribute value to match |
| `SCIM_GROUP` | Identity Provider ID | SCIM group ID |
| `PLATFORM` | `linux`, `android`, `ios`, `mac`, `windows` | `"true"` or `"false"` |
| `POSTURE` | Posture profile `posture_udid` | `"true"` or `"false"` |

---

## Workflow

### Step 1: Gather Requirements

Ask the administrator:

**Required:**

- Rule name
- Session timeout value (e.g., "8 Hours", "30 Days", "Never")
- Idle timeout value (e.g., "30 Minutes", "1 Hours", "Never")

**Optional:**

- Description
- Which applications or segment groups to scope to
- Which users/groups this applies to
- Platform restrictions
- Posture requirements

**Common scenarios:**

- "Sessions should expire after 8 hours for all apps" -> global timeout rule
- "Sensitive apps should have a 30-minute idle timeout" -> scoped to APP_GROUP
- "Contractors should re-authenticate every 4 hours" -> scoped to SCIM_GROUP
- "Mobile devices should have shorter timeouts" -> scoped to PLATFORM

---

### Step 2: Look Up Required IDs

**For application scoping:**

```text
zpa_list_segment_groups()
zpa_list_application_segments()
```text

**For identity conditions:**

```text
get_zpa_scim_group(search="<group_name>")
get_zpa_saml_attribute(search="<attribute_name>")
```text

**For posture profiles:**

```text
get_zpa_posture_profile(search="<profile_name>")
```text

---

### Step 3: Create the Rule

```text
zpa_create_timeout_policy_rule(
  name="<rule_name>",
  action_type="RE_AUTH",
  reauth_timeout="<session_timeout>",
  reauth_idle_timeout="<idle_timeout>",
  description="<description>",
  conditions=<conditions_payload>
)
```text

---

### Step 4: Verify

```text
zpa_get_timeout_policy_rule(rule_id="<returned_rule_id>")
```text

---

## Ready-to-Use Examples

### Example 1: Standard Timeout for a Segment Group

Set 8-hour session timeout and 30-minute idle timeout for internal applications.

**Step 1: Find the segment group**

```text
zpa_list_segment_groups()
```text

**Step 2: Create rule**

```text
zpa_create_timeout_policy_rule(
  name="Standard Timeout - Internal Apps",
  action_type="RE_AUTH",
  reauth_timeout="8 Hours",
  reauth_idle_timeout="30 Minutes",
  description="Standard session and idle timeouts for internal applications",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<internal_apps_segment_group_id>"]
        }
      ]
    }
  ]
)
```text

---

### Example 2: Strict Timeout for Sensitive Applications

Short session timeout (4 hours) and aggressive idle timeout (10 minutes) for sensitive apps.

```text
zpa_create_timeout_policy_rule(
  name="Strict Timeout - Sensitive Apps",
  action_type="RE_AUTH",
  reauth_timeout="4 Hours",
  reauth_idle_timeout="10 Minutes",
  description="Short timeouts for sensitive/high-security applications",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<sensitive_apps_segment_group_id>"]
        }
      ]
    }
  ]
)
```text

---

### Example 3: Contractor-Specific Timeout

Contractors must re-authenticate every 4 hours with a 15-minute idle timeout.

**Step 1: Look up contractor group**

```text
get_zpa_scim_group(search="Contractors")
```text

**Step 2: Create rule**

```text
zpa_create_timeout_policy_rule(
  name="Contractor Timeout",
  action_type="RE_AUTH",
  reauth_timeout="4 Hours",
  reauth_idle_timeout="15 Minutes",
  description="Shorter session for contractor accounts",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "SCIM_GROUP",
          "entry_values": [
            {"lhs": "<idp_id>", "rhs": "<contractors_scim_group_id>"}
          ]
        }
      ]
    }
  ]
)
```text

---

### Example 4: Long Timeout with SAML + Segment Group

Allow a 10-day session for specific SAML-identified users on a specific segment group.

**Step 1: Look up IDs**

```text
get_zpa_saml_attribute(search="Email_Users")
zpa_list_segment_groups()
```text

**Step 2: Create rule**

```text
zpa_create_timeout_policy_rule(
  name="Extended Timeout - VIP Users",
  action_type="RE_AUTH",
  reauth_timeout="10 Days",
  reauth_idle_timeout="1 Hours",
  description="Extended session for VIP users accessing standard apps",
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
          "object_type": "SAML",
          "entry_values": [
            {"lhs": "<saml_email_attr_id>", "rhs": "vip1@company.com"},
            {"lhs": "<saml_email_attr_id>", "rhs": "vip2@company.com"}
          ]
        }
      ]
    }
  ]
)
```text

**Logic:** User must be accessing apps in the segment group AND have a matching SAML email.

---

### Example 5: Platform-Specific Timeout

Mobile devices (Android/iOS) get shorter timeouts than desktops.

**Mobile rule (stricter):**

```text
zpa_create_timeout_policy_rule(
  name="Mobile Timeout - Short",
  action_type="RE_AUTH",
  reauth_timeout="4 Hours",
  reauth_idle_timeout="15 Minutes",
  description="Shorter timeouts for mobile devices",
  conditions=[
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

**Desktop rule (more relaxed):**

```text
zpa_create_timeout_policy_rule(
  name="Desktop Timeout - Standard",
  action_type="RE_AUTH",
  reauth_timeout="10 Days",
  reauth_idle_timeout="1 Hours",
  description="Standard timeouts for desktop devices",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "PLATFORM",
          "entry_values": [
            {"lhs": "mac", "rhs": "true"},
            {"lhs": "windows", "rhs": "true"},
            {"lhs": "linux", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```text

---

### Example 6: Posture-Based Timeout

Devices that pass a posture check get a longer timeout; non-compliant devices get a shorter one.

**Step 1: Look up posture profile**

```text
get_zpa_posture_profile(search="CrowdStrike_ZTA")
```text

**Compliant devices (longer timeout):**

```text
zpa_create_timeout_policy_rule(
  name="Compliant Device Timeout",
  action_type="RE_AUTH",
  reauth_timeout="30 Days",
  reauth_idle_timeout="2 Hours",
  description="Extended timeout for posture-compliant devices",
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
    }
  ]
)
```text

**Non-compliant devices (shorter timeout):**

```text
zpa_create_timeout_policy_rule(
  name="Non-Compliant Device Timeout",
  action_type="RE_AUTH",
  reauth_timeout="1 Hours",
  reauth_idle_timeout="10 Minutes",
  description="Aggressive timeout for non-compliant devices",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "POSTURE",
          "entry_values": [
            {"lhs": "<posture_udid>", "rhs": "false"}
          ]
        }
      ]
    }
  ]
)
```text

---

### Example 7: Combined Conditions -- Group + App + Platform

Engineering team accessing sensitive apps from Linux gets a specific timeout.

```text
zpa_create_timeout_policy_rule(
  name="Engineering Linux Timeout",
  action_type="RE_AUTH",
  reauth_timeout="12 Hours",
  reauth_idle_timeout="45 Minutes",
  description="Custom timeout for Engineering on Linux accessing sensitive apps",
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
          "object_type": "SCIM_GROUP",
          "entry_values": [
            {"lhs": "<idp_id>", "rhs": "<engineering_group_id>"}
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
            {"lhs": "linux", "rhs": "true"}
          ]
        }
      ]
    }
  ]
)
```text

---

## Timeout Strategy Guide

| Use Case | reauth_timeout | reauth_idle_timeout | Rationale |
|---|---|---|---|
| Standard office apps | 8-10 Hours | 30-60 Minutes | Covers a workday without constant re-auth |
| Sensitive/compliance apps | 2-4 Hours | 10-15 Minutes | Frequent re-auth for high-security apps |
| Contractors / third parties | 4 Hours | 15 Minutes | Reduced trust, tighter controls |
| Mobile devices | 4-8 Hours | 15-30 Minutes | Higher risk of device loss |
| Desktop on corporate network | 10-30 Days | 1-2 Hours | Low risk, high convenience |
| Non-compliant devices | 1-2 Hours | 10 Minutes | Encourage compliance |
| Development/test environments | 30 Days / Never | 2 Hours | Minimize developer friction |

---

## Edge Cases

### No Conditions (Global Default)

A rule with no conditions applies as the default timeout for all users and applications:

```text
zpa_create_timeout_policy_rule(
  name="Global Default Timeout",
  action_type="RE_AUTH",
  reauth_timeout="8 Hours",
  reauth_idle_timeout="30 Minutes",
  conditions=[]
)
```text

### Never Expire

For development or test environments where re-authentication is disruptive:

```text
zpa_create_timeout_policy_rule(
  name="Dev Environment - No Timeout",
  action_type="RE_AUTH",
  reauth_timeout="Never",
  reauth_idle_timeout="Never",
  conditions=[
    {
      "operator": "OR",
      "operands": [
        {
          "object_type": "APP_GROUP",
          "values": ["<dev_segment_group_id>"]
        }
      ]
    }
  ]
)
```text

Not recommended for production applications.

### Listing Existing Timeout Rules (opt-in)

Do **not** pre-list timeout rules before every create. New ZPA timeout
rules are appended at the end of the policy by default; pre-listing
adds a round trip, gives no useful information for the typical case,
and invites fan-out retries when the list comes back empty on a fresh
tenant.

Run the listing **only** when the admin explicitly asks about ordering,
duplicate names, or wants to inspect existing rules:

```text
zpa_list_timeout_policy_rules()
```text

---

## Quick Reference

**Tools used:**

- `zpa_list_segment_groups()` -- find segment group IDs
- `zpa_list_application_segments()` -- find application segment IDs
- `get_zpa_scim_group(search)` -- look up SCIM group IDs
- `get_zpa_saml_attribute(search)` -- look up SAML attribute IDs
- `get_zpa_posture_profile(search)` -- look up posture profile UDIDs
- `zpa_create_timeout_policy_rule(name, action_type, reauth_timeout, reauth_idle_timeout, conditions)` -- create the rule (no pre-flight needed)
- `zpa_list_timeout_policy_rules()` -- **only** when the admin explicitly asks about ordering or wants to inspect existing rules
- `zpa_get_timeout_policy_rule(rule_id)` -- verify the rule

**Timeout format:** `"<number> Minutes"`, `"<number> Hours"`, `"<number> Days"`, `"Never"`

**Action:** `RE_AUTH` (only supported action)

**Condition logic:**

- Multiple condition blocks = AND (all must match)
- Multiple entry_values within a block = OR (any can match)
- Separate condition blocks per object type
