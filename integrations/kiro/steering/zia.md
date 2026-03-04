# ZIA (Zscaler Internet Access) Steering

## Overview

ZIA is a cloud-native secure web gateway (SWG) providing internet security: cloud firewall, URL filtering, SSL inspection, DLP, sandbox analysis, and location-based traffic management.

## Key Concepts

- **Cloud Firewall Rules**: L3/L4 network traffic control (source, destination, ports, protocols)
- **URL Filtering Rules**: L7 web access control by URL category, user, group, location
- **SSL Inspection Rules**: Control HTTPS decryption (inspect, bypass, or do-not-decrypt)
- **DLP (Data Loss Prevention)**: Content inspection rules to prevent data exfiltration
- **URL Categories**: Classification of URLs (predefined + custom categories)
- **Locations**: Physical or logical network sites sending traffic to ZIA
- **Static IPs**: Public IPs registered with ZIA for traffic identification
- **VPN Credentials**: Authentication for GRE/IPSec tunnels (UFQDN or IP-based)
- **GRE Tunnels**: Generic Routing Encapsulation tunnels for site connectivity
- **Rule Labels**: Tags for organizing and filtering rules
- **Network Services/Groups**: Protocol+port definitions used in firewall rules
- **IP Source/Destination Groups**: Reusable IP address groups for firewall rules

## Critical: ZIA Activation Requirement

**After any ZIA create/update/delete operation, changes are STAGED and not live until activated.**

```
1. Make your changes (create/update/delete)
2. zia_get_activation_status → Confirm status is "PENDING"
3. zia_activate_configuration → Push changes live
```

Forgetting activation is the #1 source of "my change didn't work" issues.

## Critical: Location Onboarding Dependency Chain

To onboard a ZIA location, resources must be created in order:

### IP-Based VPN
```
1. zia_create_static_ip       → Register the site's public IP with ZIA
   ↓
2. zia_create_vpn_credential  → Create IP-based VPN credential (type="IP", references static IP)
   ↓
3. zia_create_location        → Create location (references static IP + VPN credential)
   ↓
4. zia_activate_configuration → Push changes live
```

### UFQDN-Based VPN
```
1. zia_create_vpn_credential  → Create UFQDN VPN credential (type="UFQDN", fqdn="user@domain.com")
   ↓
2. zia_create_location        → Create location (references VPN credential)
   ↓
3. zia_activate_configuration → Push changes live
```

## Common Workflows

### Security Policy Audit
```
1. zia_list_cloud_firewall_rules → Review all firewall rules (check rule order)
2. zia_list_url_filtering_rules  → Review URL policies
3. zia_list_ssl_inspection_rules → Check SSL inspection/bypass rules
4. zia_list_web_dlp_rules        → Review DLP policies
5. Cross-reference: Which apps/URLs bypass SSL? Are DLP rules effective on uninspected traffic?
```

### SSL Inspection Bypass Audit
```
1. zia_list_ssl_inspection_rules → Get all rules
2. Identify DO_NOT_INSPECT and DO_NOT_DECRYPT actions → These bypass inspection
3. Cross-reference with zia_list_url_filtering_rules → Are bypassed categories also URL-filtered?
4. Cross-reference with zia_list_web_dlp_rules → DLP is blind to uninspected traffic
5. Risk assessment: Critical (broad bypass + sensitive categories), High, Medium, Low
```

### URL Category Investigation
```
1. zia_url_lookup               → Classify a specific URL
2. zia_list_url_categories      → List all categories (predefined + custom)
3. zia_list_url_filtering_rules → Find rules using this category
4. zia_list_ssl_inspection_rules → Check if category is inspected
5. zia_list_web_dlp_rules       → Check if DLP applies to this category
```

### User URL Access Check
```
1. zia_users_manager / zia_user_group_manager → Find user and their groups
2. zia_url_lookup                → Classify the target URL
3. zia_list_url_filtering_rules  → Walk rules top-to-bottom, match user/group/category
4. zia_list_ssl_inspection_rules → Check if traffic is inspected
5. zia_list_web_dlp_rules        → Check if DLP blocks content
6. Present verdict: ALLOW, CAUTION, BLOCK with the matching rule
```

### Network Configuration
```
1. zia_list_locations       → View all locations
2. zia_list_static_ips      → List registered static IPs
3. zia_list_vpn_credentials → Review VPN credentials
4. zia_list_gre_tunnels     → Check GRE tunnel status
5. zia_list_gre_ranges      → View available GRE IP ranges
```

