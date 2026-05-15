# scripts/

End-user setup scripts for deploying the Zscaler MCP Server locally.

## `setup-mcp-server.py` — Interactive local deployment

Single entry point that prompts you through the whole local-deploy flow:
authentication mode → transport → credentials → image pull → container start →
agent configuration. No editing required, works on macOS, Linux, and Windows.

### Quick start

```bash
python3 scripts/setup-mcp-server.py
```

That's it. The script will:

1. Ask which **authentication mode** you want (`jwt`, `zscaler`, `api-key`, `oidcproxy`, or `none`).
2. Ask which **transport** to use (`streamable-http` or `stdio`).
3. Ask for the path to your **`.env` file** — or let you enter credentials interactively.
4. **Pull `zscaler/zscaler-mcp-server:latest`** from Docker Hub.
5. **Start the container** with the right entrypoint and env wiring for the chosen mode.
6. **Verify the endpoint** responds (HTTP modes only).
7. **Detect installed AI agents** (Claude Desktop, Claude Code, Cursor, Gemini CLI, VS Code, Windsurf, Copilot CLI) and offer to configure each one for you.

### Supported authentication modes

| Mode | What it is | Client sends | Image override |
|---|---|---|---|
| `jwt` | OAuth 2.0 client_credentials against an external IdP (Auth0). Server validates via JWKS. | `Authorization: Bearer <jwt>` | None |
| `zscaler` | Server validates the request's Zscaler OneAPI credentials against `/oauth2/v1/token` (cached). | `Authorization: Basic base64(client_id:client_secret)` | None |
| `api-key` | Static shared secret. Simplest to set up, weakest model. | `Authorization: Bearer <api-key>` | None |
| `oidcproxy` | Full OAuth 2.1 + Dynamic Client Registration via FastMCP's `OIDCProxy`. The MCP client (e.g. mcp-remote) discovers `/.well-known/...` and runs the browser flow. | (none — handled by mcp-remote) | **Yes** — entrypoint replaced with inline Python |
| `none` | No authentication. Single-user local development only. | (nothing) | None |

### Supported transports

| Transport | When to use | Compatible auth modes |
|---|---|---|
| `streamable-http` | The container runs as a long-lived HTTP server. Most flexible. | All modes |
| `stdio` | The AI agent spawns the container per session via `docker run -i`. | `none` only |

`stdio` + any HTTP-bound auth mode (`jwt` / `zscaler` / `api-key` / `oidcproxy`) is **rejected** at the prompt — there's no HTTP boundary for the auth middleware to enforce when the agent is talking to the container's stdio directly.

### Common invocations

Fully interactive (recommended for first run):

```bash
python3 scripts/setup-mcp-server.py
```

Skip prompts when you already know the mode (great for re-runs / CI):

```bash
python3 scripts/setup-mcp-server.py \
  --auth-mode zscaler \
  --transport streamable-http \
  --env-file .env
```

Refresh a JWT without rebuilding anything:

```bash
python3 scripts/setup-mcp-server.py \
  --auth-mode jwt \
  --transport streamable-http \
  --env-file .env \
  --skip-pull
```

Test the configuration without touching any AI agent configs:

```bash
python3 scripts/setup-mcp-server.py --skip-agent-config
```

Test agent wiring without starting a fresh container:

```bash
python3 scripts/setup-mcp-server.py --skip-pull --skip-verify
```

### Environment file

The script accepts any `.env` file with `KEY=value` lines. The interactive
flow defaults to `./.env` then `<repo>/.env`, but you can point at any path.
`#` and `;` comments are tolerated, as is `export FOO=bar` shell syntax — the
script writes a sanitized copy for `docker --env-file` since Docker's parser
is much stricter than typical `.env` loaders.

If you don't have a `.env` and don't want to make one, the script prompts for
each required value interactively and writes a temporary `.env` (deleted on
exit).

### What gets written to your AI agents

Each detected agent gets an `mcpServers` entry (or `servers` for VS Code)
called `zscaler-mcp-server`. Existing entries with that name are overwritten;
nothing else in the config is touched. Re-running the script with a different
auth mode safely replaces the previous entry.

| Agent | Config path (macOS) |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code (CLI) | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| VS Code | `~/Library/Application Support/Code/User/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| GitHub Copilot CLI | `~/Library/Application Support/github-copilot/mcp.json` |

Windows and Linux paths follow each agent's standard locations.

### Restart your AI agent

After the script finishes, **restart any AI agent it configured** (or, in the
case of Claude Code / CLI agents, just open a fresh shell). Most agents only
read MCP config at startup.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `Docker is not installed` | Install Docker Desktop: <https://docs.docker.com/get-docker/> |
| `docker pull` fails | Check network access to Docker Hub. Use `--skip-pull` if you've cached the image. |
| `Endpoint returned 401` | Credentials don't match what the server expects. Re-check the `.env` and re-run. |
| `Could not reach localhost:8000` | Container failed to stay running. Inspect: `docker logs zscaler-mcp-server` |
| Agent doesn't see the server after restart | Confirm the agent reads from the path the script printed. Some agents (VS Code) need an MCP-aware extension installed. |

### Re-running

The script is idempotent. Re-run anytime to:

- Switch auth modes
- Refresh a JWT
- Pick up a new image from Docker Hub
- Add a newly-installed AI agent to the configured set

Each re-run stops the old container, starts a fresh one, and rewrites the
`zscaler-mcp-server` entry in every agent config.

---

## Other scripts

`validate-template.mjs` — JSON schema validation helper for plugin templates
(unrelated to the deployment flow above).
