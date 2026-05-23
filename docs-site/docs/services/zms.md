---
id: zms
title: ZMS — Microsegmentation
sidebar_label: ZMS
sidebar_position: 10
---

# ZMS — Microsegmentation

~20 read-only tools that query the ZMS GraphQL API for microsegmentation data.

> ZMS tools use a GraphQL endpoint (`/zms/graphql`). All tools are **read-only** (no mutations).

## Domains

| Domain | Tools |
|---|---|
| Agents | `zms_list_agents`, `zms_get_agent_connection_status_statistics`, `zms_get_agent_version_statistics` |
| Agent Groups | `zms_list_agent_groups`, `zms_get_agent_group_totp_secrets` |
| Resources | `zms_list_resources`, `zms_get_resource_protection_status`, `zms_get_metadata` |
| Resource Groups | `zms_list_resource_groups`, `zms_get_resource_group_members`, `zms_get_resource_group_protection_status` |
| Policy Rules | `zms_list_policy_rules`, `zms_list_default_policy_rules` |
| App Zones | `zms_list_app_zones` |
| App Catalog | `zms_list_app_catalog` |
| Nonces | `zms_list_nonces`, `zms_get_nonce` |
| Tags | `zms_list_tag_namespaces`, `zms_list_tag_keys`, `zms_list_tag_values` |

## Gotchas

- **`customer_id` is always required.** Resolved automatically from `ZSCALER_CUSTOMER_ID`.
- **Tag hierarchy is three levels**: namespace → key → value. Navigate top-down.
- **Resource groups have two types**: `ManagedResourceGroup` (tag-based) and `UnmanagedResourceGroup` (CIDR/FQDN-based).
- **`eyez_id`** is the unique identifier for agents, agent groups, and nonces — not a numeric ID.

## Toolset

Single toolset: `zms`.

## Full tool catalog

See [Supported Tools — ZMS](../guides/supported-tools#zms--microsegmentation).
