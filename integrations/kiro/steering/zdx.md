# ZDX (Zscaler Digital Experience) Steering

## Overview

ZDX provides end-to-end visibility into user digital experience, helping identify and troubleshoot performance issues across applications, networks, and devices.

## Key Concepts

- **Applications**: Monitored SaaS and internal applications
- **Devices**: End-user devices running Zscaler Client Connector
- **Scores**: ZDX scores indicating application/device health (0-100)
- **Alerts**: Automated notifications for performance issues
- **Deep Traces**: Detailed network path analysis

## Common Workflows

### Application Health Check
```
1. zdx_list_applications - Get all monitored apps
2. zdx_get_application - Get specific app details
3. zdx_get_application_score_trend - View score history
4. zdx_get_application_metric - Get detailed metrics (PFT, DNS)
```

### Device Troubleshooting
```
1. zdx_list_devices - Find affected devices
2. zdx_get_device - Get device details
3. zdx_list_device_deep_traces - Check for deep trace data
4. zdx_get_device_deep_trace - Analyze specific trace
```

### Alert Management
```
1. zdx_list_alerts - View active alerts
2. zdx_get_alert - Get alert details
3. zdx_list_alert_affected_devices - See impacted devices
4. zdx_list_historical_alerts - Review past alerts
```

### Software Inventory
```
1. zdx_list_software - List installed software
2. zdx_get_software_details - Get software details by device
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zdx_list_applications` | List monitored applications |
| `zdx_get_application` | Get application details |
| `zdx_get_application_score_trend` | Get application score history |
| `zdx_get_application_metric` | Get app metrics (PFT, DNS, availability) |
| `zdx_list_application_users` | List users for an application |
| `zdx_get_application_user` | Get specific application user |
| `zdx_list_devices` | List monitored devices |
| `zdx_get_device` | Get device details |
| `zdx_list_alerts` | List active alerts |
| `zdx_get_alert` | Get alert details |
| `zdx_list_alert_affected_devices` | List devices affected by alert |
| `zdx_list_historical_alerts` | List past alerts |
| `zdx_list_software` | List software inventory |
| `zdx_get_software_details` | Get software details |
| `zdx_list_departments` | List departments |
| `zdx_list_locations` | List locations |
| `zdx_list_device_deep_traces` | List deep traces for device |
| `zdx_get_device_deep_trace` | Get specific deep trace |

## Understanding ZDX Scores

- **90-100**: Excellent - No issues detected
- **70-89**: Good - Minor issues may exist
- **50-69**: Fair - Performance degradation present
- **0-49**: Poor - Significant issues affecting users

## Best Practices

1. **Start with alerts** - Check active alerts first when troubleshooting
2. **Review score trends** - Look at historical patterns, not just current state
3. **Correlate across apps** - Similar issues across apps may indicate network problems
4. **Use deep traces** - For detailed network path analysis when needed

