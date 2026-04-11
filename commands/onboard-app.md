---
name: onboard-app
disable-model-invocation: true
argument-hint: "<app_name> <domain:port> [description]"
description: "End-to-end onboarding of a new application in ZPA with full dependency chain."
---

# Onboard Application in ZPA

Onboard a new application: **$ARGUMENTS**

## Step 1: Parse Input

Extract:

- **Application name**
- **Domain(s) and port(s)** (e.g., app.company.com:443)
- **Description** (optional)

If domain or port is missing, ask the administrator.

## Step 2: Check Existing Resources

```text
zpa_list_application_segments()
```text

Verify no duplicate application segment exists for this domain.

```text
zpa_list_app_connector_groups()
```text

Check if a suitable connector group already exists.

## Step 3: Create Dependencies (if needed)

Follow the ZPA dependency chain:

1. **App Connector Group** (if none suitable):

```text
zpa_create_app_connector_group(name="<name>", location="<location>", country_code="<cc>")
```text

2. **Server Group** referencing the connector group:

```text
zpa_create_server_group(name="<name>", app_connector_group_ids=["<id>"])
```text

3. **Segment Group**:

```text
zpa_create_segment_group(name="<name>")
```text

## Step 4: Create Application Segment

```text
zpa_create_application_segment(
  name="<app_name>",
  domain_names=["<domain>"],
  tcp_port_ranges=["<port>", "<port>"],
  segment_group_id="<id>",
  server_group_ids=["<id>"]
)
```text

## Step 5: Create Access Policy Rule

```text
zpa_create_access_policy_rule(
  name="Allow <app_name>",
  action="ALLOW",
  conditions=[...]
)
```text

Ask the administrator which users/groups should have access.

## Step 6: Verify

```text
zpa_get_application_segment(segment_id="<id>")
```text

Confirm the application segment is enabled and all references are correct.

Present a summary of all created resources with their IDs.
