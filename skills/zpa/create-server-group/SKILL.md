---
name: zpa-create-server-group
description: "Create a ZPA server group with all required dependencies. Server groups require app connector groups to exist first. This skill walks through the dependency chain: (1) Check for existing app connector groups, (2) Create an app connector group if none exist, (3) Create the server group referencing the connector group IDs, (4) Verify the server group was created correctly. Use when an administrator needs to set up a new server group for application access."
---

# ZPA: Create Server Group

## Keywords

create server group, new server group, zpa server group, add server group, connector group dependency, server group setup, zpa infrastructure

## Overview

Create a ZPA server group by first ensuring its required dependency -- an app connector group -- exists. Server groups are fundamental building blocks in ZPA that define which application connectors serve traffic for specific applications.

**Use this skill when:** An administrator asks to create a new server group, set up ZPA infrastructure, or needs help understanding server group dependencies.

---

## Workflow

Follow this 5-step process to create a server group with its dependencies.

### Step 1: Gather Requirements

Ask the administrator for the following information:

**Required:**

- Server group name
- Whether to use an existing app connector group or create a new one

**Optional:**

- Server group description
- Whether IP anchoring is needed (`ip_anchored`)
- Whether dynamic discovery should be enabled (`dynamic_discovery`)
- Specific application server IDs to associate (`server_ids`)
- Microtenant ID (for multi-tenant environments)

---

### Step 1.5: Pick the Server Group Pattern (baseline alignment)

Reference: ZPA Baseline Recommendations v1.0 §Server Group Definition. Pick one of the five patterns before you choose `app_connector_group_ids`:

