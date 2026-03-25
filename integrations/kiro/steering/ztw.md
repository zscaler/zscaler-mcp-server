# ZTW (Zscaler Workload Segmentation) Steering

## Overview

ZTW provides micro-segmentation for workloads across hybrid and multi-cloud environments, enabling zero trust security for east-west traffic. It manages IP groups, network services, and discovery settings for workload communication control.

## Key Concepts

- **IP Groups**: Logical groupings of IP addresses (general-purpose grouping)
- **IP Source Groups**: Source-side IP groupings for segmentation rules
- **IP Destination Groups**: Destination-side IP groupings for segmentation rules
- **Network Services**: Protocol + port definitions for segmentation rules
- **Network Service Groups**: Logical groupings of network services
- **Public Cloud Info**: Visibility into connected cloud accounts (AWS, Azure, GCP)
- **Discovery Settings**: Configuration for automatic workload discovery
- **Roles**: Admin role definitions
- **Admins**: Admin users and their role assignments

## Common Workflows

### Workload Discovery & Cloud Inventory
```
1. ztw_list_public_cloud_info      → View connected cloud accounts
2. ztw_list_public_account_details → Get detailed account information
3. ztw_get_discovery_settings      → Check discovery configuration
```

### Segmentation Configuration
```
1. ztw_list_ip_groups              → View all IP group definitions
2. ztw_list_ip_groups_lite         → Lightweight list (IDs and names only)
3. ztw_list_ip_source_groups       → List source groups
4. ztw_list_ip_source_groups_lite  → Lightweight source group list
5. ztw_list_ip_destination_groups  → List destination groups
6. ztw_list_ip_destination_groups_lite → Lightweight destination group list
7. ztw_list_network_services       → View network service definitions
8. ztw_list_network_service_groups → View service group definitions
```

### Administration
```
1. ztw_list_roles  → View admin role definitions
2. ztw_list_admins → List admin users
```

### Creating Segmentation Groups
```
1. ztw_list_ip_groups → Check existing groups
2. ztw_create_ip_group → Create a new IP group with address ranges
3. ztw_create_ip_source_group → Create source group for rules
4. ztw_create_ip_destination_group → Create destination group for rules
```

## Available Tools

### Read Operations
| Tool | Description |
|------|-------------|
| `ztw_list_ip_groups` | List all IP groups |
| `ztw_list_ip_groups_lite` | List IP groups (lightweight, IDs+names only) |
| `ztw_list_ip_source_groups` | List IP source groups |
| `ztw_list_ip_source_groups_lite` | List IP source groups (lightweight) |
| `ztw_list_ip_destination_groups` | List IP destination groups |
| `ztw_list_ip_destination_groups_lite` | List IP destination groups (lightweight) |
| `ztw_list_network_services` | List network service definitions |
| `ztw_list_network_service_groups` | List network service groups |
| `ztw_list_roles` | List admin roles |
| `ztw_list_admins` | List admin users |
| `ztw_list_public_cloud_info` | List connected cloud accounts |
| `ztw_list_public_account_details` | Get detailed cloud account info |
| `ztw_get_discovery_settings` | Get workload discovery settings |

### Write Operations (Require --enable-write-tools)
| Tool | Description |
|------|-------------|
| `ztw_create_ip_group` | Create IP group |
| `ztw_delete_ip_group` | Delete IP group |
| `ztw_create_ip_source_group` | Create IP source group |
| `ztw_delete_ip_source_group` | Delete IP source group |
| `ztw_create_ip_destination_group` | Create IP destination group |
| `ztw_delete_ip_destination_group` | Delete IP destination group |

Note: ZTW write operations support create and delete only (no update operations).

## Best Practices

1. **Map cloud accounts first** — Use `ztw_list_public_cloud_info` to understand your cloud footprint before creating segmentation rules
2. **Use lightweight list tools** — `*_lite` variants return only IDs and names, which is faster for large environments
3. **Use meaningful naming** — IP group names should reflect their purpose (e.g., "prod-db-servers", "staging-web-tier")
4. **Check discovery settings** — Ensure `ztw_get_discovery_settings` shows expected discovery configuration before relying on auto-discovered workloads
5. **Start with read operations** — Always list existing groups before creating new ones to avoid duplicates
6. **Confirm before deletion** — Deleting IP groups may break segmentation rules that reference them
