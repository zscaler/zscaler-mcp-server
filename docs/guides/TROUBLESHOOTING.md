# Troubleshooting

## Remote MCP (421 Misdirected Request)

When connecting to a **remote** MCP server (EC2, VM) from Claude Desktop or another client, you may see `421 Misdirected Request` or "Invalid Host header" in the server logs.

**Common causes:**

1. **Wrong virtualenv** — With `uv pip install -e .`, activate the project venv before starting: `source .venv/bin/activate`
2. **Host binding** — Use `--host 0.0.0.0` when exposing the server; this auto-disables Host header validation
3. **Client needs adapter** — For remote HTTP, configure an adapter (e.g. `@pyroprompts/mcp-stdio-to-streamable-http-adapter`) and ensure Node.js is installed for `npx`

**Full details:** [Authentication & Deployment Guide — Remote Deployment](../deployment/authentication-and-deployment.md#remote-deployment-ec2-vm-etc) and [421 Misdirected Request](../deployment/authentication-and-deployment.md#421-misdirected-request-invalid-host-header)

---

## Common MCP Issues

1. **Clearing VS Code Cache**

   If you encounter issues with stale configurations, reload the VS Code window:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS).
   - Select `Developer: Reload Window`.

2. **Server Not Showing Up in Agent Mode**
   Ensure that the `mcp.json` file is correctly configured and includes the appropriate server definitions. Restart your MCP server and reload the VS Code window.

3. **Tools Not Loading in Agent Mode**
   If tools are not appearing, click "Add Context" in Agent Mode and ensure all tools starting with `zcc_`, `zdx_`, `zia_`, `zpa_`, `ztw_`, `zid_`are selected.

---

## A specific tool isn't loaded

If the agent reports a tool isn't available, walk down this list in order — each item rules out one filter the server applies at startup. Every filter applies on **every transport** (`stdio`, `sse`, `streamable-http`).

1. **Was the service explicitly disabled?** Check `--disabled-services` / `ZSCALER_MCP_DISABLED_SERVICES`. A service in this list contributes zero tools.
2. **Was the tool's pattern explicitly disabled?** Check `--disabled-tools` / `ZSCALER_MCP_DISABLED_TOOLS`. This list supports wildcards (e.g. `zcc_*`) and wins over every other filter.
3. **Is it a write tool with no allowlist?** Write tools (`*_create_*`, `*_update_*`, `*_delete_*`) require both `--enable-write-tools` AND a matching pattern in `--write-tools`. With write mode disabled (the default), no write tool is registered.
4. **Was the tool's toolset filtered out?** Check the startup logs for the active selection. If you set `--toolsets` (or `ZSCALER_MCP_TOOLSETS`), only tools that belong to a listed toolset are registered. Call `zscaler_list_toolsets` from your client to see what's currently active and what's available.
5. **Did the OneAPI entitlement filter drop the tool's product?** Look for a startup log line of the form `entitlement filter applied: entitled services=[...], kept N toolset(s), removed M toolset(s)`. If the product (e.g. ZDX) isn't in the entitled list, every toolset for that product was filtered out. Either grant the OneAPI client the missing product entitlement in ZIdentity, or — for a quick diagnostic — restart the server with `--no-entitlement-filter` to confirm the filter is the cause. If you see a `entitlement filter skipped (...)` warning instead, the filter never ran (missing creds, network failure, undecodable token); the tool list is whatever your other filters produced.
6. **Did the tool resolve to a toolset at all?** The very first time you load a tool you wrote that hasn't been mapped, you'll see a one-line WARNING in the startup logs (`unmapped tool name: ...`). That tool will not register until it's mapped to a toolset; this is a developer-side issue. See [docs/guides/toolsets.md](toolsets.md#for-developers--adding-a-new-toolset).

If the agent reports a tool that genuinely doesn't exist (typo, hallucination), `zscaler_list_toolsets` and `zscaler_get_available_services` are the right introspection tools to call. Use `name_contains` / `description_contains` on `zscaler_list_toolsets` to scope the search to a single area before drilling in with `zscaler_get_toolset_tools`.

---

## How do I see what the entitlement filter dropped?

The OneAPI entitlement filter logs one INFO line at startup with the result, for example:

```text
entitlement filter applied: entitled services=['zia', 'zpa'], kept 12 toolset(s), removed 17 toolset(s)
```

To see which specific toolsets were removed, the easiest method is to compare two startup runs:

