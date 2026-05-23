---
id: zpa
title: ZPA — Zscaler Private Access
sidebar_label: ZPA
sidebar_position: 3
---

# ZPA — Zscaler Private Access

~80 tools across application segments, server groups, access policies, app connector groups, PRA, and isolation.

## Tool families

- **Application Segments** — Standard + BA + PRA segments, including `get_zpa_app_segments_by_type`
- **Access Policies** — Access, forwarding, timeout, isolation rules
- **Policy Registry** — Umbrella policy registry tools
- **App Connector Groups + Connectors** — Plus enrollment certificates
- **Server Groups, Segment Groups, Service Edge Groups** — Network primitives
- **Provisioning Keys** — Edge / connector enrollment
- **Application Servers** — Legacy per-server objects
- **PRA Portals + Credentials** — Privileged Remote Access
- **BA Certificates** — Browser Access certificates
- **App Protection** — Inspection policies + profiles
- **Posture, Trusted Networks, Isolation** — Conditional-access primitives
- **IdP, SAML/SCIM Attributes, SCIM Groups** — Identity surfaces
- **Microtenants** — Per-microtenant scoping

## Critical gotcha

> ⚠️ **ZPA dependency chain matters.** To onboard an application:
>
> 1. Create app connector group
> 2. Create server group (references the connector group)
> 3. Create segment group
> 4. Create application segment (references both)
> 5. Create access policy rule
>
> Skipping dependencies causes cryptic 400 errors.

> ⚠️ **`customer_id` is required.** Every ZPA tool needs `ZSCALER_CUSTOMER_ID` in the environment.

## Toolsets

ZPA is split into **19 resource-family-scoped sub-toolsets**:

- `zpa_app_segments`, `zpa_access_policies`, `zpa_policy`
- `zpa_app_connector_groups`, `zpa_connectors`
- `zpa_server_groups`, `zpa_segment_groups`, `zpa_service_edge_groups`
- `zpa_provisioning_keys`, `zpa_application_servers`
- `zpa_pra`, `zpa_ba_certificates`, `zpa_app_protection`
- `zpa_posture`, `zpa_trusted_networks`, `zpa_isolation`
- `zpa_idp`, `zpa_microtenants`, `zpa_misc`

See [Toolsets](../guides/toolsets) for the full list.

## Full tool catalog

See [Supported Tools — ZPA](../guides/supported-tools#zpa--private-access).