| Pattern | When to use | AC group binding |
|---|---|---|
| **Dedicated per location** (default for most apps) | Apps hosted in one DC / cloud region | The single location AC group only |
| **Secure enclave** | Sensitive / regulated apps (Finance, HR, Legal, PCI) | The **isolated** enclave AC group only — never co-mingle with general traffic |
| **Global** | Apps reachable from anywhere (AD DCs, NTP, internally LB'd web) | **All** location AC groups |
| **SIPA** | Third-party apps that require fixed source IP | Dedicated SIPA AC group(s) only — separate from general traffic so heavy general load can't degrade SIPA performance |
| **Regional** | Single-DC app that needs cross-DC failover | Multiple AC groups in a region (e.g. "US-East" SG bound to all US-East AC groups) |
| **Discovery** | Wildcard segment for unknown apps (`*.corp.example.com`) | All communal AC groups, plus `dynamic_discovery=True` |

Once you've picked the pattern, the AC group selection in Step 2 / 3 is determined.

#### Dynamic Discovery — when to disable it

The baseline doc recommends `dynamic_discovery=True` for almost all server groups. **Disable it only when:**

- Strict per-server segmentation is required (specific server IDs must be served by specific connectors).
- You need destination NAT for overlapping networks across multi-DC / multi-cloud or partner environments served by ZPA Extranet.

**Important — dynamic discovery ≠ application health checks.** Dynamic discovery only learns server reachability from connector lookups. Application health (TCP probes, HTTP checks, port polling) is configured separately on the **application segment** via the `health_reporting` field. See the `application_segment-onboard` skill for `health_reporting` defaults.

---

### Step 2: Check for Existing App Connector Groups

Before creating anything, list existing app connector groups to avoid duplicates.

```text
zpa_list_app_connector_groups()
```text

**Evaluate results:**

- If a suitable connector group already exists, note its `id` for use in Step 4
- If no connector groups exist or none are suitable, proceed to Step 3
- Present the list to the administrator and ask which to use (or confirm creating a new one)

#### Example Response

```text
I found the following existing app connector groups:

1. **US-East Connectors** (ID: 72058304567890)
   - Location: New York, US
   - Enabled: Yes
   - Connectors: 3

2. **EU-West Connectors** (ID: 72058304567891)
   - Location: Dublin, IE
   - Enabled: Yes
   - Connectors: 2

Would you like to use one of these, or should I create a new app connector group?
```text

---

### Step 3: Create App Connector Group (if needed)

If a new app connector group is required:

```text
zpa_create_app_connector_group(
  name="<connector_group_name>",
  description="<description>",
  enabled=True,
  latitude="<latitude>",
  longitude="<longitude>",
  location="<location_name>",
  city_country="<city>, <country>",
  country_code="<ISO_country_code>"
)
```text

**Important notes:**

- `country_code` accepts full names (e.g., "United States") or ISO codes ("US")
- `latitude` and `longitude` help with geo-proximity routing
- Save the returned `id` -- it is required in the next step

#### Confirm creation

```text
zpa_get_app_connector_group(group_id="<returned_id>")
```text

---

### Step 4: Create the Server Group

With the app connector group ID(s) in hand, create the server group:

```text
zpa_create_server_group(
  name="<server_group_name>",
  app_connector_group_ids=["<connector_group_id>"],
  description="<description>",
  enabled=True,
  ip_anchored=False,
  dynamic_discovery=True
)
```text

**Parameter guidance:**

- `app_connector_group_ids` (required): List of one or more app connector group IDs from Step 2 or Step 3
- `dynamic_discovery`: Set to `True` when application servers are discovered automatically; `False` when specifying servers manually via `server_ids`
- `ip_anchored`: Set to `True` only when source IP anchoring is required (advanced use case)

---

### Step 5: Verify and Summarize

Confirm the server group was created successfully:

```text
zpa_get_server_group(group_id="<returned_server_group_id>")
```text

#### Present Summary

```text
Server group created successfully.

**Server Group:**
- Name: <name>
- ID: <id>
- Enabled: Yes
- Dynamic Discovery: Yes/No
- IP Anchored: Yes/No

**Associated App Connector Group(s):**
- <connector_group_name> (ID: <connector_group_id>)

**Next Steps:**
- You can now reference this server group (ID: <id>) when creating
  application segments using `zpa_create_application_segment`
- To create a complete application, see the "application_segment-onboard" skill
```text

---

## Dependency Chain Reference

```text
App Connector Group (no dependencies)
        │
        ▼
   Server Group (requires app_connector_group_ids)
        │
        ▼
Application Segment (requires segment_group_id, optionally server_group_ids)
        │
        ▼
 Access Policy Rule (references application segments, groups, users)
```text

---

## Edge Cases

### Multiple Connector Groups

A server group can reference multiple app connector groups for redundancy:

```text
zpa_create_server_group(
  name="Multi-Region Servers",
  app_connector_group_ids=["<us_east_id>", "<eu_west_id>"],
  dynamic_discovery=True
)
```text

### Microtenant Scoping

In multi-tenant environments, pass `microtenant_id` to both the connector group and server group:

```text
zpa_create_app_connector_group(
  name="Tenant-A Connectors",
  microtenant_id="<tenant_id>",
  ...
)

zpa_create_server_group(
  name="Tenant-A Servers",
  app_connector_group_ids=["<id>"],
  microtenant_id="<tenant_id>"
)
```text

### Static Server Assignment

When dynamic discovery is disabled, associate specific application servers:

```text
zpa_list_application_servers()

zpa_create_server_group(
  name="Static Servers",
  app_connector_group_ids=["<connector_group_id>"],
  server_ids=["<server_id_1>", "<server_id_2>"],
  dynamic_discovery=False
)
```text

---

## Quick Reference

**Dependency:** App Connector Group must exist before creating a Server Group.

**Tools used:**

- `zpa_list_app_connector_groups()` -- find existing connector groups
- `zpa_create_app_connector_group(name, ...)` -- create if needed
- `zpa_get_app_connector_group(group_id)` -- verify connector group
- `zpa_create_server_group(name, app_connector_group_ids, ...)` -- create server group
- `zpa_get_server_group(group_id)` -- verify server group

**Remember:**

- Always check for existing resources before creating new ones
- The `app_connector_group_ids` parameter on server groups is required
- Present the dependency chain to the administrator so they understand the relationship
