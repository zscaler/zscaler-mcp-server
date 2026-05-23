---
id: editor-integration
title: Editor Integration
sidebar_label: Editor Integration
sidebar_position: 3
---

# Editor / AI Assistant Integration

The Zscaler MCP Server works with any MCP-compatible client. Below are the canonical configurations for the most common ones.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS), `%APPDATA%\Claude\claude_desktop_config.json` (Windows), or `~/.config/Claude/claude_desktop_config.json` (Linux):

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

Restart Claude Desktop. The tools appear under **Search & Tools**.

See the [Claude integration](../integrations/claude) page for advanced configurations including the native Claude Code plugin (`claude plugin install zscaler`).

## Cursor

Add to `~/.cursor/mcp.json`:

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

Then **Cursor Settings → Tools & Integrations → enable `zscaler-mcp-server`**. Switch to Agent Mode in chat.

See [Cursor integration](../integrations/cursor) for the native plugin with guided skills.

## VS Code + GitHub Copilot

Add to your VS Code MCP configuration (Agent Mode):

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

Open Copilot Chat → switch to Agent Mode → refresh the tools list. See [VS Code integration](../integrations/vscode).

## Gemini CLI

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

See [Gemini CLI integration](../integrations/gemini-cli) for the contextual extension.

## Kiro IDE

Kiro discovers MCP servers from `.kiro/mcp.json`. See [Kiro integration](../integrations/kiro) for the per-service steering files.

## With service selection

To limit the loaded tools to specific services:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": [
        "--env-file", "/path/to/.env",
        "zscaler-mcp-server",
        "--services", "zia,zpa,zdx"
      ]
    }
  }
}
```

Or with a specific toolset slice:

```json
{
  "args": [
    "--env-file", "/path/to/.env",
    "zscaler-mcp-server",
    "--toolsets", "zia_url_filtering,zpa_app_segments"
  ]
}
```

See [Toolsets](../guides/toolsets) for the catalog.

## With Docker

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/full/path/to/.env",
        "zscaler/zscaler-mcp-server:latest"
      ]
    }
  }
}
```

## With individual environment variables

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["zscaler-mcp-server"],
      "env": {
        "ZSCALER_CLIENT_ID": "your-client-id",
        "ZSCALER_CLIENT_SECRET": "your-client-secret",
        "ZSCALER_CUSTOMER_ID": "your-customer-id",
        "ZSCALER_VANITY_DOMAIN": "your-vanity-domain"
      }
    }
  }
}
```

## Remote MCP server

Pointing a local editor at a remote (HTTP) MCP server is supported via the `mcp-remote` shim:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-mcp-host.example.com/mcp",
        "--header", "Authorization: Bearer ${MCP_API_KEY}"
      ],
      "env": {
        "MCP_API_KEY": "your-shared-secret"
      }
    }
  }
}
```

The exact header depends on the [auth mode](../security/mcp-client-auth) the remote server runs in.
