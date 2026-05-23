---
id: mcp-client-auth
title: MCP Client Authentication
sidebar_label: MCP Client Auth
sidebar_position: 2
---

# MCP Client Authentication

When running the server over HTTP (`sse` or `streamable-http`), authentication controls **who is allowed to connect to the server**. This is independent from the Zscaler API credentials (which control how the server authenticates to Zscaler APIs).

For `stdio` transport, MCP client auth is not applicable — the operating system's process isolation provides security.

## Auto-detection

For HTTP transports the server **auto-enables authentication** when any of these environment variables is present:

- `ZSCALER_MCP_AUTH_API_KEY` → `api-key` mode
- `ZSCALER_MCP_AUTH_JWKS_URI` → `jwt` mode
- `ZSCALER_CLIENT_ID` + auth-mode flag → `zscaler` mode

Or set explicitly:

```env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=jwt
```

## Four supported modes

| Mode | Client sends | Best for |
|---|---|---|
| **`api-key`** | `Authorization: Bearer <key>` | Quick setup, internal environments, dev |
| **`jwt`** | `Authorization: Bearer <jwt>` | Enterprise SSO, multi-tenant (Auth0, Okta, Entra ID, Keycloak, Cognito, PingOne, Google) |
| **`zscaler`** | `Authorization: Basic base64(client_id:client_secret)` | Environments already using Zscaler OneAPI credentials |
| **`OIDCProxy`** (programmatic) | OAuth 2.1 flow with DCR | Library consumers, full MCP-spec OAuth, any OIDC provider |

## `api-key` mode

```env
ZSCALER_MCP_AUTH_MODE=api-key
ZSCALER_MCP_AUTH_API_KEY=your-shared-secret
```

Generate a key:

```bash
zscaler-mcp --generate-auth-token
```

Client uses:

```text
Authorization: Bearer your-shared-secret
```

## `jwt` mode

Validate JWTs issued by your enterprise IdP using its JWKS endpoint:

```env
ZSCALER_MCP_AUTH_MODE=jwt
ZSCALER_MCP_AUTH_JWKS_URI=https://your-idp.example.com/.well-known/jwks.json
ZSCALER_MCP_AUTH_ISSUER=https://your-idp.example.com/
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
```

Tokens are validated locally — no per-request call to the IdP. Compatible with any OIDC provider that exposes a JWKS endpoint.

See [Microsoft Entra ID setup](../deployment/entra-id-oidcproxy) for a step-by-step example.

## `zscaler` mode

Reuse your Zscaler OneAPI credentials for MCP client authentication:

```env
ZSCALER_MCP_AUTH_MODE=zscaler
# Uses ZSCALER_CLIENT_ID + ZSCALER_CLIENT_SECRET already in your .env
```

Client sends Basic auth:

```text
Authorization: Basic base64(client_id:client_secret)
```

The server validates against Zscaler's `/oauth2/v1/token` endpoint and caches the result for the token's lifetime (~1 hour). This is the default mode used by all GCP and Azure deployment integrations.

## OAuth 2.1 with DCR (programmatic)

For full MCP-spec OAuth 2.1 with Dynamic Client Registration, use the `auth=` parameter when embedding the server as a library. The OIDCProxy stub works with any OIDC provider:

```python
from fastmcp.server.auth.providers.oidc import OIDCProxy
from zscaler_mcp import ZscalerMCPServer

oidc = OIDCProxy(
    issuer="https://your-idp.example.com/",
    audience="zscaler-mcp-server",
    # ... provider-specific config
)

server = ZscalerMCPServer(auth=oidc)
server.run(transport="streamable-http")
```

This bypasses the env-var middleware entirely.

## Network-level controls

In addition to client authentication, the server enforces:

- **TLS by default** — non-localhost deployments must provide certificates (or set `ZSCALER_MCP_ALLOW_HTTP=true`)
- **Host header validation** — `ZSCALER_MCP_ALLOWED_HOSTS` allowlist
- **Source IP ACL** — `ZSCALER_MCP_ALLOWED_SOURCE_IPS` allowlist

See [TLS & hardening](./tls-and-hardening) for details.
