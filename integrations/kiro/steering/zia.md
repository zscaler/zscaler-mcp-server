# ZIA (Zscaler Internet Access) Steering

## Overview

ZIA is a cloud-native secure web gateway (SWG) providing internet security: cloud firewall, URL filtering, SSL inspection, DLP, sandbox analysis, ATP (Advanced Threat Protection), Cloud App Control, file-type control, and location-based traffic management.

## Available Skills

Kiro should prefer **guided skills** over ad-hoc workflows whenever a user's intent matches one of the skills below. Each skill is a multi-step playbook that auto-activates on description match and drives the right tool sequence end-to-end. When a request maps cleanly to a skill, load the SKILL.md and follow it; otherwise fall back to the ad-hoc workflows further down.

| Skill | Path | When to use |
|-------|------|-------------|
| Onboard location | `skills/zia/onboard-location/SKILL.md` | "Add a new office location", "Onboard a branch site", "Set up traffic forwarding for a new site" |
| Audit SSL inspection bypass | `skills/zia/audit-ssl-inspection-bypass/SKILL.md` | "Find which apps/categories bypass SSL inspection", "Audit DO_NOT_INSPECT / DO_NOT_DECRYPT exposure" |
| Check user URL access | `skills/zia/check-user-url-access/SKILL.md` | "Can user X reach URL Y?", "Walk URL policies for this user/group" |
| Create Cloud App Control rule | `skills/zia/create-cloud-app-control-rule/SKILL.md` | "Block uploads to Dropbox", "Create a Cloud App Control rule with action-level decisions" |
| Create firewall filtering rule | `skills/zia/create-firewall-filtering-rule/SKILL.md` | "Block IP X from country Y", "Create a Cloud Firewall rule" |
| Create SSL inspection rule | `skills/zia/create-ssl-inspection-rule/SKILL.md` | "Inspect/bypass SSL for app Z", "Create an SSL Inspection rule" |
| Create URL filtering rule | `skills/zia/create-url-filtering-rule/SKILL.md` | "Block gambling sites for finance users", "Create a URL Filtering rule" |
| Investigate sandbox | `skills/zia/investigate-sandbox/SKILL.md` | "Was this MD5 sandboxed?", "Investigate a sandbox quarantine or verdict" |
| Investigate URL category | `skills/zia/investigate-url-category/SKILL.md` | "Which rules reference this URL/category?", "Audit a URL category's policy footprint" |
| Look up cloud app name | `skills/zia/look-up-cloud-app-name/SKILL.md` | "What's the canonical enum for Dropbox / OneDrive / GitHub?" — resolve a friendly name into a ZIA `cloud_applications` enum |
| Look up rule targets | `skills/zia/look-up-rule-targets/SKILL.md` | "Find the IDs for users/groups/depts/locations/labels referenced by this rule" |
| Manage time interval | `skills/zia/manage-time-interval/SKILL.md` | "Restrict this rule to business hours", "Create or reuse a Time Interval" |

Cross-product fallback: when the request involves both ZIA and another service (ZPA, ZDX, ZCC), prefer `skills/cross-product/troubleshoot-user-connectivity/SKILL.md`.

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
1. get_zia_users / get_zia_user_groups → Find user and their groups
2. zia_url_lookup                → Classify the target URL
3. zia_list_url_filtering_rules  → Walk rules top-to-bottom, match user/group/category
4. zia_list_ssl_inspection_rules → Check if traffic is inspected
5. zia_list_web_dlp_rules        → Check if DLP blocks content
6. Present verdict: ALLOW, CAUTION, BLOCK with the matching rule
```

### ATP Policy Review
```
1. zia_get_atp_settings              → Inspect the tenant-wide ATP policy (risk tolerance, C2/malware/phishing toggles)
2. zia_get_atp_security_exceptions   → List URLs bypassed by ATP (allowlist)
3. zia_list_atp_malicious_urls       → Inspect the custom malicious-URL blocklist
4. Cross-reference with zia_list_ssl_inspection_rules → ATP analysis requires SSL inspection on the traffic
```

**Critical PUT semantics:** Both `zia_update_atp_settings` and `zia_update_atp_security_exceptions` are full-replace (PUT). Always fetch the current payload, merge your change, and submit the complete object — omitted fields are reset to API defaults.

### ATP Malware Protection Review
```
1. zia_get_atp_malware_policy        → File-handling toggles (block_unscannable_files, block_password_protected_archive_files)
2. zia_get_atp_malware_inspection    → Direction toggles (inspect_inbound, inspect_outbound)
3. zia_get_atp_malware_protocols     → Protocol toggles (inspect_http, inspect_ftp_over_http, inspect_ftp)
4. zia_get_malware_settings          → 16-field threat-class block (virus / trojan / worm / adware / spyware / ransomware /
                                         remote-access tool / unwanted-applications — each with *_blocked + *_capture)
