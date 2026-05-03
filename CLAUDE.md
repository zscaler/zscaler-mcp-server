# Zscaler MCP Server

300+ tools for managing the Zscaler Zero Trust Exchange. Services: ZPA, ZIA, ZDX, ZCC, EASM, Z-Insights, ZIdentity, ZTW (Zscaler Workload Segmentation), ZMS (Zscaler Microsegmentation).

> **Cross-tool conventions.** The most-violated rules in this repo are mirrored — same content, different formats — at `.cursor/rules/zscaler-conventions.mdc` (auto-applied in Cursor) and `.claude/CONVENTIONS.md` (Claude Code). The full convention set lives below in this file; the mirrors exist so the rules survive even if this file is trimmed and so a Cursor session always loads them. **Helper-file convention** is in [Helper File Convention (DO NOT FRAGMENT)](#helper-file-convention-do-not-fragment) below — read it before adding any new file under `zscaler_mcp/common/`.

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

Most MCP clients (Claude Desktop, Cursor) use **deferred tool loading** — they don't load all 280+ tools upfront. Instead, they search for relevant tools based on the user's prompt. This has important implications:

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

Tools are grouped into named **toolsets** (registered in `zscaler_mcp/common/toolsets.py`). Toolsets let users load only the slice of tools the agent actually needs — e.g. `zia_url_filtering` (5 tools) instead of every tool from every service (~280). The full design and catalog live in `docs/guides/toolsets.md`; the highlights for working in this codebase:

- **29 toolsets** today: ZIA is split into ~15 sub-toolsets (one per rule family + locations + admin + categories etc.), ZPA into 6 (`zpa_app_segments`, `zpa_policy`, `zpa_connectors`, `zpa_idp`, `zpa_microtenants`, `zpa_misc`), and one toolset each for ZDX, ZCC, ZTW, ZIdentity, EASM, Z-Insights, ZMS. The always-on `meta` toolset holds the cross-service tools (`zscaler_check_connectivity`, `zscaler_get_available_services`, plus the three discovery tools below).
- **Tagging is centralized.** Don't add a `toolset` field to dicts in `services.py`. Map a new tool name in `_TOOL_TOOLSET_OVERRIDES` (exact match) or `_TOOLSET_PREFIX_RULES` (predicate, first-match-wins) inside `toolsets.py`. The test `tests/test_toolsets.py::TestToolsetForTool::test_every_registered_tool_resolves` enforces this mapping is exhaustive.
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
| URL Filtering | `url_filtering_rules.py` | `zia_list_url_filtering_rules`, `zia_get_url_filtering_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | |
| SSL Inspection | `ssl_inspection.py` | `zia_list_ssl_inspection_rules`, `zia_get_ssl_inspection_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | Cloud-app auto-resolver |
| Web DLP | `web_dlp_rules.py` | `zia_list_web_dlp_rules`, `zia_list_web_dlp_rules_lite`, `zia_get_web_dlp_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | |
| File Type Control | `file_type_control_rules.py` | `zia_list_file_type_control_rules`, `zia_get_file_type_control_rule`, `zia_list_file_type_categories` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | Cloud-app auto-resolver |
| Sandbox Rules | `sandbox_rules.py` | `zia_list_sandbox_rules`, `zia_get_sandbox_rule` | `zia_create_…`, `zia_update_…`, `zia_delete_…` | Distinct from sandbox **reports** in `get_sandbox_info.py` |
| Time Intervals | `time_intervals.py` | `zia_list_time_intervals`, `zia_get_time_interval` | `zia_create_time_interval`, `zia_update_time_interval`, `zia_delete_time_interval` | Reusable schedule object referenced by all rule types via the `time_windows` field. `start_time`/`end_time` are minutes from midnight (0-1439); `days_of_week` accepts `EVERYDAY`, `SUN`-`SAT`. |

All `update_*_rule` tools in this table apply the **silent backfill** pattern for `name` and `order` (see Critical Gotchas). The `zia_update_time_interval` tool applies the same pattern for `name`, `start_time`, `end_time`, and `days_of_week`. Adding a new rule resource? Follow this same shape — never multiplex actions, always backfill required identifiers on update.

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
- `--version` — Print version and exit

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
| `README.md` | `<!-- generated:start service-summary -->` | Per-service tool counts derived from the same source. |
| `docs/guides/toolsets.md` | `<!-- generated:start toolset-catalog -->` | Toolset metadata in `zscaler_mcp/common/toolsets.py` + per-toolset tool counts from the inventory. |

Outside the marker pairs, every file is fully hand-written and the generator never touches it.

**Commands:**

- `make generate-docs` (or `zscaler-mcp --generate-docs`) — regenerate all three regions in place. Idempotent: re-running with no source changes performs no file writes.
- `make check-docs` (or `zscaler-mcp --check-docs`) — exit 0 when docs are in sync, exit 1 + list of stale files otherwise. Designed for CI; wired into `.github/workflows/tests.yml` as a dedicated step before the test suite runs.

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
- **Preview limitations:** OIDCProxy auth mode unsupported; no Ingress/TLS (LoadBalancer exposes plain HTTP — production deployments need NGINX Ingress + cert-manager + DNS); single replica default; no HPA. See `local_dev/azure_mcp_deployment/azure_mcp_deployment_plan_v4.md` "Enterprise Hardening — Future Work" table for the AKS GA roadmap.

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

## AWS Version

A parallel deployment exists at `/Users/wguilherme/go/src/github.com/zscaler/AWS/zscaler-mcp-server` for Amazon Bedrock AgentCore. Key differences:

- **No TLS handling** — AWS infrastructure (ALB, API Gateway) handles TLS termination
- **`web_server.py`** — FastAPI wrapper that bypasses MCP session initialization for Bedrock's stateless HTTP
- **`_log_security_posture_aws()`** — AWS-specific security banner (no TLS fields)
- **Same tool/service/auth architecture** — disabled_tools, disabled_services, OIDCProxy, HMAC confirmations all work identically

## Skills

37 guided skills in `skills/` for multi-step workflows. Skills are auto-activated by description match. Organized by service: `skills/zpa/` (8), `skills/zia/` (12), `skills/zdx/` (6), `skills/zms/` (5), `skills/zins/` (4), `skills/easm/` (1), `skills/cross-product/` (1). Each skill has a `SKILL.md` with frontmatter (`name`, `description`) and step-by-step instructions referencing specific tool names.

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

### Docker + OIDCProxy Setup

One self-contained script in `local_dev/scripts/` for OIDCProxy (OAuth 2.1 + DCR):

- **`setup-oidcproxy-auth.py`** — End-to-end orchestration script. Loads Auth0 credentials from `.env`, builds the Docker image, starts the container with an inline entrypoint (passed via `python -c`), verifies OAuth endpoints, and updates Claude Desktop / Cursor configs. The entrypoint code is embedded directly in the script — no separate file needed. Run from the project root.
