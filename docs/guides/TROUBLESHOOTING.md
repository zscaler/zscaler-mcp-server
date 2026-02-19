# Troubleshooting

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

## Project-Specific Issues
