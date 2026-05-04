# Supported Tools Reference

The Zscaler Integrations MCP Server provides tools for all major Zscaler services. Each service offers specific functionality for managing and querying Zscaler resources.

> **Note:** All tools marked as "Write" require the `--enable-write-tools` flag and an explicit `--write-tools` allowlist to be enabled. See the [Security & Permissions](https://github.com/zscaler/zscaler-mcp-server#-security--permissions) section in the main README for details.
>
> **This page is auto-generated.** The tables below are rebuilt from the live tool inventory by `zscaler-mcp --generate-docs`. Edit the tool descriptions in `zscaler_mcp/services.py` and re-run the generator — do not edit the generated tables by hand. CI runs `--check-docs` to enforce sync.

<!-- generated:start tools -->

## Table of Contents

- [ZIA — Internet Access](#zia-internet-access)
- [ZPA — Private Access](#zpa-private-access)
- [ZDX — Digital Experience](#zdx-digital-experience)
- [ZCC — Client Connector](#zcc-client-connector)
- [ZTW — Workload Segmentation](#ztw-workload-segmentation)
- [ZIdentity](#zidentity)
- [EASM — External Attack Surface Management](#easm-external-attack-surface-management)
- [Z-Insights](#z-insights)
- [ZMS — Microsegmentation](#zms-microsegmentation)
- [Meta (always loaded)](#meta-always-loaded)

---

## ZIA — Internet Access

74 read-only tools, 71 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `get_zia_dlp_dictionaries` | `zia_dlp` | Read-only | Manage ZIA DLP dictionaries for data loss prevention pattern and phrase matching (read-only) |
| `get_zia_dlp_engines` | `zia_dlp` | Read-only | Manage ZIA DLP engines for data loss prevention rule processing (read-only) |
| `get_zia_user_departments` | `zia_users` | Read-only | Manage ZIA user departments for organizational structure (read-only) |
| `get_zia_user_groups` | `zia_users` | Read-only | Read ZIA user groups for access control and policy assignment. Pass `name="<literal admin-supplied name>"` (e.g. `name="A000"`) for a case-insensitive substring match resolved client-side — this is the right knob for find-by-name workflows. Pass `group_id=` to fetch a single group. The `search` parameter forwards to the ZIA API and is unreliable for name-based lookups; prefer `name`. |
| `get_zia_users` | `zia_users` | Read-only | Manage ZIA users for authentication and access control (read-only) |
| `zia_geo_search` | `zia_locations` | Read-only | Perform ZIA geographic lookups (coordinates, IP, or city prefix) (read-only) |
| `zia_get_activation_status` | `zia_admin` | Read-only | Get ZIA configuration activation status (read-only) |
| `zia_get_cloud_app_control_rule` | `zia_cloud_app_control` | Read-only | Get a specific ZIA Cloud App Control rule by rule_type AND rule_id (read-only). Both arguments are required because the CAC API is category-scoped — rule_id alone is not sufficient. If you only know the app name, call zia_list_cloud_app_control_actions(cloud_app=...) first to discover the rule_type. |
| `zia_get_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Read-only | Get a specific ZIA cloud firewall DNS rule by ID (read-only) |
| `zia_get_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Read-only | Get a specific ZIA cloud firewall IPS rule by ID (read-only) |
| `zia_get_cloud_firewall_rule` | `zia_cloud_firewall` | Read-only | Get a specific ZIA cloud firewall rule by ID (read-only) |
| `zia_get_file_type_control_rule` | `zia_file_type_control` | Read-only | Get a specific ZIA File Type Control rule by ID (read-only) |
| `zia_get_gre_tunnel` | `zia_locations` | Read-only | Get a specific ZIA GRE tunnel by ID (read-only) |
| `zia_get_ip_destination_group` | `zia_cloud_firewall` | Read-only | Get a specific ZIA IP destination group by ID (read-only) |
| `zia_get_ip_source_group` | `zia_cloud_firewall` | Read-only | Get a specific ZIA IP source group by ID (read-only) |
| `zia_get_location` | `zia_locations` | Read-only | Get a specific ZIA location by ID (read-only) |
| `zia_get_location_group` | `zia_locations` | Read-only | Get a specific ZIA location group by ID (read-only) |
| `zia_get_network_app` | `zia_cloud_firewall` | Read-only | Get a specific ZIA network application by ID (read-only) |
| `zia_get_network_app_group` | `zia_cloud_firewall` | Read-only | Get a specific ZIA network application group by ID (read-only) |
| `zia_get_network_service` | `zia_cloud_firewall` | Read-only | Get a specific ZIA network service by ID (read-only) |
| `zia_get_network_svc_group` | `zia_cloud_firewall` | Read-only | Get a specific ZIA network service group by ID (read-only) |
| `zia_get_rule_label` | `zia_admin` | Read-only | Get a specific ZIA rule label by ID (read-only) |
| `zia_get_sandbox_behavioral_analysis` | `zia_sandbox` | Read-only | Retrieve sandbox behavioral analysis hash list (read-only) |
| `zia_get_sandbox_file_hash_count` | `zia_sandbox` | Read-only | Retrieve sandbox file hash usage counts (read-only) |
| `zia_get_sandbox_quota` | `zia_sandbox` | Read-only | Retrieve current ZIA sandbox quota information (read-only) |
| `zia_get_sandbox_report` | `zia_sandbox` | Read-only | Retrieve sandbox analysis report for a specific MD5 hash (read-only) |
| `zia_get_sandbox_rule` | `zia_sandbox` | Read-only | Get a specific ZIA Sandbox rule by ID (read-only) |
| `zia_get_ssl_inspection_rule` | `zia_ssl_inspection` | Read-only | Get a specific ZIA SSL inspection rule by ID (read-only) |
| `zia_get_static_ip` | `zia_locations` | Read-only | Get a specific ZIA static IP by ID (read-only) |
| `zia_get_time_interval` | `zia_time_intervals` | Read-only | Get a specific ZIA Time Interval by ID (read-only). |
| `zia_get_url_category` | `zia_url_categories` | Read-only | Get a specific ZIA URL category by ID (read-only) |
| `zia_get_url_category_predefined` | `zia_url_categories` | Read-only | Get a Zscaler-curated predefined URL category by canonical ID (e.g. 'FINANCE') or display name (e.g. 'Finance'). Case-insensitive. Refuses custom categories — use zia_get_url_category for those (read-only). |
| `zia_get_url_filtering_rule` | `zia_url_filtering` | Read-only | Get a specific ZIA URL filtering rule by ID (read-only) |
| `zia_get_vpn_credential` | `zia_locations` | Read-only | Get a specific ZIA VPN credential by ID (read-only) |
| `zia_get_web_dlp_rule` | `zia_dlp` | Read-only | Get a specific ZIA web DLP rule by ID (read-only) |
| `zia_get_workload_group` | `zia_workload_groups` | Read-only | Get a specific ZIA workload group by ID (read-only) |
| `zia_list_atp_malicious_urls` | `zia_url_categories` | Read-only | List ZIA ATP malicious URLs (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_auth_exempt_urls` | `zia_url_categories` | Read-only | List ZIA authentication exempt URLs (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_cloud_app_control_actions` | `zia_cloud_app_control` | Read-only | List the granular Cloud App Control (CAC) actions available for a cloud application — answers 'what actions can I control for <app>?', 'list actions for Azure DevOps', 'what can I block on Dropbox', 'show me available actions for ChatGPT'. Takes a single cloud_app (canonical enum like AZURE_DEVOPS or friendly name like 'Azure DevOps'); the tool auto-resolves the name, looks up its category (rule type), and returns the category's full action set. Actions are CATEGORY-LEVEL not per-app — every app in SYSTEM_AND_DEVELOPMENT shares the same actions, every app in AI_ML shares its own set, etc. The tool also handles a ZIA API quirk where calling list_available_actions(rule_type, [some_app]) sometimes returns empty because not every app is a 'representative' for its category — when that happens, it transparently walks other apps in the same category until one surfaces the action set. Returns a dict with: cloud_app, resolved_app, category, category_name, actions, actions_surfaced_via (which app finally produced the actions), and probe_attempts. Use the optional rule_type parameter only to override the auto-detected category; use query (JMESPath) to project just the actions list (e.g. 'actions') or filter them (e.g. 'actions[?contains(@, ``BLOCK``)]'). |
| `zia_list_cloud_app_control_rules` | `zia_cloud_app_control` | Read-only | List ZIA Cloud App Control rules for a specific rule_type (category). The CAC API is category-scoped, so rule_type is REQUIRED — pass one of WEBMAIL, STREAMING_MEDIA, FILE_SHARE, AI_ML, SYSTEM_AND_DEVELOPMENT, SOCIAL_NETWORKING, INSTANT_MESSAGING, BUSINESS_PRODUCTIVITY, ENTERPRISE_COLLABORATION, etc. To list across multiple categories, call this once per category. If the user names an app instead of a category, call zia_list_cloud_app_control_actions(cloud_app=...) first to discover the right rule_type. Supports server-side `search` (substring on rule name) and JMESPath client-side filtering via the `query` parameter. |
| `zia_list_cloud_app_policy` | `zia_cloud_app_control` | Read-only | List the ZIA policy-engine cloud-application catalog — canonical enum strings (e.g. ONEDRIVE, ONEDRIVE_PERSONAL, SHAREPOINT_ONLINE) consumed by Web DLP, Cloud App Control, File Type Control, Bandwidth Classes, and Advanced Settings. Use this when you need the exact enum to pass into a policy rule's cloud_applications field. Supports server-side filtering (search, app_class, group_results) and JMESPath via the query parameter. Pass app_class to narrow the catalog by category when the user describes a kind of app instead of a specific one — valid values: SOCIAL_NETWORKING, STREAMING_MEDIA, WEBMAIL, INSTANT_MESSAGING, BUSINESS_PRODUCTIVITY, ENTERPRISE_COLLABORATION, SALES_AND_MARKETING, SYSTEM_AND_DEVELOPMENT, CONSUMER, HOSTING_PROVIDER, IT_SERVICES, FILE_SHARE, DNS_OVER_HTTPS, HUMAN_RESOURCES, LEGAL, HEALTH_CARE, FINANCE, CUSTOM_CAPP, AI_ML. |
| `zia_list_cloud_app_ssl_policy` | `zia_cloud_app_control` | Read-only | List the ZIA cloud-application catalog scoped to SSL Inspection rules — returns the canonical enum strings the SSL Inspection API will accept in the cloud_applications field (e.g. ONEDRIVE, SHAREPOINT_ONLINE). Use this to resolve enum names before creating or updating SSL Inspection rules. Supports server-side filtering (search, app_class, group_results) and JMESPath via the query parameter. Pass app_class to narrow the catalog by category when the user describes a kind of app — valid values: SOCIAL_NETWORKING, STREAMING_MEDIA, WEBMAIL, INSTANT_MESSAGING, BUSINESS_PRODUCTIVITY, ENTERPRISE_COLLABORATION, SALES_AND_MARKETING, SYSTEM_AND_DEVELOPMENT, CONSUMER, HOSTING_PROVIDER, IT_SERVICES, FILE_SHARE, DNS_OVER_HTTPS, HUMAN_RESOURCES, LEGAL, HEALTH_CARE, FINANCE, CUSTOM_CAPP, AI_ML. |
| `zia_list_cloud_firewall_dns_rules` | `zia_cloud_firewall` | Read-only | List ZIA cloud firewall DNS rules (read-only). Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_cloud_firewall_ips_rules` | `zia_cloud_firewall` | Read-only | List ZIA cloud firewall IPS rules (read-only). Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_cloud_firewall_rules` | `zia_cloud_firewall` | Read-only | List ZIA cloud firewall rules with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_device_groups` | `zia_users` | Read-only | List ZIA device groups with optional device info and pseudo group filtering (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_devices` | `zia_users` | Read-only | List ZIA devices with filtering by name, user, pagination support (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_devices_lite` | `zia_users` | Read-only | List ZIA devices in lightweight format (ID, name, owner only) (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_file_type_categories` | `zia_file_type_control` | Read-only | List ZIA file-type categories (predefined and custom) used by File Type Control and Web DLP rules (read-only). |
| `zia_list_file_type_control_rules` | `zia_file_type_control` | Read-only | List ZIA File Type Control rules (read-only). Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_gre_ranges` | `zia_locations` | Read-only | List available ZIA GRE IP ranges (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_gre_tunnels` | `zia_locations` | Read-only | List ZIA GRE tunnels (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_ip_destination_groups` | `zia_cloud_firewall` | Read-only | List ZIA IP destination groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_ip_source_groups` | `zia_cloud_firewall` | Read-only | List ZIA IP source groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_location_groups` | `zia_locations` | Read-only | List ZIA location groups, referenced by ID on the location_groups operand of every ZIA rule resource (Cloud Firewall, DNS, IPS, URL Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox, Cloud App Control). Read-only — the public ZIA API does not expose location group create/update/delete. Supports name/search/group_type filters and JMESPath via the query parameter. |
| `zia_list_locations` | `zia_locations` | Read-only | List ZIA locations (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_network_app_groups` | `zia_cloud_firewall` | Read-only | List ZIA network application groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_network_apps` | `zia_cloud_firewall` | Read-only | List ZIA network applications with optional filtering by search or locale (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_network_services` | `zia_cloud_firewall` | Read-only | List ZIA network services (read-only). Pass `name="<friendly admin-supplied name>"` (e.g. `name="http"`, `name="ftp"`, `name="dns"`) for a case-insensitive substring match resolved client-side — this is the right knob when the admin gives a service name in any casing. ZIA's canonical service names are uppercase enums (`HTTP`, `FTP`, `DNS`, ...), so server-side `search` is case-sensitive and unreliable for friendly inputs. Also supports `protocol` / `locale` filters and JMESPath projection via `query`. |
| `zia_list_network_svc_groups` | `zia_cloud_firewall` | Read-only | List ZIA network service groups with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_rule_labels` | `zia_admin` | Read-only | List ZIA rule labels (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_sandbox_rules` | `zia_sandbox` | Read-only | List ZIA Sandbox rules (read-only). Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_shadow_it_apps` | `zia_shadow_it` | Read-only | List ZIA Shadow IT cloud applications — analytics catalog with numeric IDs and friendly names (e.g. 'Sharepoint Online', id 655377). NOT the policy-engine enum catalog. Use zia_list_cloud_app_policy / zia_list_cloud_app_ssl_policy for the canonical enum strings consumed by SSL inspection / DLP / Cloud App Control rules. Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_shadow_it_custom_tags` | `zia_shadow_it` | Read-only | List ZIA Shadow IT custom tags (read-only). Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_ssl_inspection_rules` | `zia_ssl_inspection` | Read-only | List ZIA SSL inspection rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_static_ips` | `zia_locations` | Read-only | List ZIA static IPs (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_time_intervals` | `zia_time_intervals` | Read-only | List ZIA Time Intervals (recurring time-of-day / day-of-week schedules referenced by policy rules via the time_windows field). Read-only. Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_url_categories` | `zia_url_categories` | Read-only | List ZIA URL categories (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_url_filtering_rules` | `zia_url_filtering` | Read-only | List ZIA URL filtering rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_vpn_credentials` | `zia_locations` | Read-only | List ZIA VPN credentials (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_web_dlp_rules` | `zia_dlp` | Read-only | List ZIA web DLP rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_web_dlp_rules_lite` | `zia_dlp` | Read-only | List ZIA web DLP rules in lite format (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zia_list_workload_groups` | `zia_workload_groups` | Read-only | List ZIA workload groups, referenced by ID on the workload_groups operand of Cloud Firewall, URL Filtering, SSL Inspection, and Web DLP rules. Read-only — workload group authoring (with its expression DSL) is intentionally left to the ZIA UI. The ZIA list endpoint has no server-side name filter; pair with JMESPath query (e.g. "[?name=='WG-AWS-Prod']") to look up a group by name. |
| `zia_url_lookup` | `zia_url_categories` | Read-only | Look up URL category for given URLs (read-only) |
| `zia_activate_configuration` | `zia_admin` | Write | Activate ZIA configuration changes (write operation) |
| `zia_add_atp_malicious_urls` | `zia_url_categories` | Write | Add URLs to ZIA ATP malicious URL list (write operation) |
| `zia_add_auth_exempt_urls` | `zia_url_categories` | Write | Add URLs to ZIA authentication exempt list (write operation) |
| `zia_add_urls_to_category` | `zia_url_categories` | Write | Add URLs to a ZIA URL category (write operation) |
| `zia_bulk_update_shadow_it_apps` | `zia_shadow_it` | Write | Bulk update sanction state and/or custom tags on ZIA Shadow IT cloud applications (write operation). |
| `zia_create_cloud_app_control_rule` | `zia_cloud_app_control` | Write | Create a new ZIA Cloud App Control (CAC) rule (write operation). The CAC API is category-scoped — rule_type is REQUIRED (e.g. WEBMAIL, FILE_SHARE, AI_ML, SYSTEM_AND_DEVELOPMENT). Workflow: first call zia_list_cloud_app_control_actions(cloud_app=<app>) to discover both the correct rule_type (returned as `category`) AND the valid `actions` enums for that app, then pass those into this tool together with `name`, `cloud_applications`, and any scoping fields (groups, departments, locations, etc.). Friendly cloud-application names like 'Dropbox' are auto-resolved to canonical enums (DROPBOX). Note: the SDK kwarg for the apps list is `applications` but this tool surfaces it as `cloud_applications` for consistency with other ZIA rule families. |
| `zia_create_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Write | Create a new ZIA cloud firewall DNS rule (write operation). The `applications` field accepts the same canonical ZIA cloud-app names used by SSL Inspection / Web DLP / FTC / CAC in their `cloud_applications` field — DNS just exposes the field as `applications`. Friendly names (e.g. "OneDrive", "Cloudflare DoH") are auto-resolved. |
| `zia_create_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Write | Create a new ZIA cloud firewall IPS rule (write operation) |
| `zia_create_cloud_firewall_rule` | `zia_cloud_firewall` | Write | Create a new ZIA cloud firewall rule (write operation) |
| `zia_create_file_type_control_rule` | `zia_file_type_control` | Write | Create a new ZIA File Type Control rule (write operation). Friendly cloud-application names are auto-resolved to canonical enums. |
| `zia_create_gre_tunnel` | `zia_locations` | Write | Create a new ZIA GRE tunnel (write operation) |
| `zia_create_ip_destination_group` | `zia_cloud_firewall` | Write | Create a new ZIA IP destination group (write operation) |
| `zia_create_ip_source_group` | `zia_cloud_firewall` | Write | Create a new ZIA IP source group (write operation) |
| `zia_create_location` | `zia_locations` | Write | Create a new ZIA location (write operation) |
| `zia_create_network_app_group` | `zia_cloud_firewall` | Write | Create a new ZIA network application group (write operation) |
| `zia_create_network_service` | `zia_cloud_firewall` | Write | Create a new ZIA network service with custom TCP/UDP ports (write operation) |
| `zia_create_network_svc_group` | `zia_cloud_firewall` | Write | Create a new ZIA network service group (write operation) |
| `zia_create_rule_label` | `zia_admin` | Write | Create a new ZIA rule label (write operation) |
| `zia_create_sandbox_rule` | `zia_sandbox` | Write | Create a new ZIA Sandbox rule (write operation) |
| `zia_create_ssl_inspection_rule` | `zia_ssl_inspection` | Write | Create a new ZIA SSL inspection rule (write operation) |
| `zia_create_static_ip` | `zia_locations` | Write | Create a new ZIA static IP (write operation) |
| `zia_create_time_interval` | `zia_time_intervals` | Write | Create a new ZIA Time Interval (reusable schedule referenced by policy rules via the time_windows field). start_time/end_time are minutes from midnight (0-1439). days_of_week accepts EVERYDAY, SUN, MON, TUE, WED, THU, FRI, SAT. |
| `zia_create_url_category` | `zia_url_categories` | Write | Create a new ZIA URL category (write operation) |
| `zia_create_url_filtering_rule` | `zia_url_filtering` | Write | Create a new ZIA URL filtering rule (write operation) |
| `zia_create_vpn_credential` | `zia_locations` | Write | Create a new ZIA VPN credential (write operation) |
| `zia_create_web_dlp_rule` | `zia_dlp` | Write | Create a new ZIA web DLP rule (write operation) |
| `zia_delete_atp_malicious_urls` | `zia_url_categories` | Write | Delete URLs from ZIA ATP malicious URL list (destructive operation) |
| `zia_delete_auth_exempt_urls` | `zia_url_categories` | Write | Delete URLs from ZIA authentication exempt list (destructive operation) |
| `zia_delete_cloud_app_control_rule` | `zia_cloud_app_control` | Write | Delete a ZIA Cloud App Control (CAC) rule by rule_type and rule_id (destructive operation). Both arguments are required because the CAC API is category-scoped. Requires HMAC confirmation token. |
| `zia_delete_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Write | Delete a ZIA cloud firewall DNS rule (destructive operation) |
| `zia_delete_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Write | Delete a ZIA cloud firewall IPS rule (destructive operation) |
| `zia_delete_cloud_firewall_rule` | `zia_cloud_firewall` | Write | Delete a ZIA cloud firewall rule (destructive operation) |
| `zia_delete_file_type_control_rule` | `zia_file_type_control` | Write | Delete a ZIA File Type Control rule (destructive operation) |
| `zia_delete_gre_tunnel` | `zia_locations` | Write | Delete a ZIA GRE tunnel (destructive operation) |
| `zia_delete_ip_destination_group` | `zia_cloud_firewall` | Write | Delete a ZIA IP destination group (destructive operation) |
| `zia_delete_ip_source_group` | `zia_cloud_firewall` | Write | Delete a ZIA IP source group (destructive operation) |
| `zia_delete_location` | `zia_locations` | Write | Delete a ZIA location (destructive operation) |
| `zia_delete_network_app_group` | `zia_cloud_firewall` | Write | Delete a ZIA network application group (destructive operation) |
| `zia_delete_network_service` | `zia_cloud_firewall` | Write | Delete a ZIA network service (destructive operation) |
| `zia_delete_network_svc_group` | `zia_cloud_firewall` | Write | Delete a ZIA network service group (destructive operation) |
| `zia_delete_rule_label` | `zia_admin` | Write | Delete a ZIA rule label (destructive operation) |
| `zia_delete_sandbox_rule` | `zia_sandbox` | Write | Delete a ZIA Sandbox rule (destructive operation) |
| `zia_delete_ssl_inspection_rule` | `zia_ssl_inspection` | Write | Delete a ZIA SSL inspection rule (destructive operation) |
| `zia_delete_static_ip` | `zia_locations` | Write | Delete a ZIA static IP (destructive operation) |
| `zia_delete_time_interval` | `zia_time_intervals` | Write | Delete a ZIA Time Interval (destructive operation). Will fail if the Time Interval is currently referenced by any policy rule. |
| `zia_delete_url_category` | `zia_url_categories` | Write | Delete a custom ZIA URL category (destructive operation). Refuses predefined categories — those are Zscaler-curated and cannot be deleted via the API. |
| `zia_delete_url_filtering_rule` | `zia_url_filtering` | Write | Delete a ZIA URL filtering rule (destructive operation) |
| `zia_delete_vpn_credential` | `zia_locations` | Write | Delete a ZIA VPN credential (destructive operation) |
| `zia_delete_web_dlp_rule` | `zia_dlp` | Write | Delete a ZIA web DLP rule (destructive operation) |
| `zia_remove_urls_from_category` | `zia_url_categories` | Write | Remove URLs from a ZIA URL category (write operation) |
| `zia_update_cloud_app_control_rule` | `zia_cloud_app_control` | Write | Update an existing ZIA Cloud App Control (CAC) rule (write operation). Both rule_type AND rule_id are required (the CAC API is category-scoped). Update is a PUT under the hood — `name` is silently backfilled from the existing rule when not supplied so partial updates work safely. Friendly cloud-application names are auto-resolved to canonical enums. |
| `zia_update_cloud_firewall_dns_rule` | `zia_cloud_firewall` | Write | Update an existing ZIA cloud firewall DNS rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied. The `applications` field accepts canonical ZIA cloud-app names (same catalog as SSL/DLP/FTC/CAC's `cloud_applications`) and auto-resolves friendly names. |
| `zia_update_cloud_firewall_ips_rule` | `zia_cloud_firewall` | Write | Update an existing ZIA cloud firewall IPS rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied. |
| `zia_update_cloud_firewall_rule` | `zia_cloud_firewall` | Write | Update an existing ZIA cloud firewall rule (write operation) |
| `zia_update_file_type_control_rule` | `zia_file_type_control` | Write | Update an existing ZIA File Type Control rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied. Friendly cloud-application names are auto-resolved. |
| `zia_update_ip_destination_group` | `zia_cloud_firewall` | Write | Update an existing ZIA IP destination group (write operation) |
| `zia_update_ip_source_group` | `zia_cloud_firewall` | Write | Update an existing ZIA IP source group (write operation) |
| `zia_update_location` | `zia_locations` | Write | Update an existing ZIA location (write operation) |
| `zia_update_network_app_group` | `zia_cloud_firewall` | Write | Update an existing ZIA network application group (write operation) |
| `zia_update_network_service` | `zia_cloud_firewall` | Write | Update an existing ZIA network service (write operation) |
| `zia_update_network_svc_group` | `zia_cloud_firewall` | Write | Update an existing ZIA network service group (write operation) |
| `zia_update_rule_label` | `zia_admin` | Write | Update an existing ZIA rule label (write operation) |
| `zia_update_sandbox_rule` | `zia_sandbox` | Write | Update an existing ZIA Sandbox rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied. |
| `zia_update_ssl_inspection_rule` | `zia_ssl_inspection` | Write | Update an existing ZIA SSL inspection rule (write operation) |
| `zia_update_static_ip` | `zia_locations` | Write | Update an existing ZIA static IP (write operation) |
| `zia_update_time_interval` | `zia_time_intervals` | Write | Update an existing ZIA Time Interval (write operation). Update is a PUT — name, start_time, end_time, and days_of_week are silently backfilled from the existing record when not supplied. |
| `zia_update_url_category` | `zia_url_categories` | Write | Update an existing custom ZIA URL category (full PUT, write operation). Refuses predefined categories — use zia_update_url_category_predefined for those, or zia_add_urls_to_category / zia_remove_urls_from_category for incremental URL/IP-range changes. |
| `zia_update_url_category_predefined` | `zia_url_categories` | Write | Update a Zscaler-curated predefined URL category (full PUT, write operation). Same field surface as zia_update_url_category. Resolves the category by canonical ID ('FINANCE') or display name ('Finance') and silently backfills configured_name from the existing category when omitted. For incremental URL/IP-range mutations prefer zia_add_urls_to_category / zia_remove_urls_from_category — both work on predefined IDs. |
| `zia_update_url_filtering_rule` | `zia_url_filtering` | Write | Update an existing ZIA URL filtering rule (write operation) |
| `zia_update_vpn_credential` | `zia_locations` | Write | Update an existing ZIA VPN credential (write operation) |
| `zia_update_web_dlp_rule` | `zia_dlp` | Write | Update an existing ZIA web DLP rule (write operation) |

---

## ZPA — Private Access

41 read-only tools, 47 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `get_zpa_app_protection_profile` | `zpa_misc` | Read-only | Manage ZPA App Protection Profiles (Inspection Profiles) (read-only) |
| `get_zpa_app_segments_by_type` | `zpa_app_segments` | Read-only | Manage ZPA application segments by type (read-only) |
| `get_zpa_enrollment_certificate` | `zpa_connectors` | Read-only | Manage ZPA Enrollment Certificates (read-only) |
| `get_zpa_isolation_profile` | `zpa_idp` | Read-only | Manage ZPA Cloud Browser Isolation (CBI) profiles (read-only) |
| `get_zpa_posture_profile` | `zpa_idp` | Read-only | Manage ZPA Posture Profiles (read-only) |
| `get_zpa_saml_attribute` | `zpa_idp` | Read-only | Manage ZPA SAML Attributes (read-only) |
| `get_zpa_scim_attribute` | `zpa_idp` | Read-only | Manage ZPA SCIM Attributes (read-only) |
| `get_zpa_scim_group` | `zpa_idp` | Read-only | Manage ZPA SCIM Groups (read-only) |
| `get_zpa_trusted_network` | `zpa_idp` | Read-only | Manage ZPA Trusted Networks (read-only) |
| `zpa_get_access_policy_rule` | `zpa_policy` | Read-only | Get a specific ZPA access policy rule by ID (read-only) |
| `zpa_get_app_connector` | `zpa_connectors` | Read-only | Get a specific ZPA app connector by ID with runtime status and control connection state (read-only) |
| `zpa_get_app_connector_group` | `zpa_connectors` | Read-only | Get a specific ZPA App Connector Group by ID (read-only). Returns the full record including the enrollmentCertId, server-group memberships, and connector membership. |
| `zpa_get_app_protection_rule` | `zpa_policy` | Read-only | Get a specific ZPA app protection rule by ID (read-only) |
| `zpa_get_application_segment` | `zpa_app_segments` | Read-only | Get a specific ZPA application segment by ID (read-only) |
| `zpa_get_application_server` | `zpa_misc` | Read-only | Get a specific ZPA application server by ID (read-only) |
| `zpa_get_ba_certificate` | `zpa_misc` | Read-only | Get a specific ZPA browser access certificate by ID (read-only) |
| `zpa_get_forwarding_policy_rule` | `zpa_policy` | Read-only | Get a specific ZPA forwarding policy rule by ID (read-only) |
| `zpa_get_isolation_policy_rule` | `zpa_policy` | Read-only | Get a specific ZPA isolation policy rule by ID (read-only) |
| `zpa_get_pra_credential` | `zpa_misc` | Read-only | Get a specific ZPA PRA credential by ID (read-only) |
| `zpa_get_pra_portal` | `zpa_misc` | Read-only | Get a specific ZPA PRA portal by ID (read-only) |
| `zpa_get_provisioning_key` | `zpa_connectors` | Read-only | Get a specific ZPA provisioning key by ID (read-only) |
| `zpa_get_segment_group` | `zpa_app_segments` | Read-only | Get a specific ZPA segment group by ID (read-only) |
| `zpa_get_server_group` | `zpa_app_segments` | Read-only | Get a specific ZPA server group by ID (read-only) |
| `zpa_get_service_edge_group` | `zpa_connectors` | Read-only | Get a specific ZPA service edge group by ID (read-only) |
| `zpa_get_timeout_policy_rule` | `zpa_policy` | Read-only | Get a specific ZPA timeout policy rule by ID (read-only) |
| `zpa_list_access_policy_rules` | `zpa_policy` | Read-only | List ZPA access policy rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_app_connector_groups` | `zpa_connectors` | Read-only | List ZPA App Connector Groups (read-only). Returns every connector group in the tenant — id, name, location, country, enrollment cert, server-group memberships. Use this to discover existing connector groups before creating server groups (which require an app_connector_group_id) or before onboarding an application. Supports name search and JMESPath client-side filtering via the query parameter. |
| `zpa_list_app_connectors` | `zpa_connectors` | Read-only | List ZPA app connectors with status, version, and health information (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_app_protection_rules` | `zpa_policy` | Read-only | List ZPA app protection rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_application_segments` | `zpa_app_segments` | Read-only | List ZPA application segments with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_application_servers` | `zpa_misc` | Read-only | List ZPA application servers (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_ba_certificates` | `zpa_misc` | Read-only | List ZPA browser access certificates (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_forwarding_policy_rules` | `zpa_policy` | Read-only | List ZPA forwarding policy rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_isolation_policy_rules` | `zpa_policy` | Read-only | List ZPA isolation policy rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_pra_credentials` | `zpa_misc` | Read-only | List ZPA PRA credentials (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_pra_portals` | `zpa_misc` | Read-only | List ZPA PRA portals (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_provisioning_keys` | `zpa_connectors` | Read-only | List ZPA provisioning keys (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_segment_groups` | `zpa_app_segments` | Read-only | List ZPA segment groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_server_groups` | `zpa_app_segments` | Read-only | List ZPA server groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_service_edge_groups` | `zpa_connectors` | Read-only | List ZPA service edge groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_list_timeout_policy_rules` | `zpa_policy` | Read-only | List ZPA timeout policy rules (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zpa_bulk_delete_app_connectors` | `zpa_connectors` | Write | Bulk delete multiple ZPA app connectors (destructive operation) |
| `zpa_create_access_policy_rule` | `zpa_policy` | Write | Create a new ZPA access policy rule (write operation) |
| `zpa_create_app_connector_group` | `zpa_connectors` | Write | Create a new ZPA app connector group (write operation) |
| `zpa_create_app_protection_rule` | `zpa_policy` | Write | Create a new ZPA app protection rule (write operation) |
| `zpa_create_application_segment` | `zpa_app_segments` | Write | Create a new ZPA application segment (write operation) |
| `zpa_create_application_server` | `zpa_misc` | Write | Create a new ZPA application server (write operation) |
| `zpa_create_ba_certificate` | `zpa_misc` | Write | Create a new ZPA browser access certificate (write operation) |
| `zpa_create_forwarding_policy_rule` | `zpa_policy` | Write | Create a new ZPA forwarding policy rule (write operation) |
| `zpa_create_isolation_policy_rule` | `zpa_policy` | Write | Create a new ZPA isolation policy rule (write operation) |
| `zpa_create_pra_credential` | `zpa_misc` | Write | Create a new ZPA PRA credential (write operation) |
| `zpa_create_pra_portal` | `zpa_misc` | Write | Create a new ZPA PRA portal (write operation) |
| `zpa_create_provisioning_key` | `zpa_connectors` | Write | Create a new ZPA provisioning key (write operation) |
| `zpa_create_segment_group` | `zpa_app_segments` | Write | Create a new ZPA segment group (write operation) |
| `zpa_create_server_group` | `zpa_app_segments` | Write | Create a new ZPA server group (write operation) |
| `zpa_create_service_edge_group` | `zpa_connectors` | Write | Create a new ZPA service edge group (write operation) |
| `zpa_create_timeout_policy_rule` | `zpa_policy` | Write | Create a new ZPA timeout policy rule (write operation) |
| `zpa_delete_access_policy_rule` | `zpa_policy` | Write | Delete a ZPA access policy rule (destructive operation) |
| `zpa_delete_app_connector` | `zpa_connectors` | Write | Delete a ZPA app connector (destructive operation) |
| `zpa_delete_app_connector_group` | `zpa_connectors` | Write | Delete a ZPA app connector group (destructive operation) |
| `zpa_delete_app_protection_rule` | `zpa_policy` | Write | Delete a ZPA app protection rule (destructive operation) |
| `zpa_delete_application_segment` | `zpa_app_segments` | Write | Delete a ZPA application segment (destructive operation) |
| `zpa_delete_application_server` | `zpa_misc` | Write | Delete a ZPA application server (destructive operation) |
| `zpa_delete_ba_certificate` | `zpa_misc` | Write | Delete a ZPA browser access certificate (destructive operation) |
| `zpa_delete_forwarding_policy_rule` | `zpa_policy` | Write | Delete a ZPA forwarding policy rule (destructive operation) |
| `zpa_delete_isolation_policy_rule` | `zpa_policy` | Write | Delete a ZPA isolation policy rule (destructive operation) |
| `zpa_delete_pra_credential` | `zpa_misc` | Write | Delete a ZPA PRA credential (destructive operation) |
| `zpa_delete_pra_portal` | `zpa_misc` | Write | Delete a ZPA PRA portal (destructive operation) |
| `zpa_delete_provisioning_key` | `zpa_connectors` | Write | Delete a ZPA provisioning key (destructive operation) |
| `zpa_delete_segment_group` | `zpa_app_segments` | Write | Delete a ZPA segment group (destructive operation) |
| `zpa_delete_server_group` | `zpa_app_segments` | Write | Delete a ZPA server group (destructive operation) |
| `zpa_delete_service_edge_group` | `zpa_connectors` | Write | Delete a ZPA service edge group (destructive operation) |
| `zpa_delete_timeout_policy_rule` | `zpa_policy` | Write | Delete a ZPA timeout policy rule (destructive operation) |
| `zpa_update_access_policy_rule` | `zpa_policy` | Write | Update an existing ZPA access policy rule (write operation) |
| `zpa_update_app_connector` | `zpa_connectors` | Write | Update a ZPA app connector (enable/disable, rename) (write operation) |
| `zpa_update_app_connector_group` | `zpa_connectors` | Write | Update an existing ZPA app connector group (write operation) |
| `zpa_update_app_protection_rule` | `zpa_policy` | Write | Update an existing ZPA app protection rule (write operation) |
| `zpa_update_application_segment` | `zpa_app_segments` | Write | Update an existing ZPA application segment (write operation) |
| `zpa_update_application_server` | `zpa_misc` | Write | Update an existing ZPA application server (write operation) |
| `zpa_update_forwarding_policy_rule` | `zpa_policy` | Write | Update an existing ZPA forwarding policy rule (write operation) |
| `zpa_update_isolation_policy_rule` | `zpa_policy` | Write | Update an existing ZPA isolation policy rule (write operation) |
| `zpa_update_pra_credential` | `zpa_misc` | Write | Update an existing ZPA PRA credential (write operation) |
| `zpa_update_pra_portal` | `zpa_misc` | Write | Update an existing ZPA PRA portal (write operation) |
| `zpa_update_provisioning_key` | `zpa_connectors` | Write | Update an existing ZPA provisioning key (write operation) |
| `zpa_update_segment_group` | `zpa_app_segments` | Write | Update an existing ZPA segment group (write operation) |
| `zpa_update_server_group` | `zpa_app_segments` | Write | Update an existing ZPA server group (write operation) |
| `zpa_update_service_edge_group` | `zpa_connectors` | Write | Update an existing ZPA service edge group (write operation) |
| `zpa_update_timeout_policy_rule` | `zpa_policy` | Write | Update an existing ZPA timeout policy rule (write operation) |

---

## ZDX — Digital Experience

27 read-only tools, 4 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zdx_get_alert` | `zdx` | Read-only | Get a specific ZDX alert by ID (read-only) |
| `zdx_get_analysis` | `zdx` | Read-only | Get status of a ZDX score analysis (read-only) |
| `zdx_get_application` | `zdx` | Read-only | Get ZDX application details (read-only) |
| `zdx_get_application_metric` | `zdx` | Read-only | Get ZDX metrics for a specified application (read-only) |
| `zdx_get_application_score_trend` | `zdx` | Read-only | Get ZDX application score trend (read-only) |
| `zdx_get_application_user` | `zdx` | Read-only | Get a specific ZDX application user (read-only) |
| `zdx_get_deeptrace_cloudpath` | `zdx` | Read-only | Get cloud path topology from a ZDX deep trace session (read-only) |
| `zdx_get_deeptrace_cloudpath_metrics` | `zdx` | Read-only | Get cloud path metrics from a ZDX deep trace session (read-only) |
| `zdx_get_deeptrace_events` | `zdx` | Read-only | Get events from a ZDX deep trace session (read-only) |
| `zdx_get_deeptrace_health_metrics` | `zdx` | Read-only | Get health metrics from a ZDX deep trace session (read-only) |
| `zdx_get_deeptrace_webprobe_metrics` | `zdx` | Read-only | Get web probe metrics from a ZDX deep trace session (read-only) |
| `zdx_get_device` | `zdx` | Read-only | Get a specific ZDX device by ID (read-only) |
| `zdx_get_device_deep_trace` | `zdx` | Read-only | Get a specific ZDX deep trace by ID (read-only) |
| `zdx_get_software_details` | `zdx` | Read-only | Get details for specific ZDX software (read-only) |
| `zdx_get_web_probes` | `zdx` | Read-only | Get web probes for an app on a device - returns web_probe_id needed for zdx_start_deeptrace (read-only) |
| `zdx_list_alert_affected_devices` | `zdx` | Read-only | List devices affected by a ZDX alert (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_alerts` | `zdx` | Read-only | List ZDX alerts (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_application_users` | `zdx` | Read-only | List users for a ZDX application (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_applications` | `zdx` | Read-only | List ZDX applications (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_cloudpath_probes` | `zdx` | Read-only | List cloud path probes for an app on a device - returns cloudpath_probe_id needed for zdx_start_deeptrace (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_deeptrace_top_processes` | `zdx` | Read-only | Get top processes from a ZDX deep trace session (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_departments` | `zdx` | Read-only | List ZDX departments (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_device_deep_traces` | `zdx` | Read-only | List ZDX deep traces for a device (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_devices` | `zdx` | Read-only | List ZDX devices with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_historical_alerts` | `zdx` | Read-only | List ZDX historical alerts (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_locations` | `zia_locations` | Read-only | List ZDX locations (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_list_software` | `zdx` | Read-only | List ZDX software inventory (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zdx_delete_analysis` | `zdx` | Write | Stop a running ZDX score analysis (destructive operation) |
| `zdx_delete_deeptrace` | `zdx` | Write | Delete a ZDX deep trace session (destructive operation) |
| `zdx_start_analysis` | `zdx` | Write | Start a ZDX score analysis on a device (write operation) |
| `zdx_start_deeptrace` | `zdx` | Write | Start a deep trace for a ZDX device (write operation) |

---

## ZCC — Client Connector

All 3 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zcc_list_devices` | `zcc` | Read-only | Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zcc_list_forwarding_profiles` | `zcc` | Read-only | Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zcc_list_trusted_networks` | `zcc` | Read-only | Returns the list of Trusted Networks By Company ID in the Client Connector Portal (read-only) Supports JMESPath client-side filtering via the query parameter. |

---

## ZTW — Workload Segmentation

13 read-only tools, 6 write tools.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `ztw_get_discovery_settings` | `ztw` | Read-only | Get ZTW workload discovery service settings (read-only) |
| `ztw_list_admins` | `ztw` | Read-only | List all existing admin users in ZTW (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_ip_destination_groups` | `zia_cloud_firewall` | Read-only | List ZTW IP destination groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_ip_destination_groups_lite` | `zia_cloud_firewall` | Read-only | List ZTW IP destination groups in lite format (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_ip_groups` | `ztw` | Read-only | List ZTW IP groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_ip_groups_lite` | `ztw` | Read-only | List ZTW IP groups in lite format (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_ip_source_groups` | `zia_cloud_firewall` | Read-only | List ZTW IP source groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_ip_source_groups_lite` | `zia_cloud_firewall` | Read-only | List ZTW IP source groups in lite format (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_network_service_groups` | `zia_cloud_firewall` | Read-only | List ZTW network service groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_network_services` | `zia_cloud_firewall` | Read-only | List ZTW network services (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_public_account_details` | `ztw` | Read-only | List detailed ZTW public cloud account information (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_public_cloud_info` | `ztw` | Read-only | List ZTW public cloud accounts with metadata (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_list_roles` | `ztw` | Read-only | List all existing admin roles in ZTW (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `ztw_create_ip_destination_group` | `zia_cloud_firewall` | Write | Create a new ZTW IP destination group (write operation) |
| `ztw_create_ip_group` | `ztw` | Write | Create a new ZTW IP group (write operation) |
| `ztw_create_ip_source_group` | `zia_cloud_firewall` | Write | Create a new ZTW IP source group (write operation) |
| `ztw_delete_ip_destination_group` | `zia_cloud_firewall` | Write | Delete a ZTW IP destination group (destructive operation) |
| `ztw_delete_ip_group` | `ztw` | Write | Delete a ZTW IP group (destructive operation) |
| `ztw_delete_ip_source_group` | `zia_cloud_firewall` | Write | Delete a ZTW IP source group (destructive operation) |

---

## ZIdentity

All 10 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zid_get_group` | `zid` | Read-only | Get a specific ZIdentity group by ID (read-only) |
| `zid_get_group_users` | `zid` | Read-only | Get users in a ZIdentity group (read-only) |
| `zid_get_group_users_by_name` | `zid` | Read-only | Get users in a ZIdentity group by group name (read-only) |
| `zid_get_user` | `zid` | Read-only | Get a specific ZIdentity user by ID (read-only) |
| `zid_get_user_groups` | `zid` | Read-only | Get groups for a ZIdentity user (read-only) |
| `zid_get_user_groups_by_name` | `zid` | Read-only | Get groups for a ZIdentity user by username (read-only) |
| `zid_list_groups` | `zid` | Read-only | List ZIdentity groups (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zid_list_users` | `zid` | Read-only | List ZIdentity users (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zid_search_groups` | `zid` | Read-only | Search ZIdentity groups (read-only) |
| `zid_search_users` | `zid` | Read-only | Search ZIdentity users (read-only) |

---

## EASM — External Attack Surface Management

All 7 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zeasm_get_finding_details` | `zeasm` | Read-only | Get details for a specific EASM finding (read-only) |
| `zeasm_get_finding_evidence` | `zeasm` | Read-only | Get scan evidence for a specific EASM finding (read-only) |
| `zeasm_get_finding_scan_output` | `zeasm` | Read-only | Get complete scan output for a specific EASM finding (read-only) |
| `zeasm_get_lookalike_domain` | `zeasm` | Read-only | Get details for a specific lookalike domain (read-only) |
| `zeasm_list_findings` | `zeasm` | Read-only | List all EASM findings for an organization (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zeasm_list_lookalike_domains` | `zeasm` | Read-only | List all lookalike domains detected for an organization (read-only) Supports JMESPath client-side filtering via the query parameter. |
| `zeasm_list_organizations` | `zeasm` | Read-only | List all EASM organizations configured for the tenant (read-only) Supports JMESPath client-side filtering via the query parameter. |

---

## Z-Insights

All 16 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zins_get_casb_app_report` | `zins` | Read-only | Provides CASB SaaS application usage analytics, including cloud app usage and cloud service adoption metrics. |
| `zins_get_cyber_incidents` | `zins` | Read-only | Provides cybersecurity incidents grouped by category, including security events, cyber attacks, and incident breakdowns. |
| `zins_get_cyber_incidents_by_location` | `zia_locations` | Read-only | Provides cybersecurity incidents grouped by location, showing incident distribution across offices and sites. |
| `zins_get_cyber_incidents_by_threat_and_app` | `zins` | Read-only | Provides cybersecurity incidents correlated by threat type and application, showing which apps are targeted and threat-application relationships. |
| `zins_get_cyber_incidents_daily` | `zins` | Read-only | Provides daily cybersecurity incident trends, showing incident patterns and security statistics over time. |
| `zins_get_firewall_by_action` | `zins` | Read-only | Provides Zero Trust Firewall traffic analytics by action (allow/block), including blocked traffic volume and firewall policy effectiveness. |
| `zins_get_firewall_by_location` | `zia_locations` | Read-only | Provides Zero Trust Firewall traffic analytics grouped by location, including firewall activity by office and branch. |
| `zins_get_firewall_network_services` | `zia_cloud_firewall` | Read-only | Provides firewall network service usage analytics, including port usage, protocol activity, and service breakdowns. |
| `zins_get_iot_device_stats` | `zins` | Read-only | Provides IoT device statistics and classifications, including device inventory, connected device types, and unmanaged devices. |
| `zins_get_shadow_it_apps` | `zins` | Read-only | Provides discovered shadow IT applications with risk scores, including unsanctioned and unauthorized application detection. |
| `zins_get_shadow_it_summary` | `zins` | Read-only | Provides shadow IT summary statistics, including total shadow apps, app categories, and risk distribution overview. |
| `zins_get_threat_class` | `zins` | Read-only | Provides detailed threat classification analytics including virus, trojan, ransomware, and other malware type breakdowns. |
| `zins_get_threat_super_categories` | `zins` | Read-only | Provides threat super-category analytics including malware, phishing, spyware, and other threat types detected across the tenant. |
| `zins_get_web_protocols` | `zins` | Read-only | Provides web protocol distribution analytics (HTTP, HTTPS, SSL), including protocol usage and HTTPS adoption metrics. |
| `zins_get_web_traffic_by_location` | `zia_locations` | Read-only | Provides web traffic analytics grouped by location, including traffic volume, bandwidth usage, and office traffic comparisons. |
| `zins_get_web_traffic_no_grouping` | `zins` | Read-only | Provides total web traffic volume metrics without grouping, including aggregate bandwidth and overall web usage statistics. |

---

## ZMS — Microsegmentation

All 20 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zms_get_agent_connection_status_statistics` | `zms` | Read-only | Get aggregated connection status statistics for ZMS agents. Returns connected/disconnected counts and percentages. |
| `zms_get_agent_group_totp_secrets` | `zms` | Read-only | Get TOTP secrets for a specific ZMS agent group. Returns TOTP secret, QR code, and generation timestamp for agent enrollment. |
| `zms_get_agent_version_statistics` | `zms` | Read-only | Get aggregated version statistics for ZMS agents. Returns software version distribution across the agent fleet. |
| `zms_get_metadata` | `zms` | Read-only | Get event metadata for ZMS resources. Returns metadata about available resource events. |
| `zms_get_nonce` | `zms` | Read-only | Get a specific ZMS nonce (provisioning key) by eyez ID. Returns detailed key information including usage counts. |
| `zms_get_resource_group_members` | `zms` | Read-only | Get members of a specific ZMS resource group. Returns workloads in the group with resource type, status, cloud info, and OS. |
| `zms_get_resource_group_protection_status` | `zms` | Read-only | Get protection status summary for ZMS resource groups. Returns protected/unprotected group counts and coverage percentage. |
| `zms_get_resource_protection_status` | `zms` | Read-only | Get protection status summary for ZMS resources. Returns protected/unprotected counts and protection coverage percentage. |
| `zms_list_agent_groups` | `zms` | Read-only | List ZMS agent groups with pagination and search. Returns group name, type, agent count, policy status, and upgrade settings. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_agents` | `zms` | Read-only | List Zscaler Microsegmentation agents with pagination and search. Returns agent name, connection status, OS, version, IPs, and group membership. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_app_catalog` | `zms` | Read-only | List ZMS application catalog entries with pagination and filtering. Filter by name or category. Sort by name, category, creation_time, or modified_time. Returns discovered apps with name, category, port/protocol specs, and processes. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_app_zones` | `zms` | Read-only | List ZMS app zones with pagination and filtering. Filter by name and sort by zone name. Returns zone name, description, member count, and VPC/subnet settings. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_default_policy_rules` | `zms` | Read-only | List default microsegmentation policy rules. Returns system-defined baseline rules with action, direction, and scope type. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_nonces` | `zms` | Read-only | List ZMS nonces (provisioning keys) with pagination and search. Returns key name, value, max usage, current usage, and agent group association. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_policy_rules` | `zms` | Read-only | List ZMS microsegmentation policy rules with pagination and filtering. Filter by name or action (ALLOW/BLOCK). Returns rule name, action, priority, source/destination targets, and port/protocol specs. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_resource_groups` | `zms` | Read-only | List ZMS resource groups with pagination and filtering. Filter by name or resource_hostname. Returns managed and unmanaged groups with member counts, CIDRs, and FQDNs. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_resources` | `zms` | Read-only | List ZMS resources (workloads) with pagination and filtering. Filter by name, status, resource_type, cloud_provider, cloud_region, or platform_os. Returns resource type, status, cloud provider, region, hostname, OS, IPs, and app zones. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_tag_keys` | `zms` | Read-only | List tag keys within a ZMS tag namespace with filtering. Filter by key_name. Returns tag key name and description. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_tag_namespaces` | `zms` | Read-only | List ZMS tag namespaces with pagination and filtering. Filter by name or origin (CUSTOM, EXTERNAL, ML, UNKNOWN). Returns namespace name, description, and origin. Supports JMESPath client-side filtering via the query parameter. |
| `zms_list_tag_values` | `zms` | Read-only | List tag values for a specific ZMS tag key with filtering. Filter by value name. Returns available values for filtering resources. Supports JMESPath client-side filtering via the query parameter. |

---

## Meta (always loaded)

All 5 tools are read-only.

| Tool | Toolset | Type | Description |
|------|---------|------|-------------|
| `zscaler_check_connectivity` | `meta` | Read-only | Check connectivity to the Zscaler API. |
| `zscaler_enable_toolset` | `meta` | Read-only | Activates a registered-but-not-loaded toolset for the rest of the session. Refuses with status 'not_entitled' if the OneAPI credentials cannot access the underlying product. |
| `zscaler_get_available_services` | `meta` | Read-only | Service-level overview of what is loaded in this session: which Zscaler services are callable, which are present but have zero callable tools because the OneAPI credentials are not entitled to them, and which were excluded by configuration. |
| `zscaler_get_toolset_tools` | `meta` | Read-only | Drills into a toolset to enumerate its tools and per-tool availability. Use after zscaler_list_toolsets has identified the relevant toolset. |
| `zscaler_list_toolsets` | `meta` | Read-only | Primary tool-discovery entry point. Lists every toolset with description, default flag, currently-enabled status, and per-row availability metadata. Supports name / description / service substring filters. |

<!-- generated:end tools -->
