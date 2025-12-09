# ZPA (Zscaler Private Access) Steering

## Overview

ZPA provides zero trust network access (ZTNA) to private applications without exposing them to the internet.

## Key Concepts

- **Application Segments**: Define which applications are accessible
- **Segment Groups**: Organize application segments logically
- **Server Groups**: Define backend servers for applications
- **App Connectors**: Software that brokers connections to private apps
- **Service Edges**: Provide local breakout for users

## Common Workflows

### Application Discovery
```
1. zpa_list_application_segments - Get all configured apps
2. zpa_get_application_segment - Get details for specific app
3. zpa_list_segment_groups - See how apps are organized
4. zpa_list_server_groups - View backend server configurations
```

### Access Policy Review
```
1. zpa_list_access_policy_rules - List all access rules
2. zpa_get_access_policy_rule - Get specific rule details
3. zpa_list_posture_profiles - Check device posture requirements
4. zpa_list_trusted_networks - View trusted network definitions
```

### Infrastructure Status
```
1. zpa_list_app_connector_groups - List connector groups
2. zpa_list_service_edge_groups - List service edge groups
3. zpa_list_provisioning_keys - Check available provisioning keys
```

## Available Tools

### Read Operations (Always Available)
| Tool | Description |
|------|-------------|
| `zpa_list_application_segments` | List all application segments |
| `zpa_get_application_segment` | Get specific application segment |
| `zpa_list_segment_groups` | List segment groups |
| `zpa_get_segment_group` | Get specific segment group |
| `zpa_list_server_groups` | List server groups |
| `zpa_get_server_group` | Get specific server group |
| `zpa_list_app_connector_groups` | List connector groups |
| `zpa_list_service_edge_groups` | List service edge groups |
| `zpa_list_application_servers` | List application servers |
| `zpa_list_access_policy_rules` | List access policies |
| `zpa_list_forwarding_policy_rules` | List forwarding policies |
| `zpa_list_timeout_policy_rules` | List timeout policies |
| `zpa_list_isolation_policy_rules` | List isolation policies |
| `zpa_list_provisioning_keys` | List provisioning keys |
| `zpa_list_posture_profiles` | List posture profiles |
| `zpa_list_trusted_networks` | List trusted networks |
| `zpa_list_saml_attributes` | List SAML attributes |
| `zpa_list_scim_groups` | List SCIM groups |

### Write Operations (Require --enable-write-tools)
| Tool | Description |
|------|-------------|
| `zpa_create_application_segment` | Create application segment |
| `zpa_update_application_segment` | Update application segment |
| `zpa_delete_application_segment` | Delete application segment |
| `zpa_create_access_policy_rule` | Create access policy |
| `zpa_update_access_policy_rule` | Update access policy |
| `zpa_delete_access_policy_rule` | Delete access policy |
| `zpa_create_segment_group` | Create segment group |
| `zpa_update_segment_group` | Update segment group |
| `zpa_delete_segment_group` | Delete segment group |

## Best Practices

1. **Always start with discovery** - Use list operations to understand current state
2. **Check dependencies before deletion** - Application segments may be referenced by policies
3. **Validate posture requirements** - Ensure posture profiles are appropriate for use case
4. **Review access policies** - Understand who has access to what applications

