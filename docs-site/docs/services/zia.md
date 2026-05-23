---
id: zia
title: ZIA — Zscaler Internet Access
sidebar_label: ZIA
sidebar_position: 2
---

# ZIA — Zscaler Internet Access

The largest service in the MCP server with ~120 tools across URL filtering, cloud firewall, DLP, SSL inspection, sandbox, ATP, cloud app control, and file type control.

## Tool families

- **URL Filtering** — `zia_list_url_filtering_rules`, `zia_create_url_filtering_rule`, …
- **Cloud Firewall** — Standard, DNS, and IPS rule families plus custom IPS signatures
- **Web DLP** — Web DLP rule lifecycle
- **SSL Inspection** — SSL rule lifecycle with cloud-app auto-resolver (friendly name → enum)
- **Sandbox** — Sandbox **policy rules** (write) + sandbox **reports** (read)
- **File Type Control** — File type rule lifecycle (cloud-app auto-resolver)
- **Cloud App Control** — Cloud app control rule lifecycle
- **ATP Policy** — Tenant-wide ATP block + security exceptions + malicious URL denylist
- **ATP Malware** — Malware policy / inspection / protocols + 16-field threat-class block
- **Advanced Settings** — Administration → Advanced Settings (~50 tenant-wide knobs)
- **Locations, Users, Groups, Departments** — Foundational tenant data
- **Static IPs, VPN Credentials, GRE Tunnels** — Traffic-forwarding primitives
- **Rule Labels, Time Intervals, Workload Groups** — Reusable rule references
- **Shadow IT** — Cloud application analytics
- **Activation** — `zia_activate_configuration`

## Critical gotcha

> ⚠️ **ZIA requires activation.** After any ZIA create/update/delete, call `zia_activate_configuration()`. Changes are staged until activation. Forgetting this is the #1 source of *"my change didn't work"* issues.

## Toolsets

ZIA is split into **21 sub-toolsets** so an agent can load only the rule family it needs:

- `zia_url_filtering`, `zia_cloud_firewall`, `zia_ssl_inspection`, `zia_dlp`, `zia_cloud_app_control`, `zia_file_type_control`, `zia_sandbox`
- `zia_locations`, `zia_url_categories`, `zia_users`, `zia_devices`, `zia_authentication_settings`, `zia_rule_labels`, `zia_workload_groups`, `zia_time_intervals`, `zia_shadow_it`
- `zia_atp_policy`, `zia_atp_malware`, `zia_advanced_settings`, `zia_admin`
- `zia_misc` (catch-all)

See [Toolsets](../guides/toolsets) for the full list.

## Full tool catalog

See [Supported Tools — ZIA](../guides/supported-tools#zia--internet-access).
