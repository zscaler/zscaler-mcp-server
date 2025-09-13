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

## Project-Specific Issues
