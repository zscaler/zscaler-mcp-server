# Platform Integrations

This directory contains official integrations for the Zscaler MCP Server with various AI development platforms.

## Available Integrations

| Platform | Directory | Config Files | Status |
|----------|-----------|-------------|--------|
| [Claude Code Plugin](#claude-code-plugin) | [`integrations/claude-code-plugin/`](./claude-code-plugin/) | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json` | Available |
| [Cursor Plugin](#cursor-plugin) | [`integrations/cursor-plugin/`](./cursor-plugin/) | `.cursor-plugin/plugin.json`, `mcp.json` | Available |
| [Gemini Extension](#gemini-extension) | [`integrations/gemini-extension/`](./gemini-extension/) | `gemini-extension.json`, `GEMINI.md` | Available |
| [Kiro Power](#kiro-power) | [`integrations/kiro/`](./kiro/) | `integrations/kiro/mcp.json`, `integrations/kiro/POWER.md` | Available |
| [Google ADK](#google-adk) | [`integrations/adk/`](./adk/) | `integrations/adk/.env`, `integrations/adk/zscaler_agent/.env` | Available |

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

### Google ADK

**[Full documentation →](./adk/README.md)**

[Google ADK (Agent Development Kit)](https://google.github.io/adk-docs/) integration for building autonomous Zscaler security agents powered by Gemini models. Create AI agents that query and manage your Zscaler environment through natural language.

**Features:**
- Gemini-powered autonomous agent with 280+ Zscaler tools
- Local development via `adk run` or Cloud Run deployment
- Configurable system prompt, model selection, and write-tool controls

**Quick start:**

```bash
cd integrations/adk
adk run zscaler_agent
```

**Config files:** `integrations/adk/.env`, `integrations/adk/zscaler_agent/.env`

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
