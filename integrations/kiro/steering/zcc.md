# ZCC (Zscaler Client Connector) Steering

## Overview

ZCC is the endpoint agent that connects users to the Zscaler Zero Trust Exchange, providing secure access to applications and internet resources.

## Key Concepts

- **Devices**: Endpoints with ZCC installed
- **Trusted Networks**: Networks where ZCC behavior may differ
- **Forwarding Profiles**: Define how traffic is routed
- **Enrollment**: Device registration and management

## Common Workflows

### Device Inventory
```
1. zcc_list_devices - Get all enrolled devices
2. zcc_devices_csv_exporter - Export device data for analysis
```

### Network Configuration
```
1. zcc_list_trusted_networks - View trusted network definitions
2. zcc_list_forwarding_profiles - Check forwarding configurations
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zcc_list_devices` | List all enrolled devices |
| `zcc_devices_csv_exporter` | Export device data as CSV |
| `zcc_list_trusted_networks` | List trusted networks |
| `zcc_list_forwarding_profiles` | List forwarding profiles |

## Device Status Values

- **Enrolled**: Device is registered and active
- **Pending**: Device enrollment in progress
- **Unenrolled**: Device has been removed

## Best Practices

1. **Regular inventory checks** - Monitor device enrollment status
2. **Export for analysis** - Use CSV export for large-scale reporting
3. **Review forwarding profiles** - Ensure traffic routing matches requirements
4. **Validate trusted networks** - Confirm network definitions are current

