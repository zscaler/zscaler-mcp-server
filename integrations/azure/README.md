# Azure Integration

Deploy the Zscaler MCP Server to Azure with your choice of deployment target, authentication mode, and Azure Key Vault for secret storage.

## Deployment Targets

| Target | Description | Image/Package |
|--------|-------------|---------------|
| **Azure Container Apps** | Managed, serverless containers | Docker Hub: `zscaler/zscaler-mcp-server:latest` |
| **Azure Virtual Machine** | Ubuntu 22.04, self-managed | PyPI: `zscaler-mcp-server` |

Both options use Azure Key Vault for secure credential storage and support all five authentication modes.

## What It Does

The `azure_mcp_operations.py` script provides a **fully interactive** deployment experience:

1. **Prompts** for deployment target (Container Apps or VM)
2. **Prompts** for credential source (`.env` file or manual entry)
3. **Collects** Zscaler API credentials and MCP auth configuration
4. **Creates** Azure infrastructure (resource group, Key Vault, NSG for VM)
5. **Stores** all secrets in Azure Key Vault
6. **Deploys** with the selected authentication mode
7. **Updates** Claude Desktop and Cursor configs to connect remotely
8. **Provides** `destroy`, `status`, `logs`, and `ssh` (VM only) commands

## Authentication Modes

| Mode | Description | Client Auth Header |
|------|-------------|-------------------|
| **OIDCProxy** | OAuth 2.1 + DCR via OIDC provider (browser login) | Handled automatically by `mcp-remote` |
| **JWT** | Validate JWTs against a JWKS endpoint | `Authorization: Bearer <JWT>` |
| **API Key** | Shared secret (auto-generated if not provided) | `Authorization: Bearer <api-key>` |
| **Zscaler** | Validate via OneAPI client credentials | `Authorization: Basic base64(id:secret)` |
| **None** | No authentication (development only) | No header |

## Prerequisites

