![Zscaler MCP](https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/docs/media/zscaler.svg)

[![PyPI version](https://badge.fury.io/py/zscaler-mcp.svg)](https://badge.fury.io/py/zscaler-mcp)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zscaler-mcp)](https://pypi.org/project/zscaler-mcp/)
[![Documentation Status](https://readthedocs.org/projects/zscaler-mcp-server/badge/?version=latest)](https://zscaler-mcp-server.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/zscaler/zscaler-mcp-server/graph/badge.svg?token=9HwNcw4Q4h)](https://codecov.io/gh/zscaler/zscaler-mcp-server)
[![License](https://img.shields.io/github/license/zscaler/zscaler-mcp-server.svg)](https://github.com/zscaler/zscaler-mcp-server)
[![Zscaler Community](https://img.shields.io/badge/zscaler-community-blue)](https://community.zscaler.com/)

**zscaler-mcp-server** is a Model Context Protocol (MCP) server that connects AI agents with the Zscaler Zero Trust Exchange platform. **By default, the server operates in read-only mode** for security, requiring explicit opt-in to enable write operations.

## Support Disclaimer

-> **Disclaimer:** Please refer to our [General Support Statement](https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/support.md) before proceeding with the use of this provider. You can also refer to our [troubleshooting guide](https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/TROUBLESHOOTING.md) for guidance on typical problems.

## 📄 Table of contents

- [📺 Overview](#overview)
- [🔒 Security & Permissions](#security-permissions)
- [🔐 MCP Client Authentication](#mcp-client-authentication)
- [Supported Tools](#supported-tools)
- [Installation & Setup](#installation--setup)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Installation](#installation)
- [Usage](#usage)
  - [Command Line](#command-line)
  - [Service Configuration](#service-configuration)
  - [Additional Command Line Options](#additional-command-line-options)
- [Zscaler API Credentials & Authentication](#zscaler-api-credentials-authentication)
  - [Quick Start: Choose Your Authentication Method](#quick-start-choose-your-authentication-method)
  - [OneAPI Authentication (Recommended)](#oneapi-authentication-recommended)
  - [Legacy API Authentication](#legacy-api-authentication)
  - [Authentication Troubleshooting](#authentication-troubleshooting)
  - [MCP Server Configuration](#mcp-server-configuration)
- [As a Library](#as-a-library)
- [Container Usage](#container-usage)
  - [Using Pre-built Image (Recommended)](#using-pre-built-image-recommended)
  - [Building Locally (Development)](#building-locally-development)
- [Editor/Assistant Integration](#editor-assistant-integration)
  - [Using `uvx` (recommended)](#using-uvx-recommended)
  - [With Service Selection](#with-service-selection)
  - [Using Individual Environment Variables](#using-individual-environment-variables)
  - [Docker Version](#docker-version)
- [Additional Deployment Options](#additional-deployment-options)
  - [Remote MCP Deployment (EC2, VM, etc.)](#remote-mcp-deployment-ec2-vm-etc)
  - [Amazon Bedrock AgentCore](#amazon-bedrock-agentcore)
- [Using the MCP Server with Agents](#using-the-mcp-server-with-agents)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [Visual Studio Code + GitHub Copilot](#visual-studio-code-github-copilot)
- [Platform Integrations](#platform-integrations)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## 📺 Overview

The Zscaler Integrations MCP Server brings context to your agents. Try prompts like:

- "List my ZPA Application segments"
- "List my ZPA Segment Groups"
- "List my ZIA Rule Labels"

> [!WARNING]
> **🔒 READ-ONLY BY DEFAULT**: For security, this MCP server operates in **read-only mode** by default. Only `list_*` and `get_*` operations are available. To enable tools that can **CREATE, UPDATE, or DELETE** Zscaler resources, you must explicitly enable write mode using the `--enable-write-tools` flag or by setting `ZSCALER_MCP_WRITE_ENABLED=true`. See the [Security & Permissions](#-security--permissions) section for details.

<!-- markdownlint-disable MD028 -->

> [!TIP]
> **Writing effective prompts**: This server exposes **280+ tools** across multiple Zscaler services. Most MCP clients (Claude Desktop, Cursor, etc.) use deferred tool loading and will search for relevant tools based on your prompt. For best results, **be specific about the service and action** in your prompts:
>
> - **Good**: *"List my ZPA application segments"* — targets the right service and tool directly
> - **Good**: *"Show ZIA firewall rules"* — clear service (`zia`) and action (`list`)
> - **Less effective**: *"Show me my devices"* — ambiguous; multiple services expose device-related tools
>
> When a service is [disabled](#additional-command-line-options), its tools are fully removed from the server. However, the AI agent may still attempt to find related tools in other services. If you get unexpected results, refine your prompt with the specific service name (e.g. `zpa`, `zia`, `zdx`, `zcc`).

## 🔒 Security & Permissions

The Zscaler MCP Server implements a **security-first design** with granular permission controls and safe defaults:

### Read-Only Mode (Default - Always Available)

By default, the server operates in **read-only mode**, exposing only tools that list or retrieve information:

- ✅ **ALWAYS AVAILABLE** - Read-only tools are registered by the server
- ✅ Safe to use with AI agents autonomously
- ✅ No risk of accidental resource modification or deletion
- ✅ All `list_*` and `get_*` operations are available (110+ read-only tools)
- ❌ All `create_*`, `update_*`, and `delete_*` operations are disabled by default
- 💡 Note: You may need to enable read-only tools in your AI agent's UI settings

```bash
# Read-only mode (default - safe)
zscaler-mcp
```

When the server starts in read-only mode, you'll see:

```text
🔒 Server running in READ-ONLY mode (safe default)
   Only list and get operations are available
   To enable write operations, use --enable-write-tools AND --write-tools flags
```

> **💡 Read-only tools are ALWAYS registered** by the server regardless of any flags. You never need to enable them server-side. Note: Your AI agent UI (like Claude Desktop) may require you to enable individual tools before use.

### Write Mode (Explicit Opt-In - Allowlist REQUIRED)

To enable tools that can create, modify, or delete Zscaler resources, you must provide **BOTH** flags:

1. ✅ `--enable-write-tools` - Global unlock for write operations
2. ✅ `--write-tools "pattern"` - **MANDATORY** explicit allowlist

> **🔐 SECURITY: Allowlist is MANDATORY** - If you set `--enable-write-tools` without `--write-tools`, **0 write tools will be registered**. This ensures you consciously choose which write operations to enable.

```bash
# ❌ WRONG: This will NOT enable any write tools (allowlist missing)
zscaler-mcp --enable-write-tools

# ✅ CORRECT: Explicit allowlist required
zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zpa_delete_*"
```

When you try to enable write mode without an allowlist:

```text
⚠️  WRITE TOOLS MODE ENABLED
⚠️  NO allowlist provided - 0 write tools will be registered
⚠️  Read-only tools will still be available
⚠️  To enable write operations, add: --write-tools 'pattern'
```

#### Write Tools Allowlist (MANDATORY)

The allowlist provides **two-tier security**:

1. ✅ **First Gate**: `--enable-write-tools` must be set (global unlock)
2. ✅ **Second Gate**: Explicit allowlist determines which write tools are registered (MANDATORY)

**Allowlist Examples:**

```bash
# Enable ONLY specific write tools with wildcards
zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zpa_delete_*"

# Enable specific tools without wildcards
zscaler-mcp --enable-write-tools --write-tools "zpa_create_application_segment,zia_create_rule_label"

# Enable all ZPA write operations (but no ZIA/ZDX/ZTW)
zscaler-mcp --enable-write-tools --write-tools "zpa_*"
```

Or via environment variable:

```bash
export ZSCALER_MCP_WRITE_ENABLED=true
export ZSCALER_MCP_WRITE_TOOLS="zpa_create_*,zpa_delete_*"
zscaler-mcp
```

**Wildcard patterns supported:**

- `zpa_create_*` - Allow all ZPA creation tools
- `zpa_delete_*` - Allow all ZPA deletion tools
- `zpa_*` - Allow all ZPA write tools
- `*_application_segment` - Allow all operations on application segments
- `zpa_create_application_segment` - Exact match (no wildcard)

When using a valid allowlist, you'll see:

```text
⚠️  WRITE TOOLS MODE ENABLED
⚠️  Explicit allowlist provided - only listed write tools will be registered
⚠️  Allowed patterns: zpa_create_*, zpa_delete_*
⚠️  Server can CREATE, MODIFY, and DELETE Zscaler resources
🔒 Security: 85 write tools blocked by allowlist, 8 allowed
```

### Tool Design Philosophy

Each operation is a **separate, single-purpose tool** with explicit naming that makes its intent clear:

#### ✅ Good (Verb-Based - Current Design)

```text
zpa_list_application_segments    ← Read-only, safe to allow-list
zpa_get_application_segment      ← Read-only, safe to allow-list
zpa_create_application_segment   ← Write operation, requires --enable-write-tools
zpa_update_application_segment   ← Write operation, requires --enable-write-tools
zpa_delete_application_segment   ← Destructive, requires --enable-write-tools
```

This design allows AI assistants (Claude, Cursor, GitHub Copilot) to:

- Allow-list read-only tools for autonomous exploration
- Require explicit user confirmation for write operations
- Clearly understand the intent of each tool from its name

### Security Layers

The server implements multiple layers of security (defense-in-depth):

1. **Read-Only Tools Always Enabled**: Safe `list_*` and `get_*` operations are always available (110+ tools)
2. **Default Write Mode Disabled**: Write tools are disabled unless explicitly enabled via `--enable-write-tools`
3. **Mandatory Allowlist**: Write operations require explicit `--write-tools` allowlist (wildcard support)
4. **Verb-Based Tool Naming**: Each tool clearly indicates its purpose (`list`, `get`, `create`, `update`, `delete`)
5. **Tool Metadata Annotations**: All tools are annotated with `readOnlyHint` or `destructiveHint` for AI agent frameworks
6. **AI Agent Confirmation**: All write tools marked with `destructiveHint=True` trigger permission dialogs in AI assistants
7. **Double Confirmation for DELETE**: Delete operations require both permission dialog AND server-side confirmation (extra protection for irreversible actions)
8. **Environment Variable Control**: `ZSCALER_MCP_WRITE_ENABLED` and `ZSCALER_MCP_WRITE_TOOLS` can be managed centrally
9. **Audit Logging**: All operations are logged for tracking and compliance

This multi-layered approach ensures that even if one security control is bypassed, others remain in place to prevent unauthorized operations.

### Cryptographic Confirmation for Destructive Actions

Delete operations use a **cryptographic confirmation token** (HMAC-SHA256) instead of a simple `confirmed=true` boolean. This prevents prompt injection attacks where a malicious prompt could trick the AI agent into confirming a destructive action. The token is bound to the specific operation parameters and expires after 5 minutes.

This mechanism is transparent to end users — the AI agent handles the confirmation flow automatically through its standard permission dialog.

To bypass confirmations in automated testing or CI/CD environments:

```bash
export ZSCALER_MCP_SKIP_CONFIRMATIONS=true
```

### HTTPS/TLS Support

**HTTPS is required by default** for non-localhost deployments. The server will refuse to start on a non-localhost interface without TLS certificates unless you explicitly set `ZSCALER_MCP_ALLOW_HTTP=true`.

When running with HTTP transports (`sse` or `streamable-http`), provide TLS certificates:

```env
ZSCALER_MCP_TLS_CERTFILE=/path/to/cert.pem
ZSCALER_MCP_TLS_KEYFILE=/path/to/key.pem

# Optional: private key password and CA bundle
ZSCALER_MCP_TLS_KEYFILE_PASSWORD=your-key-password
ZSCALER_MCP_TLS_CA_CERTS=/path/to/ca-bundle.pem
```

When TLS is configured, the server automatically starts with HTTPS. This works with both public (CA-signed) and private (self-signed) certificates. Generate a self-signed certificate for testing:

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost"
```

### Source IP Access Control

You can restrict which client IPs are allowed to connect using `ZSCALER_MCP_ALLOWED_SOURCE_IPS`. When unset (the default), source IP filtering is disabled and deferred to upstream controls (firewall rules, AWS Security Groups, etc.).

```env
# Allow only specific IPs/subnets
ZSCALER_MCP_ALLOWED_SOURCE_IPS=10.0.0.0/8,172.16.0.5

# Allow all (effectively disable — same as not setting the variable)
ZSCALER_MCP_ALLOWED_SOURCE_IPS=0.0.0.0/0
```

Supports individual IPv4/IPv6 addresses, CIDR notation, and the wildcard `0.0.0.0/0`. Health-check endpoints (`/health`, `/healthz`, `/ready`) are exempt so load-balancer probes continue to work. Requests from disallowed IPs receive `403 Forbidden`.

### .env File Security Warning

When starting with HTTP transports, the server automatically scans any `.env` file in the working directory for plaintext secrets (values containing `SECRET`, `PASSWORD`, `KEY`, or `TOKEN`). If detected, a security warning is logged recommending the use of a secrets manager or environment variables instead.

### Security Posture Banner

On startup, the server logs a consolidated **Security Posture Banner** summarizing the active security configuration — transport mode, host validation status, authentication mode, TLS status, and any active warnings. This makes it easy to verify the security state at a glance.

**Key Security Principles**:

- No "enable all write tools" backdoor exists - allowlist is **mandatory**
- AI agents must request permission before executing any write operation (`destructiveHint`)
- Every destructive action requires explicit user approval through the AI agent's permission framework
- Destructive confirmations are cryptographically bound to prevent prompt injection bypass

### Best Practices

- **Read-Only by Default**: No configuration needed for safe operations - read-only tools are always available
- **Mandatory Allowlist**: Always provide explicit `--write-tools` allowlist when enabling write mode
- **Development/Testing**: Use narrow allowlists (e.g., `--write-tools "zpa_create_application_segment"`)
- **Production/Agents**: Keep server in read-only mode (default) for AI agents performing autonomous operations
- **CI/CD**: Never set `ZSCALER_MCP_WRITE_ENABLED=true` without a corresponding `ZSCALER_MCP_WRITE_TOOLS` allowlist
- **Least Privilege**: Use narrowest possible allowlist patterns for your use case
- **Wildcard Usage**: Use wildcards for service-level control (e.g., `zpa_create_*`) or operation-level control (e.g., `*_create_*`)
- **Audit Review**: Regularly review which write tools are allowlisted and remove unnecessary ones
- **Specific Prompts**: With 280+ tools and deferred loading, AI agents match prompts to tools by relevance. Use service-specific prompts (e.g., *"List ZPA segments"* instead of *"Show my segments"*) for accurate tool selection

## 🔐 MCP Client Authentication

> **📖 Full Documentation: [Authentication & Deployment Guide](docs/deployment/authentication-and-deployment.md)**

When running the MCP server over HTTP (`sse` or `streamable-http` transports), you can enable authentication to control **who is allowed to connect** to the server. This is independent from the [Zscaler API credentials](#zscaler-api-credentials-authentication), which control how the server authenticates to Zscaler APIs.

For HTTP transports, the server **auto-detects and enables authentication** when auth-related environment variables are present. For `stdio` transport, authentication is not applicable (the operating system's process isolation provides security).

### Authentication Modes

The server supports four authentication modes, configured via environment variables:

| Mode | Description | Best For |
|------|-------------|----------|
| **`api-key`** | Simple shared secret — client sends `Authorization: Bearer <key>` | Quick setup, internal environments, development |
| **`jwt`** | External Identity Provider via JWKS — tokens validated locally using public keys | Enterprise SSO, multi-tenant deployments (Auth0, Okta, Azure AD, Keycloak, AWS Cognito, PingOne, Google) |
| **`zscaler`** | Zscaler OneAPI credential validation — client sends Basic Auth with `client_id:client_secret` | Environments already using Zscaler API credentials |
| **`auth=` param** | Full MCP-spec OAuth 2.1 with DCR via fastmcp `AuthProvider` (e.g. `OIDCProxy`) | Library consumers, programmatic OAuth 2.1, any OIDC provider |

### Quick Start

Enable authentication by setting these environment variables in your `.env` file:

```env
# Enable authentication
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=api-key

# For api-key mode: set a shared secret
ZSCALER_MCP_AUTH_API_KEY=sk-your-secret-key-here
```

Then start the server with an HTTP transport:

```bash
zscaler-mcp --transport streamable-http
```

Clients must include the key in the `Authorization` header:

```text
Authorization: Bearer sk-your-secret-key-here
```

### How It Works

Authentication is implemented as ASGI middleware that wraps the HTTP transport layer:

```text
MCP Client Request
      │
      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Auth         │────▶│  FastMCP      │────▶│  Zscaler     │
│  Middleware   │     │  Server       │     │  APIs        │
└──────────────┘     └──────────────┘     └──────────────┘
 Layer 1: WHO          MCP Protocol        Layer 2: HOW
 can connect?          Processing          server talks
                                           to Zscaler
```

- **Layer 1 (MCP Client Auth)**: Controlled by `ZSCALER_MCP_AUTH_*` variables — validates the incoming request
- **Layer 2 (Zscaler API Auth)**: Controlled by `ZSCALER_CLIENT_ID`, `ZSCALER_CLIENT_SECRET`, etc. — authenticates the server to Zscaler APIs

These two layers are completely independent. You can enable one, both, or neither.

### Configuration by Mode

#### API Key

```env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=api-key
ZSCALER_MCP_AUTH_API_KEY=sk-your-secret-key-here
```

#### JWT (External IdP via JWKS)

```env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=jwt
ZSCALER_MCP_AUTH_JWKS_URI=https://your-idp.com/.well-known/jwks.json
ZSCALER_MCP_AUTH_ISSUER=https://your-idp.com
ZSCALER_MCP_AUTH_AUDIENCE=zscaler-mcp-server
ZSCALER_MCP_AUTH_ALGORITHMS=RS256,ES256   # Optional (default: RS256,ES256)
```

#### Zscaler OneAPI Credentials

```env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=zscaler
# Uses ZSCALER_VANITY_DOMAIN and ZSCALER_CLOUD from your existing config
```

Clients authenticate with Basic Auth (`client_id:client_secret`) or custom headers (`X-Zscaler-Client-ID` / `X-Zscaler-Client-Secret`).

### Authentication Defaults

For HTTP transports (`sse`, `streamable-http`), the server **auto-detects and enables authentication** if auth-related environment variables are present (e.g., `ZSCALER_MCP_AUTH_JWKS_URI`, `ZSCALER_MCP_AUTH_API_KEY`, or `ZSCALER_VANITY_DOMAIN`). If no auth configuration is detected and `ZSCALER_MCP_AUTH_ENABLED` is not explicitly set, the server logs a security warning but continues without authentication.

To explicitly disable authentication, set:

```env
ZSCALER_MCP_AUTH_ENABLED=false
```

Authentication does not apply to `stdio` transport (process isolation provides security).

### Library-Level OAuth 2.1 (auth= Parameter)

When using `ZscalerMCPServer` as a Python library, you can pass a `fastmcp.server.auth.AuthProvider` instance (such as `OIDCProxy` or `OAuthProxy`) directly to the constructor. This provides full MCP-spec-compliant OAuth 2.1 with Dynamic Client Registration (DCR), and is the recommended approach for programmatic OAuth integration.

```python
import os
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from zscaler_mcp.server import ZscalerMCPServer

auth = OIDCProxy(
    config_url="https://your-tenant.auth0.com/.well-known/openid-configuration",
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

When `auth=` is provided:

- The server delegates authentication entirely to the `AuthProvider`
- The env-var-based auth middleware (`ZSCALER_MCP_AUTH_*`) is automatically skipped
- OAuth routes (`.well-known/oauth-protected-resource`, `/register`, `/authorize`, `/token`) are handled by the provider
- All other security features (TLS, Source IP ACL, host validation) remain active
- Works with any OIDC-compliant Identity Provider (Auth0, Okta, Azure AD, Keycloak, Google, AWS Cognito, PingOne, etc.)

**IdP requirements:** Your Identity Provider must have a **Regular Web Application** (not M2M) with the callback URL `http://localhost:8000/auth/callback` registered, and an API/resource server with identifier matching the `audience` value.

> **📖 For detailed setup instructions — including [OIDCProxy setup with Auth0/Okta/Azure AD](docs/deployment/authentication-and-deployment.md#oidcproxy-setup-oauth-21--dcr), IdP-specific JWKS configuration, Docker deployment examples, client configuration for Claude/Cursor/VS Code, and troubleshooting — see the [Authentication & Deployment Guide](docs/deployment/authentication-and-deployment.md).**

## Supported Tools

The Zscaler Integrations MCP Server provides **280+ tools** for all major Zscaler services:

| Service | Description | Tools |
|---------|-------------|-------|
| **ZIA** | Zscaler Internet Access - Security policies | 106 read/write |
| **ZPA** | Zscaler Private Access - Application access | 88 read/write |
| **ZDX** | Zscaler Digital Experience - Monitoring & analytics | 31 read-only |
| **ZTW** | Zscaler Workload Segmentation | 19 read/write |
| **Z-Insights** | Analytics - Web traffic, cyber incidents, shadow IT | 16 read-only |
| **ZIdentity** | Identity & access management | 10 read-only |
| **EASM** | External Attack Surface Management | 7 read-only |
| **ZCC** | Zscaler Client Connector - Device management | 4 read-only |

📖 **[View Complete Tools Reference →](docs/guides/supported-tools.md)**

> **Note:** All write operations require the `--enable-write-tools` flag and an explicit `--write-tools` allowlist. See the [Security & Permissions](#-security--permissions) section for details.

## Installation & Setup

### Prerequisites

- Python 3.11 or higher
- [`uv`](https://docs.astral.sh/uv/) or pip
- Zscaler API credentials (see below)

### Environment Configuration

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Then edit `.env` with your Zscaler API credentials:

**Required Configuration (OneAPI):**

- `ZSCALER_CLIENT_ID`: Your Zscaler OAuth client ID
- `ZSCALER_CLIENT_SECRET`: Your Zscaler OAuth client secret
- `ZSCALER_CUSTOMER_ID`: Your Zscaler customer ID
- `ZSCALER_VANITY_DOMAIN`: Your Zscaler vanity domain

**Optional Configuration:**

- `ZSCALER_CLOUD`: (Optional) Zscaler cloud environment (e.g., `beta`) - Required when interacting with Beta Tenant ONLY.
- `ZSCALER_USE_LEGACY`: Enable legacy API mode (`true`/`false`, default: `false`)
- `ZSCALER_MCP_SERVICES`: Comma-separated list of services to enable (default: all services)
- `ZSCALER_MCP_TRANSPORT`: Transport method - `stdio`, `sse`, or `streamable-http` (default: `stdio`)
- `ZSCALER_MCP_DEBUG`: Enable debug logging - `true` or `false` (default: `false`)
- `ZSCALER_MCP_HOST`: Host for HTTP transports (default: `127.0.0.1`)
- `ZSCALER_MCP_PORT`: Port for HTTP transports (default: `8000`)

*Alternatively, you can set these as environment variables instead of using a `.env` file.*

> **Important**: Ensure your API client has the necessary permissions for the services you plan to use. You can always update permissions later in the Zscaler console.

### Installation

#### Install with VS Code (Quick Setup)

[![VS Code Install](https://img.shields.io/badge/VS%20Code-Install-blue?logo=visual-studio-code&logoColor=white&style=for-the-badge)](https://vscode.dev/redirect?url=vscode:mcp/install?%7B%22name%22%3A%22zscaler-mcp-server%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zscaler-mcp%22%5D%2C%22env%22%3A%7B%22ZSCALER_CLIENT_ID%22%3A%22%3CYOUR_CLIENT_ID%3E%22%2C%22ZSCALER_CLIENT_SECRET%22%3A%22%3CYOUR_CLIENT_SECRET%3E%22%2C%22ZSCALER_CUSTOMER_ID%22%3A%22%3CYOUR_CUSTOMER_ID%3E%22%2C%22ZSCALER_VANITY_DOMAIN%22%3A%22%3CYOUR_VANITY_DOMAIN%3E%22%7D%7D)

> **Note**: This will open VS Code and prompt you to configure the MCP server. You'll need to replace the placeholder values (`<YOUR_CLIENT_ID>`, etc.) with your actual Zscaler credentials.

#### Install using uv (recommended)

```bash
uv tool install zscaler-mcp
```

#### Install from source using uv (development)

```bash
uv pip install -e .
```

> **Remote deployment:** When running on EC2/VM, activate the project venv before starting: `source .venv/bin/activate`. See [Remote MCP Deployment](#remote-mcp-deployment-ec2-vm-etc).

#### Install from source using pip

```bash
pip install -e .
```

#### Install using make (convenience)

```bash
make install-dev
```

> [!TIP]
> If `zscaler-mcp-server` isn't found, update your shell PATH.

For installation via code editors/assistants, see the [Using the MCP Server with Agents](#using-the-mcp-server-with-agents) section below.

## Usage

> [!NOTE]
> **Default Security Mode**: All examples below run in **read-only mode** by default (only `list_*` and `get_*` operations). To enable write operations (`create_*`, `update_*`, `delete_*`), add the `--enable-write-tools` flag to any command, or set `ZSCALER_MCP_WRITE_ENABLED=true` in your environment.

### Command Line

Run the server with default settings (stdio transport, read-only mode):

```bash
zscaler-mcp
```

Run the server with write operations enabled:

```bash
zscaler-mcp --enable-write-tools
```

Run with SSE transport:

```bash
zscaler-mcp --transport sse
```

Run with streamable-http transport:

```bash
zscaler-mcp --transport streamable-http
```

Run with streamable-http transport on custom port:

```bash
zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8080
```

### Service Configuration

The Zscaler Integrations MCP Server supports multiple ways to specify which services to enable:

#### 1. Command Line Arguments (highest priority)

Specify services using comma-separated lists:

```bash
# Enable specific services
zscaler-mcp --services zia,zpa,zdx

# Enable only one service
zscaler-mcp --services zia
```

#### 2. Environment Variable (fallback)

Set the `ZSCALER_MCP_SERVICES` environment variable:

```bash
# Export environment variable
export ZSCALER_MCP_SERVICES=zia,zpa,zdx
zscaler-mcp

# Or set inline
ZSCALER_MCP_SERVICES=zia,zpa,zdx zscaler-mcp
```

#### 3. Default Behavior (all services)

If no services are specified via command line or environment variable, all available services are enabled by default.

**Service Priority Order:**

1. Command line `--services` argument (overrides all)
2. `ZSCALER_MCP_SERVICES` environment variable (fallback)
3. All services (default when none specified)

### Excluding Services and Tools

When you want to keep most tools available but exclude a few, use `--disabled-tools` or `--disabled-services` instead of listing every tool you want to include.

Both flags support **wildcards** via [fnmatch](https://docs.python.org/3/library/fnmatch.html) patterns.

```bash
# Exclude a single tool (e.g., rate-limited CSV export)
zscaler-mcp --disabled-tools zcc_devices_csv_exporter

# Exclude all tools from a service prefix
zscaler-mcp --disabled-tools "zcc_*"

# Exclude multiple patterns
zscaler-mcp --disabled-tools "zcc_*,zdx_list_devices"

# Exclude entire services
zscaler-mcp --disabled-services zcc,zdx

# Combine: keep all services but exclude specific tools
zscaler-mcp --disabled-tools "zcc_devices_csv_exporter,zdx_*_analysis"
```

Environment variables:

```bash
export ZSCALER_MCP_DISABLED_TOOLS="zcc_devices_csv_exporter,zdx_*"
export ZSCALER_MCP_DISABLED_SERVICES="zcc"
```

**Precedence:** `--disabled-tools` takes precedence over `--tools` (include list). A tool that matches both the include list and the exclude list will be excluded.

### Additional Command Line Options

```bash
# Enable write operations (create, update, delete)
zscaler-mcp --enable-write-tools

# Enable debug logging
zscaler-mcp --debug

# Combine multiple options
zscaler-mcp --services zia,zpa --enable-write-tools --debug
```

For all available options:

```bash
zscaler-mcp --help
```

Available command-line flags:

- `--transport`: Transport protocol (`stdio`, `sse`, `streamable-http`)
- `--services`: Comma-separated list of services to enable
- `--disabled-services`: Comma-separated list of services to exclude (e.g., `zcc,zdx`)
- `--tools`: Comma-separated list of specific tools to enable
- `--disabled-tools`: Comma-separated list of tools to exclude, supports wildcards (e.g., `zcc_*,zdx_list_devices`)
- `--enable-write-tools`: Enable write operations (disabled by default for safety)
- `--write-tools`: Mandatory allowlist of write tool patterns (e.g., `"zpa_create_*,zpa_delete_*"`)
- `--debug`: Enable debug logging
- `--host`: Host for HTTP transports (default: `127.0.0.1`)
- `--port`: Port for HTTP transports (default: `8000`)
- `--user-agent-comment`: Additional text appended to User-Agent header
- `--generate-auth-token`: Generate a client auth token snippet and exit
- `--list-tools`: List all available tools and exit
- `--version`: Show server version and exit

### Supported Agents

- [Claude](https://claude.ai/)
- [Cursor](https://cursor.so/)
- [VS Code](https://code.visualstudio.com/download) or [VS Code Insiders](https://code.visualstudio.com/insiders)

## Zscaler API Credentials & Authentication

The Zscaler Integrations MCP Server supports two authentication methods: **OneAPI (recommended)** and **Legacy API**. You must choose **ONE** method - do not mix them.

> [!IMPORTANT]
> **⚠️ CRITICAL: Choose ONE Authentication Method**
>
> - **OneAPI**: Single credential set for ALL services (ZIA, ZPA, ZCC, ZDX)
> - **Legacy**: Separate credentials required for EACH service
> - **DO NOT** set both OneAPI and Legacy credentials simultaneously
> - **DO NOT** set `ZSCALER_USE_LEGACY=true` if using OneAPI

### Quick Start: Choose Your Authentication Method

#### Option A: OneAPI (Recommended - Single Credential Set)

- ✅ **One set of credentials** works for ALL services (ZIA, ZPA, ZCC, ZDX, ZTW)
- ✅ Modern OAuth2.0 authentication via Zidentity
- ✅ Easier to manage and maintain
- ✅ Default authentication method (no flag needed)
- **Use this if:** You have access to Zidentity console and want simplicity

#### Option B: Legacy Mode (Per-Service Credentials)

- ⚠️ **Separate credentials** required for each service you want to use
- ⚠️ Different authentication methods per service (OAuth for ZPA, API key for ZIA, etc.)
- ⚠️ Must set `ZSCALER_USE_LEGACY=true` environment variable
- **Use this if:** You don't have OneAPI access or need per-service credential management

#### Decision Tree

```text
Do you have access to Zidentity console?
├─ YES → Use OneAPI (Option A)
└─ NO  → Use Legacy Mode (Option B)
```

---

### OneAPI Authentication (Recommended)

OneAPI provides a single set of credentials that authenticate to all Zscaler services. This is the default and recommended method.

#### Prerequisites

Before using OneAPI, you need to:

1. Create an API Client in the [Zidentity platform](https://help.zscaler.com/zidentity/about-api-clients)
2. Obtain your credentials: `clientId`, `clientSecret`, `customerId`, and `vanityDomain`
3. Learn more: [Understanding OneAPI](https://help.zscaler.com/oneapi/understanding-oneapi)

#### Quick Setup

Create a `.env` file in your project root (or where you'll run the MCP server):

```env
# OneAPI Credentials (Required)
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_CUSTOMER_ID=your_customer_id
ZSCALER_VANITY_DOMAIN=your_vanity_domain

# Optional: Only required for Beta tenants
ZSCALER_CLOUD=beta
```

⚠️ **Security**: Do not commit `.env` to source control. Add it to your `.gitignore`.

#### OneAPI Environment Variables

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZSCALER_CLIENT_ID` | Yes | Zscaler OAuth client ID from Zidentity console |
| `ZSCALER_CLIENT_SECRET` | Yes | Zscaler OAuth client secret from Zidentity console |
| `ZSCALER_CUSTOMER_ID` | Yes | Zscaler customer ID |
| `ZSCALER_VANITY_DOMAIN` | Yes | Your organization's vanity domain (e.g., `acme`) |
| `ZSCALER_CLOUD` | No | Zscaler cloud environment (e.g., `beta`). **Only required for Beta tenants** |
| `ZSCALER_PRIVATE_KEY` | No | OAuth private key for JWT-based authentication (alternative to client secret) |

#### Verification

After setting up your `.env` file, test the connection:

```bash
# Test with a simple command
zscaler-mcp
```

If authentication is successful, the server will start without errors. If you see authentication errors, verify:

- All required environment variables are set correctly
- Your API client has the necessary permissions in Zidentity
- Your credentials are valid and not expired

---

### Legacy API Authentication

Legacy mode requires separate credentials for each Zscaler service. This method is only needed if you don't have access to OneAPI.

> [!WARNING]
> **⚠️ IMPORTANT**: When using Legacy mode:
>
> - You **MUST** set `ZSCALER_USE_LEGACY=true` in your `.env` file
> - You **MUST** provide credentials for each service you want to use
> - OneAPI credentials are **ignored** when `ZSCALER_USE_LEGACY=true` is set
> - Clients are created on-demand when tools are called (not at startup)

#### Quick Setup

Create a `.env` file with the following structure:

```env
# Enable Legacy Mode (REQUIRED - set once at the top)
ZSCALER_USE_LEGACY=true

# ZPA Legacy Credentials (if using ZPA)
ZPA_CLIENT_ID=your_zpa_client_id
ZPA_CLIENT_SECRET=your_zpa_client_secret
ZPA_CUSTOMER_ID=your_zpa_customer_id
ZPA_CLOUD=BETA

# ZIA Legacy Credentials (if using ZIA)
ZIA_USERNAME=your_zia_username
ZIA_PASSWORD=your_zia_password
ZIA_API_KEY=your_zia_api_key
ZIA_CLOUD=zscalertwo

# ZCC Legacy Credentials (if using ZCC)
ZCC_CLIENT_ID=your_zcc_client_id
ZCC_CLIENT_SECRET=your_zcc_client_secret
ZCC_CLOUD=zscalertwo

# ZDX Legacy Credentials (if using ZDX)
ZDX_CLIENT_ID=your_zdx_client_id
ZDX_CLIENT_SECRET=your_zdx_client_secret
ZDX_CLOUD=zscalertwo
```

⚠️ **Security**: Do not commit `.env` to source control. Add it to your `.gitignore`.

#### Legacy Authentication by Service

##### ZPA Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZPA_CLIENT_ID` | Yes | ZPA API client ID from ZPA console |
| `ZPA_CLIENT_SECRET` | Yes | ZPA API client secret from ZPA console |
| `ZPA_CUSTOMER_ID` | Yes | ZPA tenant ID (found in Administration > Company menu) |
| `ZPA_CLOUD` | Yes | Zscaler cloud for ZPA tenancy (e.g., `BETA`, `zscalertwo`) |
| `ZPA_MICROTENANT_ID` | No | ZPA microtenant ID (if using microtenants) |

**Where to find ZPA credentials:**

- API Client ID/Secret: ZPA console > Configuration & Control > Public API > API Keys
- Customer ID: ZPA console > Administration > Company

##### ZIA Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZIA_USERNAME` | Yes | ZIA API admin email address |
| `ZIA_PASSWORD` | Yes | ZIA API admin password |
| `ZIA_API_KEY` | Yes | ZIA obfuscated API key (from obfuscateApiKey() method) |
| `ZIA_CLOUD` | Yes | Zscaler cloud name (see supported clouds below) |

**Supported ZIA Cloud Environments:**

- `zscaler`, `zscalerone`, `zscalertwo`, `zscalerthree`
- `zscloud`, `zscalerbeta`, `zscalergov`, `zscalerten`, `zspreview`

**Where to find ZIA credentials:**

- Username/Password: Your ZIA admin account
- API Key: ZIA Admin Portal > Administration > API Key Management

##### ZCC Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZCC_CLIENT_ID` | Yes | ZCC API key (Mobile Portal) |
| `ZCC_CLIENT_SECRET` | Yes | ZCC secret key (Mobile Portal) |
| `ZCC_CLOUD` | Yes | Zscaler cloud name (see supported clouds below) |

> **NOTE**: `ZCC_CLOUD` is required and identifies the correct API gateway.

**Supported ZCC Cloud Environments:**

- `zscaler`, `zscalerone`, `zscalertwo`, `zscalerthree`
- `zscloud`, `zscalerbeta`, `zscalergov`, `zscalerten`, `zspreview`

##### ZDX Legacy Authentication

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `ZDX_CLIENT_ID` | Yes | ZDX key ID |
| `ZDX_CLIENT_SECRET` | Yes | ZDX secret key |
| `ZDX_CLOUD` | Yes | Zscaler cloud name prefix |

**Where to find ZDX credentials:**

- ZDX Portal > API Keys section

#### Legacy Mode Behavior

When `ZSCALER_USE_LEGACY=true`:

- All tools use legacy API clients by default
- You can override per-tool by setting `use_legacy: false` in tool parameters
- The MCP server initializes without creating clients at startup
- Clients are created on-demand when individual tools are called
- This allows the server to work with different legacy services without requiring a specific service during initialization

---

### Authentication Troubleshooting

**Common Issues:**

1. **"Authentication failed" errors:**
   - Verify all required environment variables are set
   - Check that credentials are correct and not expired
   - Ensure you're using the correct cloud environment

2. **"Legacy credentials ignored" warning:**
   - This is normal when using OneAPI mode
   - Legacy credentials are only loaded when `ZSCALER_USE_LEGACY=true`

3. **"OneAPI credentials ignored" warning:**
   - This is normal when using Legacy mode
   - OneAPI credentials are only used when `ZSCALER_USE_LEGACY` is not set or is `false`

4. **Mixed authentication errors:**
   - **DO NOT** set both OneAPI and Legacy credentials
   - **DO NOT** set `ZSCALER_USE_LEGACY=true` if using OneAPI
   - Choose ONE method and stick with it

### MCP Server Configuration

The following environment variables control MCP server behavior (not authentication):

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ZSCALER_MCP_TRANSPORT` | `stdio` | Transport protocol to use (`stdio`, `sse`, or `streamable-http`) |
| `ZSCALER_MCP_SERVICES` | `""` | Comma-separated list of services to enable (empty = all services). Supported values: `zcc`, `zdx`, `zia`, `zidentity`, `zpa`, `ztw` |
| `ZSCALER_MCP_TOOLS` | `""` | Comma-separated list of specific tools to enable (empty = all tools) |
| `ZSCALER_MCP_DISABLED_SERVICES` | `""` | Comma-separated list of services to exclude (e.g., `zcc,zdx`). Takes precedence over `ZSCALER_MCP_SERVICES`. |
| `ZSCALER_MCP_DISABLED_TOOLS` | `""` | Comma-separated list of tools to exclude. Supports wildcards (e.g., `zcc_*,zcc_devices_csv_exporter`). Takes precedence over `ZSCALER_MCP_TOOLS`. |
| `ZSCALER_MCP_WRITE_ENABLED` | `false` | Enable write operations (`true`/`false`). When `false`, only read-only tools are available. Set to `true` or use `--enable-write-tools` flag to unlock write mode. |
| `ZSCALER_MCP_WRITE_TOOLS` | `""` | **MANDATORY** comma-separated allowlist of write tools (supports wildcards like `zpa_*`). Requires `ZSCALER_MCP_WRITE_ENABLED=true`. If empty when write mode enabled, 0 write tools registered. |
| `ZSCALER_MCP_DEBUG` | `false` | Enable debug logging (`true`/`false`) |
| `ZSCALER_MCP_HOST` | `127.0.0.1` | Host to bind to for HTTP transports |
| `ZSCALER_MCP_PORT` | `8000` | Port to listen on for HTTP transports |
| `ZSCALER_MCP_DISABLE_HOST_VALIDATION` | `false` | Disable Host header validation when exposing on EC2/public IP (`true`/`false`). Alternatively, use `--host 0.0.0.0` which auto-disables. |
| `ZSCALER_MCP_ALLOWED_HOSTS` | `""` | Comma-separated allowed Host values for remote deployment (e.g. `34.201.19.115:*,localhost:*`). Preferred over disable for production. |
| `ZSCALER_MCP_TLS_CERTFILE` | `""` | Path to TLS certificate file (PEM format) for HTTPS. |
| `ZSCALER_MCP_TLS_KEYFILE` | `""` | Path to TLS private key file (PEM format) for HTTPS. |
| `ZSCALER_MCP_TLS_KEYFILE_PASSWORD` | `""` | Password for encrypted TLS private key (if applicable). |
| `ZSCALER_MCP_TLS_CA_CERTS` | `""` | Path to CA certificate bundle for mutual TLS or custom CA chains. |
| `ZSCALER_MCP_ALLOW_HTTP` | `false` | Allow plaintext HTTP on non-localhost interfaces. HTTPS is required by default for remote deployments. Set to `true` only when TLS is terminated upstream (reverse proxy, ZPA, VPN). |
| `ZSCALER_MCP_ALLOWED_SOURCE_IPS` | `""` | Comma-separated list of allowed client IPs/CIDRs (e.g. `10.0.0.0/8,172.16.0.5`). When unset, source IP filtering is disabled (defer to firewall/security groups). Set to `0.0.0.0/0` to allow all. |
| `ZSCALER_MCP_SKIP_CONFIRMATIONS` | `false` | Skip cryptographic confirmation for destructive actions (testing/CI only). |
| `ZSCALER_MCP_CONFIRMATION_TTL` | `300` | HMAC confirmation token lifetime in seconds (default: 5 minutes). |
| `ZSCALER_MCP_USER_AGENT_COMMENT` | `""` | Additional information to include in User-Agent comment section |

#### User-Agent Header

The MCP server automatically includes a custom User-Agent header in all API requests to Zscaler services. The format is:

```sh
User-Agent: zscaler-mcp-server/<version> python/<python_version> <os>/<architecture>
```

**Example:**

```sh
User-Agent: zscaler-mcp-server/0.3.1 python/3.11.8 darwin/arm64
```

**With Custom Comment:**

You can append additional information (such as the AI agent details) using the `ZSCALER_MCP_USER_AGENT_COMMENT` environment variable or the `--user-agent-comment` CLI flag:

```bash
# Via environment variable
export ZSCALER_MCP_USER_AGENT_COMMENT="Claude Desktop 1.2024.10.23"

# Via CLI flag
zscaler-mcp --user-agent-comment "Claude Desktop 1.2024.10.23"
```

This results in:

```sh
User-Agent: zscaler-mcp-server/0.3.1 python/3.11.8 darwin/arm64 Claude Desktop 1.2024.10.23
```

The User-Agent helps Zscaler identify API traffic from the MCP server and can be useful for support, analytics, and debugging purposes.

### As a Library

You can use the Zscaler Integrations MCP Server as a Python library in your own applications:

```python
from zscaler_mcp.server import ZscalerMCPServer

# Create server with read-only mode (default - safe)
server = ZscalerMCPServer(
    debug=True,  # Optional, enable debug logging
    enabled_services={"zia", "zpa", "zdx"},  # Optional, defaults to all services
    enabled_tools={"zia_list_rule_labels", "zpa_list_application_segments"},  # Optional, defaults to all tools
    disabled_services={"zcc"},  # Optional, exclude entire services
    disabled_tools={"zcc_*", "zdx_list_devices"},  # Optional, exclude tools by name or wildcard
    user_agent_comment="My Custom App",  # Optional, additional User-Agent info
    enable_write_tools=False  # Optional, defaults to False (read-only mode)
)

# Run with stdio transport (default)
server.run()

# Or run with SSE transport
server.run("sse")

# Or run with streamable-http transport
server.run("streamable-http")

# Or run with streamable-http transport on custom host/port
server.run("streamable-http", host="0.0.0.0", port=8080)
```

**Example with write operations enabled:**

```python
from zscaler_mcp.server import ZscalerMCPServer

# Create server with write operations enabled
server = ZscalerMCPServer(
    debug=True,
    enabled_services={"zia", "zpa"},
    enable_write_tools=True  # Enable create/update/delete operations
)

# Run the server
server.run("stdio")
```

**Available Services**: `zcc`, `zdx`, `zia`, `zidentity`, `zpa`

**Example with Environment Variables**:

```python
from zscaler_mcp.server import ZscalerMCPServer
import os

# Load from environment variables
server = ZscalerMCPServer(
    debug=True,
    enabled_services={"zia", "zpa"}
)

# Run the server
server.run("stdio")
```

### Running Examples

```bash
# Run with stdio transport
python examples/basic_usage.py

# Run with SSE transport
python examples/sse_usage.py

# Run with streamable-http transport
python examples/streamable_http_usage.py
```

## Container Usage

The Zscaler Integrations MCP Server is available as a pre-built container image for easy deployment:

### Using Pre-built Image (Recommended)

```bash
# Pull the latest pre-built image
docker pull zscaler/zscaler-mcp-server:latest

# Run with .env file (recommended)
docker run --rm --env-file /path/to/.env zscaler/zscaler-mcp-server:latest

# Run with .env file and SSE transport
docker run --rm -p 8000:8000 --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest --transport sse --host 0.0.0.0

# Run with .env file and streamable-http transport
docker run --rm -p 8000:8000 --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0

# Run with .env file and custom port
docker run --rm -p 8080:8080 --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0 --port 8080

# Run with .env file and specific services
docker run --rm --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest --services zia,zpa,zdx

# Use a specific version instead of latest
docker run --rm --env-file /path/to/.env \
  zscaler/zscaler-mcp-server:latest:1.2.3

# Alternative: Individual environment variables
docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
  -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain \
  zscaler/zscaler-mcp-server:latest
```

### Building Locally (Development)

For development or customization purposes, you can build the image locally:

```bash
# Build the Docker image
docker build -t zscaler-mcp-server .

# Run the locally built image
docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
  -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain zscaler-mcp-server
```

**Note**: When using HTTP transports in Docker, always set `--host 0.0.0.0` to allow external connections to the container.

## Editor/Assistant Integration

You can integrate the Zscaler Integrations MCP server with your editor or AI assistant. Here are configuration examples for popular MCP clients:

### Using `uvx` (recommended)

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/path/to/.env", "zscaler-mcp-server"]
    }
  }
}
```

## Additional Deployment Options

### Remote MCP Deployment (EC2, VM, etc.)

When deploying the MCP server on a **remote host** (EC2, VM, internal server) so clients connect over HTTP from another machine:

**Server setup:**

1. Install and configure credentials (see [Installation](#installation) and [Environment Configuration](#environment-configuration)).
2. If using an **editable install** (`uv pip install -e .`), you **must activate the project venv** before running—otherwise an older or different installation may run:

   ```bash
   cd /path/to/zscaler-mcp-server
   source .venv/bin/activate
   zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8000
   ```

3. Use `--host 0.0.0.0` to bind on all interfaces. This **automatically disables Host header validation** (required when clients send the server's public IP in the Host header). For production, consider `ZSCALER_MCP_ALLOWED_HOSTS` in `.env` to restrict to known hostnames.
4. Ensure the firewall allows inbound traffic on the chosen port (e.g. 8000).

**Client configuration (Claude Desktop):**

Claude Desktop expects a `command` that spawns a process. For remote HTTP, use `mcp-remote` which supports custom authentication headers.

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

On Windows, paths with spaces (e.g., `C:\Program Files\...`) cause `npx` to fail when invoked directly. Wrap the call through `cmd /c`:

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

> **`--allow-http`**: Required when connecting to a non-localhost HTTP endpoint. `mcp-remote` enforces HTTPS by default for non-localhost URLs. Omit this flag when connecting over HTTPS or to `localhost`.

**Using Zscaler auth mode (Basic Auth):**

Replace the `Authorization` header with Basic Auth credentials. The value is the Base64 encoding of `client_id:client_secret`:

```bash
# Generate the Base64 value
echo -n "your-client-id:your-client-secret" | base64
```

Then use `"Authorization: Basic <base64_value>"` in place of the Bearer header above.

**Prerequisites on the client:** Node.js (for `npx`) must be installed.

> **📖 Full remote deployment details** (venv usage, 421 troubleshooting, security, TLS): [Remote Deployment](docs/deployment/authentication-and-deployment.md#remote-deployment-ec2-vm-etc) · [421 Misdirected Request](docs/deployment/authentication-and-deployment.md#421-misdirected-request-invalid-host-header) · [Troubleshooting](docs/guides/TROUBLESHOOTING.md#remote-mcp-421-misdirected-request)

### Amazon Bedrock AgentCore

> [!IMPORTANT]
> **AWS Marketplace Image Available**: For Amazon Bedrock AgentCore deployments, we provide a dedicated container image optimized for Bedrock's stateless HTTP environment. This image includes a custom web server wrapper that handles session management and is specifically designed for AWS Bedrock AgentCore Runtime.

**🚀 Quick Start with AWS Marketplace:**

The easiest way to deploy the Zscaler Integrations MCP Server to Amazon Bedrock AgentCore is through the [AWS Marketplace listing](https://aws.amazon.com/marketplace/pp/prodview-dtjfklwemb54y?sr=0-1&ref_=beagle&applicationId=AWSMPContessa). The Marketplace image includes:

- ✅ Pre-configured for Bedrock AgentCore Runtime
- ✅ Custom web server wrapper for stateless HTTP environments
- ✅ Session management handled automatically
- ✅ Health check endpoints for ECS compatibility
- ✅ Optimized for AWS Bedrock AgentCore's requirements

**📚 Full Deployment Guide:**

For detailed deployment instructions, IAM configuration, and troubleshooting, please refer to the comprehensive [Amazon Bedrock AgentCore deployment guide](./docs/deployment/amazon_bedrock_agentcore.md).

The deployment guide covers:

- Prerequisites and AWS VPC requirements
- IAM role and trust policy configuration
- Step-by-step deployment instructions
- Environment variable configuration
- Write mode configuration (for CREATE/UPDATE/DELETE operations)
- Troubleshooting and verification steps

> [!NOTE]
> The AWS Marketplace image uses a different architecture than the standard `streamable-http` transport. It includes a FastAPI-based web server wrapper (`web_server.py`) that bypasses the MCP protocol's session initialization requirements, making it compatible with Bedrock's stateless HTTP environment. This is why the Marketplace image is recommended for Bedrock deployments.

## Using the MCP Server with Agents

This section provides instructions for configuring the Zscaler Integrations MCP Server with popular AI agents. **Before starting, ensure you have:**

1. ✅ Completed [Installation & Setup](#installation--setup)
2. ✅ Configured [Authentication](#zscaler-api-credentials-authentication)
3. ✅ Created your `.env` file with credentials

### Claude Desktop

You can install the Zscaler MCP Server in Claude Desktop using either method:

> **Windows users**: The one-click extension bundles macOS/Linux binaries and will not work on Windows. Use **Option 2: Manual Configuration** instead—it uses `uvx` to install platform-appropriate packages at runtime. See [Troubleshooting: Windows](docs/guides/TROUBLESHOOTING.md#windows-claude-desktop-extension-fails-to-start) for details.

#### Option 1: Install as Extension (macOS / Linux)

The easiest way to get started—one-click install with a user-friendly UI in Claude Desktop and low barrier to entry.

**Prerequisites:** [uv](https://docs.astral.sh/uv/) must be installed (provides `uvx`). The extension uses uvx to run the server from PyPI at runtime—**no manual `pip install zscaler-mcp` required**. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`

1. Open Claude Desktop
2. Go to **Settings** → **Extensions** → **Browse Extensions**
3. In the search box, type `zscaler`
4. Select **Zscaler MCP Server** from the results
5. Click **Install** or **Add**
6. Configure your `.env` file path when prompted (or edit the configuration after installation)
7. Restart Claude Desktop completely (quit and reopen)
8. Verify by asking Claude: "What Zscaler tools are available?"

#### Option 2: Manual Configuration (All platforms, recommended on Windows)

1. Open Claude Desktop
2. Go to **Settings** → **Developer** → **Edit Config**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/absolute/path/to/your/.env", "zscaler-mcp"]
    }
  }
}
```

> **Important**: Replace `/absolute/path/to/your/.env` with the **absolute path** to your `.env` file. On Windows, use a path like `C:\Users\You\.env`. Relative paths will not work.

1. Save the configuration file
2. Restart Claude Desktop completely (quit and reopen)
3. Verify by asking Claude: "What Zscaler tools are available?"

**Troubleshooting:**

- **"MCP server not found"**: Verify the `.env` file path is absolute and correct
- **"Authentication failed"**: Check that your `.env` file contains valid credentials
- **Tools not appearing**: Check Claude Desktop logs (Help > View Logs) for errors
- **Extension not found**: Ensure you're searching in the "Desktop extensions" tab, not "Web"
- **Windows: `ModuleNotFoundError` (rpds, pydantic_core, etc.)**: The extension bundles macOS/Linux binaries. Use Option 2 (Manual Configuration) instead. See [Troubleshooting guide](docs/guides/TROUBLESHOOTING.md#windows-claude-desktop-extension-fails-to-start).

### Cursor

1. Open Cursor
2. Go to **Settings** → **Cursor Settings** → **Tools & MCP** → **New MCP Server**
3. The configuration will be saved to `~/.cursor/mcp.json`. Add the following configuration:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/absolute/path/to/your/.env", "zscaler-mcp-server"]
    }
  }
}
```

> **Alternative**: You can also use Docker instead of `uvx`:
>
> ```json
> {
>   "mcpServers": {
>     "zscaler-mcp-server": {
>       "command": "docker",
>       "args": [
>         "run",
>         "-i",
>         "--rm",
>         "--env-file",
>         "/absolute/path/to/your/.env",
>         "zscaler/zscaler-mcp-server:latest"
>       ]
>     }
>   }
> }
> ```

1. Save the configuration file
2. Restart Cursor completely (quit and reopen)
3. Verify by asking: "List my ZIA rule labels"

**Troubleshooting:**

- Check Cursor's MCP logs (View > Output > MCP) for connection errors
- Verify the `.env` file path is absolute and credentials are correct
- The configuration file is located at `~/.cursor/mcp.json` (or `%USERPROFILE%\.cursor\mcp.json` on Windows)

## Platform Integrations

The Zscaler MCP Server ships with native integrations for several AI development platforms. Each integration includes platform-specific configuration files, 19 guided skills, and setup instructions.

| Platform | Type | Quick Start | Details |
|----------|------|------------|---------|
| **Claude Code** | Plugin | `claude plugin install zscaler` | [integrations/claude-code-plugin/](integrations/claude-code-plugin/README.md) |
| **Cursor** | Plugin | Settings → Tools & MCP → New MCP Server | [integrations/cursor-plugin/](integrations/cursor-plugin/README.md) |
| **Gemini CLI** | Extension | Register `gemini-extension.json` | [integrations/gemini-extension/](integrations/gemini-extension/README.md) |
| **Kiro IDE** | Power | Powers panel → Add Custom Power | [integrations/kiro/](integrations/kiro/README.md) |
| **Google ADK** | Agent | `adk run zscaler_agent` | [integrations/adk/](integrations/adk/README.md) |

For full documentation on all integrations, see the [Platform Integrations Guide](integrations/README.md).

### General Troubleshooting for All Agents

**Common Issues:**

1. **"Command not found: uvx"**
   - Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Or use Docker: Replace `uvx` with `docker run --rm --env-file /path/to/.env zscaler/zscaler-mcp-server:latest`

2. **".env file not found"**
   - Use absolute paths, not relative paths
   - Verify the file exists at the specified path
   - Check file permissions (should be readable)

3. **"Authentication failed"**
   - Verify all required environment variables are in `.env`
   - Check that credentials are correct and not expired
   - Ensure you're using the correct authentication method (OneAPI vs Legacy)

4. **"Tools not appearing"**
   - Some agents require you to enable tools in their UI
   - Check agent logs for connection errors
   - Verify the MCP server is running (check agent's MCP status)

5. **"Server connection timeout"**
   - Ensure the MCP server can start successfully
   - Test manually: `uvx --env-file /path/to/.env zscaler-mcp`
   - Check for port conflicts if using HTTP transports

6. **Windows: `ModuleNotFoundError: No module named 'rpds.rpds'`** (Claude Desktop extension)
   - The extension bundles macOS/Linux binaries. Use manual configuration with `uvx zscaler-mcp` instead.
   - See [Troubleshooting: Windows](docs/guides/TROUBLESHOOTING.md#windows-claude-desktop-extension-fails-to-start).

7. **Windows: `'C:\Program' is not recognized`** (Remote MCP with `npx`)
   - Paths with spaces break `npx` when called directly. Use `"command": "cmd"` with `"args": ["/c", "npx", ...]` instead.
   - See [Troubleshooting: Windows npx path issues](docs/guides/TROUBLESHOOTING.md#windows-npx-path-with-spaces).

8. **`Non-HTTPS URLs are only allowed for localhost`** (mcp-remote)
   - `mcp-remote` enforces HTTPS for non-localhost URLs by default. Add `"--allow-http"` to the `args` array before `--header`.
   - See [Troubleshooting: mcp-remote HTTPS enforcement](docs/guides/TROUBLESHOOTING.md#mcp-remote-non-https-url-rejected).

9. **`self-signed certificate` / `DEPTH_ZERO_SELF_SIGNED_CERT`** (mcp-remote with TLS)
   - When using self-signed certificates, add `"env": { "NODE_TLS_REJECT_UNAUTHORIZED": "0" }` to the MCP server entry in your client config.
   - See [Troubleshooting: Self-signed certificates](docs/guides/TROUBLESHOOTING.md#self-signed-certificate-rejected-by-mcp-remote).

**Getting Help:**

- Check agent-specific logs (usually in Help/View menu)
- Test the server manually to isolate agent vs server issues
- Review the [Troubleshooting](#troubleshooting) section for more details