### Sandbox Investigation
```
1. zia_get_sandbox_report(md5_hash, report_details="full") → Get sandbox verdict (MALICIOUS/BENIGN/SUSPICIOUS)
2. zia_get_sandbox_quota             → Check quota and subscription level (Basic vs Advanced)
3. zia_get_sandbox_behavioral_analysis → List of MD5 hashes currently blocked by sandbox
4. zia_get_sandbox_file_hash_count   → Blocked hash usage statistics
5. zia_list_ssl_inspection_rules     → SSL inspection is REQUIRED for sandbox to function
6. zia_url_lookup(urls)              → Classify URL to correlate with SSL/sandbox rules
```

**Critical:** SSL Inspection is a prerequisite for Sandbox. If traffic is not SSL-inspected (`DO_NOT_INSPECT`), Sandbox cannot analyze files. Always verify SSL inspection first.

**File not analyzed?** Check: (1) SSL inspection enabled, (2) file type/size within subscription limits (Basic: .exe/.dll/.scr/.ocx/.sys/.zip, max 2MB; Advanced: all types, max 20MB), (3) Office/PDF files with no active content are classified benign without sandbox.

## Available Tools

### Read Operations
| Tool | Description |
|------|-------------|
| `zia_list_cloud_firewall_rules` | List firewall rules |
| `zia_get_cloud_firewall_rule` | Get specific firewall rule |
| `zia_list_url_filtering_rules` | List URL filtering rules |
| `zia_get_url_filtering_rule` | Get specific URL rule |
| `zia_list_ssl_inspection_rules` | List SSL inspection rules |
| `zia_get_ssl_inspection_rule` | Get specific SSL rule |
| `zia_list_web_dlp_rules` | List DLP rules |
| `zia_list_web_dlp_rules_lite` | List DLP rules (lightweight) |
| `zia_get_web_dlp_rule` | Get specific DLP rule |
| `zia_list_url_categories` | List URL categories |
| `zia_get_url_category` | Get specific URL category |
| `zia_url_lookup` | Classify a URL into categories |
| `zia_list_locations` | List locations |
| `zia_get_location` | Get specific location |
| `zia_list_static_ips` | List static IPs |
| `zia_get_static_ip` | Get specific static IP |
| `zia_list_vpn_credentials` | List VPN credentials |
| `zia_get_vpn_credential` | Get specific VPN credential |
| `zia_list_gre_tunnels` | List GRE tunnels |
| `zia_get_gre_tunnel` | Get specific GRE tunnel |
| `zia_list_gre_ranges` | List available GRE IP ranges |
| `zia_list_rule_labels` | List rule labels |
| `zia_get_rule_label` | Get specific rule label |
| `zia_list_network_services` | List network service definitions |
| `zia_get_network_service` | Get specific network service |
| `zia_list_network_svc_groups` | List network service groups |
| `zia_get_network_svc_group` | Get specific service group |
| `zia_list_network_apps` | List network applications |
| `zia_get_network_app` | Get specific network application |
| `zia_list_network_app_groups` | List network application groups |
| `zia_get_network_app_group` | Get specific app group |
| `zia_list_ip_source_groups` | List IP source groups |
| `zia_get_ip_source_group` | Get specific IP source group |
| `zia_list_ip_destination_groups` | List IP destination groups |
| `zia_get_ip_destination_group` | Get specific IP destination group |
| `zia_list_auth_exempt_urls` | List authentication-exempt URLs |
| `zia_list_cloud_app_control_actions` | List cloud application control actions |
| `zia_list_cloud_applications` | List cloud applications |
| `zia_list_cloud_application_custom_tags` | List custom tags for cloud apps |
| `zia_list_atp_malicious_urls` | List ATP malicious URL entries |
| `zia_list_device_groups` | List device groups |
| `zia_list_devices` | List devices |
| `zia_list_devices_lite` | List devices (lightweight) |
| `zia_users_manager` | Retrieve ZIA users |
| `zia_user_group_manager` | Retrieve ZIA user groups |
| `zia_user_department_manager` | Retrieve ZIA user departments |
| `zia_dlp_dictionary_manager` | Retrieve DLP dictionaries |
| `zia_dlp_engine_manager` | Retrieve DLP engines |
| `zia_geo_search_tool` | Search geolocation data |
| `zia_get_activation_status` | Check configuration activation status |
| `zia_get_sandbox_quota` | Get sandbox submission quota |
| `zia_get_sandbox_behavioral_analysis` | Get sandbox behavioral analysis |
| `zia_get_sandbox_file_hash_count` | Check sandbox file hash |
| `zia_get_sandbox_report` | Get full sandbox report |