- [Azure CLI](https://aka.ms/installazurecli) (`az`) — logged in (`az login`)
- [Node.js](https://nodejs.org/) — for `npx mcp-remote` (Claude Desktop bridge)
- Zscaler OneAPI credentials (from ZIdentity console)
- For OIDCProxy: an OIDC provider app registration (Entra ID, Okta, Auth0, etc.)
- For VM: SSH key pair (script can generate one)

## Quick Start

```bash
# Interactive guided deployment — no .env file required
python azure_mcp_operations.py deploy

# The script will prompt you for:
#   1. Deployment target (Container Apps or VM)
#   2. Credential source (.env file or manual entry)
#   3. Auth mode (OIDCProxy, JWT, API Key, Zscaler, None)
#   4. Azure options (resource group, region, Key Vault)
```

## Operations

### MCP Server Operations

| Command | Description |
|---------|-------------|
| `deploy` | Interactive guided deployment |
| `destroy` | Tear down all Azure resources (full rollback) |
| `status` | Show deployment status and health |
| `logs` | Stream container/VM logs |
| `ssh` | SSH into VM (VM deployments only) |

```bash
python azure_mcp_operations.py deploy     # guided deployment
python azure_mcp_operations.py status     # check health
python azure_mcp_operations.py logs       # stream logs
python azure_mcp_operations.py ssh        # SSH into VM
python azure_mcp_operations.py destroy    # tear down everything
python azure_mcp_operations.py destroy -y # non-interactive destroy
```

### Foundry Agent Operations

| Command | Flags | Description |
|---------|-------|-------------|
| `agent_create` | | Create a Foundry agent with Zscaler MCP tools. Prompts for project endpoint, model, and credentials (or reads from `.env`). |
| `agent_status` | | Show agent name, version, model, MCP server URL, and project endpoint. |
| `agent_chat` | `--message "..." / -m "..."` | Start interactive multi-turn chat. Optionally pass an initial message. |
| `agent_destroy` | `--yes / -y` | Delete the Foundry agent. Pass `-y` to skip confirmation. |

```bash
python azure_mcp_operations.py agent_create              # create agent (interactive prompts)
python azure_mcp_operations.py agent_status              # check agent info
python azure_mcp_operations.py agent_chat                # interactive chat session
python azure_mcp_operations.py agent_chat -m "list ZPA segment groups"  # chat with initial message
python azure_mcp_operations.py agent_destroy             # delete agent (confirmation prompt)
python azure_mcp_operations.py agent_destroy -y          # delete agent (no prompt)
```

#### Chat Session Features

The `agent_chat` command provides a full interactive CLI experience:

- **Animated spinner** — braille-character animation (`⠋ ⠙ ⠹ ...`) with live elapsed-time counter while waiting for agent responses
- **Token tracking** — per-response token usage (input, output, total) displayed after each answer
- **Response timing** — wall-clock time for each request/response cycle
- **Session summary** — total session duration and cumulative token count on exit
- **Tool approval** — when the agent wants to call a Zscaler tool, you approve or reject before execution
- **Multi-turn** — proper response chaining ensures context is maintained across follow-up questions

Example output:

```
  ______              _
 |___  /             | |
    / / ___  ___ __ _| | ___ _ __
   / / / __|/ __/ _` | |/ _ \ '__|
  / /__\__ \ (_| (_| | |  __/ |
 /_____|___/\___\__,_|_|\___|_|

============================================================
  Zscaler MCP Agent Chat
  Agent: zscaler-mcp-agent (v1)
  Type 'quit' or 'exit' to end the session.
============================================================

You: list all zpa segment groups
⠹ Thinking (2s)

MCP Tool Approval Requested:
  Server: zscaler
  Tool:   zpa_list_segment_groups
  Args:   {"search": null, "page": null, ...}

Approve this tool call? (y/n): y
⠸ Executing tool (3s)

Agent: Here are the ZPA segment groups currently defined: ...
       [5.2s | 1,248 tokens | in:680 out:568]

You: quit

──────────────────────────────────────────────────
Session: 38s | Total tokens: 2,496
──────────────────────────────────────────────────
[INFO]  Chat session ended.
```

## Container Apps Deployment

Pulls the pre-built Docker image from Docker Hub (`zscaler/zscaler-mcp-server:latest`):

- **Serverless** — Azure manages scaling (1-3 replicas by default)
- **TLS** — Automatic HTTPS via Azure Container Apps ingress
- **No build required** — image pulled directly from Docker Hub

### Architecture (Container Apps)

```
┌──────────────────┐                           ┌──────────────────────┐
│  Claude Desktop   │     streamable-http       │   Azure Container    │
│  / Cursor         │◄─────────────────────────►│   Apps (MCP Server)  │
│  (mcp-remote)     │                           └──────────┬───────────┘
└────────┬─────────┘                                       │
         │                                                 │  Zscaler API
         ▼                                                 ▼
┌──────────────────┐    ┌────────────────┐       ┌──────────────────────┐
│  OIDC Provider   │    │  Azure Key     │       │  Zscaler Zero Trust  │
│  (if OIDCProxy)  │    │  Vault         │       │  Exchange (OneAPI)   │
└──────────────────┘    └────────────────┘       └──────────────────────┘
```

## VM Deployment

Provisions an Ubuntu 22.04 VM and installs the MCP server from PyPI:

- **Self-managed** — you control the VM (SSH access, updates, etc.)
- **systemd service** — automatic startup, restart on failure
- **NSG configured** — SSH (22) and MCP port open

### Architecture (VM)

```
┌──────────────────┐                           ┌──────────────────────┐
│  Claude Desktop   │     HTTP (port 8000)      │   Azure VM           │
│  / Cursor         │◄─────────────────────────►│   Ubuntu 22.04       │
│  (mcp-remote)     │                           │                      │
└────────┬─────────┘                           │  ┌────────────────┐  │
         │                                      │  │ systemd        │  │
         ▼                                      │  │ zscaler-mcp    │  │
┌──────────────────┐    ┌────────────────┐      │  └────────────────┘  │
│  OIDC Provider   │    │  Azure Key     │      └──────────┬───────────┘
│  (if OIDCProxy)  │    │  Vault         │                 │
└──────────────────┘    └────────────────┘                 │  Zscaler API
                                                           ▼
                                              ┌──────────────────────┐
                                              │  Zscaler Zero Trust  │
                                              │  Exchange (OneAPI)   │
                                              └──────────────────────┘
```

### VM Service Management

Once deployed, you can manage the MCP server via SSH:

```bash
# SSH into the VM (or use the script)
python azure_mcp_operations.py ssh

# On the VM:
sudo systemctl status zscaler-mcp   # check status
sudo journalctl -u zscaler-mcp -f   # stream logs
sudo systemctl restart zscaler-mcp  # restart service

# Environment variables are in:
/opt/zscaler-mcp/env

# Python virtual environment:
/opt/zscaler-mcp/venv/bin/zscaler-mcp --help
```

## Azure AI Foundry Agent Integration

For organizations using Azure AI Foundry, you can create a managed AI agent that uses your deployed MCP server as a tool. This enables:

- **Azure-hosted AI agent** — no need to run Claude Desktop or Cursor
- **REST API access** — integrate Zscaler AI into your applications
- **Microsoft 365 Copilot integration** — publish to Teams and Copilot
- **Centralized management** — manage agents through Azure portal

### Architecture (Foundry Agent)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Azure Subscription                               │
│                                                                          │
│  ┌──────────────────────────┐       ┌──────────────────────────────┐    │
│  │  Azure Container Apps    │       │  Azure AI Foundry             │    │
│  │  or VM                   │◄─────│  (Agent Service)              │    │
│  │                          │       │                              │    │
│  │  ┌────────────────────┐  │       │  McpTool(                    │    │
│  │  │ zscaler-mcp-server │  │       │    server_label="zscaler",   │    │
│  │  │ (streamable-http)  │  │       │    server_url="http://...",  │    │
│  │  └────────────────────┘  │       │    headers={X-Zscaler-*},    │    │
│  └──────────────────────────┘       │    require_approval="always" │    │
│                                     │  )                           │    │
│              │                      │                              │    │
│  ┌───────────▼──────────┐           │  ┌────────────────────────┐  │    │
│  │  Azure Key Vault     │           │  │  Azure OpenAI          │  │    │
│  │  (Zscaler secrets)   │           │  │  (GPT-4o / GPT-4)     │  │    │
│  └──────────────────────┘           │  └────────────────────────┘  │    │
│                                     └──────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                    │                            │
                    ▼                            ▼
          Zscaler Zero Trust              User Applications
          Exchange APIs                   (Portal, API, Copilot)
```

### Prerequisites for Foundry Agent

- **Azure AI Foundry project** — create at [ai.azure.com](https://ai.azure.com)
- **Azure OpenAI deployment** — GPT-4o or GPT-4 model
- **Deployed MCP server** — Container Apps or VM (from this script)
- **Python packages**: `pip install azure-ai-projects azure-identity`
- **Azure CLI** authenticated: `az login`

### Quick Start (Foundry Agent)

```bash
# 1. Deploy MCP server first (if not already done)
python azure_mcp_operations.py deploy

# 2. Create Foundry agent
python azure_mcp_operations.py agent_create
# You'll be prompted for:
#   - Foundry project endpoint (from portal → Project Overview)
#   - Model deployment name (default: gpt-4o)
#   - MCP server auth credentials (loaded from .env or entered manually)

# 3. Start interactive chat (CLI)
python azure_mcp_operations.py agent_chat

# 4. Or check agent status
python azure_mcp_operations.py agent_status

# 5. Delete agent when done
python azure_mcp_operations.py agent_destroy
```

### MCP Server Authentication from Foundry

The Foundry agent authenticates to the MCP server using custom HTTP headers
passed via `MCPTool.headers`. The script configures these based on your
deployment's auth mode:

| MCP Auth Mode | Headers Passed | Source |
|---------------|---------------|--------|
| `zscaler` | `X-Zscaler-Client-ID` + `X-Zscaler-Client-Secret` | OneAPI credentials |
| `api-key` | `X-MCP-API-Key` | MCP API key |
| `none` | *(no headers)* | — |

> **Why not `Authorization` header or `project_connection_id`?**
> Azure Foundry blocks `Authorization` in `MCPTool.headers` (sensitive header
> restriction). The `project_connection_id` / CustomKeys alternative has a
> known URI parsing bug in the Foundry service. Using `X-Zscaler-*` custom
> headers bypasses both issues while maintaining full authentication.

### Foundry Portal (UI)

After creating the agent, you can access it through the Azure AI Foundry portal:

1. Go to [ai.azure.com](https://ai.azure.com)
2. Open your project
3. Navigate to **Agents** in the left panel
4. Select `zscaler-mcp-agent`
5. Use the **Playground** to test the agent interactively

The portal also lets you publish, monitor, and manage agent versions.

### Publishing Agents

Foundry agents can be published to different scopes:

| Scope | Visibility | Admin Approval | Best For |
|-------|------------|----------------|----------|
| **Individual** | Only you (shareable via link) | Not required | Testing, pilots |
| **Organization** | Everyone in Azure AD tenant | Required (your IT admin) | Production |

Publication is **self-service** — no Microsoft involvement required. Publish through the [Foundry portal](https://ai.azure.com) or programmatically via the SDK.

### Tool Approval

The Foundry agent is configured with `require_approval="always"` by default. When the agent wants to use a Zscaler tool:

1. The agent describes what tool it wants to call and why
2. You approve or reject the tool call
3. If approved, the tool executes and returns results
4. The agent processes results and continues

This ensures human oversight for all Zscaler operations.

## Credential Sources

### From a `.env` file

Copy `env.properties` to `.env` and fill in the values. During deployment, select "From a .env file" and provide the file path.

### Interactive prompts

Select "Enter manually" and the script will prompt for each credential. Secrets are entered via `getpass` (hidden input).

## Azure Key Vault

All secrets are stored in Azure Key Vault (mandatory). During deployment you can:

- **Create a new vault** — the script handles creation, RBAC, and secret storage
- **Use an existing vault** — provide the vault name

Stored secrets include Zscaler API credentials and auth-mode-specific credentials.

## Environment Variables

### Zscaler API (required for all modes)

| Variable | Description |
|----------|-------------|
| `ZSCALER_CLIENT_ID` | OneAPI client ID from ZIdentity |
| `ZSCALER_CLIENT_SECRET` | OneAPI client secret |
| `ZSCALER_VANITY_DOMAIN` | Zscaler vanity domain |
| `ZSCALER_CUSTOMER_ID` | Zscaler customer ID |
| `ZSCALER_CLOUD` | Zscaler cloud (e.g. `production`, `beta`) |

### OIDCProxy Mode

| Variable | Description |
|----------|-------------|
| `OIDCPROXY_DOMAIN` | OIDC provider domain (e.g. `login.microsoftonline.com/<tenant>/v2.0` or `tenant.auth0.com`) |
| `OIDCPROXY_CLIENT_ID` | Application / client ID from your identity provider |
| `OIDCPROXY_CLIENT_SECRET` | Client secret from your identity provider |
| `OIDCPROXY_AUDIENCE` | Token audience / API identifier (default: `zscaler-mcp-server`) |

### JWT Mode

| Variable | Description |
|----------|-------------|
| `ZSCALER_MCP_AUTH_JWKS_URI` | JWKS endpoint URL |
| `ZSCALER_MCP_AUTH_ISSUER` | Expected JWT issuer |
| `ZSCALER_MCP_AUTH_AUDIENCE` | Expected JWT audience (default: `zscaler-mcp-server`) |

### API Key Mode

| Variable | Description |
|----------|-------------|
| `ZSCALER_MCP_AUTH_API_KEY` | Shared API key (auto-generated if omitted) |

### MCP Server Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_PORT` | `8000` | Server listen port |
| `ZSCALER_MCP_DISABLED_SERVICES` | _(none)_ | Comma-separated services to disable |
| `ZSCALER_MCP_DISABLED_TOOLS` | _(none)_ | Comma-separated tool patterns to disable |
| `ZSCALER_MCP_WRITE_ENABLED` | `false` | Enable write tools |
| `ZSCALER_MCP_WRITE_TOOLS` | _(none)_ | Comma-separated write tool patterns to allow |

## Client Configuration

After deployment, the script automatically updates your Claude Desktop and Cursor configs. If you need to configure manually, use the examples below.

### Claude Desktop (`claude_desktop_config.json`)

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**API Key / Zscaler Auth Mode:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://<PUBLIC_IP>:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization:Bearer <API_KEY>"
      ]
    }
  }
}
```

For Zscaler auth mode, use `Authorization:Basic <base64(client_id:client_secret)>`.

**OIDCProxy Mode (browser login):**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://<PUBLIC_IP>:8000/mcp",
        "--allow-http"
      ]
    }
  }
}
```

No `--header` needed — `mcp-remote` handles the OAuth flow automatically.

**JWT Mode:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://<PUBLIC_IP>:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization:Bearer <YOUR_JWT_TOKEN>"
      ]
    }
  }
}
```

**No Auth Mode:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://<PUBLIC_IP>:8000/mcp",
        "--allow-http"
      ]
    }
  }
}
```

