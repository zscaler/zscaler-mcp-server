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
  - [OAuth Proxy Mode (Phase 2)](#oauth-proxy-mode-phase-2)
- [Deployment Options](#deployment-options)
  - [Option A: Docker with stdio (No Auth)](#option-a-docker-with-stdio-no-auth)
  - [Option B: Docker with HTTP (With Auth)](#option-b-docker-with-http-with-auth)
  - [Option C: Local Python (uv / pip)](#option-c-local-python-uv--pip)
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
- [Environment Variable Reference](#environment-variable-reference)
- [Makefile Targets](#makefile-targets)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The Zscaler MCP Server has two independent authentication layers:

```
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

```
Client (Claude/Cursor) ──stdin/stdout──> Server process
```

### streamable-http / sse

The server runs as an HTTP service. Clients connect over the network. The server is exposed on a port, so authentication is strongly recommended.

```
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

```
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

```
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

```
Authorization: Basic base64(client_id:client_secret)
```

The `Authorization` header contains the Base64-encoded string of `client_id:client_secret`. For example, if your client ID is `abc123` and your secret is `xyz789`:

```bash
echo -n "abc123:xyz789" | base64
# Output: YWJjMTIzOnh5ejc4OQ==
# Header: Authorization: Basic YWJjMTIzOnh5ejc4OQ==
```

**Client sends (Method 2 — Custom Headers):**

```
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

### OAuth Proxy Mode (Phase 2)

Full MCP-spec-compliant OAuth 2.1 proxy with Dynamic Client Registration (DCR). This mode will expose standard OAuth endpoints that MCP clients expect:

- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-authorization-server`
- `/register` (Dynamic Client Registration)
- `/authorize` (proxied to external IdP)
- `/token` (proxied to external IdP)

**Status:** Planned for Phase 2. Not yet implemented. Attempting to use this mode will raise an error directing you to use `jwt`, `zscaler`, or `api-key` instead.

---

## Deployment Options

### Option A: Docker with stdio (No Auth)

The simplest deployment. The MCP client spawns the Docker container as a local process. Communication happens over stdin/stdout. No network exposure, no authentication needed.

**Prerequisites:**
1. Docker installed and running
2. Docker image built locally
3. `.env` file with Zscaler API credentials

**Step 1: Build the Docker image**

```bash
# From the project root
make docker-build
# or manually:
docker build -t zscaler-mcp-server:latest .
```

**Step 2: Verify the image**

```bash
docker images | grep zscaler-mcp-server
```

**Step 3: Create your `.env` file**

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

**Step 4: Test the container**

```bash
make docker-run
# or manually:
docker run -i --rm --env-file .env zscaler-mcp-server:latest
```

The server should start and wait for JSON-RPC input on stdin. Press `Ctrl+C` to stop.

**Step 5: Configure your MCP client** (see [Client Configuration](#client-configuration) below)

---

### Option B: Docker with HTTP (With Auth)

The server runs as a persistent HTTP service. Clients connect over the network. Authentication is strongly recommended.

**Prerequisites:**
1. Docker installed and running
2. Docker image built locally
3. `.env` file with Zscaler API credentials AND auth configuration

**Step 1: Build the Docker image** (same as Option A)

```bash
make docker-build
```

**Step 2: Configure authentication in `.env`**

Choose one of the auth modes and add the appropriate variables. For example, with `api-key`:

```bash
# .env — add these lines to your existing .env file

# Enable MCP client authentication
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=api-key
ZSCALER_MCP_AUTH_API_KEY=sk-your-secret-key-here
```

Or with `zscaler` mode:

```bash
# .env — add these lines
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=zscaler
# ZSCALER_VANITY_DOMAIN and ZSCALER_CLOUD are reused from your API config
```

**Step 3: Start the server**

```bash
make docker-run-http
# or manually:
docker run -d --restart=unless-stopped --name zscaler-mcp-server \
  -p 8000:8000 --env-file .env zscaler-mcp-server:latest \
  --transport streamable-http --host 0.0.0.0 --port 8000
```

The server is now running at `http://localhost:8000/mcp`.

**Step 4: Generate the auth token**

```bash
make docker-generate-auth-token
# or manually:
docker run --rm --env-file .env zscaler-mcp-server:latest --generate-auth-token
```

This prints ready-to-paste configuration snippets for Cursor, Claude Desktop, and other clients. Copy the appropriate snippet.

**Step 5: Verify the server is running**

```bash
# Check container status
docker ps | grep zscaler-mcp-server

# Check logs
docker logs zscaler-mcp-server

# Test the endpoint (should return 401 without auth)
curl -s http://localhost:8000/mcp
```

**Step 6: Configure your MCP client** (see [Client Configuration](#client-configuration) below)

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

**Step 1: Install the package**

```bash
# With uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

**Step 2: Create your `.env` file** (same as Option A)

**Step 3: Run with stdio (no auth)**

```bash
# Load env vars and run
export $(cat .env | xargs)
zscaler-mcp --transport stdio
```

**Step 4: Run with HTTP (with auth)**

```bash
export $(cat .env | xargs)
zscaler-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

**Step 5: Generate auth token**

```bash
export $(cat .env | xargs)
zscaler-mcp --generate-auth-token
```

---

## Client Configuration

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

**Prerequisites:**
- Node.js and npm installed
- The MCP server running in HTTP mode (`make docker-run-http`)
- An auth token generated (`make docker-generate-auth-token`)

**With API Key auth:**

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

**With Zscaler auth (Basic Auth):**

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

Replace `BASE64_ENCODED_CREDENTIALS` with the output from `make docker-generate-auth-token`.

**With Zscaler auth (Custom Headers):**

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

After editing the configuration file, restart Claude Desktop for changes to take effect.

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

```
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

```
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

### mcp-remote bridge errors

**Symptom:** Claude Desktop shows errors related to `npx` or `mcp-remote`.

**Check:**
1. Verify the package installs correctly: `npx -y mcp-remote --help`
2. Verify the MCP server is running and accessible: `curl -s http://localhost:8000/mcp`
3. Ensure the header format in the config is correct — the value after `--header` must be a single string like `"Authorization: Bearer xxx"` (header name and value separated by a colon and space)

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
| Claude Desktop + auth | `streamable-http` | any | `mcp-remote` bridge |
| Cursor + auth | `streamable-http` | any | Native `url` + `headers` |

---

## Security Recommendations

1. **Use stdio for single-user setups.** It is inherently secure (OS process isolation) and requires zero auth configuration.

2. **Always enable auth for HTTP transports.** If the server is reachable over the network, even `localhost`, enable authentication.

3. **Prefer JWT mode for enterprise.** It integrates with your existing IdP, supports token expiry, and requires no shared secrets.

4. **Rotate API keys periodically.** If using `api-key` mode, generate a new key and update clients on a regular schedule.

5. **Never commit `.env` files to version control.** The `.gitignore` should already exclude `.env` — verify this.

6. **Use separate credentials per environment.** Do not reuse production Zscaler API credentials in development.

7. **For cloud deployments**, see the [Amazon Bedrock AgentCore deployment guide](./amazon_bedrock_agentcore.md) and the [Secrets Manager integration guide](./secrets_manager_integration.md) for credential management best practices.
