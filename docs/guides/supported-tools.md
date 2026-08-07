# Supported Tools Reference

The Zscaler Integrations MCP Server provides tools for all major Zscaler services. Each service offers specific functionality for managing and querying Zscaler resources.

> **Note:** All tools marked as "Write" require the `--enable-write-tools` flag and an explicit `--write-tools` allowlist to be enabled. See the [Security & Permissions](https://github.com/zscaler/zscaler-mcp-server#-security--permissions) section in the main README for details.
>
> **This page is auto-generated.** The tables below are rebuilt from the live tool inventory by `zscaler-mcp --generate-docs`. Edit the tool descriptions in `zscaler_mcp/services.py` and re-run the generator — do not edit the generated tables by hand. CI runs `--check-docs` to enforce sync.

<!-- generated:start tools -->

## Table of Contents

- [ZIA — Internet Access](#zia--internet-access)
- [ZPA — Private Access](#zpa--private-access)
- [ZDX — Digital Experience](#zdx--digital-experience)
- [ZCC — Client Connector](#zcc--client-connector)
- [ZTW — Workload Segmentation](#ztw--workload-segmentation)
- [ZIdentity](#zidentity)
- [EASM — External Attack Surface Management](#easm--external-attack-surface-management)
- [Z-Insights](#z-insights)
- [ZMS — Microsegmentation](#zms--microsegmentation)
- [ZCell — Cellular](#zcell--cellular)

---

## ZIA — Internet Access

84 read-only tools, 82 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `get_zia_dlp_dictionaries` | `zia_dlp` | Read-only | Read ZIA DLP dictionaries: list all/lite, or fetch one by ID (read-only). |
| `get_zia_dlp_engines` | `zia_dlp` | Read-only | Read ZIA DLP engines: list all/lite, or fetch one by ID (read-only). |
| `get_zia_user_departments` | `zia_users` | Read-only | Read ZIA user departments: list with filters, or fetch one by ID (read-only). |
| `get_zia_user_groups` | `zia_users` | Read-only | Read ZIA user groups: fetch by ID, find by name, or list (read-only). |
| `get_zia_users` | `zia_users` | Read-only | Read ZIA users: list with optional filters, or fetch one by ID (read-only). |
| `zia_geo_search` | `zia_locations` | Read-only | Resolve ZIA geo data by coordinates, by IP, or by city prefix (read-only). |
| `zia_get_activation_status` | `zia_admin` | Read-only | Get the current ZIA configuration activation status. |
| `zia_get_advanced_settings` | `zia_advanced_settings` | Read-only | Get the ZIA tenant-wide Advanced Settings object. |
| `zia_get_atp_malware_inspection` | `zia_atp_malware` | Read-only | Get the ZIA malware inspection (traffic-direction toggles). |
| `zia_get_atp_malware_policy` | `zia_atp_malware` | Read-only | Get the ZIA malware policy (file-handling toggles). |
| `zia_get_atp_malware_protocols` | `zia_atp_malware` | Read-only | Get the ZIA malware protocol toggles (HTTP/FTP). |
| `zia_get_atp_security_exceptions` | `zia_atp_policy` | Read-only | Get the ZIA ATP security-exception bypass URL allowlist. |
| `zia_get_atp_settings` | `zia_atp_policy` | Read-only | Get the ZIA tenant-wide ATP policy block. |
| `zia_get_cloud_app_control_rule` | `zia_cloud_app_control` | Read-only | Get a single ZIA Cloud App Control rule by category + ID. |
| `zia_get_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Read-only | Get a single ZIA Cloud Firewall DNS rule by ID with member references. |
| `zia_get_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Read-only | Get a single ZIA Cloud Firewall IPS rule by ID with member references. |
| `zia_get_cloud_firewall_rule` | `zia_cloud_firewall` | Read-only | Get a single ZIA Cloud Firewall rule by ID with member references. |
| `zia_get_file_type_control_rule` | `zia_file_type_control` | Read-only | Get a single ZIA File Type Control rule by ID with member references. |
| `zia_get_gre_tunnel` | `zia_locations` | Read-only | Get a single ZIA GRE tunnel by ID. |
| `zia_get_ip_destination_group` | `zia_cloud_firewall` | Read-only | Get a single ZIA IP destination group by ID with full members. |
| `zia_get_ip_source_group` | `zia_cloud_firewall` | Read-only | Get a single ZIA IP source group by ID with its full member list. |
| `zia_get_ips_signature_rule` | `zia_cloud_firewall` | Read-only | Get a single ZIA custom IPS signature rule by ID with its body. |
| `zia_get_location` | `zia_locations` | Read-only | Get a single ZIA location by ID with its full configuration. |
| `zia_get_location_group` | `zia_locations` | Read-only | Get a single ZIA location group by ID. |
| `zia_get_malware_settings` | `zia_atp_malware` | Read-only | Get the ZIA 16-field malware threat-class settings block. |
| `zia_get_mobile_advanced_settings` | `zia_misc` | Read-only | Get the ZIA Mobile Advanced Threat Settings object. |
| `zia_get_network_app` | `zia_cloud_firewall` | Read-only | Get a single ZIA network application by ID. |
| `zia_get_network_app_group` | `zia_cloud_firewall` | Read-only | Get a single ZIA network application group by ID with members. |
| `zia_get_network_service` | `zia_cloud_firewall` | Read-only | Get a single ZIA network service by ID with its port definitions. |
| `zia_get_network_svc_group` | `zia_cloud_firewall` | Read-only | Get a single ZIA network service group by ID with members. |
| `zia_get_rule_label` | `zia_rule_labels` | Read-only | Get a single ZIA rule label by ID. |
| `zia_get_sandbox_behavioral_analysis` | `zia_sandbox` | Read-only | Get the ZIA Sandbox behavioral-analysis configuration. |
| `zia_get_sandbox_file_hash_count` | `zia_sandbox` | Read-only | Get the ZIA Sandbox custom file-hash blocklist usage/quota. |
| `zia_get_sandbox_quota` | `zia_sandbox` | Read-only | Get the ZIA Sandbox API submission quota. |
| `zia_get_sandbox_report` | `zia_sandbox` | Read-only | Get the ZIA Sandbox detonation report for a file MD5 hash. |
| `zia_get_sandbox_rule` | `zia_sandbox` | Read-only | Get a single ZIA Sandbox rule by ID with member references. |
| `zia_get_ssl_inspection_rule` | `zia_ssl_inspection` | Read-only | Get a single ZIA SSL Inspection rule by ID with member references. |
| `zia_get_static_ip` | `zia_locations` | Read-only | Get a single ZIA static IP by ID. |
| `zia_get_time_interval` | `zia_time_intervals` | Read-only | Get a single ZIA time interval by ID. |
| `zia_get_url_category` | `zia_url_categories` | Read-only | Get a single ZIA URL category by ID (full detail). |
| `zia_get_url_category_predefined` | `zia_url_categories` | Read-only | Get a Zscaler-curated **predefined** URL category by ID or display name. |
| `zia_get_url_filtering_rule` | `zia_url_filtering` | Read-only | Get a single ZIA URL Filtering rule by ID with member references. |
| `zia_get_vpn_credential` | `zia_locations` | Read-only | Get a single ZIA VPN credential by ID. |
| `zia_get_web_dlp_rule` | `zia_dlp` | Read-only | Get a single ZIA Web DLP rule by ID with member references. |
| `zia_get_workload_group` | `zia_workload_groups` | Read-only | Get a single ZIA workload group by ID. |
| `zia_list_atp_malicious_urls` | `zia_atp_policy` | Read-only | List the ZIA ATP malicious-URL denylist. |
| `zia_list_auth_exempt_urls` | `zia_authentication_settings` | Read-only | List the ZIA cookie-auth exempt URL list. |
| `zia_list_cloud_app_control_actions` | `zia_cloud_app_control` | Read-only | List the available CAC actions for a category (and optional cloud apps). |
| `zia_list_cloud_app_control_rules` | `zia_cloud_app_control` | Read-only | List ZIA Cloud App Control rules for a category. |
| `zia_list_cloud_app_policy` | `zia_cloud_app_control` | Read-only | List the ZIA policy-engine cloud-application catalog (Cloud App Control). |
| `zia_list_cloud_app_ssl_policy` | `zia_ssl_inspection` | Read-only | List the ZIA policy-engine cloud-application catalog (SSL Inspection). |
| `zia_list_cloud_firewall_dns_rules` | `zia_cloud_firewall` | Read-only | List ZIA Cloud Firewall DNS rules. |
| `zia_list_cloud_firewall_ips_rules` | `zia_cloud_firewall` | Read-only | List ZIA Cloud Firewall IPS rules. |
| `zia_list_cloud_firewall_rules` | `zia_cloud_firewall` | Read-only | List ZIA Cloud Firewall rules. |
| `zia_list_device_groups` | `zia_devices` | Read-only | List ZIA device groups. |
| `zia_list_devices` | `zia_devices` | Read-only | List ZIA devices. |
| `zia_list_devices_lite` | `zia_devices` | Read-only | List ZIA devices via the lighter endpoint (id/name only). |
| `zia_list_file_type_categories` | `zia_file_type_control` | Read-only | List ZIA file-type categories usable in File Type Control rules. |
| `zia_list_file_type_control_rules` | `zia_file_type_control` | Read-only | List ZIA File Type Control rules. |
| `zia_list_gre_ranges` | `zia_locations` | Read-only | List available ZIA GRE internal-IP ranges. |
| `zia_list_gre_tunnels` | `zia_locations` | Read-only | List ZIA GRE tunnels. |
| `zia_list_ip_destination_groups` | `zia_cloud_firewall` | Read-only | List ZIA IP destination groups. |
| `zia_list_ip_source_groups` | `zia_cloud_firewall` | Read-only | List ZIA IP source groups. |
| `zia_list_ips_signature_rules` | `zia_cloud_firewall` | Read-only | List ZIA custom IPS signature rules. |
| `zia_list_location_groups` | `zia_locations` | Read-only | List ZIA location groups. |
| `zia_list_locations` | `zia_locations` | Read-only | List ZIA locations. |
| `zia_list_network_app_groups` | `zia_cloud_firewall` | Read-only | List ZIA network application groups. |
| `zia_list_network_apps` | `zia_cloud_firewall` | Read-only | List ZIA network applications (predefined + custom). |
| `zia_list_network_services` | `zia_cloud_firewall` | Read-only | List ZIA network services. Use `name` for case-insensitive find-by-name. |
| `zia_list_network_svc_groups` | `zia_cloud_firewall` | Read-only | List ZIA network service groups. |
| `zia_list_rule_labels` | `zia_rule_labels` | Read-only | List ZIA rule labels. |
| `zia_list_sandbox_rules` | `zia_sandbox` | Read-only | List ZIA Sandbox rules. |
| `zia_list_shadow_it_apps` | `zia_shadow_it` | Read-only | List ZIA Shadow IT applications (analytics catalog). |
| `zia_list_shadow_it_custom_tags` | `zia_shadow_it` | Read-only | List ZIA Shadow IT custom tags. |
| `zia_list_ssl_inspection_rules` | `zia_ssl_inspection` | Read-only | List ZIA SSL Inspection rules. |
| `zia_list_static_ips` | `zia_locations` | Read-only | List ZIA static IPs. |
| `zia_list_time_intervals` | `zia_time_intervals` | Read-only | List ZIA time intervals. |
| `zia_list_url_categories` | `zia_url_categories` | Read-only | List ZIA URL categories. Narrow the request — this response can be large.  ASK THE USER FOR SCOPE BEFORE CALLING THIS UNFILTERED. This endpoint does not paginate: everything matching the request comes back in a single response, and a large tenant holds thousands of categories. If the request was broad ("show me the URL categories"), ask which ones they mean — custom or predefined (`custom_only`), URL or TLD (`type`), or a name to match (`search`) — and call once with that answer. Do not call unfiltered first and narrow afterwards; the cost is already paid by then.  Use this to see what categories exist, or to resolve a category id before calling another tool. For predefined categories the id IS the name (`OTHER_ADULT_MATERIAL`); custom categories carry a generated id and are identified by `configured_name`.  For "list the custom URL categories", pass `custom_only=True` — that is a real API filter, so only those categories are fetched.  Every category comes back with its URL, keyword and IP lists in full. The API has no parameter to return counts instead, so on a tenant whose categories hold large URL lists this response is big and nothing about the call itself makes it smaller. Two things do: filter before calling, and pass a `query` projection when the answer needs only part of each record — for example `[*].{id: id, name: configured_name, urls: custom_urls_count}` for an inventory rather than the URLs themselves. The projection is applied before the response is encoded, so it is a real saving, not cosmetic.  Filtering narrows WHICH categories are returned; it cannot cap HOW MANY. A tenant with 5000 custom categories returns 5000 rows for `custom_only=True`.  Use `zia_get_url_category` for one category's full definition once you know its id. To find which category a specific URL belongs to, use `zia_url_lookup` — a different question, and this tool does not answer it. |
| `zia_list_url_filtering_rules` | `zia_url_filtering` | Read-only | List ZIA URL Filtering rules. |
| `zia_list_vpn_credentials` | `zia_locations` | Read-only | List ZIA VPN credentials (PSK never returned). |
| `zia_list_web_dlp_rules` | `zia_dlp` | Read-only | List ZIA Web DLP rules. |
| `zia_list_web_dlp_rules_lite` | `zia_dlp` | Read-only | List ZIA Web DLP rules via the lighter SDK endpoint. |
| `zia_list_workload_groups` | `zia_workload_groups` | Read-only | List ZIA workload groups. |
| `zia_url_lookup` | `zia_url_categories` | Read-only | Which category does a URL belong to? Use THIS for that question.  Answers "what category is twilio.com?" directly: pass the URLs and get back Zscaler's classification for each, e.g. `{"url": "notpurple.com", "urlClassifications": ["SPECIALIZED_SHOPPING"]}`. The response is small and scales with the number of URLs you ask about, not with the size of the tenant's category inventory.  Do NOT try to answer it by listing categories. `zia_list_url_categories` returns the category inventory without any URLs in it, so it cannot tell you where a URL landed no matter how much of it you read.  Two limits worth knowing. Only Zscaler's PREDEFINED classification is returned, so a URL matched by a custom category still reports its predefined category here. And up to 100 URLs may be looked up per request; a URL in no predefined category comes back as `MISCELLANEOUS_OR_UNKNOWN`. |
| `zia_activate_configuration` | `zia_admin` | Write | Activate staged ZIA configuration changes (write). Run after any ZIA write. |
| `zia_add_atp_malicious_urls` | `zia_atp_policy` | Write | Add URLs to the ZIA ATP malicious-URL denylist (additive write). Activate after. |
| `zia_add_auth_exempt_urls` | `zia_authentication_settings` | Write | Add URLs to the ZIA cookie-auth exempt list (additive write). Activate after. |
| `zia_add_urls_to_category` | `zia_url_categories` | Write | Incrementally add URLs to an existing ZIA URL category. Activate after. |
| `zia_bulk_update_shadow_it_apps` | `zia_shadow_it` | Write | Bulk-apply sanction state and/or custom tags to Shadow IT apps (write). |
| `zia_create_cloud_app_control_rule` | `zia_cloud_app_control` | Write | Create a ZIA Cloud App Control rule (write). Activate after. |
| `zia_create_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Write | Create a ZIA Cloud Firewall DNS rule (write). Activate after. |
| `zia_create_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Write | Create a ZIA Cloud Firewall IPS rule (write). Activate after. |
| `zia_create_cloud_firewall_rule` | `zia_cloud_firewall` | Write | Create a ZIA Cloud Firewall rule (write). Activate after. |
| `zia_create_file_type_control_rule` | `zia_file_type_control` | Write | Create a ZIA File Type Control rule (write). Activate after. |
| `zia_create_gre_tunnel` | `zia_locations` | Write | Create a ZIA GRE tunnel (write). Finds/creates the backing static IP first. Activate after. |
| `zia_create_ip_destination_group` | `zia_cloud_firewall` | Write | Create a ZIA IP destination group (write). Activate after. |
| `zia_create_ip_source_group` | `zia_cloud_firewall` | Write | Create a ZIA IP source group (write). Call zia_activate_configuration after. |
| `zia_create_ips_signature_rule` | `zia_cloud_firewall` | Write | Create a ZIA custom IPS signature rule (write). Activate after. |
| `zia_create_location` | `zia_locations` | Write | Create a ZIA location (write). Needs ipAddresses or vpnCredentials. Activate after. |
| `zia_create_network_app_group` | `zia_cloud_firewall` | Write | Create a ZIA network application group (write). Activate after. |
| `zia_create_network_service` | `zia_cloud_firewall` | Write | Create a custom ZIA network service (write). Activate after. |
| `zia_create_network_svc_group` | `zia_cloud_firewall` | Write | Create a ZIA network service group (write). Activate after. |
| `zia_create_rule_label` | `zia_rule_labels` | Write | Create a ZIA rule label (write). Activate after. |
| `zia_create_sandbox_rule` | `zia_sandbox` | Write | Create a ZIA Sandbox rule (write). Activate after. |
| `zia_create_ssl_inspection_rule` | `zia_ssl_inspection` | Write | Create a ZIA SSL Inspection rule (write). Activate after. |
| `zia_create_static_ip` | `zia_locations` | Write | Create a ZIA static IP (write). Activate after. |
| `zia_create_time_interval` | `zia_time_intervals` | Write | Create a ZIA time interval (write). Activate after. |
| `zia_create_url_category` | `zia_url_categories` | Write | Create a new **custom** ZIA URL category (write). Activate after. |
| `zia_create_url_filtering_rule` | `zia_url_filtering` | Write | Create a ZIA URL Filtering rule (write). Activate after. |
| `zia_create_vpn_credential` | `zia_locations` | Write | Create a ZIA VPN credential (write). Activate after. |
| `zia_create_web_dlp_rule` | `zia_dlp` | Write | Create a ZIA Web DLP rule (write). Activate after. |
| `zia_delete_atp_malicious_urls` | `zia_atp_policy` | Write | Remove URLs from the ZIA ATP malicious-URL denylist (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_auth_exempt_urls` | `zia_authentication_settings` | Write | Remove URLs from the ZIA cookie-auth exempt list (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_cloud_app_control_rule` | `zia_cloud_app_control` | Write | Delete a ZIA Cloud App Control rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Write | Delete a ZIA Cloud Firewall DNS rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Write | Delete a ZIA Cloud Firewall IPS rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_cloud_firewall_rule` | `zia_cloud_firewall` | Write | Delete a ZIA Cloud Firewall rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_file_type_control_rule` | `zia_file_type_control` | Write | Delete a ZIA File Type Control rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_gre_tunnel` | `zia_locations` | Write | Delete a ZIA GRE tunnel and its backing static IP (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_ip_destination_group` | `zia_cloud_firewall` | Write | Delete a ZIA IP destination group (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_ip_source_group` | `zia_cloud_firewall` | Write | Delete a ZIA IP source group (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_ips_signature_rule` | `zia_cloud_firewall` | Write | Delete a ZIA custom IPS signature rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_location` | `zia_locations` | Write | Delete a ZIA location (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_network_app_group` | `zia_cloud_firewall` | Write | Delete a ZIA network application group (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_network_service` | `zia_cloud_firewall` | Write | Delete a ZIA network service (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_network_svc_group` | `zia_cloud_firewall` | Write | Delete a ZIA network service group (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_rule_label` | `zia_rule_labels` | Write | Delete a ZIA rule label (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_sandbox_rule` | `zia_sandbox` | Write | Delete a ZIA Sandbox rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_ssl_inspection_rule` | `zia_ssl_inspection` | Write | Delete a ZIA SSL Inspection rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_static_ip` | `zia_locations` | Write | Delete a ZIA static IP (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_time_interval` | `zia_time_intervals` | Write | Delete a ZIA time interval (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_url_category` | `zia_url_categories` | Write | Delete a **custom** ZIA URL category (destructive). Activate after.  Refuses predefined categories — those are Zscaler-curated and cannot be deleted via the API.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_url_filtering_rule` | `zia_url_filtering` | Write | Delete a ZIA URL Filtering rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_vpn_credential` | `zia_locations` | Write | Delete a ZIA VPN credential (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_delete_web_dlp_rule` | `zia_dlp` | Write | Delete a ZIA Web DLP rule (destructive). Activate after.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zia_remove_urls_from_category` | `zia_url_categories` | Write | Incrementally remove URLs from an existing ZIA URL category. Activate after. |
| `zia_update_advanced_settings` | `zia_advanced_settings` | Write | Update ZIA Advanced Settings (strict PUT-replace write). Activate after. |
| `zia_update_atp_malware_inspection` | `zia_atp_malware` | Write | Update the ZIA malware inspection (PUT-replace write). Activate after. |
| `zia_update_atp_malware_policy` | `zia_atp_malware` | Write | Update the ZIA malware policy (PUT-replace write). Activate after. |
| `zia_update_atp_malware_protocols` | `zia_atp_malware` | Write | Update the ZIA malware protocol toggles (PUT-replace write). Re-fetches authoritative state. Activate after. |
| `zia_update_atp_security_exceptions` | `zia_atp_policy` | Write | Replace the ZIA ATP security-exception allowlist (full-list write). Activate after. |
| `zia_update_atp_settings` | `zia_atp_policy` | Write | Update ZIA ATP settings (strict PUT-replace write). Activate after. |
| `zia_update_cloud_app_control_rule` | `zia_cloud_app_control` | Write | Update a ZIA Cloud App Control rule (write, PUT-replace). Activate after. |
| `zia_update_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Write | Update a ZIA Cloud Firewall DNS rule (write, PUT-replace). Activate after. |
| `zia_update_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Write | Update a ZIA Cloud Firewall IPS rule (write, PUT-replace). Activate after. |
| `zia_update_cloud_firewall_rule` | `zia_cloud_firewall` | Write | Update a ZIA Cloud Firewall rule (write, PUT-replace). Activate after. |
| `zia_update_file_type_control_rule` | `zia_file_type_control` | Write | Update a ZIA File Type Control rule (write, PUT-replace). Activate after. |
| `zia_update_ip_destination_group` | `zia_cloud_firewall` | Write | Update a ZIA IP destination group (full-replace write). Activate after. |
| `zia_update_ip_source_group` | `zia_cloud_firewall` | Write | Update a ZIA IP source group (full-replace write). Activate after. |
| `zia_update_ips_signature_rule` | `zia_cloud_firewall` | Write | Update a ZIA custom IPS signature rule (PUT-replace; backfills name/rule_text). Activate after. |
| `zia_update_location` | `zia_locations` | Write | Update a ZIA location (write). Activate after. |
| `zia_update_malware_settings` | `zia_atp_malware` | Write | Update the ZIA malware threat-class settings (strict PUT-replace write). Activate after. |
| `zia_update_mobile_advanced_settings` | `zia_misc` | Write | Update ZIA Mobile Advanced Threat Settings (PUT-replace write). Activate after. |
| `zia_update_network_app_group` | `zia_cloud_firewall` | Write | Update a ZIA network application group (full-replace write). Activate after. |
| `zia_update_network_service` | `zia_cloud_firewall` | Write | Update a ZIA network service (write). Ports, if given, replace existing. Activate after. |
| `zia_update_network_svc_group` | `zia_cloud_firewall` | Write | Update a ZIA network service group (full-replace write). Activate after. |
| `zia_update_rule_label` | `zia_rule_labels` | Write | Update a ZIA rule label (write). Activate after. |
| `zia_update_sandbox_rule` | `zia_sandbox` | Write | Update a ZIA Sandbox rule (write, PUT-replace). Activate after. |
| `zia_update_ssl_inspection_rule` | `zia_ssl_inspection` | Write | Update a ZIA SSL Inspection rule (write, PUT-replace). Activate after. |
| `zia_update_static_ip` | `zia_locations` | Write | Update a ZIA static IP (write). Activate after. |
| `zia_update_time_interval` | `zia_time_intervals` | Write | Update a ZIA time interval (PUT-replace; backfills omitted fields). Activate after. |
| `zia_update_url_category` | `zia_url_categories` | Write | Update a **custom** ZIA URL category (full PUT-replace). Activate after.  Refuses predefined categories — use zia_update_url_category_predefined or the incremental add/remove tools instead. |
| `zia_update_url_category_predefined` | `zia_url_categories` | Write | Update a Zscaler-curated **predefined** URL category (full PUT). Activate after.  For incremental "add a few URLs to FINANCE" workflows prefer zia_add_urls_to_category / zia_remove_urls_from_category instead. |
| `zia_update_url_filtering_rule` | `zia_url_filtering` | Write | Update a ZIA URL Filtering rule (write, PUT-replace). Activate after. |
| `zia_update_vpn_credential` | `zia_locations` | Write | Update a ZIA VPN credential (write). Activate after. |
| `zia_update_web_dlp_rule` | `zia_dlp` | Write | Update a ZIA Web DLP rule (write, PUT-replace). Activate after. |

---

## ZPA — Private Access

53 read-only tools, 56 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `get_zpa_app_protection_profile` | `zpa_misc` | Read-only | List ZPA App Protection (inspection) profiles, or filter by name (read-only). |
| `get_zpa_app_segments_by_type` | `zpa_app_segments` | Read-only | Retrieve ZPA application segments filtered by application type (read-only).  `application_type` must be BROWSER_ACCESS, INSPECT, or SECURE_REMOTE_ACCESS. |
| `get_zpa_enrollment_certificate` | `zpa_provisioning_keys` | Read-only | Read ZPA enrollment certificates: list all, or look one up by name or ID (read-only). |
| `get_zpa_isolation_profile` | `zpa_misc` | Read-only | List ZPA Cloud Browser Isolation (CBI) profiles, or filter by exact name (read-only). |
| `get_zpa_posture_profile` | `zpa_misc` | Read-only | List ZPA posture profiles, or look one up by ID or name (read-only). |
| `get_zpa_saml_attribute` | `zpa_idp` | Read-only | List ZPA SAML attributes, optionally scoped to a named IdP (read-only). |
| `get_zpa_scim_attribute` | `zpa_idp` | Read-only | List ZPA SCIM attributes for a named IdP, or fetch one by ID (read-only). |
| `get_zpa_scim_group` | `zpa_idp` | Read-only | Fetch one ZPA SCIM group by ID, or list all groups under a named IdP (read-only). |
| `get_zpa_trusted_network` | `zpa_misc` | Read-only | List ZPA trusted networks, or look one up by ID or name (read-only). |
| `zpa_get_access_policy_rule` | `zpa_access_policies` | Read-only | Get one ZPA access policy rule (read-only). |
| `zpa_get_app_connector` | `zpa_connectors` | Read-only | Get one ZPA app connector by ID (read-only). |
| `zpa_get_app_connector_group` | `zpa_app_connector_groups` | Read-only | Get one ZPA app connector group (read-only). |
| `zpa_get_app_protection_rule` | `zpa_access_policies` | Read-only | Get one ZPA app-protection (inspection) policy rule (read-only). |
| `zpa_get_application_segment` | `zpa_app_segments` | Read-only | Get one ZPA application segment. |
| `zpa_get_application_segment_ba` | `zpa_app_segments` | Read-only | Get one ZPA browser-access application segment. |
| `zpa_get_application_segment_pra` | `zpa_app_segments` | Read-only | Get one ZPA privileged-remote-access application segment. |
| `zpa_get_application_server` | `zpa_application_servers` | Read-only | Get one ZPA application server (read-only). |
| `zpa_get_ba_certificate` | `zpa_ba_certificates` | Read-only | Get one ZPA Browser Access certificate by ID (read-only). |
| `zpa_get_forwarding_policy_rule` | `zpa_access_policies` | Read-only | Get one ZPA client forwarding policy rule (read-only). |
| `zpa_get_isolation_policy_rule` | `zpa_access_policies` | Read-only | Get one ZPA isolation policy rule (read-only). |
| `zpa_get_lss_config` | `zpa_misc` | Read-only | Get one ZPA LSS configuration by ID (read-only). |
| `zpa_get_lss_log_format` | `zpa_misc` | Read-only | Get the pre-built LSS log-format templates (csv/json/tsv) for a log type (read-only). |
| `zpa_get_pra_credential` | `zpa_pra` | Read-only | Get one ZPA PRA credential by ID (read-only). Secrets are never returned. |
| `zpa_get_pra_portal` | `zpa_pra` | Read-only | Get one ZPA PRA portal by ID (read-only). |
| `zpa_get_provisioning_key` | `zpa_provisioning_keys` | Read-only | Get one ZPA provisioning key by ID and type (read-only). |
| `zpa_get_segment_group` | `zpa_segment_groups` | Read-only | Get one ZPA segment group. |
| `zpa_get_server_group` | `zpa_server_groups` | Read-only | Get one ZPA server group (read-only). |
| `zpa_get_service_edge` | `zpa_service_edge_groups` | Read-only | Get one ZPA Service Edge by ID (read-only). |
| `zpa_get_service_edge_group` | `zpa_service_edge_groups` | Read-only | Get one ZPA service edge group (read-only). |
| `zpa_get_timeout_policy_rule` | `zpa_access_policies` | Read-only | Get one ZPA timeout policy rule (read-only). |
| `zpa_list_access_policy_rules` | `zpa_access_policies` | Read-only | List ZPA access policy rules (read-only). |
| `zpa_list_app_connector_groups` | `zpa_app_connector_groups` | Read-only | List ZPA app connector groups (read-only). |
| `zpa_list_app_connectors` | `zpa_connectors` | Read-only | List ZPA app connectors with health/status (read-only). |
| `zpa_list_app_protection_rules` | `zpa_access_policies` | Read-only | List ZPA app-protection (inspection) policy rules (read-only). |
| `zpa_list_application_segments` | `zpa_app_segments` | Read-only | List ZPA application segments.  Each row is the full segment record with normalized highlights on top (ids, member domains/server groups, ports, and behavior toggles). |
| `zpa_list_application_segments_ba` | `zpa_app_segments` | Read-only | List ZPA browser-access (clientless) application segments. |
| `zpa_list_application_segments_pra` | `zpa_app_segments` | Read-only | List ZPA privileged-remote-access application segments. |
| `zpa_list_application_servers` | `zpa_application_servers` | Read-only | List ZPA application servers (read-only). |
| `zpa_list_ba_certificates` | `zpa_ba_certificates` | Read-only | List ZPA Browser Access certificates (read-only). |
| `zpa_list_forwarding_policy_rules` | `zpa_access_policies` | Read-only | List ZPA client forwarding policy rules (read-only). |
| `zpa_list_isolation_policy_rules` | `zpa_access_policies` | Read-only | List ZPA isolation policy rules (read-only). |
| `zpa_list_lss_client_types` | `zpa_misc` | Read-only | List ZPA LSS client types for the current customer (read-only catalog). |
| `zpa_list_lss_configs` | `zpa_misc` | Read-only | List ZPA LSS configurations — what log feed streams where (read-only). |
| `zpa_list_lss_log_types` | `zpa_misc` | Read-only | List the human-readable LSS source log types ZPA supports (read-only catalog). |
| `zpa_list_lss_status_codes` | `zpa_misc` | Read-only | List ZPA LSS session status codes used in config filters (read-only catalog). |
| `zpa_list_pra_credentials` | `zpa_pra` | Read-only | List ZPA PRA credentials (read-only). Secrets are never returned. |
| `zpa_list_pra_portals` | `zpa_pra` | Read-only | List ZPA PRA portals (read-only). |
| `zpa_list_provisioning_keys` | `zpa_provisioning_keys` | Read-only | List ZPA provisioning keys of a given type (read-only). |
| `zpa_list_segment_groups` | `zpa_segment_groups` | Read-only | List ZPA segment groups.  Each row is the full segment-group record with normalized highlights (ids, enabled state, application-segment counts/ids, timestamps) on top. |
| `zpa_list_server_groups` | `zpa_server_groups` | Read-only | List ZPA server groups (read-only). |
| `zpa_list_service_edge_groups` | `zpa_service_edge_groups` | Read-only | List ZPA service edge groups (read-only). |
| `zpa_list_service_edges` | `zpa_service_edge_groups` | Read-only | List individual ZPA Service Edges with health/status (read-only).  Distinct from `zpa_list_service_edge_groups` (the parent group resource). |
| `zpa_list_timeout_policy_rules` | `zpa_access_policies` | Read-only | List ZPA timeout policy rules (read-only). |
| `zpa_bulk_delete_app_connectors` | `zpa_connectors` | Write | Bulk-delete ZPA app connectors (destructive write). Each must be re-provisioned to reconnect.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_bulk_delete_service_edges` | `zpa_service_edge_groups` | Write | Bulk-delete ZPA Service Edges (destructive write). Each must be re-provisioned to reconnect.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_create_access_policy_rule` | `zpa_access_policies` | Write | Create a ZPA access policy rule (write). Requires `--write-tools`. |
| `zpa_create_app_connector_group` | `zpa_app_connector_groups` | Write | Create a ZPA app connector group (write).  Requires `--write-tools`. Auto-resolves the tenant's standard 'Connector' enrollment certificate when none is supplied. |
| `zpa_create_app_protection_rule` | `zpa_access_policies` | Write | Create a ZPA app-protection (inspection) policy rule (write).  Requires `--write-tools`. `zpn_inspection_profile_id` is required when action_type is 'inspect'. |
| `zpa_create_application_segment` | `zpa_app_segments` | Write | Create a ZPA application segment (write).  Requires `name` + `segment_group_id` and at least one port range (TCP or UDP, via `tcp_port_ranges`/`udp_port_ranges` or `advanced`). Requires `--write-tools`. |
| `zpa_create_application_segment_ba` | `zpa_app_segments` | Write | Create a ZPA browser-access application segment (write). |
| `zpa_create_application_segment_pra` | `zpa_app_segments` | Write | Create a ZPA privileged-remote-access application segment (write). |
| `zpa_create_application_server` | `zpa_application_servers` | Write | Create a ZPA application server (write).  Requires `--write-tools`. |
| `zpa_create_ba_certificate` | `zpa_ba_certificates` | Write | Create a ZPA Browser Access certificate from a PEM blob (write).  Requires `--write-tools`. |
| `zpa_create_forwarding_policy_rule` | `zpa_access_policies` | Write | Create a ZPA client forwarding policy rule (write). Requires `--write-tools`. |
| `zpa_create_isolation_policy_rule` | `zpa_access_policies` | Write | Create a ZPA isolation policy rule (write). Requires `--write-tools`.  `zpn_isolation_profile_id` is required when action_type is 'isolate'. |
| `zpa_create_pra_credential` | `zpa_pra` | Write | Create a ZPA PRA credential (write). Requires `--write-tools`.  Secrets (password / private_key) are write-only — they are sent to the API but never echoed back in the response. |
| `zpa_create_pra_portal` | `zpa_pra` | Write | Create a ZPA PRA portal (write). Requires `--write-tools`.  If `certificate_id` is omitted, the BA certificate is resolved by searching issued certificates for one whose name matches the portal `name`. |
| `zpa_create_provisioning_key` | `zpa_provisioning_keys` | Write | Create a ZPA provisioning key (write). Requires `--write-tools`.  `enrollment_cert_id` is required when `key_type` is 'connector'. |
| `zpa_create_segment_group` | `zpa_segment_groups` | Write | Create a ZPA segment group and return the full record.  Write tool: disabled unless the operator enables it via --write-tools. |
| `zpa_create_server_group` | `zpa_server_groups` | Write | Create a ZPA server group (write).  Requires `--write-tools`, plus at least one App Connector Group; dynamic_discovery=False requires server_ids. |
| `zpa_create_service_edge_group` | `zpa_service_edge_groups` | Write | Create a ZPA service edge group (write).  Requires `--write-tools`, plus name, latitude, longitude, and location. |
| `zpa_create_timeout_policy_rule` | `zpa_access_policies` | Write | Create a ZPA timeout policy rule (write). Requires `--write-tools`. |
| `zpa_delete_access_policy_rule` | `zpa_access_policies` | Write | Delete a ZPA access policy rule (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_app_connector` | `zpa_connectors` | Write | Delete a ZPA app connector (destructive write). Must be re-provisioned to reconnect.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_app_connector_group` | `zpa_app_connector_groups` | Write | Delete a ZPA app connector group (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_app_protection_rule` | `zpa_access_policies` | Write | Delete a ZPA app-protection (inspection) policy rule (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_application_segment` | `zpa_app_segments` | Write | Delete a ZPA application segment (destructive write). Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_application_segment_ba` | `zpa_app_segments` | Write | Delete a ZPA browser-access application segment (destructive write). Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_application_segment_pra` | `zpa_app_segments` | Write | Delete a ZPA privileged-remote-access application segment (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_application_server` | `zpa_application_servers` | Write | Delete a ZPA application server (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_ba_certificate` | `zpa_ba_certificates` | Write | Delete a ZPA Browser Access certificate (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_forwarding_policy_rule` | `zpa_access_policies` | Write | Delete a ZPA client forwarding policy rule (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_isolation_policy_rule` | `zpa_access_policies` | Write | Delete a ZPA isolation policy rule (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_pra_credential` | `zpa_pra` | Write | Delete a ZPA PRA credential (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_pra_portal` | `zpa_pra` | Write | Delete a ZPA PRA portal (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_provisioning_key` | `zpa_provisioning_keys` | Write | Delete a ZPA provisioning key (destructive write).  If the key was already removed (e.g. its component was deleted) this reports success with an explanatory message rather than erroring.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_segment_group` | `zpa_segment_groups` | Write | Delete a ZPA segment group (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_server_group` | `zpa_server_groups` | Write | Delete a ZPA server group (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_service_edge` | `zpa_service_edge_groups` | Write | Delete a single ZPA Service Edge (destructive write). Must be re-provisioned to reconnect.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_service_edge_group` | `zpa_service_edge_groups` | Write | Delete a ZPA service edge group (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_delete_timeout_policy_rule` | `zpa_access_policies` | Write | Delete a ZPA timeout policy rule (destructive write).  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zpa_update_access_policy_rule` | `zpa_access_policies` | Write | Update a ZPA access policy rule (write). Requires `--write-tools`. |
| `zpa_update_app_connector` | `zpa_connectors` | Write | Update a ZPA app connector (enable/disable, rename). Requires `--write-tools`. |
| `zpa_update_app_connector_group` | `zpa_app_connector_groups` | Write | Update a ZPA app connector group (write).  Requires `--write-tools`. The enrollment certificate is preserved unless enrollment_cert_id/name is explicitly passed. |
| `zpa_update_app_protection_rule` | `zpa_access_policies` | Write | Update a ZPA app-protection (inspection) policy rule (write). |
| `zpa_update_application_segment` | `zpa_app_segments` | Write | Update a ZPA application segment (write). Only provided fields are sent. |
| `zpa_update_application_segment_ba` | `zpa_app_segments` | Write | Update a ZPA browser-access application segment (write). Only provided fields are sent. |
| `zpa_update_application_segment_pra` | `zpa_app_segments` | Write | Update a ZPA privileged-remote-access application segment (write). Only provided fields are sent. |
| `zpa_update_application_server` | `zpa_application_servers` | Write | Update a ZPA application server (write).  Requires `--write-tools`. Only the provided fields are sent. |
| `zpa_update_forwarding_policy_rule` | `zpa_access_policies` | Write | Update a ZPA client forwarding policy rule (write). Requires `--write-tools`. |
| `zpa_update_isolation_policy_rule` | `zpa_access_policies` | Write | Update a ZPA isolation policy rule (write). Requires `--write-tools`. |
| `zpa_update_pra_credential` | `zpa_pra` | Write | Update a ZPA PRA credential (write). credential_type cannot change.  Requires `--write-tools`. Secrets are write-only. |
| `zpa_update_pra_portal` | `zpa_pra` | Write | Update a ZPA PRA portal (write). Requires `--write-tools`. |
| `zpa_update_provisioning_key` | `zpa_provisioning_keys` | Write | Update a ZPA provisioning key (write). Requires `--write-tools`. |
| `zpa_update_segment_group` | `zpa_segment_groups` | Write | Update a ZPA segment group and return the full record (write).  Requires `--write-tools`. Only the provided fields are sent (uses the SDK's v2 update path). |
| `zpa_update_server_group` | `zpa_server_groups` | Write | Update a ZPA server group (write).  Partial update. Requires `--write-tools`. `app_connector_group_ids=[]` is rejected; dynamic_discovery=False requires server_ids be supplied here or already present on the group. |
| `zpa_update_service_edge` | `zpa_service_edge_groups` | Write | Update a ZPA Service Edge (enable/disable, rename). Requires `--write-tools`. |
| `zpa_update_service_edge_group` | `zpa_service_edge_groups` | Write | Update a ZPA service edge group (write).  Requires `--write-tools`. |
| `zpa_update_timeout_policy_rule` | `zpa_access_policies` | Write | Update a ZPA timeout policy rule (write). Requires `--write-tools`. |

---

## ZDX — Digital Experience

27 read-only tools, 4 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zdx_get_alert` | `zdx_alerts` | Read-only | Get one ZDX alert as a curated, agent-facing detail view.  Read-only. Adds the impacted department / location / geolocation scope to the summary fields. |
| `zdx_get_analysis` | `zdx_troubleshooting` | Read-only | Get the status/result of a ZDX score analysis (full record).  Read-only. Returns whether the analysis is still running or its results if complete. Start one with `zdx_start_analysis`. |
| `zdx_get_application` | `zdx_reports` | Read-only | Get the ZDX score for one application, with its most-impacted regions.  Read-only. Returns the headline ZDX score plus the per-region impact breakdown for the `since` HOURS window (default 2h). Use `app_id` from `zdx_list_applications`. |
| `zdx_get_application_metric` | `zdx_reports` | Read-only | Get ZDX performance metrics for one application (time-series).  Read-only. Returns one series per metric (Page Fetch Time, DNS Time, availability), each with its datapoints over the `since` HOURS window (default 2h). Pass `metric_name` to narrow to a single metric. Use `app_id` from `zdx_list_applications`. |
| `zdx_get_application_score_trend` | `zdx_reports` | Read-only | Get the ZDX score trend (over time) for one application.  Read-only. Returns the score-over-time datapoints for the `since` HOURS window (default 2h) so the agent can reason about whether an app's experience is improving or degrading. Use `app_id` from `zdx_list_applications`. |
| `zdx_get_application_user` | `zdx_reports` | Read-only | Get one user's ZDX detail for an application (per-device breakdown).  Read-only. Returns the user's score plus the nested per-device metrics for the `since` HOURS window (default 2h). Use `app_id` from `zdx_list_applications` and `user_id` from `zdx_list_application_users`. |
| `zdx_get_deeptrace_cloudpath` | `zdx_troubleshooting` | Read-only | Get the cloud-path (hop-by-hop network path) captured during a ZDX deep trace (curated, nested JSON). Read-only. |
| `zdx_get_deeptrace_cloudpath_metrics` | `zdx_troubleshooting` | Read-only | Get cloud-path metrics captured during a ZDX deep trace (curated, nested time-series JSON). Read-only. |
| `zdx_get_deeptrace_events` | `zdx_troubleshooting` | Read-only | Get the events captured during a ZDX deep trace (curated, nested JSON with ISO timestamps). Read-only. |
| `zdx_get_deeptrace_health_metrics` | `zdx_troubleshooting` | Read-only | Get device health metrics captured during a ZDX deep trace (curated, nested time-series JSON). Read-only. |
| `zdx_get_deeptrace_webprobe_metrics` | `zdx_troubleshooting` | Read-only | Get web-probe metrics captured during a ZDX deep trace (curated, nested time-series JSON). Read-only. |
| `zdx_get_device` | `zdx_reports` | Read-only | Get one active ZDX device.  Read-only. The ZDX SDK returns a single-element list; the device record is unwrapped and shaped to the identifying fields. |
| `zdx_get_device_deep_trace` | `zdx_troubleshooting` | Read-only | Get one ZDX deep-trace session.  Read-only. The SDK returns a single-element list; the trace record is unwrapped, timestamps ISO-normalized, and shaped to the identity fields. |
| `zdx_get_software_details` | `zdx_software_inventory` | Read-only | Expand one ZDX software key into its per-user/device install rows.  Read-only. Returns the users and devices that have the given `software_key` installed. Obtain the key from `zdx_list_software`. |
| `zdx_get_web_probes` | `zdx_troubleshooting` | Read-only | List web probes for an app on a ZDX device (full records).  Read-only. Call this BEFORE `zdx_start_deeptrace` to obtain the `web_probe_id` the deep-trace payload needs. |
| `zdx_list_alert_affected_devices` | `zdx_alerts` | Read-only | List devices affected by a ZDX alert.  Read-only. Returns one identifying row per affected device. Filter by location/department/geo, location groups, and the `since` HOURS window. |
| `zdx_list_alerts` | `zdx_alerts` | Read-only | List ongoing ZDX alerts.  Read-only. Returns one triage row per ongoing alert (id, rule, severity, type, start time, impacted-device count). Filter by location/department/geo and the `since` HOURS window (max 336h). Use a returned alert `id` with `zdx_get_alert` or `zdx_list_alert_affected_devices`. |
| `zdx_list_application_users` | `zdx_reports` | Read-only | List users/devices that accessed a ZDX application, as curated rows.  Read-only. Returns one triage row per user (id, name, email, ZDX score). Filter by `score_bucket` (poor/okay/good), location/department/geo, and the `since` HOURS window (default 2h). Use a returned `id` with `zdx_get_application_user`. |
| `zdx_list_applications` | `zdx_reports` | Read-only | List active ZDX applications.  Read-only. Returns one row per application (id, name, ZDX score, impact signals). Filter by location/department/geo and the `since` HOURS window. Use a returned `id` with `zdx_get_application`, `zdx_get_application_metric`, or `zdx_list_application_users`. |
| `zdx_list_cloudpath_probes` | `zdx_troubleshooting` | Read-only | List cloud-path probes for an app on a ZDX device (full records).  Read-only. Call this BEFORE `zdx_start_deeptrace` to obtain the `cloudpath_probe_id` the deep-trace payload needs. |
| `zdx_list_deeptrace_top_processes` | `zdx_troubleshooting` | Read-only | List the top processes captured during a ZDX deep trace (full records).  Read-only. Returns the process groups captured during the session — useful for spotting resource-intensive processes impacting performance. |
| `zdx_list_departments` | `zdx_reports` | Read-only | List ZDX departments as curated id/name rows.  Read-only. Use a returned `id` as the `department_id` scope filter on other ZDX tools. `since` is in HOURS (default 2h). |
| `zdx_list_device_deep_traces` | `zdx_troubleshooting` | Read-only | List deep-trace sessions for a ZDX device (full records).  Read-only. Returns one row per trace (id, status, session name, app, ISO timestamps). Use a returned `trace_id` with the deep-trace metric/event tools or `zdx_get_device_deep_trace`. |
| `zdx_list_devices` | `zdx_reports` | Read-only | List active ZDX devices.  Read-only. Returns one identifying row per device (id, hostname, owning user). Filter by email, user ID, MAC/IP, location/department/geo, and the `since` HOURS window. Use a returned device `id` with `zdx_get_device` or the deep-trace / probe tools. |
| `zdx_list_historical_alerts` | `zdx_alerts` | Read-only | List historical (ended) ZDX alerts.  Read-only. Like `zdx_list_alerts` but for alert rules that have an Ended On date. `since` is in HOURS (default 2h, max 14 days = 336h). |
| `zdx_list_locations` | `zdx_reports` | Read-only | List ZDX locations as curated id/name rows.  Read-only. Use a returned `id` as the `location_id` scope filter on other ZDX tools. `since` is in HOURS (default 2h). |
| `zdx_list_software` | `zdx_software_inventory` | Read-only | List the ZDX software inventory.  Read-only. Returns one row per software title (key, name, vendor, version, install/user counts). Filter by location/department/geo/user/device. Use a returned `software_key` with `zdx_get_software_details` to see who has it. |
| `zdx_delete_analysis` | `zdx_troubleshooting` | Write | Stop/delete a running ZDX score analysis (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zdx_delete_deeptrace` | `zdx_troubleshooting` | Write | Delete a ZDX deep-trace session (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `zdx_start_analysis` | `zdx_troubleshooting` | Write | Start a ZDX score analysis on a device/app (write).  Evaluates connectivity and performance metrics over the optional `t0`/`t1` epoch range. Requires `--write-tools`. |
| `zdx_start_deeptrace` | `zdx_troubleshooting` | Write | Start a ZDX deep-trace session (write).  Captures network path, web-probe, health, and event data for troubleshooting. Requires `--write-tools`. Resolve `app_id` / `web_probe_id` / `cloudpath_probe_id` via `zdx_list_applications`, `zdx_get_web_probes`, `zdx_list_cloudpath_probes` first (all INTEGERS). |

---

## ZCC — Client Connector

All 4 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zcc_get_device_otp` | `zcc_devices` | Read-only | Get the OTP bundle for a ZCC device (logout / exit / uninstall / disable OTPs).  Read-only (GET, no tenant mutation) but the returned values ARE sensitive short-lived credentials — treat them like passwords. Requires the device's `udid` (from `zcc_list_devices`). |
| `zcc_list_devices` | `zcc_devices` | Read-only | List ZCC enrolled devices (read-only).  Each row is the full device record — identity, OS, agent version, registration state, assigned `policy_name`, ownership, hardware, VPN/tunnel state, and the enrollment / keep-alive timestamps. Use the returned `udid` with `zcc_get_device_otp`. |
| `zcc_list_forwarding_profiles` | `zcc_forwarding_profiles` | Read-only | List ZCC forwarding profiles (by company). Read-only. |
| `zcc_list_trusted_networks` | `zcc_trusted_networks` | Read-only | List ZCC trusted networks (by company). Read-only. |

---

## ZTW — Workload Segmentation

13 read-only tools, 6 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `ztw_get_discovery_settings` | `ztw` | Read-only | Get ZTW workload-discovery settings (read-only singleton).  Returns the decision-bearing knobs plus the full payload in `settings`. |
| `ztw_list_admins` | `ztw` | Read-only | List ZTW admin users (read-only). |
| `ztw_list_ip_destination_groups` | `ztw` | Read-only | List ZTW IP destination groups.  Use `exclude_type` to omit a group type (e.g. exclude DSTN_FQDN). Read-only. |
| `ztw_list_ip_destination_groups_lite` | `ztw` | Read-only | List ZTW IP destination groups via the lighter SDK endpoint (read-only).  Same records as `ztw_list_ip_destination_groups`; uses the lite endpoint. |
| `ztw_list_ip_groups` | `ztw` | Read-only | List ZTW IP groups.  `search` is a server-side substring match on the group name. Read-only. |
| `ztw_list_ip_groups_lite` | `ztw` | Read-only | List ZTW IP groups via the lighter SDK endpoint (read-only).  Same records as `ztw_list_ip_groups`; uses the lite endpoint. |
| `ztw_list_ip_source_groups` | `ztw` | Read-only | List ZTW IP source groups.  `search` is a server-side substring match on the group name. Read-only. |
| `ztw_list_ip_source_groups_lite` | `ztw` | Read-only | List ZTW IP source groups via the lighter SDK endpoint (read-only).  Same records as `ztw_list_ip_source_groups`; uses the lite endpoint. |
| `ztw_list_network_service_groups` | `ztw` | Read-only | List ZTW network service groups (read-only). |
| `ztw_list_network_services` | `ztw` | Read-only | List ZTW network services.  Optionally filter by `protocol` or `search`. Read-only. |
| `ztw_list_public_account_details` | `ztw` | Read-only | List ZTW public-cloud account details (read-only). |
| `ztw_list_public_cloud_info` | `ztw` | Read-only | List ZTW public-cloud account info (read-only). |
| `ztw_list_roles` | `ztw` | Read-only | List ZTW admin roles (read-only). |
| `ztw_create_ip_destination_group` | `ztw` | Write | Create a ZTW IP destination group (write).  Country names/codes are converted to COUNTRY_XX and are only valid for DSTN_OTHER groups. Requires `--write-tools`. |
| `ztw_create_ip_group` | `ztw` | Write | Create a ZTW IP group (write). Requires `--write-tools`. |
| `ztw_create_ip_source_group` | `ztw` | Write | Create a ZTW IP source group (write). Requires `--write-tools`. |
| `ztw_delete_ip_destination_group` | `ztw` | Write | Delete a ZTW IP destination group (destructive write).  Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `ztw_delete_ip_group` | `ztw` | Write | Delete a ZTW IP group (destructive write). Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |
| `ztw_delete_ip_source_group` | `ztw` | Write | Delete a ZTW IP source group (destructive write). Cannot be undone.  Confirmation required — the first call returns a prompt, not a deletion. Gated by `--write-tools`. |

---

## ZIdentity

All 10 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zid_get_group` | `zid_groups` | Read-only | Get one ZIdentity group by ID. Read-only. |
| `zid_get_group_users` | `zid_groups` | Read-only | List the users that belong to a ZIdentity group, by group ID. Read-only.  Returns lean user summaries (id, login name, display name, primary email) for each member of the group. |
| `zid_get_group_users_by_name` | `zid_groups` | Read-only | List the users in a ZIdentity group resolved by group name. Read-only.  Resolves the group by case-insensitive partial name first, then returns the lean user summaries for the first matching group's members. |
| `zid_get_user` | `zid_users` | Read-only | Get one ZIdentity user by ID. Read-only. |
| `zid_get_user_groups` | `zid_users` | Read-only | List the groups a ZIdentity user belongs to, by user ID. Read-only.  Returns lean group summaries (id, name, description, dynamic flag, source IdP) for each of the user's group memberships. |
| `zid_get_user_groups_by_name` | `zid_users` | Read-only | List a ZIdentity user's group memberships, resolving the user by name.  Read-only. Resolves the user by case-insensitive partial match (email when '@' present, else login then display name), then returns the lean group summaries for the first matching user's memberships. |
| `zid_list_groups` | `zid_groups` | Read-only | List ZIdentity groups.  Read-only. Returns lean group summaries (id, name, description, dynamic flag, source IdP) rather than the full SDK group record. Pass `name` for a case-insensitive partial-name filter. |
| `zid_list_users` | `zid_users` | Read-only | List ZIdentity users. Read-only.  Returns lean user summaries (id, login name, display name, primary email) rather than the full SDK user record. Pass any of the `*_name` / email filters for a case-insensitive partial match. |
| `zid_search_groups` | `zid_groups` | Read-only | Search ZIdentity groups by name (case-insensitive partial match). Read-only.  Returns curated group summaries. An empty result means no group name contains this string — do not retry with split keywords or no filter. |
| `zid_search_users` | `zid_users` | Read-only | Search ZIdentity users by name, login name, or email. Read-only.  Case-insensitive partial match. Values containing '@' match email; otherwise login name then display name are tried. An empty result means no user matches — do not retry with split keywords or no filter. |

---

## EASM — External Attack Surface Management

All 7 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zeasm_get_finding_details` | `zeasm_findings` | Read-only | Get the full detail for one EASM finding.  Read-only. Adds description, country, CISA/EPSS exploitation-likelihood signals, and scan provenance on top of the triage fields. |
| `zeasm_get_finding_evidence` | `zeasm_findings` | Read-only | Get the scan evidence attributed to one EASM finding.  Read-only. Returns the evidence `content` (the subset of scan output attributable to this finding) and its `source_type`. The content can be large free-form scanner text and is preserved verbatim. |
| `zeasm_get_finding_scan_output` | `zeasm_findings` | Read-only | Get the complete scan output for one EASM finding.  Read-only. Returns the full scan `content` and its `source_type`. The content can be large free-form scanner text and is preserved verbatim. |
| `zeasm_get_lookalike_domain` | `zeasm_lookalike_domains` | Read-only | Get full detail for one EASM lookalike domain.  Read-only. Adds description, registrar/registrant + lifecycle dates, and remediation guidance on top of the triage fields. Look the domain up by its `lookalike_raw` name (from `zeasm_list_lookalike_domains`). |
| `zeasm_list_findings` | `zeasm_findings` | Read-only | List EASM findings for an organization.  Read-only. Returns one triage row per finding (id, category, type, status, risk level/score, impacted asset, first/last seen) rather than the raw SDK record. Use the returned `id` with `zeasm_get_finding_details`, `zeasm_get_finding_evidence`, or `zeasm_get_finding_scan_output`. |
| `zeasm_list_lookalike_domains` | `zeasm_lookalike_domains` | Read-only | List EASM lookalike domains for an organization.  Read-only. Returns one triage row per detected lookalike/impersonation domain (the lookalike, the domain it impersonates, risk, registration state, deception methods). Use the returned `lookalike_raw` with `zeasm_get_lookalike_domain` for full detail. |
| `zeasm_list_organizations` | `zeasm` | Read-only | List ZEASM organizations.  Read-only. Returns one row per organization configured in the EASM Admin Portal, carrying just the `id` + `name`. Use the returned `id` as the `org_id` argument for `zeasm_list_findings`, `zeasm_list_lookalike_domains`, and the other EASM tools. |

---

## Z-Insights

All 16 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zins_get_casb_app_report` | `zins_saas` | Read-only | Get the CASB (Cloud Access Security Broker) SaaS-application usage report. Read-only analytics.  One row per SaaS application with its aggregated usage total, for seeing which cloud apps are being accessed. Window must be a 7- or 14-day historical interval. |
| `zins_get_cyber_incidents` | `zins_cyber_security` | Read-only | Get cyber-security incidents grouped by category. Read-only analytics.  Groups incidents by one or more dimensions (default THREAT_CATEGORY_ID); multi-dimension groupings surface their breakdown under nested `entries`. An empty result means no incidents were detected. Window must be a 7- or 14-day historical interval. |
| `zins_get_cyber_incidents_by_location` | `zins_cyber_security` | Read-only | Get cyber-security incidents grouped by location (or app/user/department). Read-only analytics.  One id/name/total row per location (or the chosen id-bearing dimension), useful for ranking which sites carry the most incidents. Window must be a 7- or 14-day historical interval. |
| `zins_get_cyber_incidents_by_threat_and_app` | `zins_cyber_security` | Read-only | Get cyber-security incidents correlated by threat category and application. Read-only analytics.  Groups by THREAT_CATEGORY_ID × APP_ID so each top-level threat-category bucket carries its per-application breakdown under nested `entries` — useful for finding the most-targeted apps. Window must be a 7- or 14-day historical interval. |
| `zins_get_cyber_incidents_daily` | `zins_cyber_security` | Read-only | Get the daily cyber-security incident trend over time. Read-only analytics.  Groups incidents by day (categorize_by=TIME) so you can spot spikes across the window. Window must be a 7- or 14-day historical interval. |
| `zins_get_firewall_by_action` | `zins_firewall` | Read-only | Get Zero Trust Firewall traffic grouped by action (allow/block). Read-only analytics.  One row per action with its aggregated total — the allowed-vs-blocked split. Window must be a 7- or 14-day historical interval. |
| `zins_get_firewall_by_location` | `zins_firewall` | Read-only | Get Zero Trust Firewall traffic grouped by location. Read-only analytics.  One id/name/total row per location, for ranking which sites drive the most firewall traffic. Window must be a 7- or 14-day historical interval. |
| `zins_get_firewall_network_services` | `zins_firewall` | Read-only | Get Zero Trust Firewall traffic grouped by network service. Read-only analytics.  One row per network service (protocol/port) with its aggregated total. Window must be a 7- or 14-day historical interval. |
| `zins_get_iot_device_stats` | `zins_iot` | Read-only | Get IoT device statistics and classifications. Read-only analytics.  A single current-state object: total/IoT/user/server/unclassified device counts plus a per-classification breakdown under `entries`. No time window — this reflects the present network state. An empty/zeroed result means no IoT devices were detected or IoT Device Visibility is not enabled. |
| `zins_get_shadow_it_apps` | `zins_shadow_it` | Read-only | Get discovered Shadow IT applications with risk and usage detail. Read-only analytics.  One row per unsanctioned/discovered app: category, risk index, sanctioned state, data volume, and user count. An empty result means no shadow apps were detected. Window must be a 7- or 14-day historical interval. |
| `zins_get_shadow_it_summary` | `zins_shadow_it` | Read-only | Get the aggregate Shadow IT summary dashboard. Read-only analytics.  A single object with org-wide totals (apps, bytes, upload/download) plus breakdowns grouped by category and by risk index. Window must be a 7- or 14-day historical interval. |
| `zins_get_threat_class` | `zins_web_traffic` | Read-only | Get threat-class distribution (Virus/Spyware, Advanced, Behavioral). Read-only analytics.  One row per threat class with its aggregated total. An empty result means no threats of these classes were detected. Window must be a 7- or 14-day historical interval. |
| `zins_get_threat_super_categories` | `zins_web_traffic` | Read-only | Get threat super-categories (malware, phishing, spyware, …) from web traffic. Read-only analytics.  One row per threat super-category with its aggregated total. An empty result means no threats were detected in the window. Window must be a 7- or 14-day historical interval. |
| `zins_get_web_protocols` | `zins_web_traffic` | Read-only | Get web traffic broken down by protocol (HTTP, HTTPS, SSL, …). Read-only analytics.  One row per protocol with its aggregated total. Window must be a 7- or 14-day historical interval. |
| `zins_get_web_traffic_by_location` | `zins_web_traffic` | Read-only | Get web traffic aggregated per location. Read-only analytics.  Each row is a location with its total transactions or bytes; pass `include_trend=True` for the per-location time-series under `trend`. Window must be a 7- or 14-day historical interval (see the time-window inputs). |
| `zins_get_web_traffic_no_grouping` | `zins_web_traffic` | Read-only | Get overall web traffic volume with no grouping. Read-only analytics.  Returns total organization traffic, optionally filtered by DLP engine or action (ALLOW/BLOCK), and optionally with an overall time-series `trend`. Window must be a 7- or 14-day historical interval. |

---

## ZMS — Microsegmentation

All 20 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zms_get_agent_connection_status_statistics` | `zms` | Read-only | Get ZMS agent connection-status statistics (curated aggregate view).  Read-only. Returns connected vs disconnected counts / percentages for fleet health. Requires ZSCALER_CUSTOMER_ID. |
| `zms_get_agent_group_totp_secrets` | `zms` | Read-only | Get the TOTP secrets for a ZMS agent group (full record).  Read-only API call, but the returned values ARE sensitive enrollment credentials — treat them like secrets. Keyed by `eyez_id`. Requires ZSCALER_CUSTOMER_ID. |
| `zms_get_agent_version_statistics` | `zms` | Read-only | Get ZMS agent version statistics (curated aggregate view).  Read-only. Returns the distribution of agent software versions across the fleet — useful for spotting outdated agents. Requires ZSCALER_CUSTOMER_ID. |
| `zms_get_metadata` | `zms` | Read-only | Get ZMS resource event metadata (full record).  Read-only. Returns metadata about the resource-level events available in the deployment. Requires ZSCALER_CUSTOMER_ID. |
| `zms_get_nonce` | `zms` | Read-only | Get one ZMS nonce.  Read-only. Keyed by `eyez_id`. The payload may carry sensitive enrollment data — handle accordingly. Requires ZSCALER_CUSTOMER_ID. |
| `zms_get_resource_group_members` | `zms` | Read-only | List the members of a ZMS resource group.  Read-only. Returns one row per member workload. Obtain `group_id` from `zms_list_resource_groups`. Requires ZSCALER_CUSTOMER_ID. |
| `zms_get_resource_group_protection_status` | `zms` | Read-only | Get the ZMS resource-group protection-status summary (aggregate view).  Read-only. Returns protected vs unprotected group counts and percentage. Requires ZSCALER_CUSTOMER_ID. |
| `zms_get_resource_protection_status` | `zms` | Read-only | Get the ZMS resource protection-status summary (curated aggregate view).  Read-only. Returns protected vs unprotected counts and protection percentage — microsegmentation coverage at a glance. Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_agent_groups` | `zms` | Read-only | List ZMS agent groups.  Read-only. Returns one row per group (eyez_id, name, type, cloud provider, agent count, policy/tamper status). Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_agents` | `zms` | Read-only | List ZMS microsegmentation agents.  Read-only. Returns one row per agent (eyez_id, name, connection status, version, OS, IP). Requires ZSCALER_CUSTOMER_ID. Use a returned `eyez_id` with the agent-group / nonce tools. |
| `zms_list_app_catalog` | `zms` | Read-only | List the ZMS application catalog.  Read-only. Returns one row per discovered application (id, name, category) plus its nested port/protocol/process specs — useful for policy planning. Filter by name/category, sort by name/category/time. Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_app_zones` | `zms` | Read-only | List ZMS app zones.  Read-only. Returns one row per app zone (id, name, description, resource count). Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_default_policy_rules` | `zms` | Read-only | List ZMS default policy rules.  Read-only. The built-in default rules evaluated when no custom rule matches. Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_nonces` | `zms` | Read-only | List ZMS enrollment nonces.  Read-only. Returns one row per nonce (eyez_id, name, status, expiry). Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_policy_rules` | `zms` | Read-only | List ZMS microsegmentation policy rules.  Read-only. Returns one row per rule (id, name, action, priority, enabled). Filter by name/action. `fetch_all` bypasses pagination — use sparingly. Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_resource_groups` | `zms` | Read-only | List ZMS resource groups.  Read-only. Returns one row per group (id, name, managed/unmanaged type, origin, member count, and CIDRs/FQDNs for unmanaged groups). Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_resources` | `zms` | Read-only | List ZMS resources (workloads).  Read-only. Returns one row per workload (id, name, type, status, cloud provider/region, OS, IPs). Filter by name/status/type/provider/region/OS. Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_tag_keys` | `zms` | Read-only | List ZMS tag keys within a namespace.  Read-only. Middle of the tag hierarchy. Returns one row per key (id, key_name, value count). Obtain `namespace_id` from `zms_list_tag_namespaces`. Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_tag_namespaces` | `zms` | Read-only | List ZMS tag namespaces.  Read-only. Top of the tag hierarchy (namespace -> key -> value). Returns one row per namespace (id, name, origin, key count). Requires ZSCALER_CUSTOMER_ID. |
| `zms_list_tag_values` | `zms` | Read-only | List ZMS tag values for a key.  Read-only. Bottom of the tag hierarchy. Returns one row per value (id, name). Needs the `tag_id` (from `zms_list_tag_keys`) and the `namespace_origin` (CUSTOM / EXTERNAL / ML / UNKNOWN). Requires ZSCALER_CUSTOMER_ID. |

---

## ZCell — Cellular

All 20 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zcell_get_customer_data_handling` | `zcell_customer_data_handling` | Read-only | Get the logged-in Zscaler Cellular customer's profile and SIM totals.  Read-only. Returns the customer record: identity, activation state, platform, configured regions, SIM counts, current usage, and the linked ZIA/ZPA cloud and SIM-provider metadata. Scoped by ZCELL_CUSTOMER_ID. |
| `zcell_get_sim_details` | `zcell_sim_handling` | Read-only | Get the full Zscaler Cellular record for one SIM by ICCID.  Read-only. Returns the identifying, status, and device fields for the SIM (ICCID, IMSI/IMEI, status, network status, APN, IP, device, tags, usage). |
| `zcell_get_sim_location_group` | `zcell_sim_location_groups` | Read-only | Get one Zscaler Cellular SIM location group.  Read-only. Adds the geo-fence definition, linked anomaly policies, and the inside/outside ICCID membership buckets on top of the summary fields. |
| `zcell_list_anomaly_policies` | `zcell_anomaly_policy` | Read-only | List Zscaler Cellular anomaly policies.  Read-only. Returns one row per policy (id, name, type, enabled state, run status, applied SIM location groups, violation count) over a `days` lookback window. Use the returned `id` with the anomaly-policy logs and violations tools. |
| `zcell_list_anomaly_policy_logs` | `zcell_anomaly_policy` | Read-only | List the activity log for one Zscaler Cellular anomaly policy.  Read-only. Returns the enable/disable/run history (status + message + timestamp) for the given `policy_id`. |
| `zcell_list_anomaly_policy_violations` | `zcell_anomaly_policy` | Read-only | List the ICCIDs that violated a Zscaler Cellular anomaly policy.  Read-only. Returns the policy rows carrying violation data over a `days` lookback window. Use `zcell_list_iccid_violations` to drill into the per-event detail for a specific ICCID. |
| `zcell_list_audit_customers_search` | `zcell_audit_data_handling` | Read-only | Search Zscaler Cellular audit-log entries over a lookback window.  Read-only. Returns curated audit rows (who changed what, when, and the operation) over a `days` window, with optional operation/object/visibility filters. The before/after data blobs are omitted from the row. |
| `zcell_list_audit_metadata` | `zcell_audit_data_handling` | Read-only | List the Zscaler Cellular audit filter vocabulary.  Read-only. Returns the valid operation types and object types you can pass to `zcell_list_audit_customers_search`. |
| `zcell_list_iccid_violations` | `zcell_anomaly_policy` | Read-only | List the anomaly-policy violation events for one ICCID.  Read-only. Returns the individual violation events (event type, zone, timestamp) attributed to `iccid` under `policy_id`, over a `days` lookback window. |
| `zcell_list_network_events` | `zcell_network_events` | Read-only | Search Zscaler Cellular network/session events over a lookback window.  Read-only. Returns curated event rows (timestamp, event, outcome, SIM/ICCID, country, carrier, RAT, IP) over a `days` window, with optional `filter_by` conditions, `sort_by`, and pagination. |
| `zcell_list_region_operational_status` | `zcell_customer_region_handling` | Read-only | List Zscaler Cellular configured regions with their operational status.  Read-only. Returns each configured region plus the broker-cluster (BC) and app-connector (AC) status blocks and the MAP A-C / B-C link statuses. |
| `zcell_list_regions` | `zcell_customer_region_handling` | Read-only | List the Zscaler Cellular regions available/configured for the customer.  Read-only. Returns each region and whether it is configured. |
| `zcell_list_sim_analytics_map` | `zcell_sim_analytics` | Read-only | List Zscaler Cellular SIM map points (dashboard lat/lng summary).  Read-only. Returns SIM location points with their ICCIDs, IMSIs, and tags — the data that backs the fleet map. Optionally scope to specific ICCIDs. |
| `zcell_list_sim_analytics_summary` | `zcell_sim_analytics` | Read-only | List the Zscaler Cellular SIM status summary (total/used/active/inactive).  Read-only. Returns the SIM-count breakdown for the tenant. |
| `zcell_list_sim_location_groups` | `zcell_sim_location_groups` | Read-only | List Zscaler Cellular SIM location groups.  Read-only. Returns one row per group (id, name, tracked ICCIDs). Use the returned `id` with `zcell_get_sim_location_group` for the geo-fence and linked-policy detail. |
| `zcell_list_sim_usage_by_country` | `zcell_sim_analytics` | Read-only | List Zscaler Cellular data usage grouped by country (top countries).  Read-only. Returns the top countries by data usage over a `days` lookback window. |
| `zcell_list_sim_usage_by_day` | `zcell_sim_analytics` | Read-only | List Zscaler Cellular data usage per day over the window.  Read-only. Returns one usage bucket per day over a `days` lookback window, optionally scoped to a single ICCID. |
| `zcell_list_sim_usage_by_sim` | `zcell_sim_analytics` | Read-only | List Zscaler Cellular data usage grouped by SIM (top SIMs).  Read-only. Returns the top SIMs by data usage over a `days` lookback window. |
| `zcell_list_sims` | `zcell_sim_handling` | Read-only | Search the Zscaler Cellular SIM inventory with filters and pagination.  Read-only (browses the inventory). Returns a page of curated SIM records plus the aggregate usage/pagination envelope. Filter by ICCID, status, network status, country, tag, device attributes, or IMEI lock status. |
| `zcell_list_tags` | `zcell_tag_handling` | Read-only | List the Zscaler Cellular SIM tags defined for the customer.  Read-only. Returns one row per tag (id, name, provenance). Use the returned tag `id` when assigning tags to SIMs. |

<!-- generated:end tools -->