> **Note:** The `--allow-http` flag is required when connecting to a non-localhost HTTP URL. For HTTPS endpoints (Container Apps with TLS), you can omit this flag.

### Cursor (`mcp.json`)

**Location:**
- macOS/Linux: `~/.cursor/mcp.json`
- Windows: `%USERPROFILE%\.cursor\mcp.json`

**API Key / Zscaler Auth Mode:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "http://<PUBLIC_IP>:8000/mcp",
      "headers": {
        "Authorization": "Bearer <API_KEY>"
      }
    }
  }
}
```

**OIDCProxy / JWT / No Auth:**

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "url": "http://<PUBLIC_IP>:8000/mcp"
    }
  }
}
```

For JWT, add the `headers` block with your token.

### Windows Configuration

On Windows, use `cmd` as the command wrapper:

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
        "http://<PUBLIC_IP>:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization:Bearer <API_KEY>"
      ]
    }
  }
}
```

## Troubleshooting

### "Non-HTTPS URLs are only allowed for localhost"

If Claude Desktop shows this error:

```
Error: Non-HTTPS URLs are only allowed for localhost or when --allow-http flag is provided
```

Add `--allow-http` to your `mcp-remote` args (see examples above). The deployment script adds this automatically for HTTP endpoints.

### Claude Desktop shows "Server disconnected"

1. Check VM/Container status: `python azure_mcp_operations.py status`
2. View logs: `python azure_mcp_operations.py logs`
3. Verify the MCP URL is reachable: `curl http://<PUBLIC_IP>:8000/mcp`
4. Ensure NSG allows traffic on port 8000

### VM service not running

SSH into the VM and check the service:

```bash
python azure_mcp_operations.py ssh

# On the VM:
sudo systemctl status zscaler-mcp
sudo journalctl -u zscaler-mcp -n 50
```

### OIDCProxy callback URL issues

For OIDCProxy mode, ensure the callback URL is registered in your identity provider (Entra ID, Okta, Auth0, etc.):

```
http://<PUBLIC_IP>:8000/auth/callback
```

Some providers may require explicitly allowing HTTP callback URLs in their settings for non-HTTPS deployments.

## Security

- **Secrets in Key Vault**: All credentials stored in Azure Key Vault (mandatory)
- **Five auth modes**: Choose the authentication level appropriate for your environment
- **TLS**: Container Apps provides automatic HTTPS; VM deployments use HTTP by default
- **NSG**: VM deployments configure Network Security Group rules for SSH and MCP port
- **HMAC confirmations**: Destructive operations require cryptographic confirmation tokens
- **Read-only by default**: Write tools are disabled unless explicitly enabled