5. Cross-reference with zia_list_ssl_inspection_rules → HTTPS inspection must be enabled for inspect_http to scan TLS payloads
```

**Critical PUT semantics:** Every malware update is full-replace (PUT). For `zia_update_malware_settings` specifically, any of the 16 booleans you omit will be reset to `False` by the API — always fetch via `zia_get_malware_settings`, mutate just the toggles you want to change, then send the full dict back. For the three `zia_update_atp_malware_*` tools all required positional arguments must be passed in a single call; there is no partial update.

**Always call `zia_activate_configuration` after any malware update** — like every ZIA write, the change is staged until activation.

### Advanced Settings Review
```
1. zia_get_advanced_settings      → Tenant-wide Administration → Advanced Settings block (~50 knobs)
                                       Highlights: enable_office365, ui_session_timeout (seconds),
                                       enforce_surrogate_ip_for_windows_app, log_internal_ip,
                                       enable_dns_resolution_on_transparent_proxy,
                                       enable_ipv6_dns_resolution_on_transparent_proxy,
                                       cascade_url_filtering, enable_policy_for_unauthenticated_traffic,
                                       http2_nonbrowser_traffic_enabled, ecs_for_all_enabled,
                                       dynamic_user_risk_enabled, block_connect_host_sni_mismatch,
                                       prefer_sni_over_conn_host, sipa_xff_header_enabled
                                       Bypass lists: auth_bypass_urls/apps, kerberos_bypass_urls/apps,
                                       digest_auth_bypass_urls/apps, basic_bypass_apps, and the
                                       *_url_categories variants
2. zia_update_advanced_settings   → Apply a merged payload (PUT-replace — see semantics below)
3. zia_activate_configuration     → Stage the change live
```

**Critical PUT semantics:** `zia_update_advanced_settings` is full-replace — the SDK forwards the payload as `**kwargs`, so any field omitted is reset to its API default (booleans → `False`, lists → `[]`, integers → `None` / portal default). Always fetch via `zia_get_advanced_settings`, mutate just the fields you want to change on the returned dict, then send the full dict back.

**Common pitfalls:**

- Setting `ui_session_timeout` too low forces frequent re-login for admins — confirm with the user before pushing values under `1800` (30 min).
- Toggling `enable_dns_resolution_on_transparent_proxy` interacts with the DNS-firewall rule family (`zia_list_cloud_firewall_dns_rules`) — review DNS rules before disabling.
- Bypass lists (`auth_bypass_urls`, `kerberos_bypass_urls`, `digest_auth_bypass_urls`) are **allowlists** that exempt traffic from authentication — adding the wrong URL silently opens an auth hole. Treat changes as security-sensitive.

### Custom IPS Signature Authoring

```text
1. zia_list_ips_signature_rules               → Inventory existing custom signatures (paginated; supports JMESPath query)
2. zia_get_ips_signature_rule(<id>)           → Inspect rule_text + metadata for a baseline / similar signature
3. zia_create_ips_signature_rule              → Author the new signature (rule_text auto-validated server-side
                                                 against the dynamic-validation endpoint BEFORE create)
4. zia_activate_configuration                  → Stage the new signature live on the cloud
5. zia_create_cloud_firewall_ips_rule          → (Optional) tighten the matching policy rule that
                                                 governs WHEN this signature is enforced (allow / drop /
                                                 reset / bypass-IPS on which traffic) — paired surface
