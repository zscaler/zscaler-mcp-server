---
id: overview
title: Services Overview
sidebar_label: Overview
sidebar_position: 1
---

# Services Overview

The Zscaler MCP Server exposes **300+ tools across 9 Zscaler services**. Each service has its own page with the full tool catalog.

| Service | Acronym | Tool count | Description |
|---|---|---|---|
| [Zscaler Internet Access](./zia) | ZIA | ~120 | URL filtering, cloud firewall, DLP, SSL inspection, sandbox, ATP, cloud app control, file type control |
| [Zscaler Private Access](./zpa) | ZPA | ~80 | Application segments, server groups, access policies, app connector groups, PRA, isolation |
| [Zscaler Digital Experience](./zdx) | ZDX | ~30 | Experience scores, deep traces, alerts, software inventory, devices, applications |
| [Zscaler Client Connector](./zcc) | ZCC | ~5 | Device enrollment, forwarding profiles, trusted networks |
| [Zscaler Cloud & Branch Connector](./ztw) | ZTW | ~10 | IP groups, network services, admin roles |
| [Zidentity](./zid) | ZID | ~2 | Users, groups |
| [External Attack Surface Management](./easm) | EASM | ~7 | Findings, lookalike domains, asset evidence |
| [Z-Insights](./zins) | ZINS | ~17 | Web traffic, threat trends, CASB, shadow IT, IoT analytics |
| [Microsegmentation](./zms) | ZMS | ~20 | Agents, resources, policy rules, app zones, tags |

For the complete per-tool catalog with descriptions, see [Supported Tools](../guides/supported-tools).

## Service discovery from an agent

The server exposes always-on meta tools that let an agent discover what's available:

- `zscaler_get_available_services` — list enabled services + their tool counts. Also surfaces **disabled** services so the agent can inform the user.
- `zscaler_list_toolsets` — list available toolsets, with `currently_enabled` and `can_enable` flags.
- `zscaler_get_toolset_tools` — drill into a toolset to see its tools.
- `zscaler_enable_toolset` — register a toolset's tools at runtime.

These tools always load regardless of `--services` / `--toolsets` filters.

## OneAPI entitlement filter

After your selected services/toolsets resolve, the server intersects them with the products your OneAPI client is **entitled** to. If your `ZSCALER_CLIENT_ID` is only entitled to ZIA + ZPA, every `zdx_*` / `zcc_*` / `zid_*` / `zeasm_*` / `zins_*` / `zms_*` toolset is filtered out at startup — even with `--toolsets all`.

This prevents an agent from discovering tools whose first call would return `401 Unauthorized`. Bypass with `--no-entitlement-filter` (diagnostics only).

See [Toolsets](../guides/toolsets) for details.

## Cross-service overlap

Some Zscaler APIs expose overlapping data. For example, both ZIA and ZCC expose device-management tools. The server maps tools to API product boundaries, not conceptual categories — so disabling ZCC does **not** remove ZIA's device tools.

Use `--disabled-tools "zia_list_device*"` in addition to `--disabled-services zcc` to fully block device access.
