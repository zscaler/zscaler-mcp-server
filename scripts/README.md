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

#### Live reload (`.env` bind-mount)

By default the script **bind-mounts** the host `.env` at `/app/.env` inside
the container, in addition to passing it via `--env-file`. The `--env-file`
seeds `os.environ` at container boot; the bind-mount makes the file
re-readable from inside the container at runtime, so the lifecycle subcommands
(see "Reconfigure a running container" below) pick up edits you make on the
host without needing to recreate the container.

Pass `--legacy-env-file` to opt out. You'll typically want to opt out when:

- The `.env` was synthesized from prompts (the script auto-detects this and
  falls back automatically — temp files get deleted on script exit, which
  would orphan the bind mount).
- You don't want host-side edits to be visible inside the container.
- You want the strict snapshot-only behaviour for compliance reasons.

### Reconfigure a running container

The `zscaler-mcp` CLI inside the container exposes four lifecycle
subcommands. They work against the local PID file (`/var/run/zscaler-mcp.pid`
by default), so they only act on the server inside the container they're
exec'd into.

#### Important: env vars are only "live" when the .env is bind-mounted

Env vars passed via `--env-file` are read **once** by Docker at
`docker run` time and copied into the container's `Config.Env` metadata
(visible via `docker inspect`). After that moment, PID 1's `os.environ`
is fixed for the life of that container — `docker stop && docker start`
re-uses the same `Config.Env`, it does NOT re-read your host's `.env`.
There is no Unix API for one process to mutate another's environment, so
`docker exec ... sh -c 'export FOO=bar'` followed by reload/restart
silently does nothing — the `export` was in a child shell that exited.

The reload/restart subcommands work either way, but their behaviour
differs based on how the container was set up:

- **Bind-mounted `.env` (the default this script sets up):** `reload` /
  `restart` re-read the bind-mounted file from inside the container.
  Edit the file on the host → run `restart` → fresh values land in the
  new process. **This is what you want.**
- **`--env-file` only (the `--legacy-env-file` opt-out):** the host
  `.env` is not visible inside the container, so reload/restart can't
  re-read it. `restart` still re-execs Python in place, but the new
  process inherits the same baked-in env. To pick up env changes you
  have to either recreate the container OR use the `docker cp`
  workflow below.

`zscaler-mcp status` shows which mode you're in via the `env source`
field: `live (bind-mounted)` (best), `live` (real path, non-default
location), `fresh-discovery` (a `.env` was placed via `docker cp`
since startup — restart will pick it up), `missing` (recorded `.env`
path is gone and no `docker cp` happened), or `none` (no `.env` was
loaded at all — typical for cloud deploys using secret managers).

#### Three ways to update env vars in a running container

| | Recreates container? | Picks up env changes? | When to use |
|---|---|---|---|
| **A.** `docker rm -f && docker run --env-file=./.env ...` | Yes | Yes | Always works. Drops sessions, image cache cold. |
| **B.** Bind-mount `.env` (the script default), then `zscaler-mcp restart` after host edits | No (one-time setup) | Yes (every edit) | Recommended long-term workflow. |
| **C.** `docker cp ./.env <ctr>:/app/.env && docker exec <ctr> zscaler-mcp restart` | No | Yes (one-shot) | Easiest fix for an already-running `--legacy-env-file` container. No setup change required. |

Workflow **C** is the one you want if you originally ran with
`--legacy-env-file` and don't want to recreate the container just to
swap a credential — copy a fresh `.env` in, then restart. The fresh
Python interpreter re-discovers `/app/.env` on startup; `status` will
report it as `fresh-discovery` before the restart, and as
`live (bind-mounted)` after.

#### Workflow

```bash
# 1. Edit your .env on the host
$EDITOR .env

# 2. Reload (cheap — sessions survive, only re-reads .env + audit toggle)
docker exec zscaler-mcp-server zscaler-mcp reload

# OR Restart (drops sessions but picks up everything: rotated creds,
#             new toolset selection, new write-tools allowlist, etc.)
docker exec zscaler-mcp-server zscaler-mcp restart

# Inspect the running server (PID, uptime, transport, .env path,
# AND whether reload/restart will actually pick up env changes)
docker exec zscaler-mcp-server zscaler-mcp status

# Clean shutdown without respawn (same as `docker stop` but explicit)
docker exec zscaler-mcp-server zscaler-mcp stop
```

`reload` sends SIGHUP and re-reads the bind-mounted `.env` with `override=True`;
the listening socket and active MCP sessions survive. `restart` sends SIGUSR2
which re-reads `.env`, then `os.execvp`s a fresh Python interpreter with the
original argv — same PID (Docker doesn't notice the swap), fresh memory,
fresh env. Active sessions die and clients reconnect. SIGTERM/SIGINT remain
unhandled, so `docker stop` and Ctrl+C continue to behave normally.

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
