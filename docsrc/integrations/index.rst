.. _platform-integrations:

Integrations
============

The Zscaler MCP Server ships with native integrations for every major MCP-aware AI development platform, plus listings in every public MCP registry. Each integration includes platform-specific configuration files, the bundled :doc:`42 guided skills <../skills/index>`, and setup instructions.

Pick a category below — every platform within each tree has its own dedicated page.

.. note::

   This page covers **MCP clients** (Claude / Cursor / Gemini / Kiro / VS Code) and **registries** (Cursor / Claude / Official MCP / Docker / GitHub). Cloud-platform deployments (AWS Bedrock, Azure Container Apps, GCP Cloud Run, Kubernetes Helm) live under :doc:`Deployment <../deployment/index>` instead — one branch per hyperscaler.

.. toctree::
   :maxdepth: 2
   :caption: MCP Clients

   mcp-clients/index

.. toctree::
   :maxdepth: 2
   :caption: Registries and Marketplaces

   registries/index

At a glance
-----------

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Platform
     - Type
     - Page
   * - **Claude**
     - Plugin + Desktop Extension
     - :doc:`mcp-clients/claude`
   * - **Cursor**
     - Plugin (also on `Cursor Marketplace <https://cursor.com/marketplace/zscaler>`__)
     - :doc:`mcp-clients/cursor`
   * - **Gemini CLI**
     - Extension
     - :doc:`mcp-clients/gemini-cli`
   * - **Kiro IDE**
     - Power
     - :doc:`mcp-clients/kiro`
   * - **VS Code**
     - GitHub Copilot Agent Mode
     - :doc:`mcp-clients/vscode`
   * - **Cursor Marketplace**
     - Public registry
     - :doc:`registries/cursor-marketplace`
   * - **Claude Marketplace**
     - Public registry
     - :doc:`registries/claude-marketplace`
   * - **Official MCP Registry**
     - Public registry
     - :doc:`registries/official-mcp-registry`
   * - **Docker MCP Hub**
     - Public registry
     - :doc:`registries/docker-mcp-hub`
   * - **GitHub MCP Registry**
     - Public registry + Copilot
     - :doc:`registries/github-mcp-registry`

Cloud deployment integrations (AWS Bedrock AgentCore, Strands client, AWS Harness, Azure Container Apps / VM / AKS, Azure AI Foundry, GCP Cloud Run / GKE / VM, Google ADK Agent, Kubernetes Helm chart) live under :doc:`../guides/index` — each cloud has its own tree.

Verification
------------

After installing any integration, verify by asking your AI client:

   *"What Zscaler tools are available?"*

or

   *"List my ZPA application segments"*

Shared components
-----------------

All integrations leverage common resources from the repository root:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Component
     - Location
     - Purpose
   * - Skills
     - ``skills/``
     - 42 guided multi-step workflows
   * - MCP Server
     - ``zscaler_mcp/``
     - The MCP server implementation (300+ tools)
   * - Docs
     - ``docs/`` and ``docsrc/``
     - Deployment guides, tool references, troubleshooting
