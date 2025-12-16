# Supported Tools Reference

The Zscaler Integrations MCP Server provides tools for all major Zscaler services. Each service offers specific functionality for managing and querying Zscaler resources.

> **Note:** All tools marked as "Write" require the `--enable-write-tools` flag and an explicit `--write-tools` allowlist to be enabled. See the [Security & Permissions](https://github.com/zscaler/zscaler-mcp-server#-security--permissions) section in the main README for details.

## Table of Contents

- [ZCC Features](#zcc-features)
- [ZDX Features](#zdx-features)
- [ZIdentity Features](#zidentity-features)
- [ZIA Features](#zia-features)
- [ZPA Features](#zpa-features)
- [ZTW Features](#ztw-features)
- [EASM Features](#easm---external-attack-surface-management)

---

## ZCC Features

All ZCC tools are **read-only** operations:

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zcc_list_devices` | Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal | Read-only |
| `zcc_devices_csv_exporter` | Downloads ZCC device information or service status as a CSV file | Read-only |
| `zcc_list_trusted_networks` | Returns the list of Trusted Networks By Company ID in the Client Connector Portal | Read-only |
| `zcc_list_forwarding_profiles` | Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal | Read-only |

---

## ZDX Features

All ZDX tools are **read-only** operations:

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zdx_list_departments` | Discover ZDX departments | Read-only |
| `zdx_list_locations` | Discover ZDX locations | Read-only |
| `zdx_list_devices` | List ZDX devices using various filters | Read-only |
| `zdx_get_device` | Get details for a specific ZDX device | Read-only |
| `zdx_list_applications` | List all active applications configured in ZDX | Read-only |
| `zdx_get_application` | Get details for a specific application | Read-only |
| `zdx_get_application_score_trend` | Get an application's ZDX score trend | Read-only |
| `zdx_get_application_metric` | Retrieve ZDX metrics for an application (PFT, DNS, availability) | Read-only |
| `zdx_list_application_users` | List users/devices for an application | Read-only |
| `zdx_get_application_user` | Get details for a specific application user | Read-only |
| `zdx_list_software` | List software inventory | Read-only |
| `zdx_get_software_details` | Get users/devices for a specific software key | Read-only |
| `zdx_list_alerts` | List ongoing alerts | Read-only |
| `zdx_get_alert` | Get details for a specific alert | Read-only |
| `zdx_list_alert_affected_devices` | List devices affected by an alert | Read-only |
| `zdx_list_historical_alerts` | List historical alert rules (ended alerts) | Read-only |
| `zdx_list_device_deep_traces` | List deep traces for a device | Read-only |
| `zdx_get_device_deep_trace` | Get details for a specific deep trace | Read-only |

---

## ZIdentity Features

All ZIdentity tools are **read-only** operations:

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zidentity_get_groups` | Retrieves Zidentity group information | Read-only |
| `zidentity_get_users` | Retrieves Zidentity user information | Read-only |
| `zidentity_search` | Search across Zidentity resources | Read-only |

---

## ZIA Features

ZIA provides both **read-only** and **write** tools. Write operations require `--enable-write-tools` flag:

### Cloud Firewall Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_cloud_firewall_rules` | List ZIA cloud firewall rules | Read-only |
| `zia_get_cloud_firewall_rule` | Get a specific cloud firewall rule | Read-only |
| `zia_create_cloud_firewall_rule` | Create a new cloud firewall rule | Write |
| `zia_update_cloud_firewall_rule` | Update an existing cloud firewall rule | Write |
| `zia_delete_cloud_firewall_rule` | Delete a cloud firewall rule | Write |

### URL Filtering Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_url_filtering_rules` | List ZIA URL filtering rules | Read-only |
| `zia_get_url_filtering_rule` | Get a specific URL filtering rule | Read-only |
| `zia_create_url_filtering_rule` | Create a new URL filtering rule | Write |
| `zia_update_url_filtering_rule` | Update an existing URL filtering rule | Write |
| `zia_delete_url_filtering_rule` | Delete a URL filtering rule | Write |

### Web DLP Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_web_dlp_rules` | List ZIA web DLP rules | Read-only |
| `zia_list_web_dlp_rules_lite` | List ZIA web DLP rules (lite) | Read-only |
| `zia_get_web_dlp_rule` | Get a specific web DLP rule | Read-only |
| `zia_create_web_dlp_rule` | Create a new web DLP rule | Write |
| `zia_update_web_dlp_rule` | Update an existing web DLP rule | Write |
| `zia_delete_web_dlp_rule` | Delete a web DLP rule | Write |

### Configuration Activation

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_get_activation_status` | Check ZIA configuration activation status | Read-only |
| `zia_activate_configuration` | Activate pending ZIA configuration changes | Write |

### Cloud Applications

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_cloud_applications` | List ZIA cloud applications | Read-only |
| `zia_list_cloud_application_tags` | List cloud application tags | Read-only |
| `zia_bulk_update_cloud_applications` | Bulk update cloud applications | Write |

### URL Categories

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_url_categories` | List URL categories | Read-only |
| `zia_get_url_category` | Get a specific URL category | Read-only |
| `zia_add_urls_to_category` | Add URLs to a category | Write |
| `zia_remove_urls_from_category` | Remove URLs from a category | Write |

### GRE Tunnels & Ranges

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_gre_tunnels` | List GRE tunnels | Read-only |
| `zia_get_gre_tunnel` | Get a specific GRE tunnel | Read-only |
| `zia_get_gre_tunnel_info` | Get GRE tunnel information | Read-only |
| `zia_create_gre_tunnel` | Create a new GRE tunnel | Write |
| `zia_update_gre_tunnel` | Update an existing GRE tunnel | Write |
| `zia_delete_gre_tunnel` | Delete a GRE tunnel | Write |
| `zia_list_gre_ranges` | List available GRE IP ranges | Read-only |

### Locations & VPN

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_locations` | List ZIA locations | Read-only |
| `zia_list_locations_lite` | List ZIA locations (lite) | Read-only |
| `zia_get_location` | Get a specific location | Read-only |
| `zia_create_location` | Create a new location | Write |
| `zia_update_location` | Update an existing location | Write |
| `zia_delete_location` | Delete a location | Write |
| `zia_list_vpn_credentials` | List VPN credentials | Read-only |
| `zia_get_vpn_credential` | Get specific VPN credential | Read-only |
| `zia_create_vpn_credential` | Create new VPN credential | Write |
| `zia_update_vpn_credential` | Update VPN credential | Write |
| `zia_delete_vpn_credential` | Delete VPN credential | Write |
| `zia_bulk_delete_vpn_credentials` | Bulk delete VPN credentials | Write |

### Static IPs

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_static_ips` | List static IPs | Read-only |
| `zia_get_static_ip` | Get a specific static IP | Read-only |
| `zia_create_static_ip` | Create a new static IP | Write |
| `zia_update_static_ip` | Update an existing static IP | Write |
| `zia_delete_static_ip` | Delete a static IP | Write |

### ATP & Security

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_atp_malicious_urls` | List ATP malicious URLs | Read-only |
| `zia_create_atp_malicious_url` | Add URL to denylist | Write |
| `zia_delete_atp_malicious_url` | Remove URL from denylist | Write |
| `zia_list_auth_exempt_urls` | List authentication exempt URLs | Read-only |
| `zia_create_auth_exempt_url` | Add URL to auth exempt list | Write |
| `zia_delete_auth_exempt_url` | Remove URL from auth exempt list | Write |

### Groups & Users

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_ip_source_groups` | List IP source groups | Read-only |
| `zia_get_ip_source_group` | Get a specific IP source group | Read-only |
| `zia_create_ip_source_group` | Create a new IP source group | Write |
| `zia_update_ip_source_group` | Update an existing IP source group | Write |
| `zia_delete_ip_source_group` | Delete an IP source group | Write |
| `zia_list_ip_destination_groups` | List IP destination groups | Read-only |
| `zia_get_ip_destination_group` | Get a specific IP destination group | Read-only |
| `zia_create_ip_destination_group` | Create a new IP destination group | Write |
| `zia_update_ip_destination_group` | Update an existing IP destination group | Write |
| `zia_delete_ip_destination_group` | Delete an IP destination group | Write |
| `zia_list_network_app_groups` | List network application groups | Read-only |
| `zia_get_network_app_group` | Get a specific network app group | Read-only |
| `zia_create_network_app_group` | Create a new network app group | Write |
| `zia_update_network_app_group` | Update an existing network app group | Write |
| `zia_delete_network_app_group` | Delete a network app group | Write |
| `zia_list_user_groups` | List user groups | Read-only |
| `zia_get_user_group` | Get a specific user group | Read-only |
| `zia_list_user_departments` | List user departments | Read-only |
| `zia_get_user_department` | Get a specific user department | Read-only |
| `zia_list_users` | List users | Read-only |
| `zia_get_user` | Get a specific user | Read-only |

### SSL Inspection Rules

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_ssl_inspection_rules` | List SSL inspection rules | Read-only |
| `zia_get_ssl_inspection_rule` | Get a specific SSL inspection rule | Read-only |
| `zia_create_ssl_inspection_rule` | Create a new SSL inspection rule | Write |
| `zia_update_ssl_inspection_rule` | Update an existing SSL inspection rule | Write |
| `zia_delete_ssl_inspection_rule` | Delete an SSL inspection rule | Write |

### Labels & Utilities

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_list_rule_labels` | List rule labels | Read-only |
| `zia_get_rule_label` | Get a specific rule label | Read-only |
| `zia_create_rule_label` | Create a new rule label | Write |
| `zia_update_rule_label` | Update an existing rule label | Write |
| `zia_delete_rule_label` | Delete a rule label | Write |
| `zia_geo_search` | Perform geographical lookup | Read-only |
| `zia_get_sandbox_quota` | Retrieve current sandbox quota information | Read-only |
| `zia_get_sandbox_behavioral_analysis` | Retrieve sandbox behavioral analysis hash list | Read-only |
| `zia_get_sandbox_file_hash_count` | Retrieve sandbox file hash usage counts | Read-only |
| `zia_get_sandbox_report` | Retrieve sandbox report for a specific hash | Read-only |

> **Note:** The legacy `zia_sandbox_info` tool is still available for backward compatibility, but new automations should call the more specific sandbox tools above for clearer intent matching.

### DLP Management

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zia_get_dlp_dictionary` | Get a specific DLP dictionary | Read-only |
| `zia_list_dlp_engines` | List DLP engines | Read-only |
| `zia_get_dlp_engine` | Get a specific DLP engine | Read-only |

---

## ZPA Features

ZPA provides both **read-only** and **write** tools. Write operations require `--enable-write-tools` flag:

### Application Segments

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_application_segments` | List application segments | Read-only |
| `zpa_get_application_segment` | Get a specific application segment | Read-only |
| `zpa_create_application_segment` | Create a new application segment | Write |
| `zpa_update_application_segment` | Update an existing application segment | Write |
| `zpa_delete_application_segment` | Delete an application segment | Write |
| `zpa_list_app_segments_by_type` | List application segments by type | Read-only |

### App Connector Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_app_connector_groups` | List app connector groups | Read-only |
| `zpa_get_app_connector_group` | Get a specific app connector group | Read-only |
| `zpa_create_app_connector_group` | Create a new app connector group | Write |
| `zpa_update_app_connector_group` | Update an existing app connector group | Write |
| `zpa_delete_app_connector_group` | Delete an app connector group | Write |

### Server Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_server_groups` | List server groups | Read-only |
| `zpa_get_server_group` | Get a specific server group | Read-only |
| `zpa_create_server_group` | Create a new server group | Write |
| `zpa_update_server_group` | Update an existing server group | Write |
| `zpa_delete_server_group` | Delete a server group | Write |

### Service Edge Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_service_edge_groups` | List service edge groups | Read-only |
| `zpa_get_service_edge_group` | Get a specific service edge group | Read-only |
| `zpa_create_service_edge_group` | Create a new service edge group | Write |
| `zpa_update_service_edge_group` | Update an existing service edge group | Write |
| `zpa_delete_service_edge_group` | Delete a service edge group | Write |

### Segment Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_segment_groups` | List segment groups | Read-only |
| `zpa_get_segment_group` | Get a specific segment group | Read-only |
| `zpa_create_segment_group` | Create a new segment group | Write |
| `zpa_update_segment_group` | Update an existing segment group | Write |
| `zpa_delete_segment_group` | Delete a segment group | Write |

### Application Servers

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_application_servers` | List application servers | Read-only |
| `zpa_get_application_server` | Get a specific application server | Read-only |
| `zpa_create_application_server` | Create a new application server | Write |
| `zpa_update_application_server` | Update an existing application server | Write |
| `zpa_delete_application_server` | Delete an application server | Write |

### Access Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_access_policy_rules` | List access policy rules | Read-only |
| `zpa_get_access_policy_rule` | Get a specific access policy rule | Read-only |
| `zpa_create_access_policy_rule` | Create a new access policy rule | Write |
| `zpa_update_access_policy_rule` | Update an existing access policy rule | Write |
| `zpa_delete_access_policy_rule` | Delete an access policy rule | Write |
| `zpa_reorder_access_policy_rule` | Reorder access policy rules | Write |

### Forwarding Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_forwarding_policy_rules` | List forwarding policy rules | Read-only |
| `zpa_get_forwarding_policy_rule` | Get a specific forwarding policy rule | Read-only |
| `zpa_create_forwarding_policy_rule` | Create a new forwarding policy rule | Write |
| `zpa_update_forwarding_policy_rule` | Update an existing forwarding policy rule | Write |
| `zpa_delete_forwarding_policy_rule` | Delete a forwarding policy rule | Write |

### Timeout Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_timeout_policy_rules` | List timeout policy rules | Read-only |
| `zpa_get_timeout_policy_rule` | Get a specific timeout policy rule | Read-only |
| `zpa_create_timeout_policy_rule` | Create a new timeout policy rule | Write |
| `zpa_update_timeout_policy_rule` | Update an existing timeout policy rule | Write |
| `zpa_delete_timeout_policy_rule` | Delete a timeout policy rule | Write |

### Isolation Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_isolation_policy_rules` | List isolation policy rules | Read-only |
| `zpa_get_isolation_policy_rule` | Get a specific isolation policy rule | Read-only |
| `zpa_create_isolation_policy_rule` | Create a new isolation policy rule | Write |
| `zpa_update_isolation_policy_rule` | Update an existing isolation policy rule | Write |
| `zpa_delete_isolation_policy_rule` | Delete an isolation policy rule | Write |

### App Protection Policy

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_app_protection_rules` | List app protection rules | Read-only |
| `zpa_get_app_protection_rule` | Get a specific app protection rule | Read-only |
| `zpa_create_app_protection_rule` | Create a new app protection rule | Write |
| `zpa_update_app_protection_rule` | Update an existing app protection rule | Write |
| `zpa_delete_app_protection_rule` | Delete an app protection rule | Write |

### Provisioning Keys

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_provisioning_keys` | List provisioning keys | Read-only |
| `zpa_get_provisioning_key` | Get a specific provisioning key | Read-only |
| `zpa_create_provisioning_key` | Create a new provisioning key | Write |
| `zpa_update_provisioning_key` | Update an existing provisioning key | Write |
| `zpa_delete_provisioning_key` | Delete a provisioning key | Write |

### PRA Credentials

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_pra_credentials` | List PRA credentials | Read-only |
| `zpa_get_pra_credential` | Get a specific PRA credential | Read-only |
| `zpa_create_pra_credential` | Create a new PRA credential | Write |
| `zpa_update_pra_credential` | Update an existing PRA credential | Write |
| `zpa_delete_pra_credential` | Delete a PRA credential | Write |

### PRA Portals

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_pra_portals` | List PRA portals | Read-only |
| `zpa_get_pra_portal` | Get a specific PRA portal | Read-only |
| `zpa_create_pra_portal` | Create a new PRA portal | Write |
| `zpa_update_pra_portal` | Update an existing PRA portal | Write |
| `zpa_delete_pra_portal` | Delete a PRA portal | Write |

### SCIM Attributes

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_scim_attributes` | List SCIM attributes | Read-only |
| `zpa_get_scim_attribute_values` | Get SCIM attribute values | Read-only |
| `zpa_get_scim_attribute_by_idp` | Get SCIM attributes by IdP | Read-only |

### Browser Access Certificates

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_ba_certificates` | List browser access certificates | Read-only |
| `zpa_get_ba_certificate` | Get a specific BA certificate | Read-only |
| `zpa_create_ba_certificate` | Create a new BA certificate | Write |
| `zpa_delete_ba_certificate` | Delete a BA certificate | Write |

### Read-Only Resources

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zpa_list_app_protection_profiles` | List app protection profiles | Read-only |
| `zpa_get_app_protection_profile` | Get a specific app protection profile | Read-only |
| `zpa_list_enrollment_certificates` | List enrollment certificates | Read-only |
| `zpa_get_enrollment_certificate` | Get a specific enrollment certificate | Read-only |
| `zpa_list_isolation_profiles` | List isolation profiles | Read-only |
| `zpa_get_isolation_profile` | Get a specific isolation profile | Read-only |
| `zpa_list_posture_profiles` | List posture profiles | Read-only |
| `zpa_get_posture_profile` | Get a specific posture profile | Read-only |
| `zpa_list_saml_attributes` | List SAML attributes | Read-only |
| `zpa_get_saml_attribute_values` | Get SAML attribute values | Read-only |
| `zpa_list_scim_groups` | List SCIM groups | Read-only |
| `zpa_get_scim_group_by_name` | Get SCIM group by name | Read-only |
| `zpa_list_trusted_networks` | List trusted networks | Read-only |
| `zpa_get_trusted_network` | Get a specific trusted network | Read-only |

---

## ZTW Features

ZTW provides both **read-only** and **write** tools. Write operations require `--enable-write-tools` flag:

### IP Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_ip_groups` | List ZTW IP groups | Read-only |
| `ztw_get_ip_group` | Get a specific IP group | Read-only |
| `ztw_list_ip_groups_lite` | List IP groups (lite) | Read-only |
| `ztw_create_ip_group` | Create a new IP group | Write |
| `ztw_update_ip_group` | Update an existing IP group | Write |
| `ztw_delete_ip_group` | Delete an IP group | Write |

### IP Source Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_ip_source_groups` | List IP source groups | Read-only |
| `ztw_get_ip_source_group` | Get a specific IP source group | Read-only |
| `ztw_create_ip_source_group` | Create a new IP source group | Write |
| `ztw_update_ip_source_group` | Update an existing IP source group | Write |
| `ztw_delete_ip_source_group` | Delete an IP source group | Write |

### IP Destination Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_ip_destination_groups` | List IP destination groups | Read-only |
| `ztw_get_ip_destination_group` | Get a specific IP destination group | Read-only |
| `ztw_create_ip_destination_group` | Create a new IP destination group | Write |
| `ztw_update_ip_destination_group` | Update an existing IP destination group | Write |
| `ztw_delete_ip_destination_group` | Delete an IP destination group | Write |

### Network Service Groups

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_network_service_groups` | List network service groups | Read-only |
| `ztw_get_network_service_group` | Get a specific network service group | Read-only |
| `ztw_create_network_service_group` | Create a new network service group | Write |
| `ztw_update_network_service_group` | Update an existing network service group | Write |
| `ztw_delete_network_service_group` | Delete a network service group | Write |

### Network Services

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_network_services` | List network services with optional filtering | Read-only |

### Administration

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_roles` | List all admin roles | Read-only |
| `ztw_list_admins` | List all admin users | Read-only |
| `ztw_get_admin` | Get a specific admin user | Read-only |

### Public Cloud Info

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_list_public_cloud_info` | List public cloud accounts with metadata | Read-only |
| `ztw_list_public_account_details` | List detailed public cloud account information | Read-only |

### Discovery Service

| Tool Name | Description | Type |
|-----------|-------------|------|
| `ztw_get_discovery_settings` | Get workload discovery service settings | Read-only |

---

## EASM - External Attack Surface Management

EASM provides **read-only** tools for monitoring your organization's external attack surface, including findings and lookalike domains.

### Organizations

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zeasm_list_organizations` | List all EASM organizations configured for the tenant | Read-only |

### Findings

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zeasm_list_findings` | List all findings for an organization's internet-facing assets | Read-only |
| `zeasm_get_finding_details` | Get detailed information for a specific finding | Read-only |
| `zeasm_get_finding_evidence` | Get scan evidence attributed to a specific finding | Read-only |
| `zeasm_get_finding_scan_output` | Get complete scan output for a specific finding | Read-only |

### Lookalike Domains

| Tool Name | Description | Type |
|-----------|-------------|------|
| `zeasm_list_lookalike_domains` | List all lookalike domains detected for an organization | Read-only |
| `zeasm_get_lookalike_domain` | Get details for a specific lookalike domain | Read-only |
