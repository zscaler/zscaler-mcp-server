.. _mcp-clients:

MCP Clients
===========

The Zscaler MCP Server runs inside every major MCP-aware AI client. Pick your client below for platform-specific install instructions, prerequisites, and walkthroughs.

.. toctree::
   :maxdepth: 1

   claude
   cursor
   gemini-cli
   kiro
   vscode

At-a-glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Client
     - Type
     - Install entry point
   * - :doc:`Claude <claude>`
     - Plugin + Extension
     - ``claude plugin install zscaler`` (Code) · Drag-and-drop ``.mcpb`` (Desktop)
   * - :doc:`Cursor <cursor>`
     - Plugin
     - Settings → Tools & MCP → New MCP Server
   * - :doc:`Gemini CLI <gemini-cli>`
     - Extension
     - Register ``gemini-extension.json``
   * - :doc:`Kiro IDE <kiro>`
     - Power
     - Powers panel → Add Custom Power
   * - :doc:`VS Code <vscode>`
     - GitHub Copilot Agent Mode
     - Add to ``mcpServers`` config

All clients share the same MCP server, tools, and skills — they differ only in how they connect the AI platform to the server.
