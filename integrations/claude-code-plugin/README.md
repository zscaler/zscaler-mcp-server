# Claude Code Plugin Integration

The Zscaler MCP Server is available as a native **Claude Code Plugin**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## What's Included

| Component | Location | Purpose |
|-----------|----------|---------|
| Plugin manifest | `.claude-plugin/plugin.json` | Plugin metadata, MCP entry point, skills, and slash commands |
| Marketplace manifest | `.claude-plugin/marketplace.json` | Claude Code marketplace listing and versioning |
| Skills | `skills/` | 19 guided multi-step workflows for common Zscaler operations |
| MCP config | `.mcp.json` | MCP server connection configuration |

### Skills (19 guided workflows)

The plugin bundles service-specific skills that Claude auto-activates based on your prompt:

| Service | Skills | Examples |
|---------|--------|----------|
| **ZPA** | 6 | Onboard application, create access/forwarding/timeout policy rules, create server group, troubleshoot connector |
| **ZIA** | 5 | Onboard location, audit SSL inspection, investigate URL category, check user access, investigate sandbox |
| **ZDX** | 5 | Troubleshoot user experience, analyze app health, investigate alerts, diagnose deep trace, audit software |
| **EASM** | 1 | Review attack surface |
| **Z-Insights** | 1 | Investigate security incident |
| **Cross-product** | 1 | Troubleshoot user connectivity (ZCC + ZDX + ZPA + ZIA) |

## Installation

### Option 1: From the Claude Code Marketplace

```bash
claude plugin install zscaler
```

### Option 2: From the repository

Clone the repository and add it as a local plugin:

```bash
git clone https://github.com/zscaler/zscaler-mcp-server.git
cd zscaler-mcp-server
claude plugin install .
```

### Option 3: Manual MCP configuration

When installed as a Claude Code plugin, the bundled `.mcp.json` resolves the env file relative to the plugin install directory using `${CLAUDE_PLUGIN_ROOT}` — no path editing required:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "${CLAUDE_PLUGIN_ROOT}/.env", "zscaler-mcp@0.10.3"]
    }
  }
}
```

If you are wiring the MCP server up **outside** the Claude Code plugin context (e.g. a standalone MCP client), replace `${CLAUDE_PLUGIN_ROOT}/.env` with an absolute path to your own `.env` file, since `${CLAUDE_PLUGIN_ROOT}` is only resolved by Claude Code at runtime.

Optionally, you can run the server via the published Docker image instead:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/absolute/path/to/.env",
        "zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [uv](https://docs.astral.sh/uv/) installed (provides the `uvx` runner used by the plugin's `.mcp.json`)
- Zscaler OneAPI credentials configured in `.env` (copy `.env.example` and fill in the values)
- Docker is **optional** — only required if you choose the Docker-based manual configuration above

## Configuration

The plugin manifest at `.claude-plugin/plugin.json` defines:

- **Name**: `zscaler`
- **MCP servers**: Configured via `.mcp.json`
- **Skills path**: `./skills/`
- **Commands path**: `./commands/` (slash commands)

The marketplace manifest at `.claude-plugin/marketplace.json` provides:

- **Version**: Current plugin version
- **Category**: Security
- **Owner**: Zscaler (`devrel@zscaler.com`)

## Verification

After installation, verify by asking Claude Code:

> "What Zscaler tools are available?"

or

> "List my ZPA application segments"

## Resources

- [Main README](../../README.md)
- [Supported Tools Reference](../../docs/guides/supported-tools.md)
- [Authentication & Deployment Guide](../../docs/deployment/authentication-and-deployment.md)
- [Troubleshooting](../../docs/guides/TROUBLESHOOTING.md)
