# Zscaler MCP Server

300+ tools for managing the Zscaler Zero Trust Exchange. Services: ZPA, ZIA, ZDX, ZCC, EASM, Z-Insights, ZIdentity, ZTW (Zscaler Workload Segmentation), ZMS (Zscaler Microsegmentation).

## Architecture Overview

### Core Components

```text
zscaler_mcp/
├── server.py          # ZscalerMCPServer class, CLI entrypoint, security posture logging
├── services.py        # Service registry + 9 concrete service classes (ZPA, ZIA, ZDX, ZCC, ZTW, ZIdentity, ZEASM, ZInsights, ZMS)
├── auth.py            # Auth middleware factory (JWT, API-key, Zscaler, OAuthProxy stub)
├── client.py          # Zscaler SDK client factory (OneAPI + legacy credential flows)
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
2. Add `query` parameter before `service`/`use_legacy` in the signature
3. Wrap the success return: `return apply_jmespath(results, query)`
4. Update the tool description in `services.py` to mention JMESPath support

### Tool Discovery via JMESPath

The `zscaler_search_tools` meta-tool exposes the full tool registry as a searchable list with JMESPath filtering. This is designed for AI agents working with deferred tool loading (Claude Desktop, Cursor) where fuzzy search returns irrelevant results. Examples:

```text
zscaler_search_tools(query="[?contains(description, 'firewall')]")
zscaler_search_tools(query="[?starts_with(name, 'zms_')]")
zscaler_search_tools(query="[?contains(name, 'list') && contains(description, 'device')]")
```

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
- `ZSCALER_MCP_LOG_TOOL_CALLS` — Enable tool-call audit logging (`true`/`false`)

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
- The audit wrapper covers all tools: service tools (via `register_read_tools`/`register_write_tools`) and core meta-tools (`zscaler_check_connectivity`, `zscaler_get_available_services`, `zscaler_search_tools`).
- Uses a dedicated logger (`zscaler_mcp.audit`) so log output can be filtered independently.

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

- **`scripts/deploy-gcp.py`** — Customer-facing deployment script. Reads `.env`, optionally stores creds in Secret Manager, deploys to Cloud Run with `zscaler` auth mode, generates Base64 auth headers, auto-configures Claude Desktop and Cursor. Supports `--teardown`.

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

Interactive deployment to Azure via `integrations/azure/azure_mcp_operations.py`. Supports two deployment targets:

### Deployment Targets

| Target | Runtime | Image/Package |
|--------|---------|---------------|
| **Container Apps** | Managed, serverless | Docker Hub: `zscaler/zscaler-mcp-server:latest` |
| **Virtual Machine** | Ubuntu 22.04, self-managed | PyPI: `zscaler-mcp-server` |

### Common Features

- **Fully interactive** — prompts for deployment target, credential source (`.env` path or manual entry), auth mode, Azure options
- **Azure Key Vault mandatory** — all secrets stored in Key Vault (create new or use existing)
- **Five auth modes** — OIDCProxy, JWT, API Key, Zscaler, None
- **State file** — `.azure-deploy-state.json` persists resource names for `status`/`logs`/`destroy`/`ssh`
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

### Auth Mode Differences

| Mode | Container command | MCP env vars | Client auth |
|------|-------------------|--------------|-------------|
| OIDCProxy | Inline Python entrypoint (base64-encoded) | `OIDCPROXY_*` env vars, `ZSCALER_MCP_AUTH_ENABLED=false` | `mcp-remote` handles OAuth flow |
| JWT / API Key / Zscaler | `/app/.venv/bin/zscaler-mcp --transport streamable-http` (Container) or systemd service (VM) | `ZSCALER_MCP_AUTH_MODE=jwt\|api-key\|zscaler` | Auth header via `mcp-remote --header` (Claude) or `headers` (Cursor) |
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

- **`integrations/azure/azure_mcp_operations.py`** — Main script. MCP operations: `deploy`, `destroy`, `status`, `logs`, `ssh`. Foundry operations: `agent_create`, `agent_status`, `agent_chat`, `agent_destroy`
- **`integrations/azure/foundry_agent.py`** — Foundry agent module with MCPTool, chat session, approval handling
- **`integrations/azure/env.properties`** — Template `.env` file with all supported variables
- **`integrations/azure/.azure-deploy-state.json`** — Created during deploy, stores resource names/FQDN/public IP
- **`integrations/azure/.azure-agent-state.json`** — Created during agent_create, stores Foundry project/agent info

## AWS Version

A parallel deployment exists at `/Users/wguilherme/go/src/github.com/zscaler/AWS/zscaler-mcp-server` for Amazon Bedrock AgentCore. Key differences:

- **No TLS handling** — AWS infrastructure (ALB, API Gateway) handles TLS termination
- **`web_server.py`** — FastAPI wrapper that bypasses MCP session initialization for Bedrock's stateless HTTP
- **`_log_security_posture_aws()`** — AWS-specific security banner (no TLS fields)
- **Same tool/service/auth architecture** — disabled_tools, disabled_services, OIDCProxy, HMAC confirmations all work identically

## Skills

20 guided skills in `skills/` for multi-step workflows. Skills are auto-activated by description match. Organized by service: `skills/zpa/` (6), `skills/zia/` (5), `skills/zdx/` (6), `skills/easm/` (1), `skills/zins/` (1), `skills/cross-product/` (1). Each skill has a `SKILL.md` with frontmatter (`name`, `description`) and step-by-step instructions referencing specific tool names.

## Platform Integrations

Native integrations available in `integrations/`: Claude Code plugin, Cursor plugin, Gemini CLI extension, Kiro IDE power, Google ADK agent, Azure deployment (Container Apps / VM), Azure AI Foundry agent, GitHub MCP Registry. See `integrations/README.md` and `docs/deployment/azure-ai-foundry.md` for details.

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