6. zia_activate_configuration                  → Activate the policy-rule change too
```

**The two surfaces are complementary, not interchangeable:**

| Surface | What it does | Tools |
|---|---|---|
| **Custom IPS signatures** (`zia_*_ips_signature_rule`) | Defines *what* to detect — Snort/Suricata-style rule body with a unique `sid:` | list / get / create / update / delete |
| **Cloud Firewall IPS rules** (`zia_*_cloud_firewall_ips_rule`) | Defines *when* to enforce IPS on firewall-matched traffic — allow / block-drop / block-reset / bypass-IPS, scoped by users, locations, src/dst, etc. | list / get / create / update / delete |

A signature without a matching policy rule is dormant. A policy rule without enabled signatures has nothing to detect.

**Critical PUT semantics for `zia_update_ips_signature_rule`:**

- The IPS signature update endpoint is full-replace. The tool silently backfills the load-bearing fields **`name` and `rule_text`** from the existing record when the caller omits them — different from rule-family tools, which backfill `name` and `order` (IPS signatures have no `order`).
- **Server-side validation is NOT re-run on update.** The dynamic-validation endpoint flags any rule whose `sid:` already exists as a duplicate — which on an update is the rule being modified itself, so a pre-flight check would reject every legitimate edit. If you change `rule_text`, validate the new body manually (in the ZIA Admin Portal or via the SDK's `validate_ips_signature_rule`) before pushing the update.

**Common pitfalls:**

- Every signature needs a unique `sid:` and a `rev:` — duplicates are rejected at create time. When forking an existing signature, bump the `sid:` to a new value and reset `rev:` to `1`.
- Forgetting `zia_activate_configuration` after the create / update / delete is the #1 cause of "my signature isn't catching traffic".
- Custom signatures complement, not replace, the predefined Zscaler-managed signatures — ZIA's IPS engine evaluates both sets.

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
| `zia_list_cloud_firewall_dns_rules` | List firewall DNS rules |
| `zia_get_cloud_firewall_dns_rule` | Get specific firewall DNS rule |
| `zia_list_cloud_firewall_ips_rules` | List firewall IPS rules |
| `zia_get_cloud_firewall_ips_rule` | Get specific firewall IPS rule |
| `zia_list_ips_signature_rules` | List custom IPS signature rules (Snort/Suricata-style detection signatures — distinct from Cloud Firewall IPS *policy* rules above; signatures = "what to detect", policy rules = "when to enforce"). Supports page / page_size + JMESPath query. |
| `zia_get_ips_signature_rule` | Get a specific custom IPS signature rule by ID — returns metadata + the raw rule_text Snort/Suricata signature body |
| `zia_list_url_filtering_rules` | List URL filtering rules |
| `zia_get_url_filtering_rule` | Get specific URL rule |
| `zia_list_ssl_inspection_rules` | List SSL inspection rules |
| `zia_get_ssl_inspection_rule` | Get specific SSL rule |
| `zia_list_web_dlp_rules` | List DLP rules |
| `zia_list_web_dlp_rules_lite` | List DLP rules (lightweight) |
| `zia_get_web_dlp_rule` | Get specific DLP rule |
| `zia_list_file_type_control_rules` | List File Type Control rules |
| `zia_get_file_type_control_rule` | Get specific File Type Control rule |
| `zia_list_file_type_categories` | List file-type categories |
| `zia_list_sandbox_rules` | List Sandbox rules |
| `zia_get_sandbox_rule` | Get specific Sandbox rule |
| `zia_list_time_intervals` | List Time Intervals (recurring schedules referenced by rules via `time_windows`) |
| `zia_get_time_interval` | Get specific Time Interval |
| `zia_list_url_categories` | List URL categories |
| `zia_get_url_category` | Get specific URL category |
| `zia_get_url_category_predefined` | Get a predefined URL category by configured name (e.g. `OTHER_BUSINESS_ECONOMY`) |
| `zia_url_lookup` | Classify a URL into categories |
| `zia_list_locations` | List locations |
| `zia_get_location` | Get specific location |
| `zia_list_location_groups` | List location groups (`DYNAMIC` and `STATIC`) |
| `zia_get_location_group` | Get specific location group |
| `zia_list_workload_groups` | List workload groups (cloud-workload identity scope) |
| `zia_get_workload_group` | Get specific workload group |
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
| `zia_list_cloud_app_control_rules` | List Cloud App Control rules |
| `zia_get_cloud_app_control_rule` | Get specific Cloud App Control rule |
| `zia_list_cloud_app_control_actions` | List cloud application control actions |
| `zia_list_shadow_it_apps` | List Shadow IT cloud applications (analytics catalog: numeric IDs, friendly names) |
| `zia_list_shadow_it_custom_tags` | List Shadow IT custom tags |
| `zia_list_cloud_app_policy` | List the policy-engine cloud-app catalog (canonical enums for Web DLP, Cloud App Control, File Type Control, Bandwidth Classes, Advanced Settings) |
| `zia_list_cloud_app_ssl_policy` | List the cloud-app catalog scoped to SSL Inspection rules (canonical enums) |
| `zia_get_atp_settings` | Get the tenant-wide ATP policy block (risk tolerance, C2/malware/phishing toggles) |
| `zia_get_atp_security_exceptions` | Get the ATP bypass URL list |
| `zia_list_atp_malicious_urls` | List ATP malicious URL entries |
| `zia_get_atp_malware_policy` | Get the ATP Malware Protection file-handling toggles (block_unscannable_files, block_password_protected_archive_files) |
| `zia_get_atp_malware_inspection` | Get the ATP Malware Protection traffic-direction toggles (inspect_inbound, inspect_outbound) |
| `zia_get_atp_malware_protocols` | Get the ATP Malware Protection protocol toggles (inspect_http, inspect_ftp_over_http, inspect_ftp) |
| `zia_get_malware_settings` | Get the full Malware Protection threat-class block (16 booleans: virus / trojan / worm / adware / spyware / ransomware / remote-access-tool / unwanted-applications, each with a matching *_capture PCAP toggle) |
| `zia_get_advanced_settings` | Get the tenant-wide Administration → Advanced Settings block (~50 knobs: DNS optimization on transparent proxy, auth/Kerberos/digest bypass URLs and apps, Office 365 one-click, UI session timeout, surrogate IP, HTTP tunnel handling, HTTP/2, ECS, dynamic user risk, SNI handling, SIPA XFF) |
| `zia_list_device_groups` | List device groups |
| `zia_list_devices` | List devices |
| `zia_list_devices_lite` | List devices (lightweight) |
| `get_zia_users` | Retrieve ZIA users |
| `get_zia_user_groups` | Retrieve ZIA user groups |
| `get_zia_user_departments` | Retrieve ZIA user departments |
| `get_zia_dlp_dictionaries` | Retrieve DLP dictionaries |
| `get_zia_dlp_engines` | Retrieve DLP engines |
| `zia_geo_search` | Search geolocation data (countries, states, cities, regions) |
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
| `zia_create_cloud_firewall_dns_rule` | Create firewall DNS rule |
| `zia_update_cloud_firewall_dns_rule` | Update firewall DNS rule (PUT — name/order silently backfilled) |
| `zia_delete_cloud_firewall_dns_rule` | Delete firewall DNS rule |
| `zia_create_cloud_firewall_ips_rule` | Create firewall IPS rule |
| `zia_update_cloud_firewall_ips_rule` | Update firewall IPS rule (PUT — name/order silently backfilled) |
| `zia_delete_cloud_firewall_ips_rule` | Delete firewall IPS rule |
| `zia_create_ips_signature_rule` | Create a custom IPS signature rule (Snort/Suricata-style). The SDK pre-flight-validates `rule_text` against the ZIA dynamic-validation endpoint *before* the create — syntax / duplicate-`sid` errors raise without leaving a stub on the tenant. |
| `zia_update_ips_signature_rule` | Update a custom IPS signature rule (PUT — `name` and `rule_text` silently backfilled when omitted). Server-side validation is NOT re-run because the existing-`sid` check would flag every legitimate edit as a duplicate of itself; validate the new rule_text manually first. |
| `zia_delete_ips_signature_rule` | Delete a custom IPS signature rule (HMAC double-confirmed) |
| `zia_create_url_filtering_rule` | Create URL filtering rule |
| `zia_update_url_filtering_rule` | Update URL filtering rule |
| `zia_delete_url_filtering_rule` | Delete URL filtering rule |
| `zia_create_ssl_inspection_rule` | Create SSL inspection rule |
| `zia_update_ssl_inspection_rule` | Update SSL inspection rule |
| `zia_delete_ssl_inspection_rule` | Delete SSL inspection rule |
| `zia_create_web_dlp_rule` | Create DLP rule |
| `zia_update_web_dlp_rule` | Update DLP rule |
| `zia_delete_web_dlp_rule` | Delete DLP rule |
| `zia_create_file_type_control_rule` | Create File Type Control rule (friendly cloud-app names auto-resolved) |
| `zia_update_file_type_control_rule` | Update File Type Control rule (PUT — name/order silently backfilled) |
| `zia_delete_file_type_control_rule` | Delete File Type Control rule |
| `zia_create_sandbox_rule` | Create Sandbox rule |
| `zia_update_sandbox_rule` | Update Sandbox rule (PUT — name/order silently backfilled) |
| `zia_delete_sandbox_rule` | Delete Sandbox rule |
| `zia_create_time_interval` | Create Time Interval (`start_time`/`end_time` minutes from midnight 0-1439; `days_of_week`: `EVERYDAY`, `SUN`-`SAT`) |
| `zia_update_time_interval` | Update Time Interval (PUT — name/start_time/end_time/days_of_week silently backfilled) |
| `zia_delete_time_interval` | Delete Time Interval (fails if referenced by any rule) |
| `zia_create_url_category` | Create custom URL category |
| `zia_update_url_category` | Update URL category |
| `zia_update_url_category_predefined` | Add/remove URLs on a predefined URL category (`configured_name` + `ADD_TO_LIST` / `REMOVE_FROM_LIST`) |
| `zia_delete_url_category` | Delete custom URL category |
| `zia_add_urls_to_category` | Add URLs to a category |
| `zia_remove_urls_from_category` | Remove URLs from a category |
| `zia_create_cloud_app_control_rule` | Create a Cloud App Control rule (per-action decisions on SaaS apps) |
| `zia_update_cloud_app_control_rule` | Update a Cloud App Control rule (PUT — name/order silently backfilled) |
| `zia_delete_cloud_app_control_rule` | Delete a Cloud App Control rule |
| `zia_update_atp_settings` | Update tenant-wide ATP policy (PUT — full payload required; fetch + merge before sending) |
| `zia_update_atp_security_exceptions` | Replace the ATP bypass URL list (PUT — full list semantics) |
| `zia_update_atp_malware_policy` | Update ATP Malware Protection file-handling toggles (PUT — both booleans required) |
| `zia_update_atp_malware_inspection` | Update ATP Malware Protection traffic-direction toggles (PUT — both booleans required) |
| `zia_update_atp_malware_protocols` | Update ATP Malware Protection protocol toggles (PUT — all three booleans required; tool re-fetches after PUT to work around an SDK response-parsing bug) |
| `zia_update_malware_settings` | Update the full Malware Protection threat-class block (PUT — any of the 16 booleans omitted is reset to False; fetch + merge before sending) |
| `zia_update_advanced_settings` | Update the Administration → Advanced Settings block (PUT — SDK forwards payload as **kwargs; any field omitted is reset to API default / `[]` for lists; fetch + merge before sending) |
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
| `zia_bulk_update_shadow_it_apps` | Bulk update sanction state / custom tags on Shadow IT cloud applications |

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

### Cloud-Application Catalogs (Shadow IT vs Policy-Engine)
ZIA has **two separate cloud-app catalogs** that are NOT interchangeable:

- **Shadow IT analytics** (`zia_list_shadow_it_apps`) → numeric IDs + friendly names ("Sharepoint Online", id 655377). Used for sanction state and usage analytics.
- **Policy-engine catalog** (`zia_list_cloud_app_policy`, `zia_list_cloud_app_ssl_policy`) → canonical enum tokens (`SHAREPOINT_ONLINE`, `ONEDRIVE`). This is the catalog the `cloud_applications` field on SSL Inspection / Web DLP / Cloud App Control / File Type Control / Bandwidth Classes / Advanced Settings rules accepts.

Passing a Shadow IT id or friendly name into a policy rule's `cloud_applications` causes ZIA to silently coerce the value to `NONE`. Always resolve via the policy-engine catalog first.

`zia_create_ssl_inspection_rule` and `zia_update_ssl_inspection_rule` auto-resolve friendly names to canonical enums before the API call (in-process resolver, 5-minute cache). The response includes a `_cloud_applications_resolution` field showing the mapping so you can echo it back to the user. Set `resolve_cloud_apps=False` to disable.

### Response Style — Don't Leak Implementation Details
When answering the user, give the **business answer in plain language**. Never narrate JMESPath queries, output validation errors, internal type coercion, or which projection you ran. The user is asking a business question; the JMESPath is just an internal optimization.

- *"how many ZIA DNS rules exist?"* → **"There are 19 ZIA DNS firewall rules in the tenant."**  Not: *"The JMESPath `length(@)` returned 19 before hitting the validation error — so there are 19 rules."*
- *"list my SSL inspection rules"* → list the names. Not: *"I projected `[*].name`."*
- If a tool errors, summarize the user-facing meaning. Don't paste back Pydantic validation messages or internal field names.

## Best Practices

1. **Always activate after changes** — Call `zia_activate_configuration` after any create/update/delete
2. **Audit SSL bypasses regularly** — `DO_NOT_INSPECT` rules create blind spots for DLP and threat detection
3. **Use `zia_url_lookup` before making URL policy changes** — Understand the current classification first
4. **Review rule order** — A broadly-scoped rule early in the list can override specific rules below it
5. **Use rule labels** — Tag rules for easier filtering and organization
6. **Confirm before write operations** — Always explain proposed changes and get explicit user confirmation
