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

> [!IMPORTANT]
> **🚧 Public Preview**: This project is currently in public preview and under active development. Features and functionality may change before the stable 1.0 release. While we encourage exploration and testing, please avoid production deployments. We welcome your feedback through [GitHub Issues](https://github.com/zscaler/zscaler-mcp-server/issues) to help shape the final release.

## 📄 Table of contents

- [📺 Overview](#overview)
- [🔒 Security & Permissions](#security-permissions)
- [Supported Tools](#supported-tools)
- [Installation & Setup](#installation-setup)
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
  - [Amazon Bedrock AgentCore](#amazon-bedrock-agentcore)
- [Using the MCP Server with Agents](#using-the-mcp-server-with-agents)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [Visual Studio Code + GitHub Copilot](#visual-studio-code-github-copilot)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## 📺 Overview

The Zscaler Integrations MCP Server brings context to your agents. Try prompts like:

- "List my ZPA Application segments"
- "List my ZPA Segment Groups"
- "List my ZIA Rule Labels"

> [!WARNING]
> **🔒 READ-ONLY BY DEFAULT**: For security, this MCP server operates in **read-only mode** by default. Only `list_*` and `get_*` operations are available. To enable tools that can **CREATE, UPDATE, or DELETE** Zscaler resources, you must explicitly enable write mode using the `--enable-write-tools` flag or by setting `ZSCALER_MCP_WRITE_ENABLED=true`. See the [Security & Permissions](#-security--permissions) section for details.

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

**Key Security Principles**:

- No "enable all write tools" backdoor exists - allowlist is **mandatory**
- AI agents must request permission before executing any write operation (`destructiveHint`)
- Every destructive action requires explicit user approval through the AI agent's permission framework

### Best Practices

- **Read-Only by Default**: No configuration needed for safe operations - read-only tools are always available
- **Mandatory Allowlist**: Always provide explicit `--write-tools` allowlist when enabling write mode
- **Development/Testing**: Use narrow allowlists (e.g., `--write-tools "zpa_create_application_segment"`)
- **Production/Agents**: Keep server in read-only mode (default) for AI agents performing autonomous operations
- **CI/CD**: Never set `ZSCALER_MCP_WRITE_ENABLED=true` without a corresponding `ZSCALER_MCP_WRITE_TOOLS` allowlist
- **Least Privilege**: Use narrowest possible allowlist patterns for your use case
- **Wildcard Usage**: Use wildcards for service-level control (e.g., `zpa_create_*`) or operation-level control (e.g., `*_create_*`)
- **Audit Review**: Regularly review which write tools are allowlisted and remove unnecessary ones

## Supported Tools

The Zscaler Integrations MCP Server provides **150+ tools** for all major Zscaler services:

| Service | Description | Tools |
|---------|-------------|-------|
| **ZCC** | Zscaler Client Connector - Device management | 4 read-only |
| **ZDX** | Zscaler Digital Experience - Monitoring & analytics | 18 read-only |
| **ZIdentity** | Identity & access management | 3 read-only |
| **ZIA** | Zscaler Internet Access - Security policies | 60+ read/write |
| **ZPA** | Zscaler Private Access - Application access | 60+ read/write |
| **ZTW** | Zscaler Workload Segmentation | 20+ read/write |
| **EASM** | External Attack Surface Management | 7 read-only |

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
- `--tools`: Comma-separated list of specific tools to enable
- `--enable-write-tools`: Enable write operations (disabled by default for safety)
- `--debug`: Enable debug logging
- `--host`: Host for HTTP transports (default: `127.0.0.1`)
- `--port`: Port for HTTP transports (default: `8000`)

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
| `ZSCALER_CLOUD` | No | Zscaler cloud environment (e.g., `beta`, `zscalertwo`). **Only required for Beta tenants** |
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
| `ZSCALER_MCP_WRITE_ENABLED` | `false` | Enable write operations (`true`/`false`). When `false`, only read-only tools are available. Set to `true` or use `--enable-write-tools` flag to unlock write mode. |
| `ZSCALER_MCP_WRITE_TOOLS` | `""` | **MANDATORY** comma-separated allowlist of write tools (supports wildcards like `zpa_*`). Requires `ZSCALER_MCP_WRITE_ENABLED=true`. If empty when write mode enabled, 0 write tools registered. |
| `ZSCALER_MCP_DEBUG` | `false` | Enable debug logging (`true`/`false`) |
| `ZSCALER_MCP_HOST` | `127.0.0.1` | Host to bind to for HTTP transports |
| `ZSCALER_MCP_PORT` | `8000` | Port to listen on for HTTP transports |
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
docker pull quay.io/zscaler/zscaler-mcp-server:latest

# Run with .env file (recommended)
docker run --rm --env-file /path/to/.env quay.io/zscaler/zscaler-mcp-server:latest

# Run with .env file and SSE transport
docker run --rm -p 8000:8000 --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --transport sse --host 0.0.0.0

# Run with .env file and streamable-http transport
docker run --rm -p 8000:8000 --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0

# Run with .env file and custom port
docker run --rm -p 8080:8080 --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0 --port 8080

# Run with .env file and specific services
docker run --rm --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:latest --services zia,zpa,zdx

# Use a specific version instead of latest
docker run --rm --env-file /path/to/.env \
  quay.io/zscaler/zscaler-mcp-server:1.2.3

# Alternative: Individual environment variables
docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
  -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain \
  quay.io/zscaler/zscaler-mcp-server:latest
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

1. ✅ Completed [Installation & Setup](#installation-setup)
2. ✅ Configured [Authentication](#zscaler-api-credentials-authentication)
3. ✅ Created your `.env` file with credentials

### Claude Desktop

You can install the Zscaler MCP Server in Claude Desktop using either method:

#### Option 1: Install as Extension (Recommended)

1. Open Claude Desktop
2. Go to **Settings** → **Extensions** → **Browse Extensions**
3. In the search box, type `zscaler`
4. Select **Zscaler MCP Server** from the results
5. Click **Install** or **Add**
6. Configure your `.env` file path when prompted (or edit the configuration after installation)
7. Restart Claude Desktop completely (quit and reopen)
8. Verify by asking Claude: "What Zscaler tools are available?"

#### Option 2: Manual Configuration

1. Open Claude Desktop
2. Go to **Settings** → **Developer** → **Edit Config**
3. Add the following configuration:

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

> **Important**: Replace `/absolute/path/to/your/.env` with the **absolute path** to your `.env` file. Relative paths will not work.

1. Save the configuration file
2. Restart Claude Desktop completely (quit and reopen)
3. Verify by asking Claude: "What Zscaler tools are available?"

**Troubleshooting:**

- **"MCP server not found"**: Verify the `.env` file path is absolute and correct
- **"Authentication failed"**: Check that your `.env` file contains valid credentials
- **Tools not appearing**: Check Claude Desktop logs (Help > View Logs) for errors
- **Extension not found**: Ensure you're searching in the "Desktop extensions" tab, not "Web"

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
>         "quay.io/zscaler/zscaler-mcp-server:latest"
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

### General Troubleshooting for All Agents

**Common Issues:**

1. **"Command not found: uvx"**
   - Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Or use Docker: Replace `uvx` with `docker run --rm --env-file /path/to/.env quay.io/zscaler/zscaler-mcp-server:latest`

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
   - Test manually: `uvx --env-file /path/to/.env zscaler-mcp-server`
   - Check for port conflicts if using HTTP transports

**Getting Help:**

- Check agent-specific logs (usually in Help/View menu)
- Test the server manually to isolate agent vs server issues
- Review the [Troubleshooting](#troubleshooting) section for more details