### Write Operations (Require --enable-write-tools)
| Tool | Description |
|------|-------------|
| `zia_activate_configuration` | **Activate pending changes** |
| `zia_create_cloud_firewall_rule` | Create firewall rule |
| `zia_update_cloud_firewall_rule` | Update firewall rule |
| `zia_delete_cloud_firewall_rule` | Delete firewall rule |
| `zia_create_url_filtering_rule` | Create URL filtering rule |
| `zia_update_url_filtering_rule` | Update URL filtering rule |
| `zia_delete_url_filtering_rule` | Delete URL filtering rule |
| `zia_create_ssl_inspection_rule` | Create SSL inspection rule |
| `zia_update_ssl_inspection_rule` | Update SSL inspection rule |
| `zia_delete_ssl_inspection_rule` | Delete SSL inspection rule |
| `zia_create_web_dlp_rule` | Create DLP rule |
| `zia_update_web_dlp_rule` | Update DLP rule |
| `zia_delete_web_dlp_rule` | Delete DLP rule |
| `zia_create_url_category` | Create custom URL category |
| `zia_update_url_category` | Update URL category |
| `zia_delete_url_category` | Delete custom URL category |
| `zia_add_urls_to_category` | Add URLs to a category |
| `zia_remove_urls_from_category` | Remove URLs from a category |
| `zia_create_location` | Create location |
| `zia_update_location` | Update location |
| `zia_delete_location` | Delete location |
| `zia_create_static_ip` | Create static IP |
| `zia_update_static_ip` | Update static IP |
| `zia_delete_static_ip` | Delete static IP |
| `zia_create_vpn_credential` | Create VPN credential |
| `zia_update_vpn_credential` | Update VPN credential |
| `zia_delete_vpn_credential` | Delete VPN credential |
| `zia_create_gre_tunnel` | Create GRE tunnel |
| `zia_delete_gre_tunnel` | Delete GRE tunnel |
| `zia_create_rule_label` | Create rule label |
| `zia_update_rule_label` | Update rule label |
| `zia_delete_rule_label` | Delete rule label |
| `zia_create_network_service` | Create network service |
| `zia_update_network_service` | Update network service |
| `zia_delete_network_service` | Delete network service |
| `zia_create_network_svc_group` | Create network service group |
| `zia_update_network_svc_group` | Update network service group |
| `zia_delete_network_svc_group` | Delete network service group |
| `zia_create_network_app_group` | Create network app group |
| `zia_update_network_app_group` | Update network app group |
| `zia_delete_network_app_group` | Delete network app group |
| `zia_create_ip_source_group` | Create IP source group |
| `zia_update_ip_source_group` | Update IP source group |
| `zia_delete_ip_source_group` | Delete IP source group |
| `zia_create_ip_destination_group` | Create IP destination group |
| `zia_update_ip_destination_group` | Update IP destination group |
| `zia_delete_ip_destination_group` | Delete IP destination group |
| `zia_add_auth_exempt_urls` | Add auth-exempt URLs |
| `zia_delete_auth_exempt_urls` | Delete auth-exempt URLs |
| `zia_add_atp_malicious_urls` | Add ATP malicious URLs |
| `zia_delete_atp_malicious_urls` | Delete ATP malicious URLs |
| `zia_bulk_update_cloud_applications` | Bulk update cloud application settings |

## Important Notes

### Rule Ordering
- Firewall, URL filtering, SSL inspection, and DLP rules are evaluated **top-to-bottom**
- First matching rule wins
- Be mindful of rule placement when creating new rules
- New rules are appended at the end by default

### Configuration Activation
- All ZIA changes are staged until `zia_activate_configuration` is called
- Always check `zia_get_activation_status` after changes — status should be "PENDING"
- Activation applies ALL pending changes, not just your latest change

## Best Practices

1. **Always activate after changes** — Call `zia_activate_configuration` after any create/update/delete
2. **Audit SSL bypasses regularly** — `DO_NOT_INSPECT` rules create blind spots for DLP and threat detection
3. **Use `zia_url_lookup` before making URL policy changes** — Understand the current classification first
4. **Review rule order** — A broadly-scoped rule early in the list can override specific rules below it
5. **Use rule labels** — Tag rules for easier filtering and organization
6. **Confirm before write operations** — Always explain proposed changes and get explicit user confirmation
