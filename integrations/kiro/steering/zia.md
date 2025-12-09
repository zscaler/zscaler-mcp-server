# ZIA (Zscaler Internet Access) Steering

## Overview

ZIA is a cloud-native secure web gateway (SWG) that provides internet security, URL filtering, cloud firewall, DLP, and SSL inspection.

## Key Concepts

- **Cloud Firewall Rules**: Control network traffic based on criteria
- **URL Filtering**: Block or allow access based on URL categories
- **SSL Inspection**: Decrypt and inspect HTTPS traffic
- **DLP (Data Loss Prevention)**: Prevent sensitive data exfiltration
- **Locations**: Physical or logical network locations

## Common Workflows

### Security Policy Audit
```
1. zia_list_cloud_firewall_rules - Review firewall rules
2. zia_list_url_filtering_rules - Check URL policies
3. zia_list_ssl_inspection_rules - Verify SSL inspection config
4. zia_list_web_dlp_rules - Review DLP policies
```

### URL Category Management
```
1. zia_list_url_categories - List all categories
2. zia_get_url_category - Get specific category details
3. zia_add_urls_to_category - Add URLs (write mode)
4. zia_remove_urls_from_category - Remove URLs (write mode)
```

### Network Configuration
```
1. zia_list_locations - View all locations
2. zia_list_gre_tunnels - Check GRE tunnel status
3. zia_list_vpn_credentials - Review VPN configs
4. zia_list_static_ips - List static IPs
```

### Activation Management
```
1. zia_get_activation_status - Check pending changes
2. zia_activate_configuration - Apply changes (write mode)
```

## Available Tools

### Read Operations (Always Available)
| Tool | Description |
|------|-------------|
| `zia_list_cloud_firewall_rules` | List firewall rules |
| `zia_get_cloud_firewall_rule` | Get specific rule |
| `zia_list_url_filtering_rules` | List URL filter rules |
| `zia_get_url_filtering_rule` | Get specific URL rule |
| `zia_list_ssl_inspection_rules` | List SSL inspection rules |
| `zia_list_web_dlp_rules` | List DLP rules |
| `zia_list_url_categories` | List URL categories |
| `zia_get_url_category` | Get specific category |
| `zia_list_locations` | List locations |
| `zia_list_gre_tunnels` | List GRE tunnels |
| `zia_list_vpn_credentials` | List VPN credentials |
| `zia_list_static_ips` | List static IPs |
| `zia_list_rule_labels` | List rule labels |
| `zia_get_activation_status` | Check activation status |
| `zia_get_sandbox_quota` | Get sandbox quota |
| `zia_list_dlp_engines` | List DLP engines |

### Write Operations (Require --enable-write-tools)
| Tool | Description |
|------|-------------|
| `zia_create_cloud_firewall_rule` | Create firewall rule |
| `zia_update_cloud_firewall_rule` | Update firewall rule |
| `zia_delete_cloud_firewall_rule` | Delete firewall rule |
| `zia_create_url_filtering_rule` | Create URL filter rule |
| `zia_update_url_filtering_rule` | Update URL filter rule |
| `zia_delete_url_filtering_rule` | Delete URL filter rule |
| `zia_add_urls_to_category` | Add URLs to category |
| `zia_remove_urls_from_category` | Remove URLs from category |
| `zia_activate_configuration` | Activate pending changes |

## Important Notes

### Configuration Activation
- ZIA changes are staged until explicitly activated
- Always check `zia_get_activation_status` before and after changes
- Use `zia_activate_configuration` to apply pending changes

### Rule Ordering
- Firewall and URL filtering rules are processed in order
- Be mindful of rule placement when creating new rules

## Best Practices

1. **Check activation status** - Verify if there are pending changes
2. **Review before activation** - Understand impact of staged changes
3. **Use rule labels** - Organize rules with meaningful labels
4. **Test in sandbox** - Validate URL/file behavior before production changes

