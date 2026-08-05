# Authentication and Deployment Guide

This guide covers every deployment model for the Zscaler MCP Server, including transport selection, authentication modes, Docker configuration, and step-by-step client setup for Claude Desktop, Cursor, and other MCP-compatible clients.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Transport Modes](#transport-modes)
- [Authentication Modes](#authentication-modes)
  - [No Authentication (Default)](#no-authentication-default)
  - [API Key Mode](#api-key-mode)
  - [JWT Mode (External IdP via JWKS)](#jwt-mode-external-idp-via-jwks)
  - [Zscaler Mode (OneAPI Credentials)](#zscaler-mode-oneapi-credentials)
  - [OIDC Mode (OAuth 2.1)](#oidc-mode-oauth-21)
- [Deployment Options](#deployment-options)
  - [Option A: Docker with stdio (No Auth)](#option-a-docker-with-stdio-no-auth)
  - [Option B: Docker with HTTP (With Auth)](#option-b-docker-with-http-with-auth)
  - [Option C: Local Python (uv / pip)](#option-c-local-python-uv--pip)
  - [Remote Deployment (EC2, VM, etc.)](#remote-deployment-ec2-vm-etc)
- [Client Configuration](#client-configuration)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [Windsurf](#windsurf)
  - [VS Code (Copilot Chat)](#vs-code-copilot-chat)
  - [Generic MCP Clients](#generic-mcp-clients)
- [Generating Auth Tokens](#generating-auth-tokens)
- [Setting Up JWT Authentication (JWKS)](#setting-up-jwt-authentication-jwks)
  - [General Process](#general-process)
  - [IdP-Specific Instructions](#idp-specific-instructions)
  - [How Token Validation Works](#how-token-validation-works)
  - [Token Expiry and Refresh](#token-expiry-and-refresh)
- [Automated Setup Script (Auth0)](#automated-setup-script-auth0)
- [OIDC Setup (OAuth 2.1)](#oidc-setup-oauth-21)
  - [Prerequisites](#prerequisites-1)
  - [Step 1: Create an OIDC Application in Your IdP](#step-1-create-an-oidc-application-in-your-idp)
  - [Step 2: Decide the Audience](#step-2-decide-the-audience)
  - [Step 3: Run the Server](#step-3-run-the-server)
  - [Step 4: Configure Your MCP Client](#step-4-configure-your-mcp-client)
  - [How It Works](#how-it-works)
  - [Troubleshooting OIDC](#troubleshooting-oidc)
- [HTTPS / TLS Configuration](#https--tls-configuration)
- [Environment Variable Reference](#environment-variable-reference)
- [Makefile Targets](#makefile-targets)
- [Troubleshooting](#troubleshooting)
  - [Server disconnects immediately in Claude Desktop](#server-disconnects-immediately-in-claude-desktop)
  - [Port 8000 already allocated](#port-8000-already-allocated)
  - [JWT mode + mcp-remote OAuth discovery failure](#jwt-mode--mcp-remote-oauth-discovery-failure)
  - [mcp-remote: Non-HTTPS URL rejected](#mcp-remote-non-https-url-rejected)
  - [Windows: npx path with spaces](#windows-npx-path-with-spaces)
  - [Self-signed certificate rejected by mcp-remote](#self-signed-certificate-rejected-by-mcp-remote)

---

## Architecture Overview

The Zscaler MCP Server has two independent authentication layers:

```text
┌───────────────┐         ┌──────────────────────────────┐         ┌─────────────────┐
│  MCP Client   │  Layer 1│   Zscaler MCP Server         │  Layer 2│  Zscaler APIs   │
│  (Claude,     │────────>│   (Auth Middleware)           │────────>│  (OneAPI)       │
│   Cursor,     │  who can│                              │  how the│                 │
│   etc.)       │  use the│  ASGI Middleware validates    │  server │  ZIA, ZPA, ZDX  │
│               │  server │  incoming MCP requests       │  talks  │  ZCC, ZIdentity │
└───────────────┘         └──────────────────────────────┘  to APIs└─────────────────┘
```

**Layer 1 (this guide):** Controls which MCP clients can connect to the server. Configured via `ZSCALER_MCP_AUTH_*` environment variables.

**Layer 2 (separate):** The Zscaler API credentials (`ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, etc.) that the server uses to call Zscaler APIs. These are always required regardless of Layer 1 settings.

> **Note:** Every Layer 1 mode — including OAuth 2.1 (`oidc`) — is configured entirely through `ZSCALER_MCP_AUTH_*` and `OIDCPROXY_*` environment variables. No mode requires writing Python or passing a provider object to the constructor.

---

## Transport Modes

The MCP protocol supports three transport mechanisms. Your choice of transport determines what kind of access protection applies — but it does **not** change which tools are exposed or how destructive operations are confirmed. Those controls apply on every transport (see [Tool-Level Controls](#tool-level-controls-every-transport) below).

| Transport | Protocol | What gates access | Recommended for |
|-----------|----------|-------------------|-----------------|
| `stdio` | stdin/stdout JSON-RPC | OS process isolation (the client is a parent process) | Local single-user setups — Claude Desktop, Cursor (default) |
| `sse` | HTTP Server-Sent Events | MCP client auth + Host header validation + Source IP ACL + TLS | Remote/shared server, older MCP clients |
| `streamable-http` | HTTP with streaming | MCP client auth + Host header validation + Source IP ACL + TLS | Remote/shared server, **recommended for HTTP** |

### stdio (Default)

The client spawns the server as a child process. Communication happens over stdin/stdout. Access protection is inherited from OS-level process isolation — anyone who can spawn the process already has access to your `.env` and your filesystem, so a network-level auth check would not add anything.

```text
Client (Claude/Cursor) ──stdin/stdout──> Server process
```

What stdio still protects against:

- Tools you didn't allowlist for write mode are not exposed (read-only by default).
- Tools whose product the OneAPI token isn't entitled to are filtered out at startup.
- Destructive operations still require the cryptographic confirmation token (HMAC-SHA256).
- Toolset selection (`--toolsets`, `ZSCALER_MCP_TOOLSETS`) still trims the tool surface.
- The `--disabled-tools` and `--disabled-services` exclusions still apply.

What stdio does **not** protect against: nothing network-related — there is no network surface to defend.

### streamable-http / sse

The server runs as an HTTP service. Clients connect over the network. The server is exposed on a port, so the network-level controls become relevant: MCP client authentication, TLS, host header validation, source IP ACLs. These layers gate **who can connect**; they are independent of the tool-level controls described in the next section, which gate **what those connected clients can call**.

```text
Client (Claude/Cursor) ──HTTP──> localhost:8000/mcp ──> Server
```

**Rule of thumb:** Use `stdio` for single-user local setups. Use `streamable-http` when the server is shared, remote, or you need network-level authentication.

---

## Tool-Level Controls (every transport)

Independent of transport choice, the following controls determine **which tools are exposed and how dangerous calls are confirmed**. Every one of them works identically on `stdio`, `sse`, and `streamable-http`.

| Control | What it does | Configured by |
|---------|--------------|---------------|
| **Read-only by default** | No write tools (`*_create_*`, `*_update_*`, `*_delete_*`) are registered unless you explicitly enable write mode. | `--enable-write-tools` / `ZSCALER_MCP_WRITE_ENABLED=true` |
| **Mandatory write allowlist** | Even with write mode enabled, no write tool is registered without a matching pattern. There is no "enable all writes" backdoor. | `--write-tools "zpa_create_*,zia_update_*"` / `ZSCALER_MCP_WRITE_TOOLS` |
| **Disabled tools / services** | Hard-exclude individual tools (with wildcards) or whole services from the registry. Wins over every other filter. | `--disabled-tools`, `--disabled-services` / `ZSCALER_MCP_DISABLED_TOOLS`, `ZSCALER_MCP_DISABLED_SERVICES` |
| **Toolsets** | Load only the slice of tools an agent actually needs (e.g. `zia_url_filtering` + `zpa_app_segments` instead of all 280+ tools). Reduces context cost and improves agent accuracy. See [docs/guides/toolsets.md](../guides/toolsets.md). | `--toolsets`, `ZSCALER_MCP_TOOLSETS` (special values: `default`, `all`) |
| **OneAPI entitlement filter** | At startup, the server reads the product entitlements from the OneAPI bearer token and silently drops toolsets for products the credentials cannot call. Prevents the agent from discovering tools whose first call would only ever return 401. | On by default; opt out with `--no-entitlement-filter` / `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true`. |
| **Destructive-op confirmation** | No delete executes on the first call. Clients that support MCP elicitation get an interactive prompt answered by a human; every other client gets a single-use HMAC-SHA256 token, bound to the exact tool and parameters, that it must pass back within 5 minutes. | Always on — there is no bypass. `ZSCALER_MCP_CONFIRMATION_TTL` tunes the window only. |
| **Tool-call audit logging** | Every tool invocation is logged with arguments (sensitive params redacted), duration, and result summary. | `--log-tool-calls` / `ZSCALER_MCP_LOG_TOOL_CALLS=true` |

These controls compose. The order in which they're applied to each tool is documented in detail in [Filter precedence](../guides/toolsets.md#filter-precedence).

---

## Authentication Modes

> **Scope.** This section is exclusively about *MCP client authentication* — the network-level check that decides which clients can connect to the server. It only applies to HTTP-based transports (`sse` and `streamable-http`). When using `stdio`, no MCP client authentication is enforced because there is no network surface; the tool-level controls above still apply.

### No Authentication (Default)

When `ZSCALER_MCP_AUTH_ENABLED` is unset or `false`, no authentication middleware is applied. Any client that can reach the HTTP endpoint can use the server.

```bash
# .env — auth disabled (default)
# ZSCALER_MCP_AUTH_ENABLED=false
```

Use this for local development or when the server is only accessible from `localhost`.

---

### API Key Mode

The simplest authentication method. A pre-shared secret key is configured on the server. Clients send it as a Bearer token.

**Server configuration:**

```bash
# .env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=api-key
ZSCALER_MCP_AUTH_API_KEY=sk-your-secret-key-here
```

**Client sends:**

```text
Authorization: Bearer sk-your-secret-key-here
```

**Characteristics:**

- No external IdP or infrastructure required
- Constant-time comparison prevents timing attacks
- No token expiry — rotate the key manually when needed
- Best for: internal tools, small teams, development environments

**Generating a strong API key:**

```bash
# macOS / Linux
openssl rand -hex 32
# Output: a4f8c3d1e9b0...  (64-character hex string)

# Use with sk- prefix convention
# ZSCALER_MCP_AUTH_API_KEY=sk-a4f8c3d1e9b0...
```

---

### JWT Mode (External IdP via JWKS)

Validates JSON Web Tokens issued by an external Identity Provider. The server downloads the IdP's public keys once (via JWKS) and validates token signatures locally — no per-request calls to the IdP.

**Server configuration:**

```bash
# .env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=jwt

# Required: your IdP's JWKS endpoint
ZSCALER_MCP_AUTH_JWKS_URI=https://your-idp.com/.well-known/jwks.json

# Required: expected token issuer (must match the "iss" claim)
ZSCALER_MCP_AUTH_ISSUER=https://your-idp.com

# Optional: expected audience (default: zscaler-mcp-server)
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server

# Optional: allowed signing algorithms (default: RS256,ES256)
ZSCALER_MCP_AUTH_ALGORITHMS=RS256,ES256
```

**Client sends:**

```text
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Compatible Identity Providers and their JWKS endpoints:**

| Provider | JWKS URI |
|----------|----------|
| Okta | `https://{domain}.okta.com/oauth2/default/v1/keys` |
| Azure AD / Entra ID | `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys` |
| Auth0 | `https://{domain}.auth0.com/.well-known/jwks.json` |
| PingOne / PingIdentity | `https://auth.pingone.com/{envId}/as/jwks` |
| Keycloak | `https://{host}/realms/{realm}/protocol/openid-connect/certs` |
| AWS Cognito | `https://cognito-idp.{region}.amazonaws.com/{pool}/.well-known/jwks.json` |
| Google | `https://www.googleapis.com/oauth2/v3/certs` |

**Characteristics:**

- Enterprise-grade, standards-based (OIDC / OAuth 2.0)
- Tokens have expiry — automatically enforced
- JWKS keys are cached and refreshed every hour (handles key rotation)
- Validates `iss`, `aud`, `exp` claims
- Best for: enterprise deployments, SSO integration, multi-tenant environments

---

### Zscaler Mode (OneAPI Credentials)

Validates Zscaler OneAPI client credentials by calling Zscaler's OAuth2 `/token` endpoint. This mode is designed for organizations that want to authenticate MCP clients using the same Zscaler API credentials.

**Server configuration:**

```bash
# .env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=zscaler

# These are reused from the Layer 2 Zscaler API config
ZSCALER_VANITY_DOMAIN=your-vanity-domain
ZSCALER_CLOUD=production    # or "beta"
```

**Client sends (Method 1 — Basic Auth):**

```text
Authorization: Basic base64(client_id:client_secret)
```

The `Authorization` header contains the Base64-encoded string of `client_id:client_secret`. For example, if your client ID is `abc123` and your secret is `xyz789`:

```bash
echo -n "abc123:xyz789" | base64
# Output: YWJjMTIzOnh5ejc4OQ==
# Header: Authorization: Basic YWJjMTIzOnh5ejc4OQ==
```

**Client sends (Method 2 — Custom Headers):**

```text
X-Zscaler-Client-ID: your-client-id
X-Zscaler-Client-Secret: your-client-secret
```

This alternative avoids Base64 encoding. Both methods are supported; the server checks custom headers first, then falls back to Basic Auth.

**Characteristics:**

- Validates credentials against Zscaler's `/oauth2/v1/token` endpoint
- Successful validations are cached for the token's lifetime (typically 1 hour)
- No additional IdP required — uses Zscaler's own auth infrastructure
- The `client_id` and `client_secret` used for MCP client auth can be the same as or different from the Layer 2 API credentials
- Best for: Zscaler-native deployments, teams already managing Zscaler API credentials

---

### OIDC Mode (OAuth 2.1)

OAuth 2.1 with a browser login, for human operators. The server acts as an **OAuth 2.0 protected resource** ([RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html)): it does not issue tokens or run an authorization flow — it points clients at your Identity Provider and verifies the tokens they come back with.

Two routes exist in this mode, and that is the whole surface:

| Route | Purpose |
|-------|---------|
| `/.well-known/oauth-protected-resource` | Names your IdP as the authorization server for this resource |
| `/mcp` | The MCP endpoint, requiring `Authorization: Bearer <token>` |

There is deliberately **no** `/authorize`, `/token`, or `/register` — those live on your IdP, and requesting them here returns `404`. An unauthenticated request to `/mcp` returns `401` with a `WWW-Authenticate` header pointing at the metadata document, which is how a client discovers where to authenticate:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer error="invalid_token",
  resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"
```

Configured entirely through environment variables, like every other mode:

```bash
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=oidc

OIDCPROXY_CONFIG_URL=https://your-idp.example.com/.well-known/openid-configuration
OIDCPROXY_CLIENT_ID=YOUR_CLIENT_ID
OIDCPROXY_BASE_URL=https://mcp.example.com
OIDCPROXY_AUDIENCE=YOUR_CLIENT_ID
```

**Characteristics:**

- User-facing login — the client opens a browser against your IdP's login page
- **No client secret.** Verifying a signature needs the IdP's public keys, not a credential of ours
- No static tokens or shared secrets on the server side
- Token refresh handled by the MCP client
- The issuer and JWKS URI are read from the IdP's discovery document at startup, so they always match what it actually signs with
- Works with any OIDC-compliant Identity Provider (Auth0, Okta, Microsoft Entra ID, Keycloak, Google, PingOne, AWS Cognito)
- Best for: production deployments, enterprise SSO, multi-user environments

**Trade-off vs. the old proxy:** clients can no longer self-register via Dynamic Client Registration. Each client needs a client ID issued by your IdP. In exchange, there is no proxy to misconfigure, no client secret to store, and the login is a normal OAuth flow your IdP already audits.

**When to use `oidc` vs other modes:**

| Scenario | Recommended Mode |
|----------|-----------------|
| Local development, quick testing | `api-key` |
| CI/CD, automation, M2M workloads | `jwt` |
| Existing Zscaler API credentials | `zscaler` |
| Production with user login, enterprise SSO | **`oidc`** |
| Multi-user with per-user audit trail | **`oidc`** |

The mode name is `oidc`; `oidcproxy` and `oauth-proxy` still resolve, so existing `.env` files keep working.

See [OIDC Setup (OAuth 2.1)](#oidc-setup-oauth-21) for detailed configuration instructions.

---

## Deployment Options

### Option A: Docker with stdio (No Auth)

The simplest deployment. The MCP client spawns the Docker container as a local process. Communication happens over stdin/stdout. No network exposure, no authentication needed.

**Prerequisites:**

1. Docker installed and running
2. Docker image built locally
3. `.env` file with Zscaler API credentials

#### Step 1: Build the Docker image

```bash
# From the project root
make docker-build
# or manually:
docker build -t zscaler-mcp-server:latest .
```

#### Step 2: Verify the image

```bash
docker images | grep zscaler-mcp-server
```

#### Step 3: Create your `.env` file

Copy `.env.example` and fill in your Zscaler API credentials:

```bash
cp .env.example .env
# Edit .env with your credentials
```

At minimum, set these values:

```bash
ZSCALER_CLIENT_ID=your-client-id
ZSCALER_CLIENT_SECRET=your-client-secret
ZSCALER_CUSTOMER_ID=your-customer-id
ZSCALER_VANITY_DOMAIN=your-vanity-domain
```

#### Step 4: Test the container

```bash
make docker-run
# or manually:
docker run -i --rm --env-file .env zscaler-mcp-server:latest
```

The server should start and wait for JSON-RPC input on stdin. Press `Ctrl+C` to stop.

#### Step 5: Configure your MCP client (see [Client Configuration](#client-configuration) below)

---

### Option B: Docker with HTTP (With Auth)

The server runs as a persistent HTTP service. Clients connect over the network. Authentication is strongly recommended.

> **Critical: Run the container separately from Claude Desktop.**
> Claude Desktop's `command` field communicates with spawned processes via **stdio** (stdin/stdout). If you put `--transport streamable-http` inside Claude Desktop's `command` args, the server will listen on HTTP while Claude Desktop tries to talk via stdin — neither side will receive messages, and Claude Desktop will disconnect the server after ~40 seconds. See [Server disconnects immediately in Claude Desktop](#server-disconnects-immediately-in-claude-desktop) for details.
>
> The correct approach: start the Docker container **independently** (in a terminal or via `docker run -d`), then configure Claude Desktop to connect to it via `mcp-remote`. Cursor, Windsurf, and VS Code can connect directly via their native `url` + `headers` config.

**Prerequisites:**

1. Docker installed and running
2. Docker image built locally
3. `.env` file with Zscaler API credentials AND auth configuration

#### Step 1: Build the Docker image (same as Option A)

```bash
make docker-build
```

#### Step 2: Configure authentication in `.env`

Choose one of the auth modes and add the appropriate variables.

**API Key mode** (recommended for local testing — simple, no token expiry, works reliably with `mcp-remote`):

```bash
# .env — add these lines to your existing .env file
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=api-key
ZSCALER_MCP_AUTH_API_KEY=sk-your-secret-key-here
```

**Zscaler mode:**

```bash
# .env — add these lines
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=zscaler
# ZSCALER_VANITY_DOMAIN and ZSCALER_CLOUD are reused from your API config
```

**JWT mode** (see [important caveat about `mcp-remote`](#jwt-mode--mcp-remote-oauth-discovery-failure)):

```bash
# .env — add these lines
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=jwt
ZSCALER_MCP_AUTH_JWKS_URI=https://your-idp.com/.well-known/jwks.json
ZSCALER_MCP_AUTH_ISSUER=https://your-idp.com/
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
```

#### Step 3: Stop any existing container, then start a new one

You must stop any existing container first to avoid port conflicts:

```bash
# Stop and remove any existing container on port 8000
docker stop zscaler-mcp-server 2>/dev/null; docker rm zscaler-mcp-server 2>/dev/null

# Start a new container
make docker-run-http
# or manually:
docker run -d --restart=unless-stopped --name zscaler-mcp-server \
  -p 8000:8000 --env-file .env zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000
```

The server is now running at `http://localhost:8000/mcp`.

**Excluding specific tools or services** — use `--disabled-tools` or `--disabled-services` to exclude tools/services without listing every tool you want to keep:

```bash
# Exclude a single tool
docker run -d --restart=unless-stopped --name zscaler-mcp-server \
  -p 8000:8000 --env-file .env zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000 \
  --disabled-tools "zia_list_devices"

# Exclude all tools from a service prefix (wildcards supported)
docker run -d --restart=unless-stopped --name zscaler-mcp-server \
  -p 8000:8000 --env-file .env zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000 \
  --disabled-tools "zcc_*,zdx_*"

# Or exclude entire services
docker run -d --restart=unless-stopped --name zscaler-mcp-server \
  -p 8000:8000 --env-file .env zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000 \
  --disabled-services "zcc,zdx"
```

You can also set these via environment variables in your `.env` file:

```text
ZSCALER_MCP_DISABLED_TOOLS=zia_list_devices
ZSCALER_MCP_DISABLED_SERVICES=zcc
```

> **If you see `Bind for 0.0.0.0:8000 failed: port is already allocated`**, an existing container or process is still using port 8000. See [Port 8000 already allocated](#port-8000-already-allocated) for resolution.

#### Step 4: Verify the server is running

```bash
# Check container status
docker ps | grep zscaler-mcp-server

# Check logs
docker logs zscaler-mcp-server

# Test the endpoint (should return 401 without auth, confirming auth is active)
curl -s http://localhost:8000/mcp

# Test with your auth token (should return 200)
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-secret-key-here" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

#### Step 5: Generate the auth token (optional — for Zscaler mode)

```bash
make docker-generate-auth-token
# or manually:
docker run --rm --env-file .env zscaler-mcp-server:latest --generate-auth-token
```

This prints ready-to-paste configuration snippets for Cursor, Claude Desktop, and other clients.

#### Step 6: Configure your MCP client (see [Client Configuration](#client-configuration) below)

**Stopping the server:**

```bash
make docker-stop
# or manually:
docker stop zscaler-mcp-server && docker rm zscaler-mcp-server
```

---

### Option C: Local Python (uv / pip)

Run the server directly as a Python process without Docker.

**Prerequisites:**

1. Python 3.10+
2. `uv` (recommended) or `pip`

#### Step 1: Install the package

```bash
# With uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

#### Step 2: Create your `.env` file (same as Option A)

#### Step 3: Run with stdio (no auth)

```bash
# Load env vars and run
export $(cat .env | xargs)
zscaler-mcp --transport stdio
```

#### Step 4: Run with HTTP (with auth)

```bash
export $(cat .env | xargs)
zscaler-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

#### Step 5: Generate auth token

```bash
export $(cat .env | xargs)
zscaler-mcp --generate-auth-token
```

---

### Remote Deployment (EC2, VM, etc.)

When running the MCP server on a **remote host** (EC2, VM, internal server) so clients on other machines connect over HTTP:

#### Server requirements

1. **Activate the correct virtualenv** — If you installed with `uv pip install -e .`, the package runs from the project's `.venv`. **You must activate it** before starting the server; otherwise a different (older) installation may be used and Host header handling can fail.

   ```bash
   cd /path/to/zscaler-mcp-server
   source .venv/bin/activate
   zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8000
   ```

2. **HTTPS is required by default** — When binding to a non-localhost interface, the server requires TLS certificates. Provide them in `.env`:

   ```bash
   ZSCALER_MCP_TLS_CERTFILE=/path/to/cert.pem
   ZSCALER_MCP_TLS_KEYFILE=/path/to/key.pem
   ```

   If TLS is terminated upstream (reverse proxy, ALB, ZPA overlay, VPN), you may explicitly allow plaintext HTTP:

   ```bash
   ZSCALER_MCP_ALLOW_HTTP=true
   ```

3. **Use `--host 0.0.0.0`** — Binding to all interfaces requires explicit host validation configuration. Without this, clients sending the server's public IP in the `Host` header receive `421 Misdirected Request`.

4. **`.env` configuration options:**
   - `ZSCALER_MCP_ALLOWED_HOSTS=34.201.19.115:*,localhost:*` — (Recommended) Restrict to known hosts.
   - `ZSCALER_MCP_DISABLE_HOST_VALIDATION=true` — Explicitly disable Host validation.
   - `ZSCALER_MCP_ALLOWED_SOURCE_IPS=10.0.0.0/8,172.16.0.5` — (Optional) Restrict by client source IP. When unset, source IP filtering is deferred to upstream firewalls/security groups.

5. **Firewall** — Allow inbound traffic on the chosen port (e.g. 8000).

#### Client configuration (Claude Desktop)

Claude Desktop expects a local process. For remote HTTP, use `mcp-remote` as a stdio-to-HTTP bridge. It supports custom authentication headers via `--header`.

> **`--allow-http` flag**: `mcp-remote` enforces HTTPS for non-localhost URLs by default. When connecting to a remote server over plain HTTP, you must include `--allow-http` in the arguments. Omit this flag when using HTTPS or connecting to `localhost`.

**macOS / Linux:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ]
    }
  }
}
```

**Windows:**

On Windows, paths containing spaces (e.g., `C:\Program Files\nodejs\npx.cmd`) cause failures when `npx` is invoked directly as the `command`. Wrap through `cmd /c` to let Windows resolve the path:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ]
    }
  }
}
```

**Using Zscaler auth mode (Basic Auth) on Windows:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Basic BASE64_ENCODED_CREDENTIALS"
      ]
    }
  }
}
```

Generate the Base64 value:

```bash
# Linux / macOS
echo -n "your-client-id:your-client-secret" | base64

# Windows (PowerShell)
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-client-id:your-client-secret"))
```

Replace `YOUR_SERVER_IP` with the server's public IP or hostname and `BASE64_ENCODED_CREDENTIALS` with the output from the command above.

**Client prerequisites:** [Node.js](https://nodejs.org/) (for `npx`) must be installed.

See [421 Misdirected Request](#421-misdirected-request-invalid-host-header) for troubleshooting.

---

## Client Configuration

> **Layer 1 vs. Layer 2 — what goes where?**
>
> The client configurations below only handle **Layer 1** — authenticating the MCP client to the server (API key, JWT, or Zscaler credentials in the `Authorization` header).
>
> **Layer 2** settings — `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, `ZSCALER_VANITY_DOMAIN`, `ZSCALER_CUSTOMER_ID`, `ZSCALER_CLOUD`, `ZSCALER_MCP_WRITE_ENABLED`, `ZSCALER_MCP_WRITE_TOOLS`, and all other `ZSCALER_*` variables — are configured **on the server side** via the `.env` file. The client never sends or needs these values; the server loads them from `.env` at startup and uses them to call Zscaler APIs on behalf of the client.
>
> In short:
>
> - **Client config** = URL + auth header (how to reach and authenticate with the MCP server)
> - **Server `.env`** = Zscaler API credentials + service/tool/write-mode configuration (how the server talks to Zscaler)

### Claude Desktop

Claude Desktop's configuration file location:

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

#### Scenario 1: stdio via Docker (No Auth) — Recommended for Single User

This is the simplest setup. Claude Desktop spawns the Docker container directly using the published image from Docker Hub — no local build required.

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

Replace `/absolute/path/to/your/.env` with the full path to your `.env` file.

**Requirements:**

- Docker must be running (Docker pulls `zscaler/zscaler-mcp-server:latest` from Docker Hub on first launch)
- No local build required

> **Developers building locally:** swap the image for the local tag built by `make docker-build` (`zscaler-mcp-server:latest`) and add `--pull=never` to skip the registry lookup.

#### Scenario 2: HTTP via mcp-remote Bridge (With Auth)

Claude Desktop does not natively support HTTP URLs with custom headers in its configuration file. To connect to an authenticated HTTP server, use the `mcp-remote` bridge — a Node.js package that acts as a stdio-to-HTTP proxy.

> **Important: The Docker container must be running independently before you start Claude Desktop.**
> Do **not** put `--transport streamable-http` inside Claude Desktop's `command` args. Claude Desktop communicates with launched processes via stdin/stdout, which is incompatible with HTTP transport. See [Server disconnects immediately in Claude Desktop](#server-disconnects-immediately-in-claude-desktop) for a detailed explanation.

**Prerequisites:**

- Node.js and npm installed (`node --version && npm --version`)
- Docker image built (`make docker-build`)
- `.env` file configured with auth settings

#### Step 1: Start the MCP server container separately

Open a terminal and run:

```bash
# Stop any existing container first to avoid port conflicts
docker stop zscaler-mcp-server 2>/dev/null; docker rm zscaler-mcp-server 2>/dev/null

# Start the container
docker run -d --restart=unless-stopped --name zscaler-mcp-server \
  -p 8000:8000 --env-file /absolute/path/to/your/.env \
  zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000

# Verify it's running
docker logs zscaler-mcp-server 2>&1 | tail -5
```

You should see `Uvicorn running on http://0.0.0.0:8000`.

#### Step 2: Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

**macOS / Linux — API Key auth** (recommended — simplest, no token expiry):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "Authorization: Bearer sk-your-secret-key-here"
      ]
    }
  }
}
```

**Windows — API Key auth:**

On Windows, `npx` may fail when its install path contains spaces (e.g., `C:\Program Files\nodejs\npx.cmd`). Use `cmd /c` as the command:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "Authorization: Bearer sk-your-secret-key-here"
      ]
    }
  }
}
```

**macOS / Linux — Zscaler auth (Basic Auth):**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "Authorization: Basic BASE64_ENCODED_CREDENTIALS"
      ]
    }
  }
}
```

**Windows — Zscaler auth (Basic Auth):**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "Authorization: Basic BASE64_ENCODED_CREDENTIALS"
      ]
    }
  }
}
```

Replace `BASE64_ENCODED_CREDENTIALS` with the output from `make docker-generate-auth-token`.

Generate it manually:

```bash
# macOS / Linux
echo -n "your-client-id:your-client-secret" | base64

# Windows (PowerShell)
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-client-id:your-client-secret"))
```

**macOS / Linux — Zscaler auth (Custom Headers):**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "X-Zscaler-Client-ID: your-client-id",
        "--header",
        "X-Zscaler-Client-Secret: your-client-secret"
      ]
    }
  }
}
```

**Windows — Zscaler auth (Custom Headers):**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "X-Zscaler-Client-ID: your-client-id",
        "--header",
        "X-Zscaler-Client-Secret: your-client-secret"
      ]
    }
  }
}
```

> **Remote (non-localhost) servers**: When connecting to a remote server over plain HTTP, add `"--allow-http"` before `"--header"` in the `args` array. `mcp-remote` enforces HTTPS for non-localhost URLs by default. See [mcp-remote: Non-HTTPS URL rejected](#mcp-remote-non-https-url-rejected).
> **JWT mode caveat:** When using JWT auth, `mcp-remote` may attempt OAuth 2.1 discovery instead of forwarding the `--header` value. If you experience 401 errors followed by 404s on `/.well-known/*` endpoints, switch to `api-key` mode for local testing or use the automated setup script (`./scripts/setup-jwt-auth.sh`). See [JWT mode + mcp-remote OAuth discovery failure](#jwt-mode--mcp-remote-oauth-discovery-failure).

#### Step 3: Restart Claude Desktop

Quit and reopen Claude Desktop for the configuration changes to take effect. The MCP server should connect and load all tools.

---

### Cursor

Cursor supports MCP servers via its settings. Configuration can be done through the UI or by editing the JSON config directly.

**Config file locations:**

| Scope | Path |
|-------|------|
| Global | `~/.cursor/mcp.json` |
| Project | `<project-root>/.cursor/mcp.json` |

#### Scenario 1: stdio via Docker (No Auth)

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

#### Scenario 2: HTTP with Auth (Recommended for Cursor)

Cursor natively supports `url` + `headers` in its MCP configuration, making HTTP auth straightforward.

**With API Key auth:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer sk-your-secret-key-here"
      }
    }
  }
}
```

**With Zscaler auth (Basic Auth):**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Basic BASE64_ENCODED_CREDENTIALS"
      }
    }
  }
}
```

**With Zscaler auth (Custom Headers):**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "X-Zscaler-Client-ID": "your-client-id",
        "X-Zscaler-Client-Secret": "your-client-secret"
      }
    }
  }
}
```

**With JWT auth:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIs..."
      }
    }
  }
}
```

For JWT, obtain the token from your Identity Provider (Okta, Azure AD, Auth0, etc.) using their standard OAuth2 flows.

---

### Windsurf

Windsurf supports MCP servers through its configuration file.

**Config file location:** `~/.codeium/windsurf/mcp_config.json`

#### stdio via Docker (No Auth)

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

#### HTTP with Auth

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "serverUrl": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer sk-your-secret-key-here"
      }
    }
  }
}
```

---

### VS Code (Copilot Chat)

VS Code supports MCP servers through its settings or workspace configuration.

**Config file:** `.vscode/mcp.json` in your workspace, or via VS Code Settings UI.

#### stdio via Docker (No Auth)

```json
{
  "servers": {
    "zscaler-mcp-server": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

#### HTTP with Auth

```json
{
  "servers": {
    "zscaler-mcp-server": {
      "type": "sse",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer sk-your-secret-key-here"
      }
    }
  }
}
```

---

### Generic MCP Clients

Any MCP client that supports HTTP-based transports can connect to the authenticated server. The key information:

| Parameter | Value |
|-----------|-------|
| Server URL | `http://localhost:8000/mcp` |
| Transport | `streamable-http` or `sse` |
| Auth Header | Depends on the configured auth mode (see above) |

For programmatic access via `curl`:

```bash
# API Key mode
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-secret-key-here" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Zscaler mode (Basic Auth)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic BASE64_ENCODED_CREDENTIALS" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Zscaler mode (Custom Headers)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Zscaler-Client-ID: your-client-id" \
  -H "X-Zscaler-Client-Secret: your-client-secret" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## Generating Auth Tokens

The `--generate-auth-token` CLI command reads your `.env` credentials and prints ready-to-use configuration snippets for each client type.

**Via Make (Docker):**

```bash
make docker-generate-auth-token
```

**Via Docker directly:**

```bash
docker run --rm --env-file .env zscaler-mcp-server:latest --generate-auth-token
```

**Via Python directly:**

```bash
export $(cat .env | xargs)
zscaler-mcp --generate-auth-token
```

**For Bearer (API Key) format:**

```bash
docker run --rm --env-file .env zscaler-mcp-server:latest --generate-auth-token bearer
```

The command outputs formatted configuration blocks for Cursor (`url` + `headers`), Claude Desktop (`mcp-remote` bridge), and the raw `Authorization` header value.

**Important:** The token is deterministic — it is simply the Base64 encoding of `client_id:client_secret` from your `.env` file. Running `--generate-auth-token` and running the server with the same `.env` will always produce and expect the same token.

**Manual token generation (without the CLI):**

```bash
# For Zscaler mode (Basic Auth)
echo -n "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" | base64

# For API Key mode (Bearer)
# Just use the API key directly: Authorization: Bearer <your-api-key>
```

---

## Setting Up JWT Authentication (JWKS)

JWT authentication mode works with any Identity Provider that publishes a JWKS (JSON Web Key Set) endpoint. The MCP server downloads the IdP's public keys once, then validates every incoming token locally — no per-request calls to the IdP.

This section covers the general process, then provides IdP-specific instructions for the most common providers.

### General Process

Regardless of which IdP you use, the setup follows four steps:

#### Step 1: Register the MCP Server as an API/Resource in Your IdP

Every IdP has a concept of a "protected resource" or "API" that clients request access to. Create one with these settings:

| Setting | Value |
|---------|-------|
| Name | `Zscaler MCP Server` (or any descriptive name) |
| Identifier / Audience | `zscaler-mcp-server` (a logical name, not a URL) |
| Signing Algorithm | `RS256` (recommended) or `ES256` |

The **identifier** becomes the `aud` (audience) claim in issued tokens. It must match the `ZSCALER_MCP_AUTH_AUDIENCE` value in your `.env` file.

#### Step 2: Create a Client Application for Token Generation

Create a **machine-to-machine** (M2M) or **service account** application in your IdP. This application is what you'll use to request JWTs. Note the **Client ID** and **Client Secret** — these are used only for token generation, not by the MCP server itself.

No special scopes or permissions are required. The MCP server only validates the token's signature, issuer, audience, and expiry — it does not check for specific claims or roles.

#### Step 3: Gather the Three Required Values

From your IdP, you need exactly three values to configure the MCP server:

| Value | What It Is | Where to Find It |
|-------|-----------|-------------------|
| **JWKS URI** | URL to the IdP's public key set | Usually at `https://<idp-domain>/.well-known/jwks.json` or a similar path |
| **Issuer** | The `iss` claim the IdP puts in tokens | Usually the IdP's base URL (check your IdP's docs) |
| **Audience** | The `aud` claim | The identifier you set in Step 1 |

You can verify the JWKS endpoint is reachable:

```bash
curl -s https://YOUR_IDP_DOMAIN/.well-known/jwks.json | python3 -m json.tool
```

It should return a JSON object with a `keys` array containing one or more public keys.

#### Step 4: Configure the MCP Server

Add these to your `.env` file:

```bash
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=jwt
ZSCALER_MCP_AUTH_JWKS_URI=https://YOUR_IDP_DOMAIN/.well-known/jwks.json
ZSCALER_MCP_AUTH_ISSUER=https://YOUR_IDP_DOMAIN/
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

Start (or restart) the server. Check the logs to confirm:

```text
MCP CLIENT AUTHENTICATION ENABLED
   Mode: jwt
   JWKS URI: https://YOUR_IDP_DOMAIN/.well-known/jwks.json
   Issuer: https://YOUR_IDP_DOMAIN/
   Audience: zscaler-mcp-server
```

#### Step 5: Request a Token and Test

Use your IdP's token endpoint with the client credentials from Step 2. The exact `curl` command varies by IdP (see examples below), but the response always includes an `access_token` field containing the JWT.

Test the token against the running server:

```bash
TOKEN="eyJhbGciOi..."

# Should pass auth and reach the MCP protocol layer
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Should return 401
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# Should return 401
curl -s http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

Once verified, paste the token into your MCP client config (see [Client Configuration](#client-configuration)).

---

### IdP-Specific Instructions

Below are the JWKS URI, issuer format, and token request command for common Identity Providers.

#### Auth0

**JWKS URI:** `https://{tenant}.{region}.auth0.com/.well-known/jwks.json`

**Issuer:** `https://{tenant}.{region}.auth0.com/` (trailing slash required)

**IdP setup:**

1. **Applications > APIs > Create API** — set Identifier to `zscaler-mcp-server`, Signing Algorithm to `RS256`
2. **Applications > Applications > Create Application** — choose "Machine to Machine", authorize it for the API above

**`.env` configuration:**

```bash
ZSCALER_MCP_AUTH_JWKS_URI=https://your-tenant.us.auth0.com/.well-known/jwks.json
ZSCALER_MCP_AUTH_ISSUER=https://your-tenant.us.auth0.com/
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

**Token request:**

```bash
curl -s --request POST \
  --url https://your-tenant.us.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "zscaler-mcp-server",
    "grant_type": "client_credentials"
  }'
```

**Default token expiry:** 24 hours (configurable in APIs > Settings > Token Expiration)

---

#### Okta

**JWKS URI:** `https://{domain}.okta.com/oauth2/default/v1/keys`

**Issuer:** `https://{domain}.okta.com/oauth2/default`

**IdP setup:**

1. **Security > API > Authorization Servers** — use `default` or create a custom one; add an audience claim for `zscaler-mcp-server`
2. **Applications > Applications > Create App Integration** — choose "API Services" (machine-to-machine)
3. Assign the application to the authorization server with a scope (e.g., `mcp:access`)

**`.env` configuration:**

```bash
ZSCALER_MCP_AUTH_JWKS_URI=https://your-domain.okta.com/oauth2/default/v1/keys
ZSCALER_MCP_AUTH_ISSUER=https://your-domain.okta.com/oauth2/default
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

**Token request:**

```bash
curl -s --request POST \
  --url https://your-domain.okta.com/oauth2/default/v1/token \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode 'client_id=YOUR_CLIENT_ID' \
  --data-urlencode 'client_secret=YOUR_CLIENT_SECRET' \
  --data-urlencode 'scope=mcp:access'
```

---

#### Azure AD / Microsoft Entra ID

**JWKS URI:** `https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys`

**Issuer:** `https://login.microsoftonline.com/{tenant-id}/v2.0`

**IdP setup:**

1. **App registrations > New registration** — register the MCP server app
2. **Expose an API** — set Application ID URI (e.g., `api://zscaler-mcp-server`), add a scope
3. **App registrations > New registration** — register a client app for token generation
4. **API permissions** — grant the client app permission to the MCP server app
5. **Certificates & secrets** — create a client secret for the client app

**`.env` configuration:**

```bash
ZSCALER_MCP_AUTH_JWKS_URI=https://login.microsoftonline.com/YOUR_TENANT_ID/discovery/v2.0/keys
ZSCALER_MCP_AUTH_ISSUER=https://login.microsoftonline.com/YOUR_TENANT_ID/v2.0
ZSCALER_MCP_AUTH_AUDIENCE=api://zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

**Token request:**

```bash
curl -s --request POST \
  --url "https://login.microsoftonline.com/YOUR_TENANT_ID/oauth2/v2.0/token" \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode 'client_id=YOUR_CLIENT_ID' \
  --data-urlencode 'client_secret=YOUR_CLIENT_SECRET' \
  --data-urlencode 'scope=api://zscaler-mcp-server/.default'
```

---

#### Keycloak

**JWKS URI:** `https://{host}/realms/{realm}/protocol/openid-connect/certs`

**Issuer:** `https://{host}/realms/{realm}`

**IdP setup:**

1. Create a realm (or use an existing one)
2. **Clients > Create client** — set Client type to "OpenID Connect", enable "Client authentication" (confidential), enable "Service accounts roles"
3. Note the Client ID and Client Secret from the Credentials tab

**`.env` configuration:**

```bash
ZSCALER_MCP_AUTH_JWKS_URI=https://keycloak.example.com/realms/your-realm/protocol/openid-connect/certs
ZSCALER_MCP_AUTH_ISSUER=https://keycloak.example.com/realms/your-realm
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

**Token request:**

```bash
curl -s --request POST \
  --url "https://keycloak.example.com/realms/your-realm/protocol/openid-connect/token" \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode 'client_id=YOUR_CLIENT_ID' \
  --data-urlencode 'client_secret=YOUR_CLIENT_SECRET'
```

---

#### AWS Cognito

**JWKS URI:** `https://cognito-idp.{region}.amazonaws.com/{user-pool-id}/.well-known/jwks.json`

**Issuer:** `https://cognito-idp.{region}.amazonaws.com/{user-pool-id}`

**IdP setup:**

1. Create a User Pool (or use an existing one)
2. **App integration > Resource servers** — create a resource server with identifier `zscaler-mcp-server` and a custom scope
3. **App integration > App clients** — create an app client with `client_credentials` grant enabled; assign the scope from step 2

**`.env` configuration:**

```bash
ZSCALER_MCP_AUTH_JWKS_URI=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_EXAMPLE/.well-known/jwks.json
ZSCALER_MCP_AUTH_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_EXAMPLE
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

**Token request:**

```bash
curl -s --request POST \
  --url "https://your-domain.auth.us-east-1.amazoncognito.com/oauth2/token" \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode 'client_id=YOUR_CLIENT_ID' \
  --data-urlencode 'client_secret=YOUR_CLIENT_SECRET' \
  --data-urlencode 'scope=zscaler-mcp-server/access'
```

---

#### PingOne / PingIdentity

**JWKS URI:** `https://auth.pingone.com/{environment-id}/as/jwks`

**Issuer:** `https://auth.pingone.com/{environment-id}/as`

**`.env` configuration:**

```bash
ZSCALER_MCP_AUTH_JWKS_URI=https://auth.pingone.com/YOUR_ENV_ID/as/jwks
ZSCALER_MCP_AUTH_ISSUER=https://auth.pingone.com/YOUR_ENV_ID/as
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

---

#### Google Cloud Identity

**JWKS URI:** `https://www.googleapis.com/oauth2/v3/certs`

**Issuer:** `https://accounts.google.com`

**`.env` configuration:**

```bash
ZSCALER_MCP_AUTH_JWKS_URI=https://www.googleapis.com/oauth2/v3/certs
ZSCALER_MCP_AUTH_ISSUER=https://accounts.google.com
ZSCALER_MCP_AUTH_AUDIENCE=YOUR_PROJECT_ID.apps.googleusercontent.com
ZSCALER_MCP_AUTH_ALGORITHMS=RS256
```

---

### How Token Validation Works

Understanding the flow helps with troubleshooting:

1. **Token request (one time):** You request a JWT from your IdP's token endpoint using client credentials. This is the only time the IdP is contacted for authentication.
2. **Server startup (one time):** The MCP server downloads the IdP's public keys from the JWKS endpoint. Keys are cached in memory for 1 hour (handles automatic key rotation).
3. **Every MCP request:** The client sends the JWT in the `Authorization: Bearer` header. The server validates the token **locally** — signature verification using the cached public keys, plus `exp`, `iss`, and `aud` claim checks. No network call to the IdP.

```text
Token request (one time):    You → IdP /token → JWT returned
Server startup (one time):   MCP Server → IdP JWKS → public keys cached (refreshed hourly)
Every MCP request:           Claude/Cursor → JWT in header → MCP Server validates locally
```

### Token Expiry and Refresh

Tokens have a finite lifetime set by your IdP (commonly 1 hour to 24 hours). When a token expires, the MCP server rejects requests with `Token has expired`.

To refresh:

1. Request a new token from your IdP (re-run the `curl` command or the setup script)
2. Update the token in your client config (Claude Desktop, Cursor, etc.)
3. Restart the client application

The MCP server does **not** need to be restarted — it validates tokens locally and the JWKS key cache refreshes automatically.

Most IdPs allow you to configure token lifetime in their dashboard. Consult your IdP's documentation for the specific setting.

---

## Automated Setup Script (Auth0)

The repository includes `scripts/setup-jwt-auth.sh` which automates the end-to-end setup for Auth0 specifically: starting the server, requesting a JWT, verifying it, and updating Claude Desktop and Cursor configs.

The same general approach applies to other IdPs — only the token request step differs. You can adapt the script by replacing the Auth0 `/oauth/token` call with your IdP's equivalent.

### Interactive Mode

```bash
./scripts/setup-jwt-auth.sh
```

The script prompts for:

1. **Server mode** — Docker or Python (local process)
2. **Auth0 Domain** — your tenant domain
3. **Auth0 Client ID** — from the M2M application
4. **Auth0 Client Secret** — from the M2M application

It then starts the server, gets a token, verifies it, and writes the client configs.

### Non-Interactive Mode

Pass everything as environment variables to skip all prompts:

```bash
SERVER_MODE=docker \
AUTH0_DOMAIN=your-tenant.us.auth0.com \
AUTH0_CLIENT_ID=your-client-id \
AUTH0_CLIENT_SECRET=your-client-secret \
./scripts/setup-jwt-auth.sh
```

### Token Refresh Only

When the token expires, re-run the script with `SKIP_SERVER_START=true` to get a fresh token and update client configs without restarting the server:

```bash
AUTH0_DOMAIN=your-tenant.us.auth0.com \
AUTH0_CLIENT_ID=your-client-id \
AUTH0_CLIENT_SECRET=your-client-secret \
SKIP_SERVER_START=true \
./scripts/setup-jwt-auth.sh
```

### Script Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_MODE` | (prompted) | `docker` or `python` |
| `AUTH0_DOMAIN` | (prompted) | Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | (prompted) | M2M application client ID |
| `AUTH0_CLIENT_SECRET` | (prompted) | M2M application client secret |
| `AUTH0_AUDIENCE` | `zscaler-mcp-server` | API identifier |
| `MCP_SERVER_URL` | `http://localhost:8000/mcp` | Server endpoint |
| `MCP_PORT` | `8000` | HTTP listen port |
| `SKIP_SERVER_START` | `false` | Skip server start (token refresh only) |
| `SKIP_CLAUDE_CONFIG` | `false` | Skip Claude Desktop config update |
| `SKIP_CURSOR_CONFIG` | `false` | Skip Cursor config update |

---

## Environment Variable Reference

### MCP Client Authentication (Layer 1)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZSCALER_MCP_AUTH_ENABLED` | No | `false` | Enable MCP client authentication. Set to `true`, `1`, or `yes` to enable. |
| `ZSCALER_MCP_AUTH_MODE` | When auth enabled | `jwt` | Auth mode: `jwt`, `zscaler`, `api-key`, or `oidc` (`oidcproxy` and `oauth-proxy` are accepted aliases) |

**API Key mode variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZSCALER_MCP_AUTH_API_KEY` | Yes | — | The shared secret API key |

**JWT mode variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZSCALER_MCP_AUTH_JWKS_URI` | Yes | — | URL to the IdP's JWKS endpoint |
| `ZSCALER_MCP_AUTH_ISSUER` | Yes | — | Expected `iss` claim in the JWT |
| `ZSCALER_MCP_AUTH_AUDIENCE` | No | `zscaler-mcp-server` | Expected `aud` claim in the JWT |
| `ZSCALER_MCP_AUTH_ALGORITHMS` | No | `RS256,ES256` | Comma-separated list of allowed signing algorithms |

**Zscaler mode variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZSCALER_VANITY_DOMAIN` | Yes | — | Your Zscaler vanity domain (reused from Layer 2) |
| `ZSCALER_CLOUD` | No | `production` | Zscaler cloud environment (reused from Layer 2) |

**OIDC mode variables** (`ZSCALER_MCP_AUTH_MODE=oidc`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OIDCPROXY_CONFIG_URL` | Yes | — | The **IdP's** OIDC discovery URL (e.g., `https://tenant.auth0.com/.well-known/openid-configuration`). Issuer and JWKS URI are read from it at startup. |
| `OIDCPROXY_BASE_URL` | Yes | — | Public base URL of **this** server (e.g., `https://mcp.example.com`) — the OAuth resource identifier |
| `OIDCPROXY_CLIENT_ID` | No | — | The app registration's client ID. Required in practice, since it supplies the default audience. |
| `OIDCPROXY_AUDIENCE` | No | `OIDCPROXY_CLIENT_ID` | Required `aud` claim. Correct for Entra ID by default; set explicitly for Auth0's API identifier. The server refuses to start if neither this nor `OIDCPROXY_CLIENT_ID` is set. |
| `OIDCPROXY_REQUIRED_SCOPES` | No | — | Comma-separated scopes a token must carry |
| `OIDCPROXY_CLIENT_SECRET` | No | — | **Not used.** Nothing here initiates an OAuth exchange, so there is no client credential to present. Ignored if set. |

The variable names keep the `OIDCPROXY_` prefix so existing deployments keep working.

### Zscaler API Credentials (Layer 2)

These are always required, regardless of Layer 1 auth settings.

| Variable | Required | Description |
|----------|----------|-------------|
| `ZSCALER_CLIENT_ID` | Yes | Zscaler OAuth client ID |
| `ZSCALER_CLIENT_SECRET` | Yes | Zscaler OAuth client secret |
| `ZSCALER_CUSTOMER_ID` | Yes | Zscaler customer ID |
| `ZCELL_CUSTOMER_ID` | Yes (for Zscaler Cellular tools) | Zscaler Cellular customer ID — distinct from `ZSCALER_CUSTOMER_ID`; also accepted as the `zcellCustomerId` config key |
| `ZSCALER_VANITY_DOMAIN` | Yes | Zscaler vanity domain |
| `ZSCALER_CLOUD` | No | Cloud environment (`production`, `beta`) |

### Server Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZSCALER_MCP_TRANSPORT` | No | `stdio` | Transport: `stdio`, `sse`, `streamable-http` |
| `ZSCALER_MCP_HOST` | No | `127.0.0.1` | HTTP bind address |
| `ZSCALER_MCP_PORT` | No | `8000` | HTTP listen port |
| `ZSCALER_MCP_DEBUG` | No | `false` | Enable debug logging |
| `ZSCALER_MCP_SERVICES` | No | all | Comma-separated list of services to enable |
| `ZSCALER_MCP_TOOLS` | No | all | Comma-separated list of tools to enable |
| `ZSCALER_MCP_DISABLED_SERVICES` | No | — | Comma-separated list of services to exclude (e.g., `zcc,zdx`). Takes precedence over `ZSCALER_MCP_SERVICES`. |
| `ZSCALER_MCP_DISABLED_TOOLS` | No | — | Comma-separated list of tools to exclude. Supports wildcards (e.g., `zcc_*,zia_list_devices`). Takes precedence over `ZSCALER_MCP_TOOLS`. |
| `ZSCALER_MCP_TOOLSETS` | No | — | Comma-separated toolset ids to enable (e.g. `zia_url_filtering,zpa_app_segments`). Special values: `default` (curated default-on subset), `all` (every toolset). When unset, every toolset whose service is enabled is loaded. The `meta` toolset is always loaded. See [Toolsets guide](../guides/toolsets.md). |
| `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER` | No | `false` | Skip the OneAPI entitlement filter that trims toolsets to the products the configured `ZSCALER_CLIENT_ID` is entitled to. Set to `true` only as an emergency override; the filter is non-fatal by default. |
| `ZSCALER_MCP_WRITE_ENABLED` | No | `false` | Enable write operations (create, update, delete) |
| `ZSCALER_MCP_WRITE_TOOLS` | No | — | Comma-separated allowlist of write tools (supports wildcards) |
| `ZSCALER_MCP_LOG_TOOL_CALLS` | No | `false` | Enable per-tool-call audit logging (tool name, arguments with sensitive values redacted, duration, result summary). |
| `ZSCALER_MCP_DISABLE_HOST_VALIDATION` | No | `false` | Disable Host header validation (use when exposing on EC2/public IP) |
| `ZSCALER_MCP_ALLOWED_HOSTS` | No | — | Comma-separated allowed Host values, e.g. `34.201.19.115:*,localhost:*` |
| `ZSCALER_MCP_TLS_CERTFILE` | No | — | Path to TLS certificate (PEM). Enables HTTPS when set with `TLS_KEYFILE`. |
| `ZSCALER_MCP_TLS_KEYFILE` | No | — | Path to TLS private key (PEM). |
| `ZSCALER_MCP_TLS_KEYFILE_PASSWORD` | No | — | Password for encrypted private key. |
| `ZSCALER_MCP_TLS_CA_CERTS` | No | — | Path to CA certificate bundle for mTLS or custom CA chains. |
| `ZSCALER_MCP_ALLOW_HTTP` | No | `false` | Allow plaintext HTTP on non-localhost. HTTPS is required by default for remote deployments. |
| `ZSCALER_MCP_ALLOWED_SOURCE_IPS` | No | — | Comma-separated allowed client IPs/CIDRs (e.g. `10.0.0.0/8,172.16.0.5`). Unset = no filtering. |
| `ZSCALER_MCP_CONFIRMATION_TTL` | No | `300` | Lifetime in seconds of the HMAC **fallback** confirmation token. Does not govern the sealed `requestState` (SDK envelope TTL, default 600s). No variable skips the confirmation itself. |
| `ZSCALER_MCP_REQUEST_STATE_KEYS` | Only for multi-replica HTTP + writes | *(unset)* | Shared key ring for the SEP-2322 `requestState`. JSON array or comma-separated; each key ≥32 bytes of randomness. Without it each replica uses its own key, so a confirmation retry that lands on a different replica fails. Sticky sessions do **not** help: `2026-07-28` requests carry no session id. First key seals, all unseal. |

---

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make docker-build` | Build the Docker image |
| `make docker-rebuild` | Clean and rebuild the Docker image |
| `make docker-run` | Run container with stdio transport (no auth) |
| `make docker-run-http` | Run container with HTTP transport and auth |
| `make docker-stop` | Stop and remove the HTTP container |
| `make docker-generate-auth-token` | Generate auth token and print client config snippets |
| `make docker-save` | Export Docker image to a `.tar` file |
| `make docker-clean` | Remove Docker images and containers |

---

## Troubleshooting

### Server won't start

**Symptom:** Container exits immediately or shows configuration errors.

**Check:**

1. Verify `.env` file exists and contains required Zscaler API credentials
2. Check auth mode variables are correct:

   ```bash
   docker run --rm --env-file .env zscaler-mcp-server:latest --generate-auth-token
   ```

   If this fails with "ZSCALER_CLIENT_ID and ZSCALER_CLIENT_SECRET must be set", your `.env` file is missing credentials.

3. Check container logs:

   ```bash
   docker logs zscaler-mcp-server
   ```

---

### 401 Unauthorized on every request

**Symptom:** The server is running but all MCP requests return 401.

**Check:**

1. Verify the `Authorization` header matches exactly what the server expects
2. For Zscaler mode, ensure the Base64 encoding is correct:

   ```bash
   echo -n "your-client-id:your-client-secret" | base64
   ```

3. For API Key mode, ensure the key matches `ZSCALER_MCP_AUTH_API_KEY` exactly
4. For JWT mode, ensure the token is not expired and the issuer/audience match
5. Check server logs for the specific error message:

   ```bash
   docker logs zscaler-mcp-server 2>&1 | grep -i "unauthorized\|auth"
   ```

---

### 421 Misdirected Request (Invalid Host header)

**Symptom:** Server logs show `Invalid Host header: 34.201.19.115:8000` and clients receive `421 Misdirected Request`.

**Cause:** The MCP SDK validates the `Host` header to protect against DNS rebinding. By default it only accepts `127.0.0.1`, `localhost`, and `::1`. When the server is exposed publicly (e.g. on EC2), clients send the public IP in the Host header, which is rejected.

**Resolution (use one):**

1. **`--host 0.0.0.0`** — Host validation is auto-disabled when binding to all interfaces.
2. **`.env`** — Add `ZSCALER_MCP_DISABLE_HOST_VALIDATION=true` or `ZSCALER_MCP_ALLOWED_HOSTS=34.201.19.115:*,localhost:*`.
3. **Correct virtualenv** — When using `uv pip install -e .`, run from the project venv:

   ```bash
   cd /path/to/zscaler-mcp-server
   source .venv/bin/activate
   zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8000
   ```

   A different env (e.g. conda) may use an older installation without the fix.

**Security:** Only disable host validation for servers intentionally exposed to the network. For production, prefer `ZSCALER_MCP_ALLOWED_HOSTS` to restrict to known hostnames.

---

### Claude Desktop fails to launch the server

**Symptom:** Claude Desktop shows "failed to launch" error.

**Check:**

1. Verify Docker is running: `docker ps`
2. Verify the image exists: `docker images | grep zscaler-mcp-server`
3. For stdio mode, verify the `.env` path in `claude_desktop_config.json` is absolute
4. For HTTP mode with `mcp-remote`, verify Node.js and npm are installed: `node --version && npm --version`
5. Check Claude Desktop logs:
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%APPDATA%\Claude\logs\`

---

### Server disconnects immediately in Claude Desktop

**Symptom:** Claude Desktop briefly shows the server as connected, then disconnects within 30-60 seconds. Server logs show the server initialized successfully (all tools registered, Uvicorn running), but Claude Desktop logs show `Server transport closed unexpectedly`.

**Cause:** Claude Desktop's `command` field launches a process and communicates with it via **stdio** (stdin/stdout). If you configure the container with `--transport streamable-http`, the server starts an HTTP listener instead of reading from stdin. Claude Desktop sends the MCP `initialize` message via stdin, the server never reads it (it's waiting for HTTP requests on port 8000), and Claude Desktop times out and kills the process.

When Claude Desktop restarts the process, the previous container hasn't fully released port 8000, causing a cascade of `Bind for 0.0.0.0:8000 failed: port is already allocated` errors.

**Incorrect configuration** (do NOT use this):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-p", "8000:8000",
        "--env-file", "/absolute/path/to/.env",
        "zscaler/zscaler-mcp-server:latest",
        "--transport", "streamable-http",
        "--host", "0.0.0.0",
        "--port", "8000"
      ]
    }
  }
}
```

**Resolution:** Run the Docker container **separately** from Claude Desktop, then use `mcp-remote` to bridge:

1. Start the container in a terminal (not via Claude Desktop):

   ```bash
   docker stop zscaler-mcp-server 2>/dev/null; docker rm zscaler-mcp-server 2>/dev/null
   docker run -d --restart=unless-stopped --name zscaler-mcp-server \
     -p 8000:8000 --env-file .env zscaler-mcp-server:latest \
     --transport streamable-http --host 0.0.0.0 --port 8000
   ```

2. Configure Claude Desktop to connect via `mcp-remote`:

   ```json
   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "http://localhost:8000/mcp",
           "--header",
           "Authorization: Bearer sk-your-api-key"
         ]
       }
     }
   }
   ```

Alternatively, if you don't need HTTP auth, use [Option A: Docker with stdio](#option-a-docker-with-stdio-no-auth) — it works directly with Claude Desktop's `command` field.

---

### Port 8000 already allocated

**Symptom:** `docker: Error response from daemon: Bind for 0.0.0.0:8000 failed: port is already allocated`

**Cause:** An existing Docker container or process is still using port 8000. This commonly happens when:

- A previous `zscaler-mcp-server` container is still running or stopping
- Claude Desktop's restart cycle launched multiple containers before the previous ones released the port
- Another application is using port 8000

**Resolution:**

```bash
# Find and stop existing containers on port 8000
docker ps --filter "publish=8000" -q | xargs -r docker stop
docker ps -a --filter "name=zscaler-mcp-server" -q | xargs -r docker rm

# If a non-Docker process is using the port (macOS/Linux)
lsof -ti :8000 | xargs -r kill -9

# Now start fresh
docker run -d --restart=unless-stopped --name zscaler-mcp-server \
  -p 8000:8000 --env-file .env zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000
```

**Prevention:** Always stop the existing container before starting a new one:

```bash
docker stop zscaler-mcp-server 2>/dev/null; docker rm zscaler-mcp-server 2>/dev/null
```

---

### JWT mode + mcp-remote OAuth discovery failure

**Symptom:** Server logs show `401 Unauthorized` on `GET /mcp` or `POST /mcp`, followed by a series of `404 Not Found` on OAuth discovery endpoints:

```text
GET /mcp HTTP/1.1" 401 Unauthorized
GET /.well-known/oauth-protected-resource/mcp HTTP/1.1" 404 Not Found
GET /.well-known/oauth-protected-resource HTTP/1.1" 404 Not Found
GET /.well-known/oauth-authorization-server HTTP/1.1" 404 Not Found
GET /.well-known/openid-configuration HTTP/1.1" 404 Not Found
POST /register HTTP/1.1" 404 Not Found
```

**Cause:** When `mcp-remote` receives a `401 Unauthorized` response, some versions attempt automatic authentication via the MCP OAuth 2.1 protocol — Dynamic Client Registration (DCR) with `/.well-known/*` discovery. In `jwt` mode the server validates a bearer token directly and serves no OAuth metadata, so these discovery endpoints return 404. The `--header` flag may be ignored or deprioritized in favor of the OAuth discovery attempt.

If you want the client to run OAuth rather than carry a pre-issued token, use [`oidc` mode](#oidc-mode-oauth-21) instead — it serves the `/.well-known/oauth-protected-resource` document `mcp-remote` is looking for.

**Resolution (choose one):**

1. **Switch to API Key mode** (recommended for local testing):

   ```bash
   # .env
   ZSCALER_MCP_AUTH_ENABLED=true
   ZSCALER_MCP_AUTH_MODE=api-key
   ZSCALER_MCP_AUTH_API_KEY=sk-your-secret-key-here
   ```

   API Key mode returns `401` without OAuth metadata hints, so `mcp-remote` correctly falls back to sending the `--header` value. Restart the Docker container after changing `.env`.

2. **Use the automated setup script** for JWT:

   ```bash
   ./local_dev/scripts/setup-jwt-auth.sh
   ```

   This script handles the full JWT flow: starts the server, fetches a token from Auth0, verifies it, and writes the client configs.

3. **Use Cursor instead of Claude Desktop** — Cursor supports `url` + `headers` natively, bypassing the `mcp-remote` bridge entirely:

   ```json
   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "url": "http://localhost:8000/mcp",
         "headers": {
           "Authorization": "Bearer eyJhbGciOi..."
         }
       }
     }
   }
   ```

---

### mcp-remote: Non-HTTPS URL rejected

**Symptom:** Client logs show:

```text
Error: Non-HTTPS URLs are only allowed for localhost or when --allow-http flag is provided
```

**Cause:** `mcp-remote` enforces HTTPS for all non-localhost URLs as a security measure. When connecting to a remote server over plain HTTP (e.g., `http://34.201.19.115:8000/mcp`), this check blocks the connection.

**Resolution:** Add `"--allow-http"` to the `args` array in your client config, before `"--header"`:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "http://YOUR_SERVER_IP:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ]
    }
  }
}
```

For Windows, use `"command": "cmd"` with `"/c", "npx", ...` — see [Windows: npx path with spaces](#windows-npx-path-with-spaces).

---

### Windows: npx path with spaces

**Symptom:** Claude Desktop logs show:

```text
'C:\Program' is not recognized as an internal or external command
```

**Cause:** On Windows, if Node.js is installed in `C:\Program Files\nodejs\`, the path contains a space. When Claude Desktop invokes `npx` as the command, Windows splits on the space and tries to run `C:\Program`, which fails.

**Resolution:** Use `cmd` as the command and pass `/c npx ...` as arguments:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ]
    }
  }
}
```

`cmd /c` handles Windows path resolution correctly and avoids the space issue.

---

### Self-signed certificate rejected by mcp-remote

**Symptom:** Client logs show:

```text
Error: self-signed certificate
code: 'DEPTH_ZERO_SELF_SIGNED_CERT'
```

**Cause:** When the MCP server uses a self-signed TLS certificate, Node.js (used by `mcp-remote`) rejects it because it cannot verify the certificate chain.

**Resolution:** Add `NODE_TLS_REJECT_UNAUTHORIZED=0` to the `env` section of your client config:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://YOUR_SERVER_IP:8000/mcp",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

> **Warning**: This disables all TLS certificate verification for this process. Only use for development/testing. For production, use CA-signed certificates.

---

### mcp-remote bridge errors

**Symptom:** Claude Desktop shows errors related to `npx` or `mcp-remote`.

**Check:**

1. Verify Node.js and npm are installed: `node --version && npm --version`
2. Verify the package installs correctly: `npx -y mcp-remote --help`
3. Verify the MCP server is running and accessible: `curl -s http://localhost:8000/mcp`
4. Ensure the header format in the config is correct — the value after `--header` must be a single string like `"Authorization: Bearer xxx"` (header name and value separated by a colon and space)
5. Make sure the Docker container is running **independently** (not spawned by Claude Desktop) — see [Server disconnects immediately in Claude Desktop](#server-disconnects-immediately-in-claude-desktop)
6. On Windows, use `"command": "cmd"` with `"args": ["/c", "npx", ...]` — see [Windows: npx path with spaces](#windows-npx-path-with-spaces)

---

### Health check and discovery endpoints return 401

**Symptom:** OAuth discovery or health check endpoints are blocked by auth.

**Resolution:** The following paths automatically bypass authentication and should work without credentials:

- `/health`
- `/healthz`
- `/ready`
- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-protected-resource/mcp`
- `/.well-known/oauth-authorization-server`
- `/.well-known/openid-configuration`
- `/register`

If these paths return 401, verify the auth middleware is properly initialized (check server logs).

---

### Zscaler auth mode: "Cannot reach Zscaler authentication service"

**Symptom:** Server logs show connection errors to the Zscaler token endpoint.

**Check:**

1. Verify `ZSCALER_VANITY_DOMAIN` is correct
2. Verify network connectivity from the container:

   ```bash
   docker exec zscaler-mcp-server wget -qO- https://YOUR_DOMAIN.zslogin.net 2>&1 | head
   ```

3. For `beta` cloud, ensure `ZSCALER_CLOUD=beta` is set
4. Check if a firewall or proxy is blocking outbound HTTPS

---

### JWT auth mode: "Failed to retrieve signing key from JWKS endpoint"

**Symptom:** Server logs show JWKS retrieval errors.

**Check:**

1. Verify `ZSCALER_MCP_AUTH_JWKS_URI` is reachable:

   ```bash
   curl -s YOUR_JWKS_URI | head
   ```

2. Verify the URL returns valid JWKS JSON (should contain a `keys` array)
3. Check if the container can reach the IdP (DNS resolution, firewall rules)
4. Verify the token's `kid` (Key ID) header matches a key in the JWKS endpoint

---

## Quick Reference: Which Setup Should I Use?

| Scenario | Transport | Auth Mode | Client Config |
|----------|-----------|-----------|---------------|
| Single user, local development | `stdio` | None | Docker command in client config |
| Single user, wants auth | `streamable-http` | `api-key` | HTTP URL + Bearer header |
| Team sharing one server | `streamable-http` | `jwt` or `api-key` | HTTP URL + auth headers |
| Enterprise with IdP, machine-to-machine | `streamable-http` | `jwt` | HTTP URL + Bearer JWT |
| Enterprise SSO, per-user browser login | `streamable-http` | `oidc` | HTTP URL, no header — client runs OAuth |
| Zscaler-native organization | `streamable-http` | `zscaler` | HTTP URL + Basic Auth / custom headers |
| Claude Desktop + auth (macOS/Linux) | `streamable-http` | any | `mcp-remote` bridge (`npx` command) |
| Claude Desktop + auth (Windows) | `streamable-http` | any | `mcp-remote` bridge (`cmd /c npx`) |
| Remote server (non-localhost HTTP) | `streamable-http` | any | `mcp-remote` + `--allow-http` |
| Remote server (HTTPS with TLS) | `streamable-http` | any | `mcp-remote` (no `--allow-http` needed) |
| Cursor + auth | `streamable-http` | any | Native `url` + `headers` |

---

## OIDC Setup (OAuth 2.1)

Step-by-step instructions for `oidc` mode, in which the server is an OAuth 2.0 protected resource ([RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html)) and clients authenticate against your Identity Provider directly. The examples use Auth0; the same process applies to any OIDC-compliant IdP.

### Prerequisites

1. An OIDC-compliant Identity Provider (Auth0, Okta, Microsoft Entra ID, Keycloak, Google, etc.)
2. `zscaler-mcp-server` installed (or the Docker image)
3. Nothing else — no additional packages

### Step 1: Create an OIDC Application in Your IdP

Clients authenticate against your IdP, so they need an application registration there.

> **The redirect URI belongs to the client, not to this server.** In the old proxy design the server was itself the OAuth client, so the callback was `<server>/auth/callback`. It no longer is. The callback is now a loopback address the MCP client listens on. Register the URI **your client** actually uses.
>
> **With `mcp-remote`, pin the port or the URI you register will not match.** It has no fixed default port — its README claims 3334, but the code derives one from a hash of the server URL (`3335 + hash % 45816`). Pass `3334` as the **first argument after the URL**; that exact position is the only one it reads, and elsewhere the value is parsed as a port, silently becomes `NaN`, and the derived port is used with no warning. IdPs match `redirect_uri` byte-for-byte, so the mismatch fails every login. An explicitly-passed port is used verbatim, so it stays stable across runs.
>
> **Important:** Do not use a Machine-to-Machine (M2M) application. M2M apps only support the `client_credentials` grant, which has no user-facing login. (M2M is the right choice for [JWT mode](#jwt-mode-external-idp-via-jwks) instead.) Register the client as a **public client** using authorization code + PKCE — no client secret is involved anywhere in this mode.

**Auth0 example:**

1. Go to **Auth0 Dashboard > Applications > Applications > Create Application**
2. Select **"Native"** (public client with PKCE)
3. Name it (e.g., `zscaler-mcp-client`)
4. In **Settings**, note the **Client ID**
5. Under **Application URIs > Allowed Callback URLs**, add your client's callback:

   ```text
   http://localhost:3334/oauth/callback
   ```

6. Save changes

**Okta example:**

1. Go to **Okta Admin > Applications > Create App Integration**
2. Select **OIDC - OpenID Connect**, then **Native Application**
3. Set the **Sign-in redirect URI** to `http://localhost:3334/oauth/callback`
4. Note the **Client ID**

**Microsoft Entra ID example:**

1. Go to **Azure Portal > App registrations > New registration**
2. Set the **Redirect URI** to `http://localhost:3334/oauth/callback`, platform **Mobile and desktop applications** (public client)
3. Under **Authentication > Advanced settings**, set **Allow public client flows** to **Yes**
4. Under **API permissions**, add `openid`, `profile`, `email` and grant admin consent
5. Under **Expose an API**, set the **Application ID URI** to your server's full MCP endpoint URL (e.g. `https://mcp.example.com/mcp`) and add a delegated scope named `mcp.access`
6. In the **Manifest**, set `api.requestedAccessTokenVersion` to `2`
7. Note the **Application (client) ID**

> **Important:** For Entra ID, set `OIDCPROXY_AUDIENCE` to the **Application (client) ID** (not an API identifier). Entra ID uses the client ID as the `aud` claim. Since `OIDCPROXY_AUDIENCE` defaults to `OIDCPROXY_CLIENT_ID`, you can simply omit it.
>
> **Entra ID needs three things the other IdPs don't**, and each one fails the login differently. Steps 5 and 6 above are two of them; the third is that `OIDCPROXY_BASE_URL` must be the **full MCP endpoint URL including the path** — a bare origin cannot work, because the client normalizes it to a trailing slash and Entra ID refuses to register an Application ID URI ending in `/`. The client must also be told the scope explicitly (`--static-oauth-client-metadata`), since Entra ID cannot discover it.
>
> **📖 Full step-by-step guide with screenshots:** [OIDC Setup with Microsoft Entra ID](entra-id-oidcproxy.md)

### Step 2: Decide the Audience

`OIDCPROXY_AUDIENCE` is the value the server requires in the token's `aud` claim. Without it, a token your IdP issued for a completely different application would be accepted here, so the server refuses to start if it cannot determine one.

- **Entra ID:** the client ID. Omit `OIDCPROXY_AUDIENCE` and it defaults to `OIDCPROXY_CLIENT_ID`.
- **Auth0:** a separate API identifier. Go to **Auth0 Dashboard > Applications > APIs > Create API**, set the **Identifier** to e.g. `zscaler-mcp-server`, and use that as `OIDCPROXY_AUDIENCE`. Under **Application Access**, authorize your application for it.
- **Okta:** the authorization server's audience (**Okta Admin > Security > API > Authorization Servers**).

### Step 3: Run the Server

`oidc` is configured with environment variables and uses the standard entrypoint — there is no wrapper script and no custom Docker command.

```bash
# .env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=oidc

OIDCPROXY_CONFIG_URL=https://YOUR_DOMAIN/.well-known/openid-configuration
OIDCPROXY_CLIENT_ID=your-client-id
OIDCPROXY_BASE_URL=https://mcp.example.com
OIDCPROXY_AUDIENCE=zscaler-mcp-server        # optional; defaults to the client id
# OIDCPROXY_REQUIRED_SCOPES=zscaler.read     # optional; scopes a token must carry
```

| Variable | Notes |
|----------|-------|
| `OIDCPROXY_CONFIG_URL` | The **IdP's** discovery document. The issuer and JWKS URI are read from it at startup, so they always match what the IdP signs with. |
| `OIDCPROXY_BASE_URL` | **This server's** public URL — the OAuth resource identifier clients use. Not the IdP's. |
| `OIDCPROXY_AUDIENCE` | Required in the token's `aud`. Defaults to `OIDCPROXY_CLIENT_ID`. |
| `OIDCPROXY_CLIENT_SECRET` | **Not used.** Ignored if set; safe to delete. |

Locally:

```bash
export ZSCALER_MCP_ALLOW_HTTP=true   # local dev only, no TLS
zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

Docker — the normal image entrypoint, no override:

```bash
docker run -d --name zscaler-mcp-server \
  -p 8000:8000 \
  --env-file .env \
  -e ZSCALER_MCP_AUTH_ENABLED=true \
  -e ZSCALER_MCP_AUTH_MODE=oidc \
  -e OIDCPROXY_CONFIG_URL="https://YOUR_DOMAIN/.well-known/openid-configuration" \
  -e OIDCPROXY_CLIENT_ID="your-client-id" \
  -e OIDCPROXY_BASE_URL="http://localhost:8000" \
  -e OIDCPROXY_AUDIENCE="zscaler-mcp-server" \
  -e ZSCALER_MCP_ALLOW_HTTP=true \
  zscaler/zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000
```

Verify the metadata document names your IdP:

```bash
curl -s http://localhost:8000/.well-known/oauth-protected-resource | jq
```

```json
{
  "resource": "http://localhost:8000",
  "authorization_servers": ["https://YOUR_DOMAIN"],
  "bearer_methods_supported": ["header"]
}
```

`/.well-known/oauth-authorization-server`, `/register`, `/authorize` and `/token` correctly return `404` — this server is not an authorization server.

### Step 4: Configure Your MCP Client

No static Bearer token is needed. The client reads the metadata document, authenticates with your IdP, and attaches the resulting token itself.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.example.com/mcp"]
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "https://mcp.example.com/mcp"
    }
  }
}
```

Notice there is **no** `Authorization` header. The flow is:

1. The client `POST`s to `/mcp` and gets `401` with a `WWW-Authenticate` header naming the metadata URL
2. It fetches `/.well-known/oauth-protected-resource` and learns which IdP to use
3. It fetches the IdP's own metadata and runs the OAuth flow **against the IdP** — a browser window opens on your IdP's login page
4. After login, the client retries `/mcp` with `Authorization: Bearer <token>`
5. The server verifies the signature, issuer, audience and expiry against the IdP's JWKS
6. Token refresh is handled by the client

Your client needs a client ID from the IdP unless Dynamic Client Registration is both supported *and* switched on there — Entra ID never supports it, and Auth0 supports it but leaves it **off** by default, in which case the registration attempt fails and `mcp-remote` reports only `ServerError`. `mcp-remote` takes pre-registered credentials via `--static-oauth-client-info`, which accepts inline JSON or `@/path/to/file.json`:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote", "https://mcp.example.com/mcp", "3334",
        "--static-oauth-client-info", "{\"client_id\":\"YOUR_CLIENT_ID\"}"
      ]
    }
  }
}
```

To confirm whether your tenant permits self-registration, call the `registration_endpoint` from its discovery document directly — Auth0 advertises the endpoint whether or not the feature is enabled, and answers `400 dynamic client registration is disabled` when it is not.

### How It Works

```text
┌──────────────┐     ┌───────────────────────────┐     ┌──────────────────┐
│  MCP Client  │     │  Zscaler MCP Server       │     │  Identity        │
│  (Claude,    │     │  (protected resource)     │     │  Provider        │
│   Cursor)    │     │                           │     │  (Auth0, Entra)  │
│              │     │  ┌─────────────────────┐  │     │                  │
│  1. POST /mcp├────>│  │ 401 + WWW-Auth ─────┼  │     │                  │
│              │<────│  │ resource_metadata=… │  │     │                  │
│              │     │  └─────────────────────┘  │     │                  │
│  2. Discover ├────>│  ┌─────────────────────┐  │     │                  │
│     resource │<────│  │ /.well-known/oauth- │  │     │                  │
│              │     │  │ protected-resource  │  │     │                  │
│              │     │  │  → names the IdP    │  │     │                  │
│              │     │  └─────────────────────┘  │     │                  │
│              │     │                           │     │                  │
│  3. OAuth flow ─── directly with the IdP ──────┼────>│  User Login      │
│     /authorize, /token, callback to the client │<────│  + Consent       │
│              │     │                           │     │                  │
│  4. POST /mcp├────>│  ┌─────────────────────┐  │     │                  │
│   + Bearer   │     │  │ verify signature /  │  │     │                  │
│              │<────│  │ iss / aud / exp ────┼──┼────>│  JWKS (public    │
│              │     │  └─────────────────────┘  │     │  keys)           │
└──────────────┘     └───────────────────────────┘     └──────────────────┘
```

The server never holds a client credential and never sees the user's password — it only checks signatures against public keys.

### Troubleshooting OIDC

#### `oidc auth mode requires: OIDCPROXY_CONFIG_URL, OIDCPROXY_BASE_URL`

**Symptom:** The server exits at startup with this message.

**Cause:** Required configuration is missing. The server refuses to start half-configured rather than publish metadata clients cannot use.

**Fix:** Set both. `OIDCPROXY_BASE_URL` is **this server's** public URL (the resource identifier), not the IdP's.

#### `oidc auth mode requires OIDCPROXY_AUDIENCE (or OIDCPROXY_CLIENT_ID to default it)`

**Cause:** Neither was set, so there is no expected `aud` value. Accepting any audience would mean a token your IdP issued for an unrelated application would be honoured here.

**Fix:** Set `OIDCPROXY_CLIENT_ID` (the audience then defaults to it, which is correct for Entra ID) or set `OIDCPROXY_AUDIENCE` explicitly (correct for Auth0's API identifier).

#### `Could not read the IdP's OpenID configuration from …`

**Cause:** The server could not fetch the discovery document at startup — wrong URL, or no network path from the host to the IdP.

**Fix:** Verify the URL in a browser or with `curl`. Note that Entra ID's URL is tenant-scoped and ends in `/v2.0/.well-known/openid-configuration`. If the server runs in a locked-down network, confirm egress to the IdP is allowed.

#### `401 invalid_token` after a successful login

**Symptom:** The browser reports success, but `/mcp` still returns `401`.

**Cause:** Almost always an issuer or audience mismatch. Check the server's startup log line, which reports exactly what it will accept:

```text
OIDC auth configured as a protected resource (issuer=…, resource=…, audience=…)
```

**Fix:** Decode the token your client received (e.g. at [jwt.io](https://jwt.io)) and compare its `iss` and `aud` with that line. For Entra ID, `aud` is the client ID; for Auth0, it is the API identifier, and the API must be authorized for the application. Note that the issuer is taken from the IdP's discovery document, not from `OIDCPROXY_CONFIG_URL`, so it does not need to be a prefix of that URL.

#### "Callback URL mismatch" from your IdP

**Cause:** The redirect URI your client used is not registered on the IdP application. The callback belongs to the **client**, not to this server.

**Fix:** The IdP's error page names the `redirect_uri` it received. If that port is not the one you registered, `mcp-remote` chose it: with no port argument it derives one from a hash of the server URL. Pin it by passing the port **immediately after the URL** — `mcp-remote https://mcp.example.com/mcp 3334` — and register `http://localhost:3334/oauth/callback`. The position matters: in any later slot the value is not read as a port and the derived one is used silently. Also register the exact host string the client sends; `127.0.0.1` and `localhost` are different URIs to an IdP even though they reach the same socket.

Note that `<server>/auth/callback` is **not** the callback in this mode — that was the old proxy's URI, when the server was the OAuth client.

#### "ERR_CONNECTION_REFUSED" on the callback URL

**Cause:** `mcp-remote`'s local callback server timed out while you were completing the login (default 30 seconds).

**Fix:** Restart the client and complete the login promptly, or raise `--auth-timeout`.

#### Using an M2M application instead of a Regular Web Application

**Symptom:** The IdP errors out after consent, or no login page appears.

**Cause:** M2M applications only support the `client_credentials` grant, which has no user login.

**Fix:** Create a Regular Web Application. M2M apps belong to [JWT mode](#jwt-mode-external-idp-via-jwks).

#### Requiring specific scopes

Set `OIDCPROXY_REQUIRED_SCOPES` to a comma-separated list. A token missing any of them is rejected, and the requirement is also advertised in the resource metadata so clients know to request them. Leave it unset to accept any successfully-verified token.

---

## HTTPS / TLS Configuration

When running with HTTP transports (`sse` or `streamable-http`), you can enable TLS to encrypt traffic between MCP clients and the server. This is strongly recommended for any deployment accessible over a network.

### Configuration

Set the following environment variables in your `.env` file:

```bash
# Required for TLS
ZSCALER_MCP_TLS_CERTFILE=/path/to/cert.pem
ZSCALER_MCP_TLS_KEYFILE=/path/to/key.pem

# Optional
ZSCALER_MCP_TLS_KEYFILE_PASSWORD=your-key-password     # if the private key is encrypted
ZSCALER_MCP_TLS_CA_CERTS=/path/to/ca-bundle.pem        # for mutual TLS or custom CA chains
```

When both `ZSCALER_MCP_TLS_CERTFILE` and `ZSCALER_MCP_TLS_KEYFILE` are set and point to valid files, the server automatically starts with HTTPS. No additional flags are needed.

### Generating a Self-Signed Certificate (Testing)

For local testing or development, generate a self-signed certificate:

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost"
```

Then set the paths in your `.env`:

```bash
ZSCALER_MCP_TLS_CERTFILE=./cert.pem
ZSCALER_MCP_TLS_KEYFILE=./key.pem
```

### Docker TLS

When running in Docker, mount the certificate files and use absolute container paths:

```bash
docker run -d --name zscaler-mcp-server \
  -p 8000:8000 \
  -v /path/to/certs:/certs:ro \
  --env-file .env \
  -e ZSCALER_MCP_TLS_CERTFILE=/certs/cert.pem \
  -e ZSCALER_MCP_TLS_KEYFILE=/certs/key.pem \
  zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0
```

### Client Configuration for HTTPS

When the server uses TLS, clients connect via `https://` instead of `http://`.

**With a CA-signed certificate (production):**

No additional client configuration is needed — standard TLS validation applies.

**With a self-signed certificate (testing):**

Clients using Node.js (e.g., `mcp-remote`) will reject self-signed certificates by default. Add `NODE_TLS_REJECT_UNAUTHORIZED=0` to the client config:

**macOS / Linux:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://YOUR_SERVER_IP:8000/mcp",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

**Windows:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "cmd",
      "args": [
        "/c", "npx", "-y", "mcp-remote",
        "https://YOUR_SERVER_IP:8000/mcp",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

> **Warning**: `NODE_TLS_REJECT_UNAUTHORIZED=0` disables all certificate verification. Only use this for development and testing with self-signed certificates. For production, use CA-signed certificates.

---

## Security Recommendations

1. **Use stdio for single-user setups.** It is inherently secure (OS process isolation) and requires zero auth configuration.

2. **Always enable auth for HTTP transports.** If the server is reachable over the network, even `localhost`, enable authentication.

3. **Prefer JWT mode for enterprise.** It integrates with your existing IdP, supports token expiry, and requires no shared secrets.

4. **Rotate API keys periodically.** If using `api-key` mode, generate a new key and update clients on a regular schedule.

5. **Never commit `.env` files to version control.** The `.gitignore` should already exclude `.env` — verify this.

6. **Use separate credentials per environment.** Do not reuse production Zscaler API credentials in development.

7. **HTTPS is required by default for remote deployments.** The server blocks plaintext HTTP on non-localhost interfaces unless `ZSCALER_MCP_ALLOW_HTTP=true` is set. Provide TLS certificates or terminate TLS at a reverse proxy. See [HTTPS / TLS Configuration](#https--tls-configuration).

8. **Use source IP restrictions for defense in depth.** Set `ZSCALER_MCP_ALLOWED_SOURCE_IPS` to restrict which clients can connect, complementing upstream firewall rules. When unset, source IP filtering is disabled.

9. **For cloud deployments**, see the [Amazon Bedrock AgentCore deployment guide](./amazon_bedrock_agentcore.md) and the [Secrets Manager integration guide](./secrets_manager_integration.md) for credential management best practices.

10. **Use `oidc` mode for multi-user production deployments.** It gives per-user authentication through your existing IdP, token refresh handled by the client, and an audit trail in the IdP. No shared secrets and no manually rotated tokens — the server holds no credential at all, only the IdP's public keys.
