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
  - [OAuth Proxy Mode (OIDCProxy)](#oauth-proxy-mode-oidcproxy)
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
- [OIDCProxy Setup (OAuth 2.1 + DCR)](#oidcproxy-setup-oauth-21--dcr)
  - [Prerequisites](#prerequisites-1)
  - [Step 1: Create an OIDC Application in Your IdP](#step-1-create-an-oidc-application-in-your-idp)
  - [Step 2: Create an API / Resource Server in Your IdP](#step-2-create-an-api--resource-server-in-your-idp)
  - [Step 3: Run the Server with OIDCProxy](#step-3-run-the-server-with-oidcproxy)
  - [Step 4: Configure Your MCP Client](#step-4-configure-your-mcp-client)
  - [How It Works](#how-it-works)
  - [Automated Setup Script (Auth0)](#automated-setup-script-auth0-oidcproxy)
  - [Troubleshooting OIDCProxy](#troubleshooting-oidcproxy)
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

> **Note:** Layer 1 can be configured either via environment variables (`ZSCALER_MCP_AUTH_*`) or programmatically via the `auth=` parameter. OIDCProxy mode uses the programmatic approach and provides full OAuth 2.1 compliance with Dynamic Client Registration.

---

## Transport Modes

The MCP protocol supports three transport mechanisms. Your choice of transport determines whether authentication is relevant.

| Transport | Protocol | Auth Applicable | Use Case |
|-----------|----------|-----------------|----------|
| `stdio` | stdin/stdout JSON-RPC | No | Local process — Claude Desktop, Cursor (default) |
| `sse` | HTTP Server-Sent Events | Yes | Remote/shared server, legacy MCP clients |
| `streamable-http` | HTTP with streaming | Yes | Remote/shared server, recommended for HTTP |

### stdio (Default)

The client spawns the server as a child process. Communication happens over stdin/stdout. Security is inherited from OS-level process isolation — no network exposure, no authentication needed.

```text
Client (Claude/Cursor) ──stdin/stdout──> Server process
```

### streamable-http / sse

The server runs as an HTTP service. Clients connect over the network. The server is exposed on a port, so authentication is strongly recommended.

```text
Client (Claude/Cursor) ──HTTP──> localhost:8000/mcp ──> Server
```

**Rule of thumb:** Use `stdio` for single-user local setups. Use `streamable-http` when the server is shared, remote, or you need authentication.

---

## Authentication Modes

Authentication only applies to HTTP-based transports (`sse` and `streamable-http`). When using `stdio`, no authentication is enforced.

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

### OAuth Proxy Mode (OIDCProxy)

Full MCP-spec-compliant OAuth 2.1 proxy with Dynamic Client Registration (DCR). The server exposes standard OAuth endpoints that MCP clients discover automatically:

- `/.well-known/oauth-authorization-server` — OAuth metadata
- `/.well-known/oauth-protected-resource` — Protected resource metadata
- `/register` — Dynamic Client Registration (DCR)
- `/authorize` — Authorization endpoint (proxied to your IdP)
- `/token` — Token endpoint (proxied to your IdP)

Unlike the env-var-based modes (`api-key`, `jwt`, `zscaler`), OIDCProxy is configured **programmatically** by passing a `fastmcp.server.auth.AuthProvider` instance to the `ZscalerMCPServer` constructor:

```python
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from zscaler_mcp.server import ZscalerMCPServer

auth = OIDCProxy(
    config_url="https://your-idp.example.com/.well-known/openid-configuration",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    base_url="http://localhost:8000",
    audience="zscaler-mcp-server",
)

server = ZscalerMCPServer(auth=auth)
server.run("streamable-http", host="0.0.0.0", port=8000)
```

**Characteristics:**

- Full OAuth 2.1 compliance — clients discover endpoints via standard metadata
- Dynamic Client Registration — clients register automatically, no manual token management
- Works with any OIDC-compliant Identity Provider (Auth0, Okta, Azure AD, Keycloak, Google, PingOne, AWS Cognito)
- User-facing login — redirects users to your IdP's login page
- No static tokens or shared secrets — tokens are issued per-session
- Automatic token refresh handled by the MCP client
- Best for: production deployments, enterprise SSO, multi-user environments

**When to use OIDCProxy vs other modes:**

| Scenario | Recommended Mode |
|----------|-----------------|
| Local development, quick testing | `api-key` |
| CI/CD, automation, M2M workloads | `jwt` |
| Existing Zscaler API credentials | `zscaler` |
| Production with user login, enterprise SSO | **OIDCProxy** |
| Multi-user with per-user audit trail | **OIDCProxy** |

See [OIDCProxy Setup (OAuth 2.1 + DCR)](#oidcproxy-setup-oauth-21--dcr) for detailed configuration instructions.

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

This is the simplest setup. Claude Desktop spawns the Docker container directly.

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--pull=never",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler-mcp-server:latest"
      ]
    }
  }
}
```

Replace `/absolute/path/to/your/.env` with the full path to your `.env` file.

**Requirements:**

- Docker image must be built locally (`make docker-build`)
- Docker must be running
- No additional setup needed

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
        "--pull=never",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler-mcp-server:latest"
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
        "--pull=never",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler-mcp-server:latest"
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
        "--pull=never",
        "--env-file",
        "/absolute/path/to/your/.env",
        "zscaler-mcp-server:latest"
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
| `ZSCALER_MCP_AUTH_MODE` | When auth enabled | `jwt` | Auth mode: `jwt`, `zscaler`, `api-key`, or `oauth-proxy` |

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

**OIDCProxy mode** (programmatic — not configured via env vars):

OIDCProxy mode is configured programmatically via the `auth=` parameter, not through environment variables. However, when using Docker with a custom entrypoint, these environment variables are used by the entrypoint script:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OIDCPROXY_CONFIG_URL` | Yes | — | OIDC discovery URL (e.g., `https://tenant.auth0.com/.well-known/openid-configuration`) |
| `OIDCPROXY_CLIENT_ID` | Yes | — | OAuth client ID from your IdP |
| `OIDCPROXY_CLIENT_SECRET` | Yes | — | OAuth client secret from your IdP |
| `OIDCPROXY_BASE_URL` | Yes | — | Public base URL of the MCP server (e.g., `http://localhost:8000`) |
| `OIDCPROXY_AUDIENCE` | No | `zscaler-mcp-server` | API audience / resource server identifier |

### Zscaler API Credentials (Layer 2)

These are always required, regardless of Layer 1 auth settings.

| Variable | Required | Description |
|----------|----------|-------------|
| `ZSCALER_CLIENT_ID` | Yes | Zscaler OAuth client ID |
| `ZSCALER_CLIENT_SECRET` | Yes | Zscaler OAuth client secret |
| `ZSCALER_CUSTOMER_ID` | Yes | Zscaler customer ID |
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
| `ZSCALER_MCP_WRITE_ENABLED` | No | `false` | Enable write operations (create, update, delete) |
| `ZSCALER_MCP_WRITE_TOOLS` | No | — | Comma-separated allowlist of write tools (supports wildcards) |
| `ZSCALER_MCP_DISABLE_HOST_VALIDATION` | No | `false` | Disable Host header validation (use when exposing on EC2/public IP) |
| `ZSCALER_MCP_ALLOWED_HOSTS` | No | — | Comma-separated allowed Host values, e.g. `34.201.19.115:*,localhost:*` |
| `ZSCALER_MCP_TLS_CERTFILE` | No | — | Path to TLS certificate (PEM). Enables HTTPS when set with `TLS_KEYFILE`. |
| `ZSCALER_MCP_TLS_KEYFILE` | No | — | Path to TLS private key (PEM). |
| `ZSCALER_MCP_TLS_KEYFILE_PASSWORD` | No | — | Password for encrypted private key. |
| `ZSCALER_MCP_TLS_CA_CERTS` | No | — | Path to CA certificate bundle for mTLS or custom CA chains. |
| `ZSCALER_MCP_ALLOW_HTTP` | No | `false` | Allow plaintext HTTP on non-localhost. HTTPS is required by default for remote deployments. |
| `ZSCALER_MCP_ALLOWED_SOURCE_IPS` | No | — | Comma-separated allowed client IPs/CIDRs (e.g. `10.0.0.0/8,172.16.0.5`). Unset = no filtering. |
| `ZSCALER_MCP_SKIP_CONFIRMATIONS` | No | `false` | Skip cryptographic confirmation for destructive actions (testing/CI only). |

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
        "run", "-i", "--rm", "--pull=never",
        "-p", "8000:8000",
        "--env-file", "/path/to/.env",
        "zscaler-mcp-server:latest",
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

**Cause:** When `mcp-remote` receives a `401 Unauthorized` response, some versions attempt automatic authentication via the MCP OAuth 2.1 protocol — Dynamic Client Registration (DCR) with `/.well-known/*` discovery. The Zscaler MCP Server uses direct JWT validation (bearer token in header), not the full OAuth 2.1 DCR flow, so these discovery endpoints return 404. The `--header` flag may be ignored or deprioritized in favor of the OAuth discovery attempt.

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
| Enterprise with IdP (Okta, Azure AD) | `streamable-http` | `jwt` | HTTP URL + Bearer JWT |
| Zscaler-native organization | `streamable-http` | `zscaler` | HTTP URL + Basic Auth / custom headers |
| Claude Desktop + auth (macOS/Linux) | `streamable-http` | any | `mcp-remote` bridge (`npx` command) |
| Claude Desktop + auth (Windows) | `streamable-http` | any | `mcp-remote` bridge (`cmd /c npx`) |
| Remote server (non-localhost HTTP) | `streamable-http` | any | `mcp-remote` + `--allow-http` |
| Remote server (HTTPS with TLS) | `streamable-http` | any | `mcp-remote` (no `--allow-http` needed) |
| Cursor + auth | `streamable-http` | any | Native `url` + `headers` |

---

## OIDCProxy Setup (OAuth 2.1 + DCR)

This section provides step-by-step instructions for configuring OIDCProxy mode, which implements full MCP-spec OAuth 2.1 with Dynamic Client Registration. The examples use Auth0, but the same process applies to any OIDC-compliant Identity Provider.

### Prerequisites

1. An OIDC-compliant Identity Provider (Auth0, Okta, Azure AD, Keycloak, Google, etc.)
2. Python 3.10+ with `zscaler-mcp-server` installed (or Docker)
3. The `fastmcp` package (included as a dependency of `zscaler-mcp-server`)

### Step 1: Create an OIDC Application in Your IdP

OIDCProxy acts as an OAuth proxy between MCP clients and your Identity Provider. It needs its own application registration in your IdP.

> **Important:** You must create a **Regular Web Application** (or "Confidential Client"), NOT a Machine-to-Machine (M2M) application. M2M applications only support `client_credentials` grant, which does not support user-facing login flows.

**Auth0 example:**

1. Go to **Auth0 Dashboard > Applications > Applications > Create Application**
2. Select **"Regular Web Applications"**
3. Name it (e.g., `zscaler-mcp-server-OIDCProxy`)
4. In **Settings**, note the **Client ID** and **Client Secret**
5. Under **Application URIs > Allowed Callback URLs**, add:

   ```text
   http://localhost:8000/auth/callback
   ```

   (Adjust the port if your server runs on a different port)
6. Save changes

**Okta example:**

1. Go to **Okta Admin > Applications > Create App Integration**
2. Select **OIDC - OpenID Connect**, then **Web Application**
3. Set the **Sign-in redirect URI** to `http://localhost:8000/auth/callback`
4. Note the **Client ID** and **Client Secret**

**Azure AD example:**

1. Go to **Azure Portal > App registrations > New registration**
2. Set the **Redirect URI** to `http://localhost:8000/auth/callback` (type: Web)
3. Under **Certificates & secrets**, create a **Client secret**
4. Note the **Application (client) ID** and secret value

### Step 2: Create an API / Resource Server in Your IdP

The OIDCProxy uses an `audience` parameter to identify which API the tokens are for. You need to register this API in your IdP.

**Auth0 example:**

1. Go to **Auth0 Dashboard > Applications > APIs > Create API**
2. Set the **Identifier** to `zscaler-mcp-server` (this becomes the `audience` value)
3. Under **Application Access**, find your OIDCProxy application and set:
   - **User Access**: Authorized
   - **Client Access**: Authorized
4. Save

**Okta example:**

1. Go to **Okta Admin > Security > API > Authorization Servers**
2. Use the `default` server or create a custom one
3. Add a scope or use existing scopes
4. The **Audience** is the authorization server's URI

### Step 3: Run the Server with OIDCProxy

There are two ways to run the server with OIDCProxy: programmatically (Python script) or via Docker with a custom entrypoint.

#### Option A: Programmatic (Python script)

Create a script (e.g., `run_server.py`):

```python
import os
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from zscaler_mcp.server import ZscalerMCPServer

auth = OIDCProxy(
    config_url="https://YOUR_DOMAIN/.well-known/openid-configuration",
    client_id=os.getenv("OIDCPROXY_CLIENT_ID"),
    client_secret=os.getenv("OIDCPROXY_CLIENT_SECRET"),
    base_url="http://localhost:8000",
    audience="zscaler-mcp-server",
)

# Allow standard OIDC scopes for Dynamic Client Registration
if auth.client_registration_options:
    auth.client_registration_options.valid_scopes = [
        "openid", "profile", "email",
    ]

server = ZscalerMCPServer(auth=auth)
server.run("streamable-http", host="0.0.0.0", port=8000)
```

Set environment variables and run:

```bash
export OIDCPROXY_CLIENT_ID="your-client-id"
export OIDCPROXY_CLIENT_SECRET="your-client-secret"
export ZSCALER_MCP_ALLOW_HTTP=true  # Only for local dev without TLS

python run_server.py
```

#### Option B: Docker with custom entrypoint

The Docker image's CLI entrypoint does not expose the `auth=` parameter. Use a custom entrypoint script that is mounted into the container. See `local_dev/scripts/oidcproxy_entrypoint.py` for a reference implementation.

```bash
docker run -d --name zscaler-mcp-server \
  -p 8000:8000 \
  --env-file .env \
  -e OIDCPROXY_CONFIG_URL="https://YOUR_DOMAIN/.well-known/openid-configuration" \
  -e OIDCPROXY_CLIENT_ID="your-client-id" \
  -e OIDCPROXY_CLIENT_SECRET="your-client-secret" \
  -e OIDCPROXY_BASE_URL="http://localhost:8000" \
  -e OIDCPROXY_AUDIENCE="zscaler-mcp-server" \
  -e ZSCALER_MCP_ALLOW_HTTP=true \
  -v /path/to/oidcproxy_entrypoint.py:/app/oidcproxy_entrypoint.py:ro \
  zscaler-mcp-server:latest \
  python /app/oidcproxy_entrypoint.py
```

### Step 4: Configure Your MCP Client

OIDCProxy uses dynamic OAuth — no static Bearer token is needed. MCP clients discover the OAuth endpoints automatically and handle the authorization flow.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Notice there is **no** `Authorization` header — the client handles OAuth automatically:

1. `mcp-remote` discovers OAuth metadata at `/.well-known/oauth-authorization-server`
2. It registers dynamically via `POST /register` (DCR)
3. A browser window opens with the OIDCProxy consent page
4. After clicking "Allow Access", you're redirected to your IdP's login page
5. After login, the client receives tokens and connects to `/mcp` with a Bearer token
6. Token refresh is handled automatically

### How It Works

```text
┌──────────────┐     ┌───────────────────────────┐     ┌──────────────────┐
│  MCP Client  │     │  Zscaler MCP Server       │     │  Identity        │
│  (Claude,    │     │  with OIDCProxy           │     │  Provider        │
│   Cursor)    │     │                           │     │  (Auth0, Okta)   │
│              │     │  ┌─────────────────────┐  │     │                  │
│  1. Discover ├────>│  │ OAuth Metadata      │  │     │                  │
│     OAuth    │<────│  │ /.well-known/*      │  │     │                  │
│              │     │  └─────────────────────┘  │     │                  │
│  2. Register ├────>│  ┌─────────────────────┐  │     │                  │
│     (DCR)    │<────│  │ /register           │  │     │                  │
│              │     │  └─────────────────────┘  │     │                  │
│  3. Authorize├────>│  ┌─────────────────────┐  │     │                  │
│              │     │  │ /authorize ─────────┼──┼────>│  User Login      │
│              │     │  │ /auth/callback <────┼──┼─────│  + Consent       │
│              │     │  └─────────────────────┘  │     │                  │
│  4. Token    ├────>│  ┌─────────────────────┐  │     │                  │
│     Exchange │<────│  │ /token              │  │     │                  │
│              │     │  └─────────────────────┘  │     │                  │
│  5. MCP      ├────>│  ┌─────────────────────┐  │     │                  │
│     Request  │<────│  │ /mcp (authenticated)│  │     │                  │
│              │     │  └─────────────────────┘  │     │                  │
└──────────────┘     └───────────────────────────┘     └──────────────────┘
```

### Automated Setup Script (Auth0) {#automated-setup-script-auth0-oidcproxy}

For Auth0, an automated setup script handles Docker image building, container startup, endpoint verification, and client configuration:

```bash
# Interactive mode (prompts for credentials)
python local_dev/scripts/setup-oidcproxy-auth.py --server-mode docker

# Non-interactive mode
python local_dev/scripts/setup-oidcproxy-auth.py \
  --server-mode docker \
  --auth0-domain your-tenant.auth0.com \
  --auth0-client-id YOUR_CLIENT_ID \
  --auth0-client-secret YOUR_CLIENT_SECRET \
  --auth0-audience zscaler-mcp-server \
  --mcp-port 8000

# Local mode (without Docker)
python local_dev/scripts/setup-oidcproxy-auth.py --server-mode local
```

The script performs:

1. Builds the Docker image (if `--server-mode docker`)
2. Starts the server with OIDCProxy auth
3. Verifies OAuth endpoints (`/.well-known/*`, `/register`, `/mcp`)
4. Clears stale `mcp-remote` OAuth caches
5. Updates Claude Desktop and Cursor configurations
6. Prints connection instructions

### Troubleshooting OIDCProxy

#### "Client Not Registered" page

**Symptom:** Browser shows "The client ID was not found in the server's client registry."

**Cause:** The Docker container was restarted, wiping the in-memory client registry. `mcp-remote` cached an old `client_id` locally.

**Fix:** Clear the `mcp-remote` OAuth cache and restart your MCP client:

```bash
rm -rf ~/.mcp-auth/mcp-remote-*/
```

Then restart Claude Desktop or Cursor.

#### "Callback URL mismatch" from your IdP

**Symptom:** Auth0 (or your IdP) shows "The provided redirect_uri is not in the list of allowed callback URLs."

**Cause:** The OIDCProxy callback URL (`http://localhost:8000/auth/callback`) is not registered in your IdP application settings.

**Fix:** Add `http://localhost:8000/auth/callback` to the Allowed Callback URLs in your IdP application settings.

#### "Client is not authorized to access resource server"

**Symptom:** After clicking "Allow Access", you see an error like "Client X is not authorized to access resource server Y."

**Cause:** Your IdP application is not authorized to access the API/resource server.

**Fix (Auth0):** Go to Applications > APIs > your API > Application Access tab. Set both "User Access" and "Client Access" to "Authorized" for your OIDCProxy application.

#### Using an M2M application instead of a Regular Web Application

**Symptom:** Auth0 shows "Oops! something went wrong" after clicking "Allow Access" on the consent page.

**Cause:** You are using a Machine-to-Machine (M2M) application, which only supports `client_credentials` grant. OIDCProxy requires `authorization_code` grant with user login.

**Fix:** Create a new **Regular Web Application** in your IdP. M2M apps are for JWT mode; OIDCProxy needs a web application.

#### "ERR_CONNECTION_REFUSED" on the callback URL

**Symptom:** Browser shows "localhost:16442 refused to connect" after logging in.

**Cause:** The `mcp-remote` callback server timed out while you were completing the login flow.

**Fix:** Restart Claude Desktop and complete the login flow quickly. The callback server has a timeout — if you take too long on the IdP login page, it shuts down.

#### "Requested scopes are not valid: openid, profile, email"

**Symptom:** `mcp-remote` crashes with `InvalidClientMetadataError`.

**Cause:** The OIDCProxy is not configured to accept standard OIDC scopes during Dynamic Client Registration.

**Fix:** Set `valid_scopes` after instantiating `OIDCProxy`:

```python
auth = OIDCProxy(...)
if auth.client_registration_options:
    auth.client_registration_options.valid_scopes = [
        "openid", "profile", "email",
    ]
```

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

10. **Use OIDCProxy for multi-user production deployments.** It provides per-user authentication via your existing IdP, automatic token management, and a full audit trail. No shared secrets or manually rotated tokens.
