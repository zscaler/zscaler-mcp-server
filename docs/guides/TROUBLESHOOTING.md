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
   If tools are not appearing, click "Add Context" in Agent Mode and ensure all tools starting with `zcc_`, `zdx_`, `zia_`, `zpa_`, `ztw_`, `zidentity_`are selected.

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

## Project-Specific Issues
