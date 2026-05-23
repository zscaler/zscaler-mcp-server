---
id: configuration
title: Configuration
sidebar_label: Configuration
sidebar_position: 2
---

# Configuration

The Zscaler MCP Server reads configuration from a `.env` file in the working directory, environment variables, or CLI flags (in that order of precedence — CLI flags win).

## Minimum required

Create a `.env` file in your project root:

```env
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_VANITY_DOMAIN=your_vanity_domain
ZSCALER_CUSTOMER_ID=your_customer_id
```

:::warning
**Never commit `.env` to source control.** Add it to your `.gitignore`. For production deployments, use a managed secrets store — see [Secrets Manager integration](../deployment/secrets-manager).
:::

## Zscaler API credentials

| Variable | Required | Description |
|---|---|---|
| `ZSCALER_CLIENT_ID` | ✅ | Zidentity OneAPI client ID |
| `ZSCALER_CLIENT_SECRET` | ✅* | Zidentity OneAPI client secret |
| `ZSCALER_PRIVATE_KEY` | ✅* | PEM-encoded private key (JWT auth, alternative to `CLIENT_SECRET`) |
| `ZSCALER_VANITY_DOMAIN` | ✅ | Your Zidentity vanity domain (e.g. `acme`) |
| `ZSCALER_CUSTOMER_ID` | ZPA only | Your Zscaler customer/tenant ID — required when calling ZPA tools |
| `ZSCALER_CLOUD` | optional | Cloud override (e.g. `beta`, `zscalertwo`) |
| `ZSCALER_MCP_USER_AGENT_COMMENT` | optional | Appended to the SDK's `User-Agent` header |

\* Either `ZSCALER_CLIENT_SECRET` or `ZSCALER_PRIVATE_KEY` is required.

See [Authentication](./authentication) for how to create these credentials.

## Server & transport

| Variable | Default | Description |
|---|---|---|
| `ZSCALER_MCP_TRANSPORT` | `stdio` | Transport mode: `stdio`, `sse`, `streamable-http` |
| `ZSCALER_MCP_HOST` | `127.0.0.1` | Bind address for HTTP transports |
| `ZSCALER_MCP_PORT` | `8000` | Listen port for HTTP transports |
| `ZSCALER_MCP_DEBUG` | `false` | Enable debug logging |
| `ZSCALER_MCP_LOG_TOOL_CALLS` | `false` | Log every tool invocation (args, duration, result summary) |

## Service & tool selection

| Variable | Default | Description |
|---|---|---|
| `ZSCALER_MCP_SERVICES` | all | Comma-separated services to enable: `zia,zpa,zdx,zcc,ztw,zid,zeasm,zins,zms` |
| `ZSCALER_MCP_DISABLED_SERVICES` | none | Comma-separated services to exclude |
| `ZSCALER_MCP_DISABLED_TOOLS` | none | Comma-separated tool patterns (supports `fnmatch` wildcards) |
| `ZSCALER_MCP_TOOLSETS` | (all enabled) | Comma-separated toolset ids — `default` or `all` are special. See [Toolsets](../guides/toolsets) |
| `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER` | `false` | Skip the OneAPI entitlement filter |

## Write operations

| Variable | Default | Description |
|---|---|---|
| `ZSCALER_MCP_WRITE_ENABLED` | `false` | Global unlock for write tools |
| `ZSCALER_MCP_WRITE_TOOLS` | (none) | **Mandatory** allowlist — comma-separated patterns with wildcards |
| `ZSCALER_MCP_SKIP_CONFIRMATIONS` | `false` | Bypass HMAC confirmation tokens (use only in CI/CD) |
| `ZSCALER_MCP_CONFIRMATION_TTL` | `300` | Confirmation token TTL (seconds) |

See [Write operations](../security/write-operations) for the full safety model.

## HTTP-only security

These variables only apply to `sse` and `streamable-http` transports:

| Variable | Default | Description |
|---|---|---|
| `ZSCALER_MCP_AUTH_ENABLED` | auto | Enable MCP client authentication |
| `ZSCALER_MCP_AUTH_MODE` | (auto-detect) | `api-key`, `jwt`, or `zscaler` |
| `ZSCALER_MCP_AUTH_API_KEY` | — | Shared secret (api-key mode) |
| `ZSCALER_MCP_AUTH_JWKS_URI` | — | JWKS endpoint (JWT mode) |
| `ZSCALER_MCP_AUTH_ISSUER` | — | Expected token issuer (JWT mode) |
| `ZSCALER_MCP_AUTH_AUDIENCE` | — | Expected token audience (JWT mode) |
| `ZSCALER_MCP_TLS_CERTFILE` | — | TLS certificate path |
| `ZSCALER_MCP_TLS_KEYFILE` | — | TLS key path |
| `ZSCALER_MCP_ALLOW_HTTP` | `false` | Permit plaintext HTTP on non-localhost |
| `ZSCALER_MCP_ALLOWED_HOSTS` | — | Comma-separated allowed `Host` header values |
| `ZSCALER_MCP_ALLOWED_SOURCE_IPS` | — | Comma-separated allowed client IPs/CIDRs |
| `ZSCALER_MCP_DISABLE_HOST_VALIDATION` | `false` | Skip host header validation |

See [TLS & hardening](../security/tls-and-hardening) for details.

## CLI flags

Every environment variable above has an equivalent CLI flag. Run `zscaler-mcp --help` for the complete list. CLI flags **always override** environment variables.

```bash
zscaler-mcp --help
```

Common flags:

- `--transport stdio|sse|streamable-http`
- `--services zia,zpa,zdx`
- `--disabled-services zcc`
- `--toolsets zia_url_filtering,zpa_app_segments`
- `--enable-write-tools --write-tools "zpa_create_*,zia_update_*"`
- `--host 0.0.0.0 --port 8080`
- `--log-tool-calls`
- `--list-tools` — print every registered tool and exit
- `--version`

## Lifecycle subcommands

The CLI exposes four subcommands for managing a running server:

- `zscaler-mcp status` — show PID, uptime, transport, port, `.env` path
- `zscaler-mcp reload` — soft reload via SIGHUP (re-reads `.env`, sessions survive)
- `zscaler-mcp restart` — hard restart via SIGUSR2 + execvp (sessions die, fresh process)
- `zscaler-mcp stop` — clean shutdown via SIGTERM

These work locally and inside containers — see the [Docker deployment guide](../deployment/docker) for the bind-mount pattern that makes live `.env` reloading work in production.
