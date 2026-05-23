# Claude

The Zscaler MCP Server ships in two flavours for Anthropic's Claude family of products:

| Integration | Surface | Best for |
|-------------|---------|----------|
| **Claude Code Plugin** | [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI | Terminal-driven workflows, IDE integrations, and the 19 bundled multi-step skills |
| **Claude Desktop Extension** | Claude Desktop app (Directory of Connectors) | Point-and-click install from the Desktop app's built-in Directory, no shell required |

Pick whichever matches the Claude product you already use — both expose the same Zscaler tool surface and read the same OneAPI credentials.

---

## Claude Code Plugin

The Zscaler MCP Server is available as a native **Claude Code Plugin**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

### What's Included

| Component | Location | Purpose |
|-----------|----------|---------|
| Plugin manifest | `.claude-plugin/plugin.json` | Plugin metadata, MCP entry point, skills, and slash commands |
| Marketplace manifest | `.claude-plugin/marketplace.json` | Claude Code marketplace listing and versioning |
| Skills | `skills/` | 19 guided multi-step workflows for common Zscaler operations |
| MCP config | `.mcp.json` | MCP server connection configuration |

#### Skills (19 guided workflows)

The plugin bundles service-specific skills that Claude auto-activates based on your prompt:

| Service | Skills | Examples |
|---------|--------|----------|
| **ZPA** | 6 | Onboard application, create access/forwarding/timeout policy rules, create server group, troubleshoot connector |
| **ZIA** | 5 | Onboard location, audit SSL inspection, investigate URL category, check user access, investigate sandbox |
| **ZDX** | 5 | Troubleshoot user experience, analyze app health, investigate alerts, diagnose deep trace, audit software |
| **EASM** | 1 | Review attack surface |
| **Z-Insights** | 1 | Investigate security incident |
| **Cross-product** | 1 | Troubleshoot user connectivity (ZCC + ZDX + ZPA + ZIA) |

### Installation

#### Option 1: From the Claude Code Marketplace

```bash
claude plugin install zscaler
```

#### Option 2: From the repository

Clone the repository and add it as a local plugin:

```bash
git clone https://github.com/zscaler/zscaler-mcp-server.git
cd zscaler-mcp-server
claude plugin install .
```

#### Option 3: Manual MCP configuration

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

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [uv](https://docs.astral.sh/uv/) installed (provides the `uvx` runner used by the plugin's `.mcp.json`)
- Zscaler OneAPI credentials configured in `.env` (copy `.env.example` and fill in the values)
- Docker is **optional** — only required if you choose the Docker-based manual configuration above

### Configuration

The plugin manifest at `.claude-plugin/plugin.json` defines:

- **Name**: `zscaler`
- **MCP servers**: Configured via `.mcp.json`
- **Skills path**: `./skills/`
- **Commands path**: `./commands/` (slash commands)

The marketplace manifest at `.claude-plugin/marketplace.json` provides:

- **Version**: Current plugin version
- **Category**: Security
- **Owner**: Zscaler (`devrel@zscaler.com`)

### Verification

After installation, verify by asking Claude Code:

> "What Zscaler tools are available?"

or

> "List my ZPA application segments"

---

## Claude Desktop Extension

The Zscaler MCP Server is also published as a **Claude Desktop Extension** — a single-file `.mcpb` bundle installed directly from Claude Desktop's built-in Directory of Connectors. Once enabled, every read-only Zscaler tool becomes available to your Claude Desktop conversations with no shell, no `.env` file, and no manual MCP configuration.

### Requirements

Claude Desktop runs its own pre-flight check (the **"All requirements met"** banner on the extension's detail page) before allowing the install. The extension needs:

- **Claude Desktop** — the desktop application, not the Claude Code CLI
- **Python ≥ 3.11** — the bundled MCP server runs as a Python process
- **[uv](https://docs.astral.sh/uv/) on your `PATH`** — Claude Desktop launches the server with `uv run python -m zscaler_mcp.server` as declared in the bundle's `manifest.json`. If `uv` cannot be found, the Requirements check fails and the **Install** button stays disabled. (If you don't have a 3.11+ interpreter handy, `uv` can install one for you via `uv python install`.)
- **Zscaler OneAPI credentials** — `client_id`, `client_secret`, `customer_id`, `vanity_domain`. Supplied through the extension's configuration form after install; no `.env` file is needed.

The "fetch a few dependencies" dialog Claude Desktop shows during install is `uv` resolving the Python packages declared in the bundle's `pyproject.toml`. First install may take a minute or two depending on network speed; subsequent launches reuse the cached environment and start in seconds.

### Installation walkthrough

#### Step 1 — Find the extension in the Directory

Open Claude Desktop → **Directory** → **Connectors** and search for `zscaler`:

![Directory search for Zscaler MCP Server](/img/claude-extension-install01.png)

#### Step 2 — Review the extension details

Click the result to open the detail view. You'll see the full description, the live tool count, the Zscaler-developed badge, and — once `uv` is detected on your system — the green **"All requirements met"** banner that enables the **Install** button:

![Zscaler MCP Server extension details with All requirements met](/img/claude-extension-install02.png)

#### Step 3 — Confirm the install

Click **Install**. Claude Desktop asks for confirmation and notes that it will fetch the Python dependencies declared in the bundle:

![Install confirmation dialog](/img/claude-extension-install03.png)

#### Step 4 — Verify the extension is enabled

When the install completes, the detail view updates to show the **Enabled** toggle and a **Configure** button. The extension is now installed but not yet usable — it has no credentials:

![Extension enabled, with Configure button](/img/claude-extension-install04.png)

#### Step 5 — Configure your Zscaler credentials

Click **Configure** to open the credential form. Fill in your OneAPI values:

![Configuration form with Zscaler credential fields](/img/claude-extension-install05.png)

| Field | Purpose |
|-------|---------|
| `ZSCALER_CLIENT_ID` | OneAPI client ID from the ZIdentity console |
| `ZSCALER_CLIENT_SECRET` | OneAPI client secret |
| `ZSCALER_CUSTOMER_ID` | Zscaler customer / tenant ID (required for ZPA tools) |
| `ZSCALER_VANITY_DOMAIN` | ZIdentity vanity domain (e.g. `acme.zsapi.net`) |
| `ZSCALER_CLOUD` | Cloud override; leave `production` unless you're on a non-prod cloud |
| **Enabled Tools** | Optional comma-separated allowlist; leave empty to expose every read-only tool the server registers |
| **User-Agent comment** | Optional suffix appended to outbound API calls' `User-Agent` header — useful for tagging traffic in audit logs |

Click **Save**. The extension is now wired up and Claude Desktop can invoke any read-only Zscaler tool from the chat interface.

### Verification

In a new Claude Desktop conversation, ask:

> "What Zscaler tools are available?"

Claude responds with the toolsets loaded for the OneAPI credentials you configured. You can also try a concrete query such as *"list my ZPA application segments"* — Claude prompts you to approve the tool call (the per-tool approval is part of Claude Desktop's built-in safety surface), then returns the result.

### Building the bundle locally

If you want to install a custom build (for example a development branch or a private fork), run:

```bash
make build-mcpb
```

from the repo root. This refreshes the manifest, packs every runtime file into `zscaler-mcp-server-<VERSION>.mcpb`, and writes the single bundle to the repo root. Drag that file into Claude Desktop's **Settings → Developer → Install Extension** to install it locally without going through the Directory.

The bundle pulls all its dependencies via `uv` at install time, so it stays under 500 KB on disk and the lock files inside it pin every Python package to a reproducible version.

### Write tools

By default the Desktop Extension exposes only read-only tools. To enable create / update / delete operations, set the **Enable Write Tools** toggle in the configuration form (or its underlying `ZSCALER_MCP_WRITE_ENABLED=true` env var) and populate the **Write Tools Allowlist** with the patterns you want to permit (e.g. `zpa_create_*,zia_update_url_filtering_*`). Destructive operations still require an in-session HMAC confirmation token — Claude is prompted to confirm before the tool actually executes.

---

## Resources

- [Main README](../../README.md)
- [Supported Tools Reference](../../docs/guides/supported-tools.md)
- [Authentication & Deployment Guide](../../docs/deployment/authentication-and-deployment.md)
- [Troubleshooting](../../docs/guides/TROUBLESHOOTING.md)
