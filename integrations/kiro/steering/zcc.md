# ZCC (Zscaler Client Connector) Steering

## Overview

ZCC is the endpoint agent that connects users to the Zscaler Zero Trust Exchange. It runs on user devices and routes traffic through ZPA (for private apps) and ZIA (for internet/SaaS). ZCC provides device enrollment status, forwarding profiles, and trusted network configuration.

## Key Concepts

- **Devices**: Endpoints with ZCC installed — includes enrollment status, OS, version, and last-seen information
- **Trusted Networks**: Network definitions where ZCC behavior may differ (e.g., corporate LAN may bypass certain tunnels)
- **Forwarding Profiles**: Define how traffic is routed through Zscaler (which traffic goes to ZPA vs ZIA vs direct)
- **CSV Export**: Bulk device data export for analysis and reporting

## Common Workflows

### Device Inventory & Status Check

Use for understanding the fleet of enrolled devices.

```
1. zcc_list_devices          → Get all enrolled devices with status, OS, version
2. Filter results by enrollment status:
   - Enrolled: Device is active and connected
   - Pending: Device enrollment in progress
   - Unenrolled: Device has been removed
3. zcc_devices_csv_exporter  → Export full device data for analysis in spreadsheet/BI tools
```

### Traffic Forwarding Review

Use to understand how traffic is being routed.

```
1. zcc_list_forwarding_profiles → Check forwarding configurations
2. Review: which traffic types go through ZPA, ZIA, or bypass
3. zcc_list_trusted_networks    → Check if trusted networks may alter routing
```

### Cross-Product Correlation

ZCC data is the starting point for cross-product troubleshooting:

```
1. zcc_list_devices          → Find user's device, confirm enrollment
2. Then correlate with:
   - ZDX: zdx_list_devices   → Get device health metrics
   - ZPA: zpa_list_access_policy_rules → Check access policies
   - ZIA: zia_list_url_filtering_rules → Check internet access policies
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zcc_list_devices` | List all enrolled devices with status |
| `zcc_devices_csv_exporter` | Export device data as CSV |
| `zcc_list_trusted_networks` | List trusted network definitions |
| `zcc_list_forwarding_profiles` | List forwarding profiles |

All ZCC tools are **read-only**.

## Device Status Values

| Status | Meaning |
|--------|---------|
| Enrolled | Device is registered and actively connected |
| Pending | Device enrollment is in progress |
| Unenrolled | Device has been removed from management |

## Best Practices

1. **Check enrollment first in troubleshooting** — An unenrolled or pending device explains most "can't access anything" issues
2. **Use CSV export for large-scale analysis** — `zcc_devices_csv_exporter` is better than paginating through `zcc_list_devices` for fleet-wide reporting
3. **Review forwarding profiles** — Misconfigured forwarding profiles can cause traffic to bypass ZPA/ZIA
4. **Check trusted networks** — Users on trusted networks may bypass ZPA/ZIA, which changes access behavior
5. **Combine with ZDX** — ZCC shows device enrollment; ZDX shows device health metrics. Both are needed for full device troubleshooting.
