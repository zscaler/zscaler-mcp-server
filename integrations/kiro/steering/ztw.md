# ZTW (Zscaler Workload Segmentation) Steering

## Overview

ZTW provides micro-segmentation for workloads across hybrid and multi-cloud environments, enabling zero trust security for east-west traffic.

## Key Concepts

- **IP Groups**: Logical groupings of IP addresses
- **Network Services**: Service definitions for segmentation rules
- **Public Cloud Info**: Visibility into cloud workloads
- **Discovery Settings**: Configuration for workload discovery

## Common Workflows

### Workload Discovery
```
1. ztw_list_public_cloud_info - View cloud accounts
2. ztw_list_public_account_details - Get detailed account info
3. ztw_get_discovery_settings - Check discovery configuration
```

### Segmentation Configuration
```
1. ztw_list_ip_groups - View IP group definitions
2. ztw_list_ip_source_groups - List source groups
3. ztw_list_ip_destination_groups - List destination groups
4. ztw_list_network_service_groups - View service groups
```

### Administration
```
1. ztw_list_roles - View admin roles
2. ztw_list_admins - List admin users
3. ztw_get_admin - Get specific admin details
```

## Available Tools

### Read Operations (Always Available)
| Tool | Description |
|------|-------------|
| `ztw_list_ip_groups` | List IP groups |
| `ztw_get_ip_group` | Get specific IP group |
| `ztw_list_ip_groups_lite` | List IP groups (lightweight) |
| `ztw_list_ip_source_groups` | List IP source groups |
| `ztw_get_ip_source_group` | Get specific source group |
| `ztw_list_ip_destination_groups` | List IP destination groups |
| `ztw_get_ip_destination_group` | Get specific destination group |
| `ztw_list_network_service_groups` | List network service groups |
| `ztw_get_network_service_group` | Get specific service group |
| `ztw_list_network_services` | List network services |
| `ztw_list_roles` | List admin roles |
| `ztw_list_admins` | List admin users |
| `ztw_get_admin` | Get specific admin |
| `ztw_list_public_cloud_info` | List public cloud accounts |
| `ztw_list_public_account_details` | Get detailed cloud account info |
| `ztw_get_discovery_settings` | Get discovery settings |

### Write Operations (Require --enable-write-tools)
| Tool | Description |
|------|-------------|
| `ztw_create_ip_group` | Create IP group |
| `ztw_update_ip_group` | Update IP group |
| `ztw_delete_ip_group` | Delete IP group |
| `ztw_create_ip_source_group` | Create IP source group |
| `ztw_update_ip_source_group` | Update IP source group |
| `ztw_delete_ip_source_group` | Delete IP source group |
| `ztw_create_ip_destination_group` | Create IP destination group |
| `ztw_update_ip_destination_group` | Update IP destination group |
| `ztw_delete_ip_destination_group` | Delete IP destination group |

## Best Practices

1. **Map cloud accounts first** - Understand your cloud footprint
2. **Define groups logically** - Use meaningful naming for IP groups
3. **Start with discovery** - Let ZTW discover workloads before creating rules
4. **Review regularly** - Cloud environments change frequently

