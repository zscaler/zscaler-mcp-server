---
disable-model-invocation: true
argument-hint: "<rule_name> <action: bypass|intercept> [app_name] [user_or_group]"
description: "Create a ZPA client forwarding policy rule to bypass or intercept traffic."
---

# Create ZPA Forwarding Policy Rule

Create forwarding rule: **$ARGUMENTS**

## Step 1: Parse Input

Extract:
- **Rule name**
- **Action**: BYPASS (direct access), INTERCEPT (through ZPA), or INTERCEPT_ACCESSIBLE
- **Application** to apply to (optional)
- **User or group** (optional)

## Step 2: Look Up Required IDs

```
zpa_list_application_segments()
zpa_list_scim_groups()
```

## Step 3: Build Conditions

Construct conditions similar to access policy rules.

**Bypass for specific app:**
```json
[{"operands": [{"object_type": "APP", "values": ["<segment_id>"]}]}]
```

## Step 4: Create the Rule

```
zpa_create_forwarding_policy_rule(
  name="<rule_name>",
  action="<BYPASS|INTERCEPT|INTERCEPT_ACCESSIBLE>",
  conditions=[...]
)
```

## Step 5: Verify

```
zpa_list_forwarding_policy_rules()
```

Confirm rule creation and position. Present summary noting that BYPASS means traffic goes directly without ZPA interception.
