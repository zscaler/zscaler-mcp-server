---
name: create-access-rule
disable-model-invocation: true
argument-hint: "<rule_name> <action: allow|deny> [app_or_group] [user_or_group]"
description: "Create a ZPA access policy rule with v2 conditions for application access control."
---

# Create ZPA Access Policy Rule

Create rule: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Rule name**
- **Action**: ALLOW or DENY
- **Application or app group** to apply to (optional)
- **User, group, or department** to apply to (optional)

If insufficient details, ask the administrator what conditions to apply.

## Step 2: Look Up Required IDs

**For application conditions:**

```text
zpa_list_application_segments()
zpa_list_segment_groups()
```text

**For identity conditions:**

```text
zpa_list_scim_groups()
zpa_list_saml_attributes()
```text

## Step 3: Build Conditions

Construct v2 conditions. Common patterns:

**By SCIM group:**

```json
[{"operands": [{"object_type": "SCIM_GROUP", "entry_values": [{"lhs": "<idp_id>", "rhs": "<group_id>"}]}]}]
```text

**By application:**

```json
[{"operands": [{"object_type": "APP", "values": ["<segment_id>"]}]}]
```text

**Combined (group + app):**
Multiple condition objects are AND-ed together.

## Step 4: Create the Rule

```text
zpa_create_access_policy_rule(
  name="<rule_name>",
  action="<ALLOW|DENY>",
  conditions=[...]
)
```text

## Step 5: Verify

```text
zpa_list_access_policy_rules()
```text

Confirm the rule was created, its position in the rule order, and that conditions are correct.

Present a summary with the rule details, noting that rule ordering matters (rules are evaluated top-down, first match wins).
