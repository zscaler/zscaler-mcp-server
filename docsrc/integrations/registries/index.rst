.. _registries:

Registries and Marketplaces
===========================

The Zscaler MCP Server is published to **five** public registries. Each registry has its own discovery surface and its own install flow — pick the one that matches the MCP client you're using.

.. toctree::
   :maxdepth: 1

   cursor-marketplace
   claude-marketplace
   official-mcp-registry
   docker-mcp-hub
   github-mcp-registry

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Registry
     - Best for
     - Install command
   * - :doc:`Cursor Marketplace <cursor-marketplace>`
     - Cursor IDE users
     - One-click "Add to Cursor" button
   * - :doc:`Claude Marketplace <claude-marketplace>`
     - Claude Code CLI users
     - ``claude plugin install zscaler``
   * - :doc:`Official MCP Registry <official-mcp-registry>`
     - Any spec-compliant MCP client
     - Discoverable via the official MCP registry
   * - :doc:`Docker MCP Hub <docker-mcp-hub>`
     - Containerized deployments (any client)
     - ``docker pull zscaler/zscaler-mcp-server``
   * - :doc:`GitHub MCP Registry <github-mcp-registry>`
     - GitHub Copilot users, MCP-compatible clients reading from GitHub
     - Surfaces via the ``server.json`` manifest at the repo root

Picking the right registry
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - You're using …
     - Pick …
     - Why
   * - Cursor IDE
     - :doc:`Cursor Marketplace <cursor-marketplace>`
     - Bundled Cursor plugin, one-click install
   * - Claude Code CLI
     - :doc:`Claude Marketplace <claude-marketplace>`
     - ``claude plugin install zscaler``, bundled skills
   * - Claude Desktop
     - :doc:`../../guides/claude-desktop-extension`
     - ``.mcpb`` bundle, no separate plugin install needed
   * - GitHub Copilot
     - :doc:`GitHub MCP Registry <github-mcp-registry>`
     - Native integration with the Copilot MCP picker
   * - VS Code / Gemini CLI / Kiro / other generic MCP clients
     - :doc:`Docker MCP Hub <docker-mcp-hub>` or PyPI directly
     - Universal — works with any MCP-compliant client
   * - A managed cloud deployment (Cloud Run, Bedrock, Container Apps)
     - :doc:`Docker MCP Hub <docker-mcp-hub>`
     - Pull the image, point your cloud runtime at it

See also
--------

- :doc:`../index` — the integrations overview, including IDE plugins.
- :doc:`../../guides/claude-desktop-extension` — the Claude Desktop Extension (``.mcpb``) install walkthrough.
- :ref:`claude-code-plugin` — Claude Code (CLI) plugin details.
- :ref:`cursor-plugin` — Cursor plugin details.
