# Zscaler MCP Server

300+ tools for managing the Zscaler Zero Trust Exchange. Services: ZPA, ZIA, ZDX, ZCC, EASM, Z-Insights, ZIdentity, ZTW (Zscaler Workload Segmentation), ZMS (Zscaler Microsegmentation).

## Architecture Overview

### Core Components

```
zscaler_mcp/
├── server.py          # ZscalerMCPServer class, CLI entrypoint, security posture logging
├── services.py        # Service registry + 9 concrete service classes (ZPA, ZIA, ZDX, ZCC, ZTW, ZIdentity, ZEASM, ZInsights, ZMS)
├── auth.py            # Auth middleware factory (JWT, API-key, Zscaler, OAuthProxy stub)
├── client.py          # Zscaler SDK client factory (OneAPI + legacy credential flows)
├── security.py        # HTTP security warnings (TLS, plaintext)
├── common/
│   ├── tool_helpers.py   # register_read_tools / register_write_tools with disabled_tools filtering
│   ├── elicitation.py    # HMAC-SHA256 confirmation tokens for destructive actions
│   └── logging.py        # log_security_warning helper
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

2. **Zscaler API Authentication** (`client.py`) — controls how the server talks to Zscaler APIs
   - OneAPI credentials (`ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, etc.)
   - Legacy per-service credentials (ZPA, ZIA, ZCC, ZDX, ZTW)
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

## Critical Gotchas

- **ZIA requires activation.** After any ZIA create/update/delete, call `zia_activate_configuration()`. Changes are staged until activation. Forgetting this is the #1 source of "my change didn't work" issues.
- **`use_legacy` parameter.** Every tool has a `use_legacy` parameter that defaults to `False`. Do NOT change it unless the user explicitly asks for legacy API behavior.
- **ZDX is read-only.** ZDX tools only query data. There are no create/update/delete operations except for deep traces (`zdx_start_deep_trace`).
- **ZDX `since` parameter is in hours**, not timestamps. Default is 2 hours. Example: `since=24` means "last 24 hours."
- **IDs are strings**, even when they look numeric. Always pass IDs as strings.
- **ZPA dependency chain matters.** To onboard an application: create app connector group -> create server group (references connector group) -> create segment group -> create application segment (references server and segment groups) -> create access policy rule. Skipping dependencies causes cryptic 400 errors.
- **ZIA dependency chain for locations.** To onboard a location: create static IP -> create VPN credential (references static IP) -> create location (references VPN credential and static IP). The location won't work without the traffic forwarding prerequisites.

## ZMS (Zscaler Microsegmentation)

ZMS tools use the ZMS GraphQL API (`/zms/graphql`) for querying microsegmentation data. All ZMS tools are **read-only** (queries only — no mutations).

### ZMS Architecture

- **GraphQL-based**: All ZMS operations use GraphQL queries via `POST /zms/graphql`
- **Customer-scoped**: Every query requires `ZSCALER_CUSTOMER_ID` (automatically resolved from env)
- **Paginated responses**: Results use `nodes[]` + `pageInfo { pageNumber, pageSize, totalCount, totalPages }`
- **Two pagination patterns**: Some domains use `page`/`pageSize` (agents, agent_groups, nonces); others use `pageNum`/`pageSize` (resources, resource_groups, policy_rules, app_zones, app_catalog, tags)
- **No legacy mode**: ZMS only works with OneAPI credentials — the `use_legacy` parameter has no effect

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

- `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_VANITY_DOMAIN` — OneAPI credentials from ZIdentity console

Optional legacy credentials:

- ZPA: `ZPA_CLIENT_ID`, `ZPA_CLIENT_SECRET`, `ZPA_CUSTOMER_ID`, `ZPA_CLOUD`
- ZIA: `ZIA_USERNAME`, `ZIA_PASSWORD`, `ZIA_API_KEY`, `ZIA_CLOUD`
- ZCC: `ZCC_CLIENT_ID`, `ZCC_CLIENT_SECRET`, `ZCC_CLOUD`
- ZTW: `ZTW_USERNAME`, `ZTW_PASSWORD`, `ZTW_API_KEY`, `ZTW_CLOUD`
- ZDX: `ZDX_CLIENT_ID`, `ZDX_CLIENT_SECRET`, `ZDX_CLOUD`

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
- `ZSCALER_MCP_WRITE_ENABLED` — Enable write tools (`true`/`false`)
- `ZSCALER_MCP_WRITE_TOOLS` — Comma-separated write tool patterns to allow (wildcards)
- `ZSCALER_MCP_SKIP_CONFIRMATIONS` — Skip HMAC confirmation for destructive ops (`true`/`false`)
- `ZSCALER_MCP_CONFIRMATION_TTL` — Confirmation token TTL in seconds (default 300)
- `ZSCALER_MCP_DISABLE_HOST_VALIDATION` — Disable host header checks (`true`/`false`)