1. Start the server normally and call `zscaler_list_toolsets` — note which toolsets show as currently enabled.
2. Restart with `--no-entitlement-filter` (or set `ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true`), call `zscaler_list_toolsets` again — anything new is what the filter was hiding.

If you instead see a `WARN entitlement filter skipped (...)` line, the filter never ran — and the parenthesized reason tells you why (missing OneAPI credentials, the ZIdentity token endpoint was unreachable, the token didn't decode, or the token had no recognizable product entitlements). Your tool list in that case is whatever your `--toolsets` / disabled-tools / write-tools settings produced; nothing extra was filtered.

---

## Windows: Claude Desktop Extension Fails to Start

### Symptom

```text
ModuleNotFoundError: No module named 'rpds.rpds'
```

Or similar errors involving `pydantic_core`, `orjson`, `cryptography`, `cffi`, or other packages with `.cpython-*-darwin.so` binaries.

### Root Cause

The Claude Desktop extension (installed via **Settings → Extensions → Browse Extensions**) bundles pre-compiled Python packages. That bundle is built for macOS/Linux and includes `.so` / `.dylib` binaries. Windows requires `.pyd` binaries, so those packages cannot load.

**Affected packages** (examples): `rpds-py`, `pydantic-core`, `orjson`, `cryptography`, `cffi`, `jiter`, `charset-normalizer`, `markupsafe`, `pyyaml`, `websockets`, `zstandard`, and others with compiled extensions.

### Recommended Fix: Use Manual Configuration (Option 2)

On **Windows**, use **Manual Configuration** instead of the one-click extension. This runs the server via `uvx`, which installs platform-appropriate wheels at runtime.

1. Open Claude Desktop
2. Go to **Settings** → **Developer** → **Edit Config**
3. Add (adjust the path for your `.env` file):

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "uvx",
      "args": ["--env-file", "C:\\path\\to\\your\\.env", "zscaler-mcp"]
    }
  }
}
```

1. Save and restart Claude Desktop.

### If You Already Installed the Extension

If you installed the extension and it fails, you can either:

**A) Switch to manual configuration** (recommended): Remove the extension from Claude Desktop, then add the manual config above.

**B) Apply the workaround script** (if you must keep using the extension): See [GitHub issue #25](https://github.com/zscaler/zscaler-mcp-server/issues/25) and the community fix script at [Galtman117/claude-mcp-windows-fixes](https://github.com/Galtman117/claude-mcp-windows-fixes). This disables the bundled packages and installs Windows-native versions via pip.

### Summary

| Installation method | Windows support |
|---------------------|-----------------|
| **Manual config** (`uvx zscaler-mcp`) | ✅ Recommended |
| **Extension** (one-click install)      | ❌ Bundled macOS/Linux binaries; use manual config instead |
| **Docker**                             | ✅ Works (Linux container) |
| **VS Code / Cursor** (`uvx`)           | ✅ Works |

## mcp-remote: Non-HTTPS URL Rejected

### Symptom

```text
Error: Non-HTTPS URLs are only allowed for localhost or when --allow-http flag is provided
```

### Root Cause

`mcp-remote` enforces HTTPS for all non-localhost URLs by default. When connecting to a remote server using plain HTTP (e.g., `http://34.201.19.115:8000/mcp`), this security check blocks the connection.

### Fix

Add `"--allow-http"` to the `args` array in your Claude Desktop configuration, **before** `"--header"`:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "http://YOUR_SERVER_IP:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ]
    }
  }
}
```

On Windows, use `"command": "cmd"` with `"args": ["/c", "npx", ...]`. See [Windows: npx path with spaces](#windows-npx-path-with-spaces) below.

When the server uses HTTPS (with TLS certificates configured), you don't need `--allow-http` — use `https://` in the URL instead.

---

## Windows: npx Path with Spaces

### Symptom

```text
'C:\Program' is not recognized as an internal or external command
```

### Root Cause

Node.js is commonly installed to `C:\Program Files\nodejs\`. When Claude Desktop invokes `npx` directly, Windows splits the path on the space character and tries to execute `C:\Program`, which fails.

### Fix

Use `cmd` as the command and pass `npx` through `/c`:

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
        "http://YOUR_SERVER_IP:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ]
    }
  }
}
```

This applies to all Windows configurations that use `npx`, regardless of the authentication mode.

---

## Self-Signed Certificate Rejected by mcp-remote

### Symptom

