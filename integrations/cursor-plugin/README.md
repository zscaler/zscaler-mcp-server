# Cursor Plugin Integration

The Zscaler MCP Server is available as a native **Cursor Plugin**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within [Cursor](https://cursor.so/).

## What's Included

| Component | Location | Purpose |
|-----------|----------|---------|
| Plugin manifest | `.cursor-plugin/plugin.json` | Plugin metadata, version, and entry points |
| Skills | `skills/` | 19 guided multi-step workflows for common Zscaler operations |
| MCP config | `mcp.json` | MCP server connection configuration |

### Skills (19 guided workflows)

The plugin bundles service-specific skills that Cursor auto-activates based on your prompt:

| Service | Skills | Examples |
|---------|--------|----------|
| **ZPA** | 6 | Onboard application, create access/forwarding/timeout policy rules, create server group, troubleshoot connector |
| **ZIA** | 5 | Onboard location, audit SSL inspection, investigate URL category, check user access, investigate sandbox |
| **ZDX** | 5 | Troubleshoot user experience, analyze app health, investigate alerts, diagnose deep trace, audit software |
| **EASM** | 1 | Review attack surface |
| **Z-Insights** | 1 | Investigate security incident |
| **Cross-product** | 1 | Troubleshoot user connectivity (ZCC + ZDX + ZPA + ZIA) |

## Installation

### Option 1: Cursor Settings UI

1. Open Cursor
2. Go to **Settings** → **Cursor Settings** → **Tools & MCP** → **New MCP Server**
3. Add the following configuration:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
    }
  }
}
```

### Option 2: Edit `mcp.json` directly

Add to `~/.cursor/mcp.json` (macOS/Linux) or `%USERPROFILE%\.cursor\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
    }
  }
}
```

### Option 3: Docker

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/absolute/path/to/.env",
        "quay.io/zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

## Prerequisites

- [Cursor](https://cursor.so/) installed
- [uv](https://docs.astral.sh/uv/) installed (for `uvx` method) or Docker
- Zscaler OneAPI credentials configured in `.env`

## Configuration

The plugin manifest at `.cursor-plugin/plugin.json` defines:

- **Name**: `zscaler`
- **Category**: Security
- **Skills path**: `./skills/`
- **MCP config**: `./mcp.json`

## Verification

After installation, verify by asking Cursor:

> "What Zscaler tools are available?"

or

> "List my ZPA application segments"

## Resources

- [Main README](../../README.md)
- [Supported Tools Reference](../../docs/guides/supported-tools.md)
- [Authentication & Deployment Guide](../../docs/deployment/authentication-and-deployment.md)
- [Troubleshooting](../../docs/guides/TROUBLESHOOTING.md)
