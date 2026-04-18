# Platform Integrations

This directory contains official integrations for the Zscaler MCP Server with various AI development platforms.

## Available Integrations

| Platform | Directory | Config Files | Status |
|----------|-----------|-------------|--------|
| [Claude Code Plugin](#claude-code-plugin) | [`integrations/claude-code-plugin/`](./claude-code-plugin/) | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json` | Available |
| [Cursor Plugin](#cursor-plugin) | [`integrations/cursor-plugin/`](./cursor-plugin/) | `.cursor-plugin/plugin.json`, `mcp.json` | Available |
| [Gemini Extension](#gemini-extension) | [`integrations/gemini-extension/`](./gemini-extension/) | `gemini-extension.json`, `GEMINI.md` | Available |
| [Kiro Power](#kiro-power) | [`integrations/kiro/`](./kiro/) | `integrations/kiro/mcp.json`, `integrations/kiro/POWER.md` | Available |
| [Google Cloud (Cloud Run / GKE / VM)](#google-cloud-cloud-run--gke--vm) | [`integrations/google/gcp/`](./google/gcp/) | `integrations/google/gcp/env.properties` | Available |
| [Google ADK Agent](#google-adk-agent) | [`integrations/google/adk/`](./google/adk/) | `integrations/google/adk/zscaler_agent/.env` | Available |
| [Azure (Container Apps / VM)](#azure-container-apps--vm) | [`integrations/azure/`](./azure/) | `integrations/azure/env.properties` | Available |
| [GitHub MCP Registry](#github-mcp-registry) | [`integrations/github/`](./github/) | `server.json` | Available |

All integrations share the same MCP server, tools, and skills — they differ only in how they connect the AI platform to the server.

---

### Claude Code Plugin

**[Full documentation →](./claude-code-plugin/README.md)**

Native [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin with marketplace support, 19 guided skills, and slash commands.

**Quick install:**

```bash
claude plugin install zscaler
```

**Config files at repo root:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`

---

### Cursor Plugin

**[Full documentation →](./cursor-plugin/README.md)**

Native [Cursor](https://cursor.so/) plugin with 19 guided skills for ZPA, ZIA, ZDX, EASM, Z-Insights, and cross-product workflows.

**Quick install:** Settings → Cursor Settings → Tools & MCP → New MCP Server

**Config files at repo root:** `.cursor-plugin/plugin.json`, `mcp.json`

---

### Gemini Extension

**[Full documentation →](./gemini-extension/README.md)**

[Google Gemini CLI](https://github.com/google/gemini-cli) extension with contextual tool guidance via `GEMINI.md`.

**Config files at repo root:** `gemini-extension.json`, `GEMINI.md`

---

### Kiro Power

**[Full documentation →](./kiro/README.md)**

[AWS Kiro IDE](https://kiro.dev) power with service-specific steering files for on-demand context loading.

**Features:**
- 280+ tools across 8 Zscaler services
- Service-specific steering files for ZPA, ZIA, ZDX, ZCC, ZTW, EASM, ZIdentity, and Z-Insights
- Natural language queries for security configuration management

**Quick install:**
1. Open Kiro IDE
2. Go to Powers panel → Add Custom Power
3. Select "Local Directory" or provide the GitHub URL
4. Point to `integrations/kiro/`

**Config files:** `integrations/kiro/mcp.json`, `integrations/kiro/POWER.md`

---

### Google Cloud (Cloud Run / GKE / VM)

**[Full documentation →](./google/README.md)**

Interactive deployment of the Zscaler MCP Server to Google Cloud with three deployment targets:
- **Cloud Run** — managed, serverless container (Docker Hub / GCP Marketplace image)
- **GKE (Kubernetes)** — container on existing GKE cluster
- **Compute Engine VM** — Debian 12, self-managed (Python library from PyPI)

**Features:**
- Fully interactive — prompts for deployment target, credentials, auth mode, and GCP options
- GCP Secret Manager integration (optional, recommended)
- Four auth modes (JWT, API Key, Zscaler, None)
- Auto-configures Claude Desktop and Cursor client configs
- Management commands: `status`, `logs`, `ssh` (VM only), `destroy`

**Quick start:**

```bash
cd integrations/google/gcp
python gcp_mcp_operations.py deploy
```

**Config files:** `integrations/google/gcp/env.properties`

---

### Google ADK Agent

**[Full documentation →](./google/adk/README.md)**

[Google ADK (Agent Development Kit)](https://google.github.io/adk-docs/) integration for building autonomous Zscaler security agents powered by Gemini models. Deploys a Gemini-powered agent that wraps the MCP server as an internal subprocess.

**Features:**
- Gemini-powered autonomous agent with 300+ Zscaler tools
- Local development, Cloud Run, Vertex AI Agent Engine, and Agentspace deployment
- Configurable system prompt, model selection, and write-tool controls

**Quick start:**

```bash
cd integrations/google/adk
python adk_agent_operations.py local_run
```

**Config files:** `integrations/google/adk/zscaler_agent/.env`

---

### Azure (Container Apps / VM)

**[Full documentation →](./azure/README.md)**

Interactive deployment to Azure with two deployment targets:
- **Container Apps** — managed, serverless (Docker Hub image)
- **Virtual Machine** — Ubuntu 22.04, self-managed (Python library from PyPI)

**Features:**
- Fully interactive — prompts for deployment target, credentials, auth mode, and Azure options
- Azure Key Vault integration (mandatory) — create new or use existing
- Five authentication modes (OIDCProxy, JWT, API Key, Zscaler, None)
- VM includes systemd service, SSH access, and NSG configuration
- Management commands: `status`, `logs`, `ssh` (VM only), `destroy`

**Quick start:**

```bash
cd integrations/azure
python azure_mcp_operations.py deploy
```

**Config files:** `integrations/azure/env.properties`

---

### GitHub MCP Registry

**[Full documentation →](./github/README.md)**

Listed on the [GitHub MCP Registry](https://github.com/modelcontextprotocol/registry), enabling one-click installation from GitHub Copilot and MCP-compatible clients.

**Features:**
- One-click install via PyPI (`uvx zscaler-mcp`) or Docker (`docker.io/zscaler/zscaler-mcp-server`)
- Only 4 env vars required (Zscaler OneAPI credentials)
- Secrets marked as `isSecret` for secure client-side storage
- Version automatically updated by the release pipeline

**Config files at repo root:** `server.json`

---

## Shared Components

All integrations leverage common resources from the repository root:

| Component | Location | Purpose |
|-----------|----------|---------|
| Skills | `skills/` | 19 guided multi-step workflows (ZPA, ZIA, ZDX, EASM, Z-Insights, Cross-product) |
| MCP Server | `zscaler_mcp/` | The MCP server implementation (280+ tools) |
| Docs | `docs/` | Deployment guides, tool references, troubleshooting |

## Adding New Integrations

When adding a new platform integration:

1. Create a new directory under `integrations/` with the platform name
2. Include a `README.md` with setup instructions
3. Place any platform-specific config files at the repo root (if required by the platform) or within the integration directory
4. Update this file with the new integration details
