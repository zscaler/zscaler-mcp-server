# Zscaler MCP Server

300+ tools for managing the Zscaler Zero Trust Exchange. Services: ZPA, ZIA, ZDX, ZCC, EASM, Z-Insights, ZIdentity, ZTW (Zscaler Workload Segmentation), ZMS (Zscaler Microsegmentation).

> **Cross-tool conventions.** The most-violated rules in this repo are mirrored at `.claude/CONVENTIONS.md` (Claude Code) so they survive even if this file is trimmed. A parallel Cursor mirror at `.cursor/rules/zscaler-conventions.mdc` (auto-applied in Cursor sessions) is **planned but not yet committed** — until it lands, Cursor sessions rely on this `CLAUDE.md` being loaded explicitly. The full convention set lives below; **Helper-file convention** is in [Helper File Convention (DO NOT FRAGMENT)](#helper-file-convention-do-not-fragment) — read it before adding any new file under `zscaler_mcp/common/`.

## Architecture Overview

### Core Components

```text
zscaler_mcp/
├── server.py          # ZscalerMCPServer class, CLI entrypoint, security posture logging
├── services.py        # Service registry + 9 concrete service classes (ZPA, ZIA, ZDX, ZCC, ZTW, ZIdentity, ZEASM, ZInsights, ZMS)
├── auth.py            # Auth middleware factory (JWT, API-key, Zscaler, OAuthProxy stub)
├── client.py          # Zscaler SDK client factory (OneAPI only — single ZIdentity-based credential flow)
├── security.py        # HTTP security warnings (TLS, plaintext)
├── cloud/
│   └── gcp_secrets.py   # GCP Secret Manager credential loader (opt-in via ZSCALER_MCP_GCP_SECRET_MANAGER=true)
├── common/
│   ├── tool_helpers.py    # register_read_tools / register_write_tools with disabled_tools filtering
│   ├── jmespath_utils.py  # apply_jmespath() — shared JMESPath client-side filtering for all list tools
│   ├── elicitation.py     # HMAC-SHA256 confirmation tokens for destructive actions
│   └── logging.py         # log_security_warning helper
└── tools/                # 112 tool modules organized by service (zia/, zpa/, zdx/, zcc/, ztw/, zid/, easm/, zins/, zms/)
```

### Request Flow

1. **Client connects** via transport (stdio, SSE, or streamable-http)
2. **Auth middleware** validates credentials (JWT/API-key/Zscaler/OIDCProxy) — HTTP transports only
3. **Host header validation** checks against `ZSCALER_MCP_ALLOWED_HOSTS` allowlist
4. **Source IP ACL** filters by `ZSCALER_MCP_ALLOWED_SOURCE_IPS` (if configured)
5. **Tool dispatch** routes to the appropriate service tool function
6. **Zscaler SDK client** is created on-demand (lazy initialization per tool call, not at startup)
7. **Response** returned to client; write operations may require HMAC confirmation first

### Service Architecture

Each service follows the same pattern:

- **Service class** in `services.py` (e.g., `ZPAService`) — defines `read_tools` and `write_tools` lists
- **Tool modules** in `tools/{service}/` — each module exports one or more tool functions
- **Tool registration** via `register_read_tools()` / `register_write_tools()` in `tool_helpers.py`

Tool registration respects three layers of filtering:

1. `enabled_tools` — positive allowlist (only register these tools)
2. `disabled_tools` — negative blocklist with fnmatch wildcards (exclude matching tools)
3. `write_tools` — write-specific allowlist with wildcards (only these write tools are allowed)

### Authentication Layers

The server has two independent auth systems:

1. **MCP Client Authentication** (`auth.py`) — controls WHO can connect to the server
   - Modes: `jwt`, `api-key`, `zscaler`, or programmatic `auth=` parameter (OIDCProxy)
   - Auto-detection: if `ZSCALER_MCP_AUTH_JWKS_URI` is set, uses JWT; if `ZSCALER_MCP_AUTH_API_KEY`, uses api-key; etc.
   - Enabled by default for HTTP transports; not applicable for stdio
   - The `auth=` parameter on `ZscalerMCPServer` takes a `fastmcp.server.auth.AuthProvider` (e.g., `OIDCProxy`) and bypasses the env-var middleware entirely
   - Compatible with any OIDC provider: Auth0, Okta, Microsoft Entra ID, Keycloak, Google, AWS Cognito, PingOne
   - **Entra ID guide**: `docs/deployment/entra-id-oidcproxy.md` — step-by-step with screenshots. Key difference: `audience` must be the client ID (Entra sets `aud` to client_id in ID tokens, unlike Auth0 which uses an API identifier)

2. **Zscaler API Authentication** (`client.py`) — controls how the server talks to Zscaler APIs
   - OneAPI credentials only (`ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET` or `ZSCALER_PRIVATE_KEY`, `ZSCALER_VANITY_DOMAIN`, `ZSCALER_CUSTOMER_ID` for ZPA)
   - Client is created lazily on first tool call, not at server startup

## Tool Naming & Discovery

All tools follow `{service}_{verb}_{resource}` naming: `zia_list_locations`, `zpa_create_access_policy_rule`, `zdx_get_application`. Service prefixes: `zia_`, `zpa_`, `zdx_`, `zcc_`, `easm_`, `zins_`, `zid_`, `ztw_`, `zms_`. Use the prefix to discover tools for a given service.

### Deferred Tool Loading & AI Agent Behavior

Most MCP clients (Claude Desktop, Cursor) use **deferred tool loading** — they don't load all 360+ tools upfront. Instead, they search for relevant tools based on the user's prompt. This has important implications:

- **Tool search returns "closest N" results**, even if none are relevant. If a service is disabled, the search will return unrelated tools from other services rather than saying "not found."
- **The `zscaler_get_available_services` tool** was designed to solve this. It returns enabled services with tool counts AND explicitly lists disabled services with a note instructing the agent to inform the user. Its description mentions all service names (ZCC, ZDX, ZPA, ZIA, ZTW, etc.) so it surfaces in tool search when someone asks about any service.
- **Design principle**: When the server can't fulfill a request (disabled service, missing tool), it should give the agent enough information to explain WHY rather than leaving the agent to hallucinate with unrelated tools.

### Disabled Tools & Services

Two independent exclusion mechanisms, applied at registration time (not runtime):

- **`--disabled-services` / `ZSCALER_MCP_DISABLED_SERVICES`** — removes entire services. Values are service names: `zcc`, `zdx`, `zpa`, `zia`, `ztw`, `zid`, `zeasm`, `zins`, `zms`. The service class is never instantiated and its tools are never registered. Does NOT support wildcards (exact service names only).

- **`--disabled-tools` / `ZSCALER_MCP_DISABLED_TOOLS`** — removes individual tools by name pattern. Supports `fnmatch` wildcards (e.g., `zcc_*`, `zia_list_device*`). Applied in `register_read_tools()` and `register_write_tools()` via `fnmatch.fnmatch()`.

**Cross-service overlap**: Some Zscaler APIs expose overlapping data. For example, ZIA has device management tools (`zia_list_devices`) that return the same data as ZCC's tools. Disabling the `zcc` service removes all `zcc_*` tools but does NOT remove ZIA's device tools. Use `--disabled-tools` to also block the ZIA overlap if needed.

The `zscaler_get_available_services` tool exposes disabled services to the AI agent so it can inform users instead of searching for workarounds.

## Toolsets

Tools are grouped into named **toolsets** (registered in `zscaler_mcp/common/toolsets.py`). Toolsets let users load only the slice of tools the agent actually needs — e.g. `zia_url_filtering` (5 tools) instead of every tool from every service (~360). The full design and catalog live in `docs/guides/toolsets.md`; the highlights for working in this codebase:

- **52 toolsets** today (catalog grew from 29 → 52 as ZIA / ZPA / ZDX were split into resource-family-scoped groups):
  - **ZIA: 21 sub-toolsets.** One per rule family (`zia_url_filtering`, `zia_cloud_firewall`, `zia_ssl_inspection`, `zia_dlp`, `zia_cloud_app_control`, `zia_file_type_control`, `zia_sandbox`), plus locations, URL categories, users, devices (`zia_devices`), authentication settings (`zia_authentication_settings` — cookie-auth exempt URL list), rule labels (`zia_rule_labels`), workload groups, time intervals, shadow IT, ATP policy (`zia_atp_policy` — tenant-wide ATP settings + security-exception bypass list + malicious-URL denylist), ATP malware (`zia_atp_malware` — malware policy / inspection / protocols + the 16-field threat-class block, backed by `zscaler.zia.malware_protection_policy.MalwareProtectionPolicyAPI`), advanced settings (`zia_advanced_settings` — tenant-wide *Administration → Advanced Settings* singleton, ~50 knobs across DNS opt / bypass / surrogate IP / HTTP/2 / ECS / dynamic-user-risk / SIPA, backed by `zscaler.zia.advanced_settings.AdvancedSettingsAPI`), admin (`zia_admin` for activation + intermediate-CA / generic config) and `zia_misc` as the catch-all.
  - **ZPA: 19 sub-toolsets.** Resource-family scoped: `zpa_app_segments` (standard + BA + PRA segments and `get_zpa_app_segments_by_type`), `zpa_access_policies` (all access/forwarding/timeout/isolation rules), `zpa_policy` (umbrella policy registry tools), `zpa_app_connector_groups`, `zpa_connectors` (individual connectors + enrollment certs), `zpa_server_groups`, `zpa_segment_groups`, `zpa_service_edge_groups`, `zpa_provisioning_keys`, `zpa_application_servers`, `zpa_pra` (PRA portals + credentials), `zpa_ba_certificates`, `zpa_app_protection`, `zpa_posture`, `zpa_trusted_networks`, `zpa_isolation`, `zpa_idp` (SAML/SCIM attributes + groups), `zpa_microtenants`, `zpa_misc`.
  - **ZDX: 5 sub-toolsets.** Replaced the single `zdx` toolset: `zdx_alerts`, `zdx_locations` (locations + departments), `zdx_software_inventory`, `zdx_troubleshooting` (deep traces + analyses + probes), `zdx_reports` (default catch-all for everything else: devices, applications, web/cloudpath probe reads).
  - **One toolset each** for ZCC, ZTW, ZIdentity, EASM, Z-Insights, ZMS. The always-on `meta` toolset holds the cross-service tools (`zscaler_check_connectivity`, `zscaler_get_available_services`, plus the three discovery tools below).
- **Tagging is centralized.** Don't add a `toolset` field to dicts in `services.py`. Map a new tool name in `_TOOL_TOOLSET_OVERRIDES` (exact match) or `_TOOLSET_PREFIX_RULES` (predicate, first-match-wins) inside `toolsets.py`. The test `tests/test_toolsets.py::TestToolsetForTool::test_every_registered_tool_resolves` enforces this mapping is exhaustive.
- **Prefix-rule ordering is load-bearing.** `_TOOLSET_PREFIX_RULES` is evaluated first-match-wins, and several predicates across services share substrings (`_location` would hijack `zdx_list_locations` into `zia_locations` if evaluated first; `_device` would pull `zdx_list_devices` into ZIA's device toolset; `_app_connector_group` must be evaluated before `_app_connector`). The current file follows two conventions: (1) **ZDX block sits at the top** of the rules list, with every predicate explicitly scoped to `n.startswith("zdx_")`, so ZDX tools can never be poached by a downstream service's predicate; (2) within each service, more-specific prefixes precede general ones. When adding a new toolset that shares a substring with an existing one, add the rule *above* the broader rule and gate it with the service prefix.
- **Selection layers** (resolved in `ZscalerMCPServer.__init__`): explicit `--toolsets` / `ZSCALER_MCP_TOOLSETS` (supports `default` and `all` keywords) → fall back to "every toolset whose service is in `enabled_services`" (preserves today's behaviour). Filter precedence: `disabled_tools` > toolset selection > `enabled_tools` allowlist > `write_tools` allowlist.
- **Per-toolset instructions.** Each toolset can carry an `instructions` callable. At server startup `_compose_server_instructions()` calls each enabled toolset's snippet and concatenates them into the FastMCP `instructions` field — sent to the agent only when the matching tools are loaded. Snippets shared across multiple toolsets (e.g. the rule-family `order`/`rank` reminder bound to all 5 ZIA rule toolsets) are de-duplicated.
- **Three discovery meta-tools** (always loaded): `zscaler_list_toolsets` (catalog with currently-enabled status + tool counts), `zscaler_get_toolset_tools` (member tools of a toolset), `zscaler_enable_toolset` (register a toolset's tools at runtime). The runtime-enable path uses the same `register_read_tools`/`register_write_tools` codepath as startup, so all filter precedence still applies.
- **OneAPI entitlement filter** (always-on, opt-out via `--no-entitlement-filter` / `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true`). After the operator-driven `selected_toolsets` is resolved, `zscaler_mcp/common/entitlements.py::apply_entitlement_filter` exchanges the configured OneAPI credentials for a bearer token and intersects the selection with the products listed in the `service-info[].prd` claim. Cache-first: in `ZSCALER_MCP_AUTH_MODE=zscaler` the auth-middleware cache is reused (no extra `/oauth2/v1/token` call); otherwise it cold-fetches via `auth.fetch_oneapi_token`. Roles (`rnm`) are intentionally ignored — only product entitlement is reliable. Failure mode is non-fatal: missing creds, decode failure, network error, or empty `service-info` all log a single WARN line and the selection passes through unchanged. The `meta` toolset is always preserved.
- **Deferred to a follow-up:** HTTP header overrides (`X-MCP-Toolsets`) and URL-path shortcuts (`/mcp/x/{toolsets}/readonly`) — both require per-request server architecture (FastMCP transport surgery).

## Critical Gotchas

- **ZIA requires activation.** After any ZIA create/update/delete, call `zia_activate_configuration()`. Changes are staged until activation. Forgetting this is the #1 source of "my change didn't work" issues.
- **OneAPI is the only supported authentication mode.** Every tool authenticates against ZIdentity through `zscaler.ZscalerClient` using the unified `ZSCALER_CLIENT_ID` / `ZSCALER_CLIENT_SECRET` (or `ZSCALER_PRIVATE_KEY`) / `ZSCALER_VANITY_DOMAIN` / `ZSCALER_CUSTOMER_ID` (ZPA only) credentials.
- **ZDX is read-only.** ZDX tools only query data. There are no create/update/delete operations except for deep traces (`zdx_start_deep_trace`).
- **ZDX `since` parameter is in hours**, not timestamps. Default is 2 hours. Example: `since=24` means "last 24 hours."
- **IDs are strings**, even when they look numeric. Always pass IDs as strings.
- **ZPA dependency chain matters.** To onboard an application: create app connector group -> create server group (references connector group) -> create segment group -> create application segment (references server and segment groups) -> create access policy rule. Skipping dependencies causes cryptic 400 errors.
- **ZIA dependency chain for locations.** To onboard a location: create static IP -> create VPN credential (references static IP) -> create location (references VPN credential and static IP). The location won't work without the traffic forwarding prerequisites.
- **ZIA policy-rule updates are PUT, not PATCH.** Every ZIA `update_*_rule` tool ultimately maps to a PUT under the hood (full-replace). Tools silently backfill the required `name` and `order` from the existing rule when a partial payload is supplied, so partial updates "just work" — but any other field omitted from the payload may be reset by the API. When in doubt, fetch the rule first and merge changes into the existing payload. Tools using this pattern: `zia_update_ssl_inspection_rule`, `zia_update_cloud_firewall_dns_rule`, `zia_update_cloud_firewall_ips_rule`, `zia_update_file_type_control_rule`, `zia_update_sandbox_rule`. The same backfill pattern is applied to `zia_update_time_interval` for the `name`, `start_time`, `end_time`, and `days_of_week` fields.
- **ZIA cloud-application catalogs are NOT interchangeable.** Two distinct catalogs exist:
  - **Shadow IT analytics catalog** (`zia_list_shadow_it_apps`, `zia_list_shadow_it_custom_tags`, `zia_bulk_update_shadow_it_apps`) — friendly names + numeric IDs, used for analytics/sanctioning.
  - **Policy-engine catalog** (`zia_list_cloud_app_policy`, `zia_list_cloud_app_ssl_policy`) — canonical `UPPER_SNAKE_CASE` enum strings used by SSL Inspection, Web DLP, Cloud App Control, File Type Control rules.
  - The `cloud_applications` field on policy rules expects canonical enums. Tools that accept friendly names (`zia_create_ssl_inspection_rule`, `zia_update_ssl_inspection_rule`, `zia_create_file_type_control_rule`, `zia_update_file_type_control_rule`, `zia_create_cloud_firewall_dns_rule`, `zia_update_cloud_firewall_dns_rule` (where the field is named `applications`), `zia_list_cloud_app_control_actions`) auto-resolve them via `zscaler_mcp/common/zia_helpers.py::resolve_cloud_applications` (5-minute in-process cache, strict mode), surfacing the audit trail in `_cloud_applications_resolution`. See `skills/zia/look-up-cloud-app-name/SKILL.md`.
- **DNS rules expose the cloud-app catalog as `applications`, not `cloud_applications`.** Same canonical ZIA app names (`ONEDRIVE`, `GOOGLE_DRIVE`, `CLOUDFLARE_DOH`, etc.) used by SSL Inspection / Web DLP / FTC / CAC — the field is just named `applications` on this rule type. The resolver IS wired here: `zia_create/update_cloud_firewall_dns_rule` auto-resolve friendly names through `resolve_cloud_applications` exactly like SSL Inspection does, surfacing the audit trail in `_cloud_applications_resolution`. The DNS-related sub-categories (DNS tunnels, network apps, DNS-over-HTTPS providers) are part of that same catalog, not a separate vocabulary.
- **ZIA Sandbox rules vs sandbox reports.** `zia_*_sandbox_rule` tools manage Sandbox **policy rules** (write). `zia_get_sandbox_*` tools (`quota`, `report`, `behavioral_analysis`, `file_hash_count`) are read-only sandbox **report/quota** tools. Don't confuse the two.

## ZIA (Zscaler Internet Access)

ZIA is the largest service in the server. Tool modules are organized one-resource-per-file under `zscaler_mcp/tools/zia/`. Every tool follows the strict `{service}_{verb}_{resource}` design — one tool per action (list / get / create / update / delete), no multiplexed `action=` parameters.

### ZIA Policy-Rule Tool Family (one-tool-per-action design)

| Resource | Module | List / Get | Create / Update / Delete | Notes |
|----------|--------|-----------|--------------------------|-------|
| Cloud Firewall | `cloud_firewall_rules.py` | `zia_list_cloud_firewall_rules`, `zia_get_cloud_firewall_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | |
| Cloud Firewall DNS | `cloud_firewall_dns_rules.py` | `zia_list_cloud_firewall_dns_rules`, `zia_get_cloud_firewall_dns_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | `applications` ≠ cloud-app enum |
| Cloud Firewall IPS | `cloud_firewall_ips_rules.py` | `zia_list_cloud_firewall_ips_rules`, `zia_get_cloud_firewall_ips_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | |
| Custom IPS Signatures | `ips_signature_rules.py` | `zia_list_ips_signature_rules`, `zia_get_ips_signature_rule` | `zia_create_ips_signature_rule`, `zia_update_ips_signature_rule`, `zia_delete_ips_signature_rule` | Snort/Suricata-style signature **definitions** (not policy rules — distinct from Cloud Firewall IPS above). Tiny field set (`name`, `description`, `rule_text`); the SDK pre-flight-validates `rule_text` on create against the dynamic-validation endpoint and surfaces syntax / duplicate-`sid` errors as `ValueError` before any tenant-side write. Update is PUT-replace; the tool backfills `name` + `rule_text` (the load-bearing fields here, instead of the usual `name` + `order`) when the caller omits them. Lives in the `zia_cloud_firewall` toolset alongside the Cloud Firewall IPS policy-rule family via explicit overrides — admins working on intrusion prevention typically want the **what to detect** (signature) and **when to enforce** (policy rule) surfaces loaded together. |
| URL Filtering | `url_filtering_rules.py` | `zia_list_url_filtering_rules`, `zia_get_url_filtering_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | |
| SSL Inspection | `ssl_inspection.py` | `zia_list_ssl_inspection_rules`, `zia_get_ssl_inspection_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | Cloud-app auto-resolver |
| Web DLP | `web_dlp_rules.py` | `zia_list_web_dlp_rules`, `zia_list_web_dlp_rules_lite`, `zia_get_web_dlp_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | |
| File Type Control | `file_type_control_rules.py` | `zia_list_file_type_control_rules`, `zia_get_file_type_control_rule`, `zia_list_file_type_categories` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | Cloud-app auto-resolver |
| Sandbox Rules | `sandbox_rules.py` | `zia_list_sandbox_rules`, `zia_get_sandbox_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | Distinct from sandbox **reports** in `get_sandbox_info.py` |
| Time Intervals | `time_intervals.py` | `zia_list_time_intervals`, `zia_get_time_interval` | `zia_create_time_interval`, `zia_update_time_interval`, `zia_delete_time_interval` | Reusable schedule object referenced by all rule types via the `time_windows` field. `start_time`/`end_time` are minutes from midnight (0-1439); `days_of_week` accepts `EVERYDAY`, `SUN`-`SAT`. |

All `update_*_rule` tools in this table apply the **silent backfill** pattern for `name` and `order` (see Critical Gotchas). The `zia_update_time_interval` tool applies the same pattern for `name`, `start_time`, `end_time`, and `days_of_week`. The `zia_update_ips_signature_rule` tool applies it for `name` and `rule_text` — IPS signatures have no `order` field, so the load-bearing pair shifts to the identifying name and the signature body itself. Adding a new rule resource? Follow this same shape — never multiplex actions, always backfill the load-bearing identifying fields on update.

### ZIA Tenant-Wide Singletons (ATP Policy + Malware Protection + Advanced Settings)

Some ZIA configuration is not rule-shaped but a single mutable object owned by the tenant. The **Advanced Threat Protection (ATP)** family — both the policy block and the Malware Protection sub-family — lives here, as do the **Administration → Advanced Settings** knobs. They all follow a different update contract than the rule families above.

| Resource | Module | Read | Write | Notes |
|----------|--------|------|-------|-------|
| ATP Policy Settings | `atp_settings.py` | `zia_get_atp_settings` | `zia_update_atp_settings` | Tenant-wide ATP block (risk tolerance, C2/malware/phishing toggles). **Strict PUT-replace** — no silent backfill. Any field omitted is reset to the API default. Always fetch via `zia_get_atp_settings` first, merge changes onto the response, then submit the complete payload. |
| ATP Security Exceptions | `atp_settings.py` | `zia_get_atp_security_exceptions` | `zia_update_atp_security_exceptions` | Tenant-wide ATP bypass URL list (the allowlist). Update is a full-list replace — pass the complete URL set you want to remain on the allowlist, not just the delta. |
| ATP Malicious URLs | `atp_settings.py` | `zia_list_atp_malicious_urls` | `zia_add_atp_malicious_urls`, `zia_delete_atp_malicious_urls` | Block-list (denylist) management via add/delete operations rather than full-replace; conceptually opposite of the security-exceptions allowlist. The delete tool is HMAC-confirmed. |
| ATP Malware Policy | `atp_malware_protection.py` | `zia_get_atp_malware_policy` | `zia_update_atp_malware_policy` | File-handling toggles (`block_unscannable_files`, `block_password_protected_archive_files`). PUT-replace with positional booleans — both arguments are required on every update. |
| ATP Malware Inspection | `atp_malware_protection.py` | `zia_get_atp_malware_inspection` | `zia_update_atp_malware_inspection` | Traffic-direction toggles (`inspect_inbound`, `inspect_outbound`). PUT-replace with positional booleans. |
| ATP Malware Protocols | `atp_malware_protection.py` | `zia_get_atp_malware_protocols` | `zia_update_atp_malware_protocols` | Protocol toggles (`inspect_http`, `inspect_ftp_over_http`, `inspect_ftp`). PUT-replace with positional booleans. **SDK quirk:** the response-parser on the SDK's update returns the wrong field names (`inspectInbound` / `inspectOutbound` instead of `inspectHttp` / `inspectFtpOverHttp`). The MCP tool transparently re-fetches via `zia_get_atp_malware_protocols` after a successful PUT so callers get authoritative state. |
| Malware Settings | `atp_malware_protection.py` | `zia_get_malware_settings` | `zia_update_malware_settings` | 16-field threat-class block (virus / trojan / worm / adware / spyware / ransomware / remote-access tool / unwanted-applications, each with a matching `*_capture` PCAP toggle). **Strict PUT-replace** — any omitted field is reset to `False`. Always fetch via `zia_get_malware_settings`, mutate, then send the full dict back. Unknown keys are silently dropped (only the 16 documented snake_case attributes round-trip through the SDK model). |
| Advanced Settings | `advanced_settings.py` | `zia_get_advanced_settings` | `zia_update_advanced_settings` | The *Administration → Advanced Settings* block — ~50 knobs across authentication / Kerberos / digest bypass URLs and apps, DNS optimization on transparent proxy (IPv4 + IPv6), Office 365 one-click, UI session timeout, surrogate IP enforcement, HTTP tunnel handling, domain-fronting block, HTTP/2 non-browser traffic, ECS-for-all, dynamic user risk, CONNECT-host / SNI mismatch handling, and SIPA XFF header insertion. **Strict PUT-replace** — the SDK forwards the payload as `**kwargs`, so any field omitted is reset to API default (or `[]` for list fields). Always fetch via `zia_get_advanced_settings` first, merge changes, then send the full dict back. |

**Module layout convention.** Every tool backed by `zscaler.zia.atp_policy.ATPPolicyAPI` lives in **one file** (`atp_settings.py` — 7 tools across ATP policy, security exceptions, and the malicious-URL denylist), every tool backed by `zscaler.zia.malware_protection_policy.MalwareProtectionPolicyAPI` lives in **one file** (`atp_malware_protection.py` — 8 tools across the four malware singletons), and every tool backed by `zscaler.zia.advanced_settings.AdvancedSettingsAPI` lives in **one file** (`advanced_settings.py` — 2 tools for the singleton). One SDK API class → one MCP module → one logical surface. The historical `atp_malicious_urls.py` split was unwound (PR #65) for this reason.

The first three rows (ATP policy + security exceptions + malicious URLs) live in the dedicated **`zia_atp_policy`** toolset; the four malware-family rows live in **`zia_atp_malware`**; the Advanced Settings row lives in its own **`zia_advanced_settings`**. All three toolsets are `default=True`. Splitting them is intentional — each surface has its own update contract and operationally-distinct audit posture, and admins frequently want to enable or audit only one of them.

All three of these singleton surfaces still require ZIA activation (`zia_activate_configuration`) after writes, like every other ZIA write operation.

## ZMS (Zscaler Microsegmentation)

ZMS tools use the ZMS GraphQL API (`/zms/graphql`) for querying microsegmentation data. All ZMS tools are **read-only** (queries only — no mutations).

### ZMS Architecture

- **GraphQL-based**: All ZMS operations use GraphQL queries via `POST /zms/graphql`
- **Customer-scoped**: Every query requires `ZSCALER_CUSTOMER_ID` (automatically resolved from env)
- **Paginated responses**: Results use `nodes[]` + `pageInfo { pageNumber, pageSize, totalCount, totalPages }`
- **Two pagination patterns**: Some domains use `page`/`pageSize` (agents, agent_groups, nonces); others use `pageNum`/`pageSize` (resources, resource_groups, policy_rules, app_zones, app_catalog, tags)

### ZMS Domains (9 domains, 20 tools)

| Domain | Tools | SDK path |
|--------|-------|----------|
| Agents | `zms_list_agents`, `zms_get_agent_connection_status_statistics`, `zms_get_agent_version_statistics` | `client.zms.agents` |
| Agent Groups | `zms_list_agent_groups`, `zms_get_agent_group_totp_secrets` | `client.zms.agent_groups` |
| Resources | `zms_list_resources`, `zms_get_resource_protection_status`, `zms_get_metadata` | `client.zms.resources` |
| Resource Groups | `zms_list_resource_groups`, `zms_get_resource_group_members`, `zms_get_resource_group_protection_status` | `client.zms.resource_groups` |
| Policy Rules | `zms_list_policy_rules`, `zms_list_default_policy_rules` | `client.zms.policy_rules` |
| App Zones | `zms_list_app_zones` | `client.zms.app_zones` |
| App Catalog | `zms_list_app_catalog` | `client.zms.app_catalog` |
| Nonces | `zms_list_nonces`, `zms_get_nonce` | `client.zms.nonces` |
| Tags | `zms_list_tag_namespaces`, `zms_list_tag_keys`, `zms_list_tag_values` | `client.zms.tags` |

### ZMS Gotchas

- **`customer_id` is always required.** Resolved automatically from `ZSCALER_CUSTOMER_ID` env var. If missing, tools return an error.
- **Tag hierarchy is three levels**: namespace → key → value. To list tag values, you need the namespace origin and tag key ID (navigate top-down).
- **Resource groups have two types**: `ManagedResourceGroup` (tag-based membership) and `UnmanagedResourceGroup` (CIDR/FQDN-based). The GraphQL uses inline fragments.
- **`eyez_id`** is the unique identifier for agents, agent groups, and nonces — not a numeric ID.
- **`namespace_origin`** for tag values must be one of: `CUSTOM`, `EXTERNAL`, `ML`, `UNKNOWN`.
- **Policy rules have `fetchAll` flag** which bypasses pagination. Use sparingly on large tenants.

## JMESPath Client-Side Filtering

All list tools across every service support JMESPath client-side filtering via an optional `query` parameter. This leverages the `jmespath` library (already a dependency of `zscaler-sdk-python`) to filter and project results after the API call returns.

### Architecture

- **`zscaler_mcp/common/jmespath_utils.py`** — shared `apply_jmespath(data, expression)` helper used by all services
- **`zscaler_mcp/tools/zms/__init__.py`** — ZMS-specific wrapper that preserves the `[result]` envelope for GraphQL responses
- When `query` is `None`, results pass through unchanged (full backward compatibility)
- Invalid expressions return `[{"error": "Invalid JMESPath expression: ..."}]` instead of crashing

### How It Works

Every `*_list_*` tool (88 total across ZIA, ZPA, ZDX, ZCC, ZTW, ZID, EASM, ZMS) accepts an optional `query` parameter. The JMESPath expression is applied to the tool's result data **after** the API call completes:

```python
# Non-ZMS tools: result is a list of dicts
results = [x.as_dict() for x in items]
return apply_jmespath(results, query)  # filters the list

# ZMS tools: result is a GraphQL connection dict {"nodes": [...], "page_info": {...}}
return apply_jmespath_query(result, query)  # filters within the envelope
```

### Expression Syntax

Standard [JMESPath](https://jmespath.org/) syntax. Field names are **snake_case** (the SDK converts camelCase API responses). Examples:

| Service | Expression | What it does |
|---------|-----------|--------------|
| ZIA | `[?name=='HQ'].{name: name, id: id}` | Find location named "HQ", project name+id |
| ZPA | `[?enabled==\`true\`]` | Filter to enabled application segments |
| ZDX | `[?platform=='Windows'].{user_name: user_name}` | Windows devices, project usernames |
| ZCC | `[*].{name: name, os_type: os_type}` | Project name and OS for all devices |
| ZMS | `nodes[?cloud_provider=='AWS']` | Filter resources to AWS workloads |
| EASM | `results[?severity=='critical']` | Filter findings to critical severity |

### Adding JMESPath to a New List Tool

1. Import: `from zscaler_mcp.common.jmespath_utils import apply_jmespath`
2. Add `query` parameter before `service` in the signature
3. Wrap the success return: `return apply_jmespath(results, query)`
4. **Declare the return type as `Any`** — never `List[dict]` / `List[str]`. JMESPath expressions like `length(@)`, `[*].name`, or `sum(...)` produce scalars or differently-shaped lists; a strict element type causes the MCP/Pydantic output validator to reject the response, which forces the AI agent to narrate around the error and exposes implementation details (JMESPath, validation failures) to the user. Document the happy-path shape in the docstring instead.
5. Update the tool description in `services.py` to mention JMESPath support

### Response Style for AI Agents

The user is asking a **business question**. Tool plumbing — JMESPath, server-side `search` keys, pagination, output validation, type coercion, fallback retries — is internal optimization. Never narrate it.

**Plain-language answers only.** Translate tool output into the answer the admin actually wanted.

**Empty list responses are authoritative — do not fan out retries.** The `search` parameter on every `*_list_*` tool is a server-side substring match on the resource's `name` field. **An empty result means the resource does not exist by that name. Stop.** Do NOT then re-call the same tool with split keywords, broader JMESPath projections, larger `page_size`, no filter, or a different projection "to double-check" — each costs a round trip and adds zero information. The single allowed follow-up is asking the user to clarify the name.

- ❌ Five calls in sequence: `search="DataCenter Switches SSH"` → empty → `query="[?contains(name,'DataCenter') || contains(name,'SSH')]"` → `query="[*].{id,name}", page_size=200` → unfiltered list → "let me drop the projection in case it's too aggressive".
- ✅ One call: `search="DataCenter Switches SSH"` → empty → *"I can't find an application segment named `DataCenter Switches SSH`. Want me to use a different name?"*

**Don't narrate strategy pivots.** If the first call returns nothing or fails and a retry is genuinely warranted, retry quietly. The user cares whether you found the answer, not which knob you turned.

- ❌ *"The `search` filter came back empty. The tool's `search` may not be a substring match. Let me list without the filter and apply JMESPath instead so I'm not relying on server-side fuzzy matching."*
- ✅ *"I didn't find a connector group by that name. Here's what's in the tenant: …"*  (or just proceed silently to the second attempt and report the final answer)

**Don't claim a tool doesn't exist without checking.** If a `*_get_*` / `*_create_*` / `*_update_*` / `*_delete_*` tool is visible, the matching `*_list_*` almost certainly exists too — search the registry by service prefix and verb before declaring a gap. False "no such tool" claims send admins down the wrong path. Concrete examples of correct list tools that have been mis-claimed as missing: `zpa_list_app_connector_groups`, `zpa_list_segment_groups`, `zpa_list_application_segments`.

**Don't expose internal field names or validators.** Pydantic messages, MCP output-validator errors, and SDK tuple shapes (`(result, response, err)`) are noise. Convert them into a one-line user-facing summary.

**Examples of plain-language responses:**

- User: *"how many ZIA DNS rules exist?"* → Agent: *"There are **19** ZIA DNS firewall rules in the tenant."*  ❌ Do **not** say *"The JMESPath `length(@)` returned 19 before hitting the validation error — so there are 19 rules."*
- User: *"list the names of my SSL inspection rules"* → Agent lists the names. ❌ Do not mention *"I projected `[*].name`."*
- User: *"create the segment"* and the lookup returns empty → Agent: *"I can't find any application segment named X. Want me to create one or use a different name?"* ❌ Do **not** say *"The `search` filter returned zero rows; possibly server-side substring mismatch."*

### Tool Discovery via Toolsets

Tool discovery for AI agents goes through the always-on toolset meta-tools, **not** JMESPath against the tool catalog. The flow is:

1. `zscaler_list_toolsets(name_contains=..., description_contains=..., service=...)` — find the relevant toolset (logical grouping per resource family per service). Each row carries `currently_enabled`, `tool_count`, `can_enable`, and (when `can_enable: false`) `unavailable_reason`.
2. `zscaler_get_toolset_tools(toolset=..., name_contains=..., description_contains=...)` — drill into a toolset to confirm a specific tool is callable. Each row carries `available` and (when `available: false`) `unavailable_reason`.
3. `zscaler_get_available_services` — service-level overview when you need a one-shot "what is loaded right now". Use for status, not as a discovery primitive.

A `zscaler_search_tools` meta-tool existed in earlier versions; it was removed because it duplicated the toolset discovery path and encouraged the agent to second-guess `available: false` results. The JMESPath helper that powered it lives on (and is still exported by `zscaler_mcp/common/jmespath_utils.py`) — it remains the post-processing engine for the optional `query` parameter on every `*_list_*` tool that returns paginated tenant data.

## Write Operations — Safety Rules

1. **Write tools are disabled by default.** Enable with `--write-tools` flag and an explicit allowlist (wildcards supported). Example: `--write-tools "zpa_create_*,zia_update_*"`.
2. **Always confirm before mutating.** Read operations are safe. Create/update/delete operations modify the live Zscaler environment. Ask the user before executing write operations.
3. **Delete operations require HMAC-SHA256 confirmation.** Destructive actions return a confirmation token that must be passed back to confirm. Controlled by `ZSCALER_MCP_SKIP_CONFIRMATIONS` and `ZSCALER_MCP_CONFIRMATION_TTL`.
4. **Always list/get first** to understand current state before creating or modifying resources.
5. **Pagination:** List tools support `page` and `page_size` parameters. For large tenants, paginate rather than fetching everything.
6. **ZPA policy rule ordering:** New rules are appended at the end by default. Policy rules are evaluated top-to-bottom — order matters for access control.

### Confirmation Token Flow (Elicitation)

Destructive write operations (delete, bulk update) use cryptographic confirmation:

1. Tool returns `{"confirmation_required": true, "token": "<HMAC-SHA256>", "expires_at": "..."}` instead of executing
2. The token is bound to: tool name, resource ID, action, and timestamp
3. Agent must present the token back to confirm execution within the TTL (default 5 minutes)
4. Tokens are single-use and tamper-proof — prompt injection cannot forge or replay them

Implementation: `zscaler_mcp/common/elicitation.py` — `generate_confirmation_token()` and `verify_confirmation_token()`.

## ZDX Filtering

ZDX query tools accept optional filters that significantly improve result quality:

- `location_id`: Filter by office/site location
- `department_id`: Filter by department
- `geo_id`: Filter by geolocation
- `since`: Hours to look back (default 2)

Always ask the user for scope before running broad ZDX queries on large tenants.

## Environment

Required env vars (set in `.env`):

- `ZSCALER_CLIENT_ID` — OneAPI client ID from the ZIdentity console
- `ZSCALER_CLIENT_SECRET` — OneAPI client secret (or `ZSCALER_PRIVATE_KEY` for JWT-based auth)
- `ZSCALER_VANITY_DOMAIN` — ZIdentity vanity domain (e.g. `acme.zsapi.net`)
- `ZSCALER_CUSTOMER_ID` — Zscaler customer/tenant ID; required when calling ZPA tools

Optional:

- `ZSCALER_PRIVATE_KEY` — PEM-encoded private key for JWT auth (used in place of `ZSCALER_CLIENT_SECRET`)
- `ZSCALER_CLOUD` — cloud override (e.g. `BETA`, `zscalertwo`)
- `ZSCALER_MCP_USER_AGENT_COMMENT` — appended to the SDK's `User-Agent` header

Server & security env vars:

- `ZSCALER_MCP_TRANSPORT` — Transport mode: `stdio` (default), `sse`, `streamable-http`
- `ZSCALER_MCP_HOST`, `ZSCALER_MCP_PORT` — Bind address for HTTP transports (default `127.0.0.1:8000`)
- `ZSCALER_MCP_AUTH_ENABLED` — Enable MCP client authentication (`true`/`false`, HTTP only)
- `ZSCALER_MCP_AUTH_MODE` — Auth mode: `api-key`, `jwt`, or `zscaler` (or use `auth=` param for OAuth 2.1 with DCR)
- `ZSCALER_MCP_TLS_CERTFILE`, `ZSCALER_MCP_TLS_KEYFILE` — TLS certificate and key paths
- `ZSCALER_MCP_ALLOW_HTTP` — Allow plaintext HTTP on non-localhost (`true`/`false`)
- `ZSCALER_MCP_ALLOWED_HOSTS` — Comma-separated allowed Host header values (supports wildcards)
- `ZSCALER_MCP_ALLOWED_SOURCE_IPS` — Comma-separated allowed client IPs/CIDRs
- `ZSCALER_MCP_DISABLED_TOOLS` — Comma-separated tool patterns to exclude (wildcards via fnmatch)
- `ZSCALER_MCP_DISABLED_SERVICES` — Comma-separated service names to exclude
- `ZSCALER_MCP_TOOLSETS` — Comma-separated toolset ids to enable (e.g. `zia_url_filtering,zpa_app_segments`). Special values: `default` (curated default-on subset) and `all` (every toolset). When unset, every toolset whose service is enabled is loaded. The `meta` toolset is always loaded. See `docs/guides/toolsets.md`.
- `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER` — Skip the OneAPI entitlement filter (`true`/`false`). When `false` (default), the server intersects the selected toolsets with the products entitled by the OneAPI bearer token (`service-info[].prd`). Set `true` as an emergency override.
- `ZSCALER_MCP_WRITE_ENABLED` — Enable write tools (`true`/`false`)
- `ZSCALER_MCP_WRITE_TOOLS` — Comma-separated write tool patterns to allow (wildcards)
- `ZSCALER_MCP_SKIP_CONFIRMATIONS` — Skip HMAC confirmation for destructive ops (`true`/`false`)
- `ZSCALER_MCP_CONFIRMATION_TTL` — Confirmation token TTL in seconds (default 300)
- `ZSCALER_MCP_DISABLE_HOST_VALIDATION` — Disable host header checks (`true`/`false`)
- `ZSCALER_MCP_LOG_TOOL_CALLS` — Enable tool-call audit logging (`true`/`false`)
- `ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION` — Disable defense-in-depth output sanitization (BiDi / zero-width / HTML / code-fence stripping). On by default. Use only for diagnostics — disabling it removes a prompt-injection defense layer. (`true`/`false`)

## CLI Flags

- `--transport` — Transport mode (`stdio`, `sse`, `streamable-http`)
- `--services` — Comma-separated services to enable (e.g., `zia,zpa,zdx`)
- `--disabled-services` — Comma-separated services to exclude (e.g., `zcc,zdx`)
- `--disabled-tools` — Comma-separated tool patterns to exclude (wildcards: `"zcc_*,zia_list_device*"`)
- `--toolsets` — Comma-separated toolset ids to enable. Use `default` for the curated default-on subset, `all` for everything (e.g. `"zia_url_filtering,zpa_app_segments"` or `"default"`). See `docs/guides/toolsets.md`.
- `--no-entitlement-filter` — Skip the OneAPI entitlement filter that trims `selected_toolsets` to the products the configured `ZSCALER_CLIENT_ID` is entitled to. Emergency override only; the filter is non-fatal by default and skips itself on any failure.
- `--write-tools` — Enable and allowlist write tools (wildcards: `"zpa_create_*,zia_update_*"`)
- `--generate-auth-token` — Generate an API key for MCP client authentication
- `--list-tools` — List all available tools and exit
- `--generate-docs` — Refresh the auto-generated regions of `docs/guides/supported-tools.md`, `README.md`, and `docs/guides/toolsets.md` from the live tool inventory, then exit. Run after adding/renaming/removing a tool. See "Auto-generated docs" under Development.
- `--check-docs` — Exit 0 if every auto-generated Markdown region is in sync with the live tool inventory; exit 1 (with a list of stale files) otherwise. Designed for CI.
- `--user-agent-comment` — Custom User-Agent suffix for API calls
- `--host` — HTTP bind address (default `127.0.0.1`)
- `--port` — HTTP listen port (default `8000`)
- `--log-tool-calls` — Enable tool-call audit logging (logs tool name, args, duration, result summary)
- `--dotenv-path` — Explicit path to the `.env` file to load. Overrides the default search (project root + CWD). Recorded in the PID file so `zscaler-mcp reload` / `restart` re-read the same source. (env: `ZSCALER_MCP_DOTENV_PATH`)
- `--pid-file` — Override the PID file location used by the lifecycle subcommands. Defaults to `/var/run/zscaler-mcp.pid` (or `/tmp/zscaler-mcp.pid` if `/var/run` is not writable). Set per instance when running multiple servers on the same host. (env: `ZSCALER_MCP_PID_FILE`)
- `--version` — Print version and exit

### Lifecycle Subcommands

In addition to the top-level flags above, the CLI exposes five subcommands for managing a running server. They are mutually exclusive with the serve path — running `zscaler-mcp` with no subcommand starts the server as before.

- `zscaler-mcp reload` — Soft reload (SIGHUP). Re-reads `.env` and re-applies env-driven toggles. MCP sessions and the listening socket survive.
- `zscaler-mcp restart` — Hard restart (SIGUSR2). Re-reads `.env`, then `os.execvp`'s a fresh Python interpreter with the original argv. Same PID, fresh memory, fresh env. Sessions die — clients reconnect.
- `zscaler-mcp status` — Print PID, uptime, transport, port, and `.env` path of the running server (or report none running).
- `zscaler-mcp stop` — Clean shutdown (SIGTERM, no respawn). Same signal Docker uses, so the running server has no SIGTERM handler installed and falls through to FastMCP/uvicorn's default shutdown.
- `zscaler-mcp update` — Check GitHub Releases (PyPI JSON fallback) for a newer version and report installed vs latest plus a channel-correct upgrade instruction. With `--apply` (pip/venv and system installs only): pin-upgrade via `pip install --upgrade zscaler-mcp==<latest>` in the **running server's** interpreter environment (falls back to the CLI's own when no server is running), verify the install in a fresh interpreter, then SIGUSR2-restart the server so the execvp re-imports the new code in place. `--apply` refuses with exit 2 on the `container` channel (the image is the source of truth; in-place changes are lost on recreate — and the shipped image's uv-built venv has no pip anyway), on `uvx` (uv re-resolves from PyPI itself), and on `editable` installs (update the checkout via git). Channel detection: `/.dockerenv` / PID-1 cgroup → container; `uv` in `sys.prefix` → uvx; `direct_url.json` editable flag or missing dist-info → editable; else venv/system.

See **Process Lifecycle Management** below for the full design.

## Tool-Call Audit Logging

Opt-in logging of every tool invocation for troubleshooting and observability. Controlled by `--log-tool-calls` or `ZSCALER_MCP_LOG_TOOL_CALLS=true`. This is intentionally separate from `--debug` to avoid excessive verbosity during normal debugging.

### What It Logs

Every tool call produces two log lines via the `zscaler_mcp.audit` logger:

```text
[TOOL CALL] zia_list_locations | args: {page: 1, page_size: 50, name: "HQ"}
[TOOL OK]   zia_list_locations | 342ms | 15 items
```

On error:

```text
[TOOL CALL] zms_list_resources | args: {page_num: 1}
[TOOL ERR]  zms_list_resources | 1204ms | ConnectionError: timeout
```

### Security

Sensitive parameters (password, secret, token, key, credential, and any parameter name containing these substrings) are automatically redacted to `***REDACTED***`. Full response data is never logged — only a summary (item count, error message).

### Implementation

- **`zscaler_mcp/common/tool_helpers.py`** — `_wrap_with_audit()` wraps every tool function at registration time. The wrapper is a no-op when logging is disabled (zero overhead).
- The audit wrapper covers all tools: service tools (via `register_read_tools`/`register_write_tools`) and the always-on meta-tools (`zscaler_check_connectivity`, `zscaler_get_available_services`, `zscaler_list_toolsets`, `zscaler_get_toolset_tools`, `zscaler_enable_toolset`).
- Uses a dedicated logger (`zscaler_mcp.audit`) so log output can be filtered independently.

## Output Sanitization

Defense-in-depth against prompt-injection payloads embedded in admin-editable Zscaler resources. Free-form fields like rule descriptions, label descriptions, location names, and custom URL category names are returned to the agent as-is by the Zscaler APIs. If an attacker — or a careless admin — stuffs invisible Unicode characters, raw HTML, or fake code fences into one of those fields, the agent that consumes the tool response can be tricked into following injected instructions.

The server therefore runs every string in every tool result through a three-stage sanitizer **before it leaves the wire**.

### Three Stages

1. **Invisible / control-character stripping.** Removes zero-width characters (ZWSP, ZWJ, ZWNJ, word joiner, invisible times/separator/plus), the full BiDi control range (LRO, RLO, LRE, RLE, PDF, LRI, RLI, FSI, PDI, LTR/RTL marks), Arabic letter mark, soft hyphen, BOM, and any unassigned/private/format-category codepoint. NBSP (U+00A0) is normalised to a regular space. Tab, LF, and CR survive (multi-line descriptions are legitimate).
2. **HTML / Markdown sanitization.** Uses [`bleach`](https://bleach.readthedocs.io/) (Mozilla's de-facto Python equivalent of `bluemonday`) configured with an empty tag/attribute allowlist — every HTML tag and HTML comment is stripped; printable text is kept. A regex pass collapses Markdown image syntax `![alt](url)` to `alt` (so embedded URLs never reach the agent) and Markdown link syntax `[text](url)` to `text (url)` (URL is visible but no longer a directive).
3. **Code-fence info-string filtering.** Markdown fenced blocks (` ``` ` and `~~~`) whose info-string contains role/override tokens (`system`, `user`, `assistant`, `tool`, `function`, `developer`, `ignore`, `override`, `instruction`, `prompt`, `role`) get their info-string rewritten to `text`. The code body itself is preserved. Empty info-strings and legitimate language tags (`python`, `json`, …) pass through.

Sanitization is applied recursively to dicts, lists, and tuples. Dict keys are **not** sanitized (they're machine-defined field names; touching them would break callers that index by key). Bounded recursion (depth 32) protects against pathological structures.

### Wiring

`_wrap_with_audit()` in `zscaler_mcp/common/tool_helpers.py` always passes results through `sanitize_value()`. Every tool — read, write, or meta — inherits the defense for free. Sanitization runs even when audit logging is off; the audit wrapper is no longer "no-op when logging disabled" (it is now "no-op for logging when logging disabled, but always sanitizes").

### Opt-Out

Sanitization is **on by default**. Operators can disable it for diagnostics:

```bash
export ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION=true
```

Disabling sanitization removes a defense-in-depth layer; only do this temporarily and under audit. There is no CLI flag — this is intentional, the env var makes the choice deliberate.

### Implementation

- **`zscaler_mcp/common/sanitize.py`** — `sanitize_text()` for single strings, `sanitize_value()` for recursive traversal, plus three private stage functions (`_strip_invisible`, `_sanitize_html_markdown`, `_sanitize_code_fences`).
- **`tests/test_sanitize.py`** — 46 tests covering golden injection inputs (RLO override, ZWSP, embedded `<script>`, fake `system` fence, etc.) and integration through the audit wrapper.
- Dependency: `bleach>=6.2.0` (added to `pyproject.toml`).

## Process Lifecycle Management

Operators can reconfigure a running server (locally or inside a Docker container) without recreating the container, via five CLI subcommands: `zscaler-mcp reload`, `zscaler-mcp restart`, `zscaler-mcp status`, `zscaler-mcp stop`, `zscaler-mcp update`.

### Design

When the server starts (after `parse_args()` succeeds, before `server.run()`), it writes a JSON PID file containing the running PID, start time, transport, host:port, the resolved `.env` path, the original `argv`, and the Python interpreter path. Two signal handlers are then installed in the running server:

- **SIGHUP → soft reload.** Re-reads `.env` with `override=True` (so stale values get replaced), then re-applies env-driven runtime toggles (currently: `ZSCALER_MCP_LOG_TOOL_CALLS`). The Zscaler SDK client has no module-level cache — it's created on every tool call — so once new credentials land in `os.environ`, the next tool call already picks them up. The auth-middleware token cache is keyed by credential hash, so credential rotation naturally misses old entries and re-validates against the new values. **MCP sessions and the listening socket survive.** This is the right path when you only changed a knob (audit logging, log level, a non-credential env var).
- **SIGUSR2 → hard restart.** Re-reads `.env` into `os.environ` (so the child inherits fresh values immediately), removes the PID file, then `os.execvp`'s a fresh Python interpreter with the original `argv`. **Same PID** (Docker doesn't notice the swap), fresh memory, fresh env, fresh module imports, fresh entitlement-filter result. **Sessions die — clients reconnect.** This is the right path when you rotated credentials, changed `--toolsets` selection, flipped `--enable-write-tools`, swapped vanity domain, etc. — anything that's read once at startup.
- **SIGTERM / SIGINT → not handled.** Deliberately. The standard FastMCP/uvicorn signal handling kicks in, which is what `docker stop`, `systemctl stop`, and Ctrl+C all expect. `zscaler-mcp stop` simply sends SIGTERM and lets that path do its job.

The atexit-registered cleanup removes the PID file on clean shutdown so `zscaler-mcp status` doesn't lie about a dead PID.

### Env-source classification (the "what will actually change?" question)

The reload/restart messaging — and the `status` output — is gated by `_classify_env_source()` so the CLI tells the truth instead of always claiming it will "re-read .env". The classifier checks two things: the `dotenv_path` recorded in the PID file (set at server startup), and whether a `.env` exists in any of the default search paths now (which catches the `docker cp` workflow). Four branches:

| `dotenv_path` in PID file | File exists at that path? | Default-path `.env` present now? | Label | What `reload`/`restart` actually does |
|---|---|---|---|---|
| Set | Yes | n/a | `live` (or `live (bind-mounted)` if path is `/app/.env`) | Re-reads the file, picks up host-side edits, then execs |
| Set | No | Yes | `fresh-discovery` | SIGHUP no-ops, but `restart` execs a fresh process that re-discovers and loads the newly-placed `.env`. **`docker cp` workflow.** |
| Set | No | No | `missing` | Logs a warning, skips the re-read, execs with same `os.environ`. Common case: container started with `--env-file` only, no bind mount, no `docker cp`. |
| `None` | n/a | Yes | `fresh-discovery` | Same as above — fresh process discovers the `.env` placed since startup. |
| `None` | n/a | No | `none` | Skips the re-read entirely. Common case: AgentCore deployments using Secrets Manager, or any deploy that uses container env-vars without a `.env` file. |

The "missing" and "none" branches are explicitly NOT a bug — they reflect the underlying constraint that env vars in a running container's PID 1 are immutable from outside the container unless you bind-mount a file PID 1 can re-read (or you inject one with `docker cp`). The CLI surfaces this fact instead of silently claiming success. AgentCore deploys (`none` branch) still benefit from `restart`: re-importing `zscaler_mcp.config` triggers a fresh Secrets Manager fetch on the new process boot, picking up rotated secrets there.

### Why Docker `--env-file` snapshots survive container `stop`/`start`

A common mental-model bug worth pinning here: `docker run --env-file=./.env ...` reads the host `.env` **once** at `docker run` time and copies the resolved `KEY=VALUE` pairs into the container's `Config.Env` metadata (visible via `docker inspect`). After that moment, the container has **no link** to the host file — you could delete `./.env` on the host and the container still holds the values. `docker stop && docker start <same-container>` reuses `Config.Env` from the metadata; **it does NOT re-read the host file**. The only ways to change `Config.Env` are (a) `docker rm` + `docker run` (full recreate, picks up the current host `.env`), or (b) bind-mount the file inside so PID 1 can re-read it on reload/restart. Likewise, `docker exec <ctr> sh -c 'export FOO=bar'` mutates a transient child shell's env — PID 1's env is untouched, since no Unix API lets one process write another's environment.

### Updating env vars in a running container — three workflows

| Workflow | Recreates container? | Picks up env changes? | When to use |
|---|---|---|---|
| **A.** `docker rm -f && docker run --env-file=./.env ...` | Yes | Yes (Docker re-reads host `.env` at run-time) | Always works. Disruptive — active sessions die, image cache cold for that container. |
| **B.** Bind-mount `.env` at `/app/.env` once, then `zscaler-mcp restart` after every host-side edit | No (one-time setup) | Yes (PID 1 re-reads `/app/.env` on every restart) | Recommended long-term workflow. Default in `scripts/setup-mcp-server.py`. |
| **C.** `docker cp ./.env <container>:/app/.env && docker exec <container> zscaler-mcp restart` | No | Yes (fresh execvp'd process re-discovers `/app/.env`) | Easiest one-off fix for an already-running container without a bind mount. No setup change required. |

Workflow C is what makes `restart` valuable for containers that are already running without a bind mount — the operator doesn't have to recreate just to swap a credential. The "fresh-discovery" classifier branch is what tells the operator this is about to work.

### PID file location

In priority order:

1. `--pid-file <path>` / `ZSCALER_MCP_PID_FILE`
2. `/var/run/zscaler-mcp.pid` (typical inside containers running as a user with write access there)
3. `/tmp/zscaler-mcp.pid`
4. `~/.zscaler-mcp/server.pid` (auto-created)

For multiple instances on the same host (e.g. one per port), set `ZSCALER_MCP_PID_FILE=/tmp/zscaler-mcp-8001.pid` per instance.

### .env file resolution

`zscaler_mcp/server.py::_resolve_dotenv_path()` resolves the `.env` source in this order, then records the absolute path in the PID file so reload/restart re-read the same source:

1. `--dotenv-path <path>` / `ZSCALER_MCP_DOTENV_PATH`
2. `<project_root>/.env` (editable install)
3. `<cwd>/.env`

The first-pass load happens **before** `parse_args()` (so env-var defaults resolve correctly); the path is then re-resolved after parsing to honour `--dotenv-path` and the final value lands in the PID file.

### Container deployment

For `zscaler-mcp restart` to pick up live `.env` edits inside a container, the `.env` file must be **bind-mounted** (not just passed via `--env-file`, which snapshots values at container start). The `scripts/setup-mcp-server.py` setup script defaults to bind-mounting:

```bash
docker run -d --name zscaler-mcp-server \
  --env-file /path/to/.env \                           # boot-time injection
  -v /path/to/.env:/app/.env:ro \                      # live re-read on restart
  -e ZSCALER_MCP_DOTENV_PATH=/app/.env \
  zscaler/zscaler-mcp-server:latest --transport streamable-http
```

Then to apply a config change:

```bash
$EDITOR /path/to/.env                                  # edit on the host
docker exec zscaler-mcp-server zscaler-mcp restart     # re-read + execvp inside container
```

Same workflow for `reload` (cheap, sessions survive) when only a runtime toggle changed.

Operators who want the snapshot-only behaviour can opt out via `setup-mcp-server.py --legacy-env-file`.

### Cross-platform

SIGHUP and SIGUSR2 are Unix-only. On Windows the `reload`/`restart` subcommands print a clear error and exit 2; `status` works (just reads the PID file); `stop` falls back to SIGTERM. Native Windows operators must restart their supervisor (Docker Desktop, NSSM, etc.) directly. Container deployments are unaffected — the container OS is Linux.

### Implementation

- **`zscaler_mcp/lifecycle.py`** — PID-file dataclass + read/write/remove, signal-handler installer (`install_serve_handlers`), five `cmd_*` subcommand entry points (`cmd_reload`, `cmd_restart`, `cmd_status`, `cmd_stop`, `cmd_update`), argparse subparser registration (`register_subparsers`), the soft-reload helper (`_do_soft_reload`), and the update machinery (`_fetch_latest_version` — GitHub Releases primary / PyPI fallback, `_detect_install_channel`, `_apply_update`). The pip upgrade always runs in the CLI process, never inside the server — the server only ever receives the SIGUSR2 that makes its execvp re-import the already-updated venv.
- **`zscaler_mcp/server.py::_resolve_dotenv_path()`** — single source of truth for `.env` discovery, recorded in the PID file.
- **`zscaler_mcp/server.py::main()`** — wires lifecycle: short-circuits to `lifecycle.dispatch()` for subcommands, otherwise writes the PID file + installs handlers + atexit-registers cleanup before calling `server.run()`.
- **`zscaler_mcp/common/tool_helpers.py::refresh_tool_call_logging()`** — re-applies the `ZSCALER_MCP_LOG_TOOL_CALLS` toggle from current `os.environ`. Called by the SIGHUP handler.
- **`tests/test_lifecycle.py`** — 72 tests covering PID-file round-trip, default-path resolution, every subcommand against missing/stale/live PID files, the SIGHUP-triggered env reload (raises the signal against `os.getpid()` and asserts the env update lands), env-source classification (every branch including the `docker cp`-fed `fresh-discovery` path), reload/restart messaging accuracy, argparse integration, and the `update` subcommand (version-tuple ordering, GitHub→PyPI fallback, container/uvx/editable channel detection and `--apply` refusal, pip-failure rollback messaging, post-install verification mismatch, and the SIGUSR2 restart against a live PID).

## Development

- Package manager: `uv` (not pip, not poetry)
- Install: `make install-dev` or `uv pip install -e .`
- Dependencies: `make sync-dev-deps`
- Run locally: `uvx zscaler-mcp` (requires `.env` in working directory)
- Docker: `make docker-build && make docker-run` (stdio) or `make docker-run-http` (HTTP + auth)
- Lint: `ruff check .` and `ruff format .`
- Tests: `pytest tests/ --ignore=tests/e2e -v`
- Clean: `make clean`

### Adding a New Tool

1. Create module in `zscaler_mcp/tools/{service}/` with the tool function
2. Add the tool definition to the service class in `services.py` (in `read_tools` or `write_tools` list)
3. Import the tool function in the service class's `register_tools` method
4. The tool is automatically picked up by `register_read_tools()` / `register_write_tools()` and respects all filtering (enabled_tools, disabled_tools, write_tools)
5. **Refresh generated docs**: run `make generate-docs` (or `zscaler-mcp --generate-docs`) and commit the resulting changes to `docs/guides/supported-tools.md`, `README.md`, and `docs/guides/toolsets.md`. CI runs `--check-docs` and will fail the build if the committed docs are stale. See "Auto-generated docs" below.

### Adding a New Service

1. Create a new service class in `services.py` extending `BaseService`
2. Define `read_tools` and `write_tools` lists
3. Implement `register_tools()` method
4. Add the service to `_AVAILABLE_SERVICES` registry at the bottom of `services.py`
5. Create tool modules under `zscaler_mcp/tools/{service_name}/`

### Auto-generated docs

Three Markdown files are partially auto-generated from the live tool inventory. Edits to the generated regions are overwritten — change the source instead and re-run the generator:

| File | Region marker | Source of truth |
|------|---------------|-----------------|
| `docs/guides/supported-tools.md` | `<!-- generated:start tools -->` | Tool descriptions in `zscaler_mcp/services.py` (`read_tools` / `write_tools` lists). |
| `docs-site/docs/guides/supported-tools.md` | `<!-- generated:start tools -->` | Mirror of the above for the Docusaurus site. |
| `README.md` | `<!-- generated:start service-summary -->` | Per-service tool counts derived from the same source. |
| `docs/guides/toolsets.md` | `<!-- generated:start toolset-catalog -->` | Toolset metadata in `zscaler_mcp/common/toolsets.py` + per-toolset tool counts from the inventory. |
| `docs-site/src/data/toolsets.json` | (whole file) | Same source — feeds the docs-site React `ToolsetsCatalog` component which renders the card-grid view at `/docs/guides/toolsets`. The whole file is generated; there are no markers. |
| `integrations/anthropic/manifest.json` | (whole file) | MCPB (Claude Desktop Directory) bundle manifest. Static template + live tool inventory + version from `zscaler_mcp.__version__`. Owned by `zscaler_mcp/common/mcpb.py` (path is `mcpb.MANIFEST_RELATIVE_PATH`). Copied to the repo root only transiently at pack time. See "MCPB bundle" below. |

Outside the marker pairs (and outside whole-file targets), every file is fully hand-written and the generator never touches it. Whole-file targets are fully owned by the generator — manual edits get stomped on the next `make generate-docs`.

**Commands:**

- `make generate-docs` (or `zscaler-mcp --generate-docs`) — regenerate all three regions in place. Idempotent: re-running with no source changes performs no file writes.
- `make check-docs` (or `zscaler-mcp --check-docs`) — exit 0 when docs are in sync, exit 1 + list of stale files otherwise. Designed for CI; wired into `.github/workflows/tests.yml` as a dedicated step before the test suite runs.

### Auto-mirrored integration docs (docs-site)

The Docusaurus site at `docs-site/` re-publishes the canonical, video-rich integration walkthroughs that live under `integrations/`. Nine pages in `docs-site/docs/` are full-file mirrors — editing them by hand has no effect, the next sync run overwrites them. The mirror is driven by `docs-site/scripts/sync_integrations_to_docs.py` (stdlib-only Python; no zscaler-mcp deps). The script lives under `docs-site/scripts/` rather than the top-level `scripts/` folder because it's a maintainer-only build helper — `scripts/` is reserved for end-user-runnable entry points (today: `setup-mcp-server.py`).

| docs-site page | Source README |
|---|---|
| `deployment/azure.md` | `integrations/azure/README.md` |
| `deployment/gcp.md` | `integrations/google/README.md` |
| `integrations/google-adk.md` | `integrations/google/adk/README.md` |
| `integrations/aws-harness.md` | `integrations/aws/harness/README.md` |
| `integrations/claude.md` | `integrations/claude-code-plugin/README.md` |
| `integrations/cursor.md` | `integrations/cursor-plugin/README.md` |
| `integrations/gemini-cli.md` | `integrations/gemini-extension/README.md` |
| `integrations/kiro.md` | `integrations/kiro/README.md` |
| `integrations/github-registry.md` | `integrations/github/README.md` |

What the sync does on every run, per file:

1. **Image refs** — every `![alt](../../assets/foo.png)` rewrites to an absolute `https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/assets/foo.png` URL. This avoids duplicating binaries inside `docs-site/static/`; the trade-off is that the image must be committed to `master` before the dev preview can render it. For walkthrough screenshots that need to render immediately (before a push), copy them into `docs-site/static/img/` and reference them as `/img/<name>.png` — that path is served directly by Docusaurus regardless of master state.
2. **Relative repo links** — first tried against an explicit cross-reference map (`_CROSS_REF_REDIRECTS`) that redirects sibling-README links to the synced docs-site page (e.g. `./adk/README.md` from `integrations/google/README.md` → `/docs/integrations/google-adk`). Anything that doesn't match falls back to a `github.com/.../blob/master/...` URL so the link still works.
3. **Strip the leading H1** — Docusaurus already renders the page title from frontmatter `title:`; keeping the source H1 would render the title twice.
4. **Prepend frontmatter + generated banner** — frontmatter gives Docusaurus the title and sidebar label, the banner tells editors not to hand-edit the file.

Commands:

- `make sync-integration-docs` — write the mirror in place. Idempotent.
- `make check-integration-docs` (or `python docs-site/scripts/sync_integrations_to_docs.py --check`) — exit 0 when synced, exit 1 + list of stale files otherwise.

CI wiring: `.github/workflows/docs-site.yml` runs `--check` as the first step of the docs build, before installing Node. A stale mirror fails the workflow loudly instead of silently shipping out-of-date content. The workflow also triggers on `integrations/**/README.md` changes (not just `docs-site/**`), so editing a source README automatically rebuilds the site after the mirror is regenerated.

Adding a new mirrored page: append a `SyncTarget(...)` entry to `SYNC_MAP` in `docs-site/scripts/sync_integrations_to_docs.py`, then run the sync. Also add an entry to `sidebars.ts` under `integrationsTree` so the new page shows up in the left sidebar.

**Implementation:** `zscaler_mcp/common/docgen.py`. The generator instantiates each service with `zscaler_client=None` (mirroring the pattern already used by `parse_args` for `--list-tools`) so the SDK isn't needed at doc-generation time. Adding a new auto-generated region: append a `(path, region_name, renderer_fn)` tuple to `TARGETS`, insert the matching marker pair in the file, and add a renderer test in `tests/test_docgen.py`. Tests assert that the committed docs are always in sync (`TestRepoIsInSync::test_committed_docs_are_in_sync`).

### Helper File Convention (DO NOT FRAGMENT)

To keep the codebase organized, helper modules follow strict rules. **Read this before creating ANY new helper file.**

**Where helpers live (3 buckets — and only 3):**

1. **`zscaler_mcp/common/`** — cross-cutting helpers shared between tools.
   - **One helper file per service**: `zia_helpers.py`, `zpa_helpers.py`, `zdx_helpers.py`, etc. (create on first need).
   - **Shared (cross-product) infra modules** that already exist: `elicitation.py` (HMAC tokens), `jmespath_utils.py`, `logging.py`, `tool_helpers.py` (registration). Don't add a new file here unless it's genuinely cross-product infra.
2. **`zscaler_mcp/utils/utils.py`** — low-level, product-agnostic utilities (e.g. `parse_list`, condition-format converters). Append, don't fragment.
3. **Inside the tool module itself** — helpers used by exactly one module belong as private functions in that module (`_build_*_payload`, `_validate_*`).

**Rules:**

- **DO NOT** create per-feature helper modules like `zia_rule_helpers.py`, `zia_cloud_app_resolver.py`, `zia_time_interval_helpers.py`. Add new functions/constants as a new section in the existing `zia_helpers.py` (use `# ====` section headers).
- **DO NOT** mix products in one file. ZIA helpers go in `zia_helpers.py`, ZPA helpers go in `zpa_helpers.py`. Cross-product helpers go in the shared infra modules in `common/`.
- **Split a service helper file only when** (a) it grows past ~600 lines, OR (b) a new section needs heavy external deps the rest of the file doesn't share. When splitting, name the new file by the helper category, not the consumer (e.g. `zia_pagination.py`, not `zia_user_groups_helpers.py`).
- **Public API**: every helper file exposes its surface via `__all__` so callers know what's intended for import.
- **Imports**: tool modules import from the helper file via the canonical name `from zscaler_mcp.common.{service}_helpers import ...`. Don't re-export through `common/__init__.py`.

**When in doubt, extend `{service}_helpers.py`.** Adding a new file requires explicit justification.

### Key Design Decisions

- **Lazy client initialization**: Zscaler SDK clients are created on first tool call, not at server startup. This avoids authentication failures blocking startup and allows credential rotation without restart.
- **Security-first defaults**: Read-only mode, auth enabled by default for HTTP, TLS enforced unless explicitly opted out, HMAC confirmations for destructive actions.
- **No runtime tool filtering**: `disabled_tools` and `disabled_services` are applied at registration time. Once the server is running, the tool list is fixed. This prevents race conditions and ensures consistent behavior.
- **Agent-aware metadata**: The `zscaler_get_available_services` tool exists specifically to help AI agents understand what's available and what's not. Its description is written to surface in tool searches for any service name.
- **Cross-service data overlap**: Zscaler's APIs have intentional overlap (e.g., ZIA and ZCC both expose device data). The server maps tools to API product boundaries, not conceptual categories. Users need `--disabled-tools` in addition to `--disabled-services` to block cross-service data access.

## GCP Cloud Run Deployment

The server can be deployed to Google Cloud Run as a managed container with optional GCP Secret Manager integration.

### Architecture

```text
┌─ Cloud Run ─────────────────────────────────────────────┐
│  zscaler-mcp-server container                           │
│                                                         │
│  1. gcp_secrets.load_secrets()  ← GCP Secret Manager   │
│  2. ZscalerMCPServer starts    ← streamable-http       │
│  3. AuthMiddleware (zscaler)   ← Basic auth validation  │
│  4. Tool dispatch              ← Zscaler SDK calls      │
└─────────────────────────────────────────────────────────┘
          ▲                              │
          │ POST /mcp                    │ HTTPS
          │ Authorization: Basic ...     ▼
   Claude / Cursor              Zscaler OneAPI
```

### Key Files

- **`zscaler_mcp/cloud/gcp_secrets.py`** — Runtime Secret Manager loader. Fetches credentials at startup using Application Default Credentials. Activated by `ZSCALER_MCP_GCP_SECRET_MANAGER=true`. Maps env var names to secret IDs by lowercasing and replacing `_` with `-` (e.g., `ZSCALER_CLIENT_ID` → `zscaler-client-id`). Only `ZSCALER_CLIENT_ID` and `ZSCALER_CLIENT_SECRET` are required; other secrets are silently skipped if missing.

- **`integrations/google/gcp/gcp_mcp_operations.py`** — Unified GCP deployment script. Interactive CLI with 3 targets (Cloud Run, GKE, Compute Engine VM). Reads `.env`, optionally stores creds in Secret Manager, deploys with configurable auth mode, auto-configures Claude Desktop and Cursor.

### Default Auth: Zscaler Mode

GCP deployments default to `ZSCALER_MCP_AUTH_MODE=zscaler`. Clients authenticate with `Authorization: Basic base64(client_id:client_secret)` — the same Zscaler OneAPI credentials used for API access. The server validates them against Zscaler's `/oauth2/v1/token` endpoint and caches the result for the token's lifetime (~1 hour).

### Environment Variables (GCP-specific)

- `ZSCALER_MCP_GCP_SECRET_MANAGER` — Enable runtime Secret Manager loader (`true`/`false`)
- `GCP_PROJECT_ID` — GCP project for Secret Manager API calls

### Gotchas

- **Secret Manager is optional.** Credentials can be passed as direct env vars instead. Secret Manager is recommended for production but not required.
- **`--allow-unauthenticated` at Cloud Run level** is required even when MCP auth is enabled. Cloud Run IAM controls infrastructure-level access; MCP auth (`zscaler` mode) controls application-level access. These are independent layers.
- **`ZSCALER_MCP_ALLOW_HTTP=true`** is required on Cloud Run because TLS is terminated by Google's infrastructure before reaching the container.
- **Both URL formats are valid.** Cloud Run assigns two URLs to each service: `https://SERVICE-HASH.a.run.app` (old) and `https://SERVICE-PROJECT_NUM.REGION.run.app` (new). Both resolve to the same service.

## Azure Deployment

Interactive deployment to Azure via `integrations/azure/azure_mcp_operations.py`. Supports three deployment targets:

### Deployment Targets

| Target | Runtime | Image/Package | Status |
|--------|---------|---------------|--------|
| **Container Apps** | Managed, serverless | Docker Hub: `zscaler/zscaler-mcp-server:latest` | GA |
| **Virtual Machine** | Ubuntu 22.04, self-managed | PyPI: `zscaler-mcp-server` | GA |
| **Azure Kubernetes Service (AKS)** | Kubernetes Deployment + LoadBalancer Service | Docker Hub: `zscaler/zscaler-mcp-server:latest` | **Preview** |

### Common Features

- **Fully interactive** — prompts for deployment target, credential source (`.env` path or manual entry), auth mode, Azure options
- **Azure Key Vault** — Container Apps + VM use it (Container Apps offers a deploy-time choice between KV and direct env vars; VM is KV-only). **AKS Preview** also offers a choice: **Azure Key Vault via Workload Identity Federation + Key Vault CSI driver (default, recommended)** or plain Kubernetes `env` vars on the Deployment (PoC fallback).
- **Five auth modes** — OIDCProxy, JWT, API Key, Zscaler, None. AKS Preview supports four of these (OIDCProxy not yet supported).
- **State file** — `.azure-deploy-state.json` persists resource names for `status`/`logs`/`destroy`/`ssh`. AKS deployments also write `.aks-manifest.yaml` (the generated Deployment + Service spec).
- **Client config** — auto-updates Claude Desktop (`claude_desktop_config.json`) and Cursor (`mcp.json`) with correct auth headers

### Container Apps Specifics

- Pulls image directly from Docker Hub (no local build, no ACR)
- TLS terminated by Azure Container Apps ingress
- Scales 1-3 replicas automatically

### VM Specifics

- Provisions Ubuntu 22.04 VM (`Standard_B2s` by default)
- Creates NSG with SSH (22) and MCP port rules
- Installs Python 3.11, creates venv, installs `zscaler-mcp-server` from PyPI
- Configures systemd service (`zscaler-mcp.service`) for auto-start and restart on failure
- SSH access via `python azure_mcp_operations.py ssh`

### AKS Specifics (Preview)

- **Cluster lifecycle:** create new AKS cluster on the fly (Standard_B2s, 1 node, managed identity, Standard SKU LB) **or** attach to an existing cluster. New clusters on the Key Vault path are created with `--enable-workload-identity --enable-oidc-issuer --enable-addons azure-keyvault-secrets-provider` so the cluster comes up federation-ready.
- **Container image:** same `zscaler/zscaler-mcp-server:latest` from Docker Hub used by Container Apps
- **Credential storage (interactive choice):**
  - **Azure Key Vault (default, recommended).** The script provisions / attaches to a Key Vault, stores every Zscaler secret in it, creates a User-Assigned Managed Identity, grants it `Key Vault Secrets User`, and creates a federated credential linking the Pod's K8s `ServiceAccount` (`zscaler-mcp-sa`) to the UAMI. The Key Vault CSI driver mounts the secrets and syncs them into a K8s `Secret` (`zscaler-mcp-secrets`) consumed by the Deployment via `valueFrom.secretKeyRef`. The manifest also includes a `SecretProviderClass` (`zscaler-mcp-spc`).
  - **Plain env vars (PoC).** Credentials are baked into the Deployment manifest at deploy time (visible via `kubectl describe deployment`).
- **K8s manifest:** script generates `.aks-manifest.yaml` and `kubectl apply`s it. Contents depend on storage choice (KV path = ServiceAccount + SecretProviderClass + Deployment with secretKeyRef + Service; env-vars path = Deployment with inline values + Service).
- **Resource defaults:** 200m–1000m CPU, 512Mi–1Gi memory, single replica (scale via `kubectl scale`)
- **kubectl context:** set automatically via `az aks get-credentials --overwrite-existing`
- **External access:** Azure Standard Load Balancer with public IP (port 80 → container port 8000)
- **Smart destroy:** if the script created the cluster → deletes the entire resource group (everything goes with it, including the UAMI and Key Vault). If you used an existing cluster → only the K8s objects we created are removed (Deployment, Service, and on the KV path also ServiceAccount, SecretProviderClass, synced Secret) plus the per-deployment UAMI and federated credential. The Key Vault is preserved when the cluster is preserved.
- **Status / logs:** `op_status` runs `az aks show` + `kubectl get pods` + `kubectl get svc`; `op_logs` runs `kubectl logs deployment/zscaler-mcp-server -n <ns> -f` with graceful Ctrl+C handling.
- **Helpers:** `run_kubectl()` wraps `kubectl` calls (alongside `run_az()`); `_build_aks_env_vars()` and `_build_aks_kv_env_vars()` build the env lists for the two storage paths; `_build_aks_kv_manifest()` renders the full KV-path manifest; `_create_uami()`, `_grant_uami_kv_role()`, `_create_federated_credential()`, `_enable_aks_workload_identity()`, and `_enable_aks_kv_csi()` orchestrate the federation setup.
- **Preview limitations:** OIDCProxy auth mode unsupported; no Ingress/TLS (LoadBalancer exposes plain HTTP — production deployments need NGINX Ingress + cert-manager + DNS); single replica default; no HPA. The AKS GA roadmap (enterprise hardening — Ingress/TLS, HPA, multi-replica) is tracked separately.

### Auth Mode Differences

| Mode | Container command | MCP env vars | Client auth |
|------|-------------------|--------------|-------------|
| OIDCProxy | Inline Python entrypoint (base64-encoded). **Container Apps + VM only** — not yet supported on AKS Preview. | `OIDCPROXY_*` env vars, `ZSCALER_MCP_AUTH_ENABLED=false` | `mcp-remote` handles OAuth flow |
| JWT / API Key / Zscaler | `/app/.venv/bin/zscaler-mcp --transport streamable-http` (Container Apps + AKS) or systemd service (VM) | `ZSCALER_MCP_AUTH_MODE=jwt\|api-key\|zscaler` | Auth header via `mcp-remote --header` (Claude) or `headers` (Cursor) |
| None | Same CLI entrypoint | `ZSCALER_MCP_AUTH_ENABLED=false` | No header |

### Key Vault Flow

1. Script creates Key Vault (or uses existing) with RBAC authorization enabled
2. Assigns "Key Vault Secrets Officer" role to the signed-in user
3. Stores Zscaler API creds + auth-mode-specific secrets
4. For Container Apps: values passed as env vars; for VM: values written to `/opt/zscaler-mcp/env`

### VM cloud-init

The VM deployment uses cloud-init to:

1. Install Python 3.11 and create a venv at `/opt/zscaler-mcp/venv`
2. Install `zscaler-mcp-server` from PyPI
3. Write environment variables to `/opt/zscaler-mcp/env`
4. Create and enable `zscaler-mcp.service` systemd unit
5. Start the service

### Foundry Agent Integration

After deploying the MCP server, you can optionally create an Azure AI Foundry agent that uses it as a tool:

```bash
python azure_mcp_operations.py agent_create   # creates agent in Foundry
python azure_mcp_operations.py agent_chat     # interactive chat session
python azure_mcp_operations.py agent_chat -m "list all zpa segment groups"  # one-shot with initial message
python azure_mcp_operations.py agent_status   # check agent status
python azure_mcp_operations.py agent_destroy  # delete agent
python azure_mcp_operations.py agent_destroy -y  # skip confirmation prompt
```

**What it does:**

- Creates a Foundry agent (`zscaler-mcp-agent`) with `MCPTool` pointing to your deployed MCP server
- Uses GPT-4o (configurable) for reasoning
- Configures `require_approval="always"` for human oversight on tool calls
- Authenticates to MCP server via `X-Zscaler-Client-ID` / `X-Zscaler-Client-Secret` headers (NOT `Authorization` or `project_connection_id` — both are blocked/buggy in Foundry)
- Stores agent state in `.azure-agent-state.json`

**Chat UX features (`agent_chat`):**

- Animated braille spinner with live elapsed-time counter while waiting for responses
- Per-response stats: wall-clock time, token usage (input/output/total)
- End-of-session summary: total session duration, messages sent, cumulative token count
- Proper response chaining for multi-turn conversations with tool approvals
- Zscaler ASCII logo banner on chat start
- Graceful error handling for API errors (DeploymentNotFound, auth failures, rate limits, connection issues) with actionable remediation steps instead of raw tracebacks

**In-chat commands:**

| Command | Description |
|---------|-------------|
| `help` | Show available commands, usage tips, and example prompts |
| `status` | Show agent info, project endpoint, session duration, tokens, and messages sent |
| `clear` | Clear the terminal screen |
| `reset` | Reset conversation context (clears response chain, token count, message count) |
| `quit` / `exit` / `q` | End the chat session and display a summary |

**Foundry portal:** After `agent_create`, view and test the agent at [ai.azure.com](https://ai.azure.com) → your project → Agents → `zscaler-mcp-agent` → Playground.

**Prerequisites:**

- Azure AI Foundry project ([ai.azure.com](https://ai.azure.com))
- Azure OpenAI model deployment (GPT-4o or GPT-4) — must be deployed in the project, not just selected
- Python packages: `azure-ai-projects`, `azure-identity`
- Azure CLI: `az login`
- `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_OPENAI_MODEL` in `integrations/azure/.env`

**Deployment guide:** `docs/deployment/azure-ai-foundry.md` — end-to-end walkthrough with screenshots covering both CLI and portal methods, Foundry project creation, model deployment, and troubleshooting.

**Publication:** Self-service — no Microsoft involvement. Publish to Individual (testing) or Organization (production) scope through Foundry portal or SDK.

**Command reference:**

| Command | Flag | Description |
|---------|------|-------------|
| `agent_create` | | Create Foundry agent with MCP tool and auth headers |
| `agent_status` | | Show agent name, version, model, and MCP URL |
| `agent_chat` | | Interactive multi-turn chat with tool approval |
| `agent_chat` | `--message "..."` / `-m "..."` | Send an initial message on start |
| `agent_destroy` | | Delete agent from Foundry (prompts for confirmation) |
| `agent_destroy` | `--yes` / `-y` | Delete agent without confirmation prompt |

### Files

- **`integrations/azure/azure_mcp_operations.py`** — Main script. MCP operations: `deploy`, `destroy`, `status`, `logs`, `ssh` (Container Apps + VM + AKS Preview). Foundry operations: `agent_create`, `agent_status`, `agent_chat`, `agent_destroy`
- **`integrations/azure/foundry_agent.py`** — Foundry agent module with MCPTool, chat session, approval handling
- **`integrations/azure/env.properties`** — Template `.env` file with all supported variables
- **`integrations/azure/.azure-deploy-state.json`** — Created during deploy, stores resource names/FQDN/public IP (and AKS cluster name + namespace + `cluster_created` flag)
- **`integrations/azure/.azure-agent-state.json`** — Created during agent_create, stores Foundry project/agent info
- **`integrations/azure/.aks-manifest.yaml`** — Generated K8s manifest (Deployment + LoadBalancer Service) — written only for AKS deployments

## Kubernetes (Helm Chart) Deployment

Cluster-vendor-agnostic Helm chart at `integrations/helm-chart/` for deploying the MCP server to any Kubernetes cluster — EKS, GKE, AKS, OpenShift, Rancher, k3s, Talos, `kind`, `minikube`. Sibling to the Azure / GCP / AWS deployment scripts but deliberately decoupled from any hyperscaler: the chart never calls `aws`, `az`, or `gcloud`. You bring the cluster; the chart installs one workload.

### Architecture

```text
┌─ Kubernetes cluster (any distro) ────────────────────────────┐
│                                                              │
│  Deployment: zscaler-mcp-zscaler-mcp-server (1 replica)     │
│    ├─ image: zscaler/zscaler-mcp-server:latest               │
│    ├─ args: --transport streamable-http --host 0.0.0.0 ...   │
│    ├─ envFrom: secretRef: zscaler-mcp-creds  ← bulk envvars  │
│    └─ runAsUser: 1000  (matches the `app` user in the image) │
│  Service (ClusterIP, port 80 → 8000)                         │
│  Secret (chart-managed OR pre-existing)                      │
│  Optional: Ingress / HTTPRoute / Certificate / PDB / HPA     │
└──────────────────────────────────────────────────────────────┘
            ▲                              │
            │ POST /mcp                    │ HTTPS
            │ Authorization: Basic ...     ▼
     Claude / Cursor                Zscaler OneAPI
```

### Key Files

- **`integrations/helm-chart/charts/zscaler-mcp-server/`** — The chart itself. `Chart.yaml`, `values.yaml`, plus templates for Deployment / Service / Secret / ServiceAccount and optional Ingress / HTTPRoute / Certificate (cert-manager) / PDB / HPA / `helm test` smoke pod. Every optional template is gated by an explicit boolean in `values.yaml` — no opt-out surprises.

- **`integrations/helm-chart/helm_mcp_operations.py`** — Interactive Python deployer mirroring `integrations/azure/azure_mcp_operations.py` and `integrations/google/gcp/gcp_mcp_operations.py`. Stdlib + `kubectl` + `helm 3`; no cloud SDK, no `pip install`. Six subcommands: `deploy`, `destroy`, `status`, `logs`, `configure`, `test`. Writes `.helm-deploy-state.json` so follow-up subcommands don't re-prompt.

### Credential Setup — Five Paths

| # | Path | When | Storage |
|---|------|------|---------|
| 1 | `helm_mcp_operations.py deploy` | Local dev, day-1 walkthroughs | Materialised from `.env` via `kubectl create secret --from-env-file` |
| 2 | Manual `kubectl create secret --from-env-file` + `helm install` | CI, GitOps reconcilers | Pre-existing Secret referenced via `secret.create=false` |
| 3 | Inline `--set secret.values.*` | Smoke tests, templating pipelines | Chart-rendered Secret (`secret.create=true`) |
| 4 | Pre-existing Secret (ArgoCD/Flux/SealedSecrets/sops) | GitOps workflows | Operator-provided Secret; chart references it by name |
| 5 | External Secrets Operator (ESO) | Production with AWS Secrets Manager / Azure Key Vault / GCP Secret Manager / Vault / 1Password | ESO materialises the Secret; chart references it by name |

All five paths converge on the same chart contract: the Deployment uses `envFrom: secretRef:` to bulk-import every key in the Secret as an environment variable. **No translation into `values.yaml` syntax** — whatever `ZSCALER_MCP_*` / `ZSCALER_*` keys live in your `.env` (or remote-secret backend) flow into the container untouched. This was a deliberate UX choice when the chart was added: forcing the user to mirror every env var into `secret.values.*` was a non-starter for anyone with a non-trivial `.env`.

### Auto-Configuration of MCP Clients

When `deploy` finishes (or `configure` is run later), the script:

1. Pulls `ZSCALER_CLIENT_ID` + `ZSCALER_CLIENT_SECRET` directly from the cluster Secret (works regardless of which credential-setup path created it).
2. Computes `Authorization: Basic base64(client_id:client_secret)` locally.
3. Starts a background `kubectl port-forward` (when no Ingress was configured).
4. Writes the `zscaler-mcp-server` entry into `~/.cursor/mcp.json` (Cursor's HTTP-native shape) and `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS (via the `mcp-remote` bridge).

Same pattern as the Azure / GCP scripts — the client config never carries raw credentials, only the derived `Authorization: Basic` header.

### Pod-Startup Recovery (built into the rollout wait loop)

`deploy` doesn't use `helm upgrade --wait`. Instead the script polls pod state every 5 seconds with a quiet `kubectl get pods -o json`, classifies the result, and bails out early with a tailored hint on terminal failure states (after a 15-second grace window so the kubelet's first-attempt transients don't trip it):

- `ImagePullBackOff` / `ErrImagePull` / `InvalidImageName` → image / tag / registry guidance; on a `kind` context it adds the `kind load docker-image` recipe so the user can side-load a local image.
- `CreateContainerConfigError` / `CreateContainerError` / `RunContainerError` → dumps Kubernetes' `container.state.waiting.message` verbatim (usually pinpoints the missing Secret key or invalid env-var name) plus the `kubectl describe pod` command.
- `CrashLoopBackOff` / `OOMKilled` / `Error` → same recovery surface plus the last 20 pod events.

On any terminal state, the script automatically dumps the last 20 pod events so the operator doesn't have to copy-paste `kubectl describe`. The `$ kubectl ...` info-lines that previously spammed the rollout loop are silenced (`run_kubectl(..., quiet=True)`); the user only sees state-change summaries.

### Gotchas

- **`runAsUser: 1000` is mandatory.** The image runs as the `app` user (uid=1000, gid=1000) baked in via `Dockerfile`'s `USER app`. The chart pins `runAsUser: 1000` + `runAsGroup: 1000` + `fsGroup: 1000` numerically — Kubernetes cannot introspect a `USER <name>` directive, so without numeric UIDs `runAsNonRoot: true` trips admission with `image has non-numeric user (app), cannot verify user is non-root`. If you override `image.repository` to point at a custom build, make sure it still runs under UID 1000.

- **`secret.create=false` requires `secret.existingName`.** Enforced by the chart's `validateValues` template — fails install with a clear error rather than silently rendering an empty `envFrom`.

- **`ingress.enabled` and `httproute.enabled` are mutually exclusive.** Same validateValues template — pick one.

- **Pre-existing Secret + Secret rotation.** When `secret.create: false`, the chart **does not** render the `checksum/credentials` pod annotation. Secret rotation is the operator's responsibility (External Secrets Operator handles this natively via [Stakater reloader](https://github.com/stakater/Reloader) or its own reconciliation). Chart-managed Secrets DO render the annotation, so any change to `secret.values.*` triggers a rolling restart automatically.

- **Pin a versioned tag (or digest) in production.** `image.tag` defaults to `latest`. Each release publishes immutable + rolling semver tags (`X.Y.Z`, `X.Y`, and `X` once the major version is > 0) via the `docker-image-publish` job chained inside `release.yml` — NOT via a `release:` trigger in `docker-build-push.yml`, which GitHub suppresses for releases that semantic-release publishes with `GITHUB_TOKEN` (same suppression PR #78 fixed for the MCPB bundle). Releases ≤ v0.12.6 predate this job and have no versioned tags unless backfilled via `gh workflow run docker-build-push.yml -f tag=vX.Y.Z`. For maximum strictness, pin `image.digest` (`sha256:...`), which wins over `image.tag`.

- **Helm chart vs hyperscaler scripts.** This chart is the answer when **the cluster is already a fact**. If you need to *stand up* cluster infrastructure (EKS, AKS, GKE, networking, IAM, Key Vault), use `integrations/azure/azure_mcp_operations.py` (Container Apps / VM / AKS-Preview), `integrations/google/gcp/gcp_mcp_operations.py` (Cloud Run / GKE / Compute Engine), or `integrations/aws/bedrock-agentcore/aws_mcp_operations.py`. Those scripts provision and manage the underlying cloud infrastructure end-to-end. The Helm chart deliberately doesn't.

### Documentation

- **Source of truth:** `integrations/helm-chart/README.md` (1 → 5 credential paths, full `values.yaml` reference, Deployment Script Reference enumerating every subcommand + flag, Operations cheat sheet, Troubleshooting matrix, Recovering-from-failed-install runbook).
- **Docs-site mirror:** `docs-site/docs/deployment/helm-chart.md` — auto-synced from the source README via `make sync-integration-docs` (registered in `_CROSS_REF_REDIRECTS` so sibling-repo links rewrite to GitHub master URLs).
- **Top-level README:** `Additional Deployment Options` → `Kubernetes (Helm Chart)` subsection plus a row in the `Platform Integrations` table.

## AWS Version

A parallel deployment exists at `/Users/wguilherme/go/src/github.com/zscaler/AWS/zscaler-mcp-server` for Amazon Bedrock AgentCore. Key differences:

- **No TLS handling** — AWS infrastructure (ALB, API Gateway) handles TLS termination
- **`web_server.py`** — FastAPI wrapper that bypasses MCP session initialization for Bedrock's stateless HTTP
- **`_log_security_posture_aws()`** — AWS-specific security banner (no TLS fields)
- **Same tool/service/auth architecture** — disabled_tools, disabled_services, OIDCProxy, HMAC confirmations all work identically

## Skills

41 guided skills in `skills/` for multi-step workflows. Skills are auto-activated by frontmatter description match. Organized by service: `skills/zpa/` (11), `skills/zia/` (12), `skills/zdx/` (6), `skills/zms/` (5), `skills/zins/` (4), `skills/easm/` (1), `skills/zcc/` (1), `skills/cross-product/` (1). Each skill has a `SKILL.md` with frontmatter (`name`, `description`) and step-by-step instructions referencing specific tool names.

### Skill Frontmatter — Hard Limits

The frontmatter at the top of every `SKILL.md` is parsed by external skill loaders (Claude's skill uploader, MCP client skill registries) and has hard byte/character ceilings that the API enforces at upload time. Violating these turns into a cryptic 400 from the upload UI, so they have to be checked before authoring.

- **`description` ≤ 1024 characters.** The Claude skill uploader rejects any skill whose frontmatter `description` field exceeds **1024 characters** with the error `field 'description' in SKILL.md must be at most 1024 characters`. Count the value of the YAML `description:` field (the prose between the quotes, not the YAML key) and keep it under 1024. The description doubles as the skill's auto-activation matcher — it should list the **trigger phrases an admin actually uses** ("block ChatGPT", "allow Dropbox uploads", "create a Cloud App Control rule for X") plus a one-sentence summary of what the skill does. Trim ruthlessly: every example you add costs character budget you can't recover. Long technical caveats (API quirks, multi-resource ordering, error-handling patterns) belong in the body of the skill, not in the description.
- **`name`** — must be unique within `skills/`, kebab-case, prefixed with the service (`zia-`, `zpa-`, `zdx-`, `zcc-`, `zms-`, `zins-`, `easm-`, `cross-product-`). No character ceiling enforced by the loader, but keep it under ~50 characters so it renders cleanly in skill pickers.
- **Keep frontmatter to two fields**: `name` and `description`. Other fields (`tags`, `priority`, `version`) are silently dropped by current loaders and add maintenance noise.
- **Validate before commit.** A one-liner sanity check: `python -c "import yaml,sys; d=yaml.safe_load(open('skills/.../SKILL.md').read().split('---')[1]); print(len(d['description']))"` — must print a number ≤ 1024.

When a skill needs more discoverability than 1024 characters can hold (e.g. a multi-resource workflow with many trigger phrases), prefer **splitting into two skills** that chain together over stuffing every keyword into one description. The skill chaining pattern (`zia-look-up-rule-targets`, `zia-look-up-cloud-app-name`, `zia-manage-time-interval`) was designed for exactly this — each chained skill carries its own focused description, and the parent skill's description only lists *its* trigger phrases plus the chain hand-offs.

### Skill Conventions (Emerging)

Newer skills — especially in Z-Insights and ZMS — follow two conventions that improve resilience on tenants where a feature is unlicensed or returns sparse data. When authoring or reviewing a skill that depends on multiple independent API reads, prefer this shape:

- **`## Validation` section** after the workflow steps, listing each tool the skill calls, its expected response shape, and the right action when the result is empty or errors. Empty / unlicensed responses are not workflow failures — they're authoritative signals that should be surfaced as gaps in the final report. Reference: `skills/zins/audit-shadow-it/SKILL.md::Validation`.
- **`### Partial Data` edge case** under the skill's `## Edge Cases` section, telling the agent how to behave when one tool in the chain succeeds and another fails. The canonical guidance: "present the available sections and clearly flag the gap — do not fail the whole audit." Common cause: an add-on (IoT Device Visibility, CASB, ZMS) isn't entitled on the tenant. Mark the missing section as `Not available — feature not licensed / data not collected` so the requester can see the scope of what was actually audited.

Both patterns are about making skills *licensing-aware*: a Z-Insights audit on a tenant without CASB should still produce a useful shadow-IT report, just with a clearly-labeled CASB section marked unavailable.

### Skill Discovery via Integrations

Each MCP client integration exposes the skill catalog in the idiomatic way for that client:

- **Claude Code, Cursor, Gemini CLI** — skills are auto-loaded by description match; the agent picks one when the user's request fits.
- **Kiro IDE** — skill discovery is wired through the **per-service steering files** under `integrations/kiro/steering/`. Each steering file has an `## Available Skills` section enumerating the relevant skills with intent cues, so when Kiro loads (say) `zia.md` for a ZIA question it sees all 12 ZIA skills inline rather than having to search the filesystem. This lets the agent prefer a guided skill over an ad-hoc tool sequence. The same per-service files also include their service's tool catalog and gotchas. Bump these references when adding, renaming, or removing a skill — there is no auto-generator for this catalog yet.

## Platform Integrations

Native integrations available in `integrations/`: Claude Code plugin, Cursor plugin, Gemini CLI extension, Kiro IDE power, Google Cloud deployment (Cloud Run / GKE / Compute Engine VM), Google ADK agent, Azure deployment (Container Apps / VM / AKS Preview), Azure AI Foundry agent, GitHub MCP Registry. See `integrations/README.md` for details.

### Google Cloud Deployment

`integrations/google/gcp/gcp_mcp_operations.py` — unified interactive deployment script (modeled after Azure's `azure_mcp_operations.py`):

- **3 targets:** Cloud Run (container), GKE (K8s), Compute Engine VM (Python from PyPI + systemd)
- **Operations:** `deploy`, `destroy`, `status`, `logs`, `ssh` (VM only)
- **Secret Manager:** Built-in GCP Secret Manager integration (optional)
- **Auth modes:** JWT, API Key, Zscaler, None
- **State file:** `.gcp-deploy-state.json` — tracks deployment type for management commands
- **Client config:** Auto-updates Claude Desktop and Cursor configs

ADK agent lives at `integrations/google/adk/` (deploys to Cloud Run / Vertex AI Agent Engine / Agentspace).

### GitHub MCP Registry

The server is published to the [GitHub MCP Registry](https://github.com/modelcontextprotocol/registry) via `server.json` at the repo root. This enables one-click installation from GitHub Copilot and any MCP-compatible client.

**Key files:**

- **`server.json`** — MCP Registry manifest (name, description, version, packages, env vars). Version is auto-updated by `set-version.sh` and committed by `.releaserc.json` during releases.
- **`README.md`** — contains `<!-- mcp-name: io.github.zscaler/zscaler-mcp-server -->` (PyPI ownership proof)
- **`Dockerfile`** — contains `LABEL io.modelcontextprotocol.server.name="io.github.zscaler/zscaler-mcp-server"` (Docker ownership proof)

**Two package types declared:**

1. **PyPI** (`registryType: "pypi"`, `runtimeHint: "uvx"`) — env vars via `environmentVariables` property
2. **Docker** (`registryType: "oci"`, `runtimeHint: "docker"`) — env vars via `runtimeArguments` with `-e` flags

**Only 4 env vars are required** for the registry (stdio transport): `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_VANITY_DOMAIN`. Auth, TLS, and host validation are not applicable for stdio.

**Publishing:** `mcp-publisher login github && mcp-publisher publish` (from repo root). See `integrations/github/README.md` for full steps.

### MCPB bundle (Claude Desktop Directory)

The server ships as a `.mcpb` (MCP Bundle) on Anthropic's Claude Desktop Directory. MCPB is the format for **local stdio** MCP servers — there is no MCPB path for remote/HTTP servers; Claude-Desktop users wanting the remote variant configure `mcp-remote` in `claude_desktop_config.json` directly.

**Committed files:**

- **`integrations/anthropic/manifest.json`** — MCPB v0.4 manifest. **Auto-generated** by `zscaler_mcp/common/mcpb.py` (a docgen whole-file target; its path is the `mcpb.MANIFEST_RELATIVE_PATH` constant). Never hand-edit; run `make generate-docs` after touching the tool inventory and commit the result. `make check-docs` (CI) fails the build if it drifts. **`mcpb pack` requires the manifest at the pack root**, so `scripts/build_mcpb.py` copies it to the repo root transiently at pack time; that root copy is `.gitignore`d (`/manifest.json`) and must never be committed.
- **`.mcpbignore`** — `.gitignore`-style exclusion list for `mcpb pack`. Keeps the bundle to ~460 KB by stripping `docs/`, `docs-site/`, `docsrc/`, `tests/`, `integrations/`, `assets/` (except `assets/icon.png`), `skills/`, `commands/`, `requirements.txt`, etc. — everything that isn't `zscaler_mcp/` source + `pyproject.toml` + the (root-copied) `manifest.json` + `assets/icon.png` + `README.md` + `LICENSE`.
- **`assets/icon.png`** — directory listing icon. Un-ignored explicitly in `.mcpbignore` via `!assets/icon.png`.

**Architectural decisions encoded in `mcpb.py`:**

1. **`server.type: "uv"`** instead of `"python"`. The legacy `python` + `pip install --target` approach embedded platform-locked compiled wheels (`cryptography`, `pydantic-core`, `orjson` all ship `.so` / `.pyd`), producing an OS-and-arch-locked bundle that silently failed on other platforms / Python versions. `uv run` defers wheel selection to install time, so the bundle stays source-only and **cross-platform** (one `.mcpb` for darwin/win32/linux). Bundle size went from ~58 MB to ~460 KB. `scripts/build_mcpb.py` asserts `server.type == "uv"` and refuses to build otherwise.
2. **MCPB spec 0.4** — current shipping spec. Bump only when Anthropic releases a new one and we audit for breaking changes.
3. **Env-var fixes** — the previous manifest set `ZSCALER_MCP_ENABLED_SERVICES` / `_ENABLED_TOOLS` / `_DEBUG_MODE` in the runtime env, but `zscaler_mcp/server.py` reads `ZSCALER_MCP_SERVICES` / `_TOOLS` / `_DEBUG`. The old names were silently ignored, so Claude-Desktop users toggling "Enabled Services" / "Debug Mode" got no effect. Fixed in `mcpb.py::_STATIC_TEMPLATE` and asserted by `tests/test_mcpb.py::TestServerConfig::test_env_uses_correct_zscaler_mcp_var_names`.
4. **`integrations/anthropic/` placement** — the committed manifest lives with the other platform-integration assets rather than cluttering the repo root. The build copies it to the pack root (`mcpb pack`'s requirement) only at build time. `icon`/`entry_point` paths in the manifest stay relative to the pack root (repo root). Asserted by `tests/test_mcpb.py::TestCommittedManifest`.

**Commands:**

- `make build-mcpb` — the single command for cutting a bundle, wrapping `scripts/build_mcpb.py`. Regenerates the manifest from the live tool inventory, validates it's in sync + `server.type == "uv"` + all three platforms, copies the manifest to the pack root, packs via `npx @anthropic-ai/mcpb@latest pack`, and emits `dist/zscaler-mcp-server.mcpb` + the versioned `dist/zscaler-mcp-server-<VERSION>.mcpb`.
- `make generate-docs` — regenerates the manifest (alongside all other docgen targets). Run after adding/renaming/removing a tool.
- `make check-docs` — CI guard that fails if the committed manifest (or any other generated doc) drifts.

**Release integration (automated):**

- `.github/set-version.sh` regenerates the manifest after bumping `__init__.py::__version__` so the committed manifest tracks the new release. `integrations/anthropic/manifest.json` is listed in `@semantic-release/git`'s assets so the regen lands in the version-bump commit.
- `.github/workflows/mcpb-build.yml` is a **standalone, `workflow_dispatch`-only workflow** (optional `tag` input) for re-attaching a bundle to an existing release or a dry-run build. It checks out the release tag, verifies the manifest is in sync (`--check-docs`), builds the cross-platform `.mcpb` via `scripts/build_mcpb.py`, **PGP-signs it**, and **attaches the versioned bundle + signature + checksum to the GitHub Release** as assets. The *automatic* happy path is the `mcpb-bundle-attach` job chained inside `release.yml` (`needs: release`) — a standalone `release: published` trigger would never fire, because GitHub suppresses workflow events raised by the `GITHUB_TOKEN` that semantic-release uses to publish releases (see PR #78). Anthropic's directory pipeline can detect each new release and pull the attached `.mcpb` automatically — no manual per-version resubmission.
- **Signing.** The workflow imports the project's PGP key via `crazy-max/ghaction-import-gpg@v6` using the same `GPG_PRIVATE_KEY` + `PASSPHRASE` repo secrets as the main `release.yml`, then produces a detached ASCII-armored signature (`<bundle>.mcpb.asc`) and a SHA-256 checksum (`<bundle>.mcpb.sha256`), self-verifies both, and attaches all three. Consumers verify with `gpg --verify <bundle>.mcpb.asc <bundle>.mcpb` and `shasum -a 256 -c <bundle>.mcpb.sha256`.

### Local Setup Script (`scripts/setup-mcp-server.py`)

Interactive bootstrapper for local Docker-based deployments. Loads `.env`, prompts for transport (stdio / sse / streamable-http) and auth mode (`none`, `api-key`, `jwt`, `zscaler`), starts the container, and writes a working MCP client configuration into Claude Desktop / Cursor / Gemini / Kiro.

Key design choices:

- **Client configs receive only an auth header — never the raw Zscaler credentials.** When the user picks `zscaler` auth mode with `streamable-http`, the script generates a single `Authorization: Basic base64(client_id:client_secret)` header on the client side instead of dropping `X-Zscaler-Client-ID` / `X-Zscaler-Client-Secret` into the MCP client's JSON. This matches the canonical pattern used by remote deployments (GCP Cloud Run, Azure Container Apps) and keeps the credentials off the client filesystem.
- The server's `AuthMiddleware` accepts **both** formats (`Authorization: Basic` and the `X-Zscaler-*` pair) — they hit the same `/oauth2/v1/token` validation path and the same cache — so the client-side switch to `Authorization: Basic` is a pure improvement, not a compatibility break.
- The helper that builds the header dictionary lives in `_client_auth_headers()` (`scripts/setup-mcp-server.py`). Don't duplicate the base64 encoding in callers — call the helper and trust its output.
