---
name: create-server-group
disable-model-invocation: true
argument-hint: "<server_group_name> [connector_group_name]"
description: "Create a ZPA server group with required app connector group dependency."
---

# Create ZPA Server Group

Create server group: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Server group name**
- **Connector group name** (optional -- will check for existing ones)

## Step 2: Check Existing Connector Groups

```text
zpa_list_app_connector_groups()
```text

If no suitable connector group exists and no name was provided, ask the administrator if one should be created.

## Step 3: Create Connector Group (if needed)

```text
zpa_create_app_connector_group(
  name="<name>",
  location="<location>",
  country_code="<cc>"
)
```text

## Step 4: Create Server Group

```text
zpa_create_server_group(
  name="<server_group_name>",
  app_connector_group_ids=["<connector_group_id>"]
)
```text

## Step 5: Verify

```text
zpa_get_server_group(group_id="<id>")
```text

Confirm the server group references the correct connector group. Present a summary with IDs for use in application segment creation.
