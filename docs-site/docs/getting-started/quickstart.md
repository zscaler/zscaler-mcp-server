---
id: quickstart
title: Quickstart
sidebar_label: Quickstart
sidebar_position: 4
---

# Quickstart

This guide gets you from zero to your first AI-driven Zscaler query in under five minutes.

## 1. Install

```bash
uv tool install zscaler-mcp-server
```

Or use `uvx` for an ephemeral install:

```bash
uvx zscaler-mcp-server --version
```

See [Installation](./installation) for other methods (Docker, source, pip).

## 2. Configure your credentials

Create a `.env` file:

```env
ZSCALER_CLIENT_ID=your_client_id
ZSCALER_CLIENT_SECRET=your_client_secret
ZSCALER_VANITY_DOMAIN=your_vanity_domain
ZSCALER_CUSTOMER_ID=your_customer_id
```

Don't have credentials yet? See [Authentication](./authentication) for how to create them in the Zidentity console.

## 3. Verify the server runs

```bash
zscaler-mcp --list-tools | head -30
```

You should see a list of every registered tool, grouped by service. If you don't, double-check your credentials and that the `.env` file is in your current working directory.

## 4. Wire it into your AI assistant

The simplest configuration uses `uvx` to run the server in an ephemeral environment.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on your platform:

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

Restart Claude Desktop. The Zscaler tools will appear under the **Search & Tools** menu.

### Cursor

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

Open **Cursor Settings → Tools & Integrations**, enable `zscaler-mcp-server`, then switch to Agent Mode in chat.

See [Editor integration](../usage/editor-integration) for VS Code, Gemini CLI, Kiro IDE, and other clients.

## 5. Run your first prompt

In your AI assistant, try:

```text
List my ZPA application segments
```

or

```text
Show me the top 10 ZIA URL filtering rules by priority
```

or

```text
What's the ZDX experience score for my San Francisco office over the last 24 hours?
```

:::tip Writing effective prompts
The server exposes 300+ tools. Most MCP clients use deferred tool loading — they search for the relevant tool based on your prompt. **Be specific about the service and action.**

- ✅ *"List my ZPA application segments"*
- ✅ *"Show ZIA firewall rules"*
- ❌ *"Show me my devices"* (ambiguous — multiple services expose device-related tools)
:::

## 6. (Optional) Enable write operations

By default the server is **read-only**. To enable creating/updating/deleting resources:

```bash
zscaler-mcp \
  --enable-write-tools \
  --write-tools "zpa_create_*,zpa_delete_*"
```

The `--write-tools` allowlist is **mandatory** — `--enable-write-tools` alone registers zero write tools. See [Write operations](../security/write-operations) for the complete safety model.

## Next steps

- [Configuration reference](./configuration) — every environment variable and CLI flag
- [Toolsets](../guides/toolsets) — load only the slice of tools you need
- [Services overview](../services/overview) — what each Zscaler service can do through the MCP server
- [Deployment](../deployment/docker) — Docker, Azure, GCP, AWS Bedrock
- [Troubleshooting](../guides/troubleshooting) — common issues and fixes