## CLI Flags

- `--transport` — Transport mode (`stdio`, `sse`, `streamable-http`)
- `--services` — Comma-separated services to enable (e.g., `zia,zpa,zdx`)
- `--disabled-services` — Comma-separated services to exclude (e.g., `zcc,zdx`)
- `--disabled-tools` — Comma-separated tool patterns to exclude (wildcards: `"zcc_*,zia_list_device*"`)
- `--write-tools` — Enable and allowlist write tools (wildcards: `"zpa_create_*,zia_update_*"`)
- `--generate-auth-token` — Generate an API key for MCP client authentication
- `--list-tools` — List all available tools and exit
- `--user-agent-comment` — Custom User-Agent suffix for API calls
- `--host` — HTTP bind address (default `127.0.0.1`)
- `--port` — HTTP listen port (default `8000`)
- `--version` — Print version and exit

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

### Adding a New Service

1. Create a new service class in `services.py` extending `BaseService`
2. Define `read_tools` and `write_tools` lists
3. Implement `register_tools()` method
4. Add the service to `_AVAILABLE_SERVICES` registry at the bottom of `services.py`
5. Create tool modules under `zscaler_mcp/tools/{service_name}/`

### Key Design Decisions

- **Lazy client initialization**: Zscaler SDK clients are created on first tool call, not at server startup. This avoids authentication failures blocking startup and allows credential rotation without restart.
- **Security-first defaults**: Read-only mode, auth enabled by default for HTTP, TLS enforced unless explicitly opted out, HMAC confirmations for destructive actions.
- **No runtime tool filtering**: `disabled_tools` and `disabled_services` are applied at registration time. Once the server is running, the tool list is fixed. This prevents race conditions and ensures consistent behavior.
- **Agent-aware metadata**: The `zscaler_get_available_services` tool exists specifically to help AI agents understand what's available and what's not. Its description is written to surface in tool searches for any service name.
- **Cross-service data overlap**: Zscaler's APIs have intentional overlap (e.g., ZIA and ZCC both expose device data). The server maps tools to API product boundaries, not conceptual categories. Users need `--disabled-tools` in addition to `--disabled-services` to block cross-service data access.

## AWS Version

A parallel deployment exists at `/Users/wguilherme/go/src/github.com/zscaler/AWS/zscaler-mcp-server` for Amazon Bedrock AgentCore. Key differences:

- **No TLS handling** — AWS infrastructure (ALB, API Gateway) handles TLS termination
- **`web_server.py`** — FastAPI wrapper that bypasses MCP session initialization for Bedrock's stateless HTTP
- **`_log_security_posture_aws()`** — AWS-specific security banner (no TLS fields)
- **Same tool/service/auth architecture** — disabled_tools, disabled_services, OIDCProxy, HMAC confirmations all work identically

## Skills

20 guided skills in `skills/` for multi-step workflows. Skills are auto-activated by description match. Organized by service: `skills/zpa/` (6), `skills/zia/` (5), `skills/zdx/` (6), `skills/easm/` (1), `skills/zins/` (1), `skills/cross-product/` (1). Each skill has a `SKILL.md` with frontmatter (`name`, `description`) and step-by-step instructions referencing specific tool names.

## Platform Integrations

Native integrations available in `integrations/`: Claude Code plugin, Cursor plugin, Gemini CLI extension, Kiro IDE power, Google ADK agent. See `integrations/README.md` for details.

### Docker + OIDCProxy Setup

One self-contained script in `local_dev/scripts/` for OIDCProxy (OAuth 2.1 + DCR):

- **`setup-oidcproxy-auth.py`** — End-to-end orchestration script. Loads Auth0 credentials from `.env`, builds the Docker image, starts the container with an inline entrypoint (passed via `python -c`), verifies OAuth endpoints, and updates Claude Desktop / Cursor configs. The entrypoint code is embedded directly in the script — no separate file needed. Run from the project root.
