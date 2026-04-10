---
disable-model-invocation: true
argument-hint: "<rule_name> <reauth_timeout_seconds> [idle_timeout_seconds] [app_or_group]"
description: "Create a ZPA timeout policy rule for session re-authentication and idle timeout."
---

# Create ZPA Timeout Policy Rule

Create timeout rule: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Rule name**
- **Re-authentication timeout** in seconds (e.g., 86400 = 24 hours)
- **Idle timeout** in seconds (optional, e.g., 1800 = 30 minutes)
- **Application or group** scope (optional)

## Step 2: Look Up Application IDs (if scoped)

```text
zpa_list_application_segments()
zpa_list_segment_groups()
```text

## Step 3: Build Conditions

If scoped to specific applications:

```json
[{"operands": [{"object_type": "APP", "values": ["<segment_id>"]}]}]
```text

## Step 4: Create the Rule

```text
zpa_create_timeout_policy_rule(
  name="<rule_name>",
  reauth_timeout=<seconds>,
  reauth_idle_timeout=<idle_seconds>,
  conditions=[...]
)
```text

## Step 5: Verify

```text
zpa_list_timeout_policy_rules()
```text

Present summary with rule details and human-readable timeout values (e.g., "24 hours re-auth, 30 minutes idle").