```text
Error: self-signed certificate
code: 'DEPTH_ZERO_SELF_SIGNED_CERT'
```

### Root Cause

When the MCP server is configured with a self-signed TLS certificate (`ZSCALER_MCP_TLS_CERTFILE` / `ZSCALER_MCP_TLS_KEYFILE`), Node.js (used by `mcp-remote`) rejects the connection because the certificate chain cannot be verified against any trusted CA.

### Fix

Add `NODE_TLS_REJECT_UNAUTHORIZED=0` to the `env` section of your client configuration:

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://YOUR_SERVER_IP:8000/mcp",
        "--header",
        "Authorization: Bearer sk-your-api-key"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

> **Warning**: This disables all TLS certificate verification for this process. Only use for development and testing. For production, use CA-signed certificates.

---

## Plaintext Secrets Warning in Server Logs

### Symptom

Server logs show:

```text
SECURITY WARNING: .env file contains plaintext secrets. Consider using a secrets manager.
```

### Root Cause

The server automatically scans `.env` files for plaintext secrets (values containing patterns like `SECRET`, `PASSWORD`, `KEY`, or `TOKEN`). This warning is informational — the server still starts normally.

### Recommendations

- Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.) for production deployments.
- Set credentials as environment variables instead of storing them in `.env` files.
- If using `.env` files, ensure they are excluded from version control (`.gitignore`).

---

## Updating the Server

### How do I know a new version is out?

Run the built-in version check from any machine where the CLI is installed (or via `docker exec` against a running container):

```bash
zscaler-mcp update
```

It queries GitHub Releases (falling back to PyPI if GitHub is unreachable) and reports the installed version, the latest release, the detected install channel, and the correct upgrade instruction for that channel:

```text
zscaler-mcp update check
========================================
  installed       : 0.12.6
  latest          : 0.13.0
  install channel : venv
  release notes   : https://github.com/zscaler/zscaler-mcp-server/releases/tag/v0.13.0
Update available: 0.12.6 -> 0.13.0
  how to update   : run `zscaler-mcp update --apply` to upgrade in place and restart.
```

The check is read-only and changes nothing. It exits non-zero only when neither GitHub nor PyPI is reachable (e.g. no network egress).

### Updating a pip/venv install (systemd VM, local install)

This is the one channel where the server can update itself in place:

```bash
zscaler-mcp update --apply
```

What it does, in order:

1. Pin-upgrades the package (`pip install --upgrade zscaler-mcp==<latest>`) in the **running server's** interpreter environment — resolved from the PID file, so it targets the right venv even when the CLI is invoked from outside it. When no server is running, it upgrades the CLI's own environment.
2. Verifies the install by importing the package version in a fresh interpreter. On a pip failure or a verification mismatch it prints the exact rollback command (`pip install zscaler-mcp==<previous>`) and exits non-zero without touching the running server.
3. Sends SIGUSR2 to the running server, which re-execs itself in place (same PID) and re-imports the freshly upgraded code. If no server is running, it reminds you to restart your service (e.g. `systemctl restart zscaler-mcp`).

The upgrade always runs in the CLI process, never inside the server — the server process is never asked to modify its own loaded packages.

To keep a VM permanently current, put `zscaler-mcp update --apply` in a cron job or systemd timer. Deployments that prefer controlled change windows simply run it manually instead.

### Updating a container (Docker, Kubernetes, Cloud Run, Container Apps)

`--apply` deliberately refuses inside a container (exit 2): the image is the source of truth, and an in-place change would be silently lost on the next recreate, pod reschedule, or scale event. (The shipped image's uv-built venv contains no pip, so an in-place install would not work anyway.) Update by pulling the new image tag and recreating:

```bash
docker pull zscaler/zscaler-mcp-server:<latest>
docker rm -f zscaler-mcp-server
docker run -d --name zscaler-mcp-server ... zscaler/zscaler-mcp-server:<latest>
```

or for Helm/Kubernetes:

```bash
helm upgrade <release> ... --set image.tag=<latest>
```

Each release publishes immutable and rolling semver tags (`X.Y.Z`, `X.Y`), so standard ecosystem tooling (Renovate, Dependabot, Flux image automation, Watchtower) can track releases automatically if you want unattended container updates.

### Updating a uvx install

Nothing to do in most cases — `uvx zscaler-mcp` re-resolves from PyPI, so a fresh client session already picks up the new version. For a persistent uv tool install, run `uv tool upgrade zscaler-mcp`.

---

## Project-Specific Issues
