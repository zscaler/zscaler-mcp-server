---
id: zdx
title: ZDX — Zscaler Digital Experience
sidebar_label: ZDX
sidebar_position: 4
---

# ZDX — Zscaler Digital Experience

~30 tools across experience scores, deep traces, alerts, software inventory, devices, and applications.

> ⚠️ **ZDX is read-only.** ZDX tools only query data. The only write operation is `zdx_start_deep_trace`.

## Tool families

- **Applications** — `zdx_list_applications`, `zdx_get_application_score`, `zdx_get_application_metric`
- **Devices** — Active devices, per-device details
- **Locations + Departments** — Tenant geography
- **Software Inventory** — Discover software per device or org-wide
- **Alerts** — Ongoing + historical
- **Deep Traces** — Start a deep trace, fetch results
- **Web / Cloudpath Probes** — Read probe data
- **Cyber + Threat Reports** — Read analytics

## Critical gotcha

> ⚠️ **The `since` parameter is in HOURS, not timestamps.** Default is 2 hours. `since=24` means "last 24 hours". For wider ranges, use `since=168` (one week).

## Filters

ZDX queries accept filters that significantly improve result quality:

- `location_id` — filter by office/site
- `department_id` — filter by department
- `geo_id` — filter by geolocation
- `since` — hours to look back (default 2)

Always ask the user for scope before running broad ZDX queries on large tenants.

## Toolsets

ZDX is split into **5 sub-toolsets**:

- `zdx_alerts`
- `zdx_locations` (locations + departments)
- `zdx_software_inventory`
- `zdx_troubleshooting` (deep traces + analyses + probes)
- `zdx_reports` (default catch-all: devices, applications, web/cloudpath reads)

See [Toolsets](../guides/toolsets).

## Full tool catalog

See [Supported Tools — ZDX](../guides/supported-tools#zdx--digital-experience).
