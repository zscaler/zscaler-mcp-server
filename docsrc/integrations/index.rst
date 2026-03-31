.. _platform-integrations:

Platform Integrations
=====================

The Zscaler MCP Server ships with native integrations for several AI development platforms. Each integration includes platform-specific configuration files, 19 guided skills, and setup instructions.

.. list-table:: Available Integrations
   :header-rows: 1
   :widths: 15 15 35 35

   * - Platform
     - Type
     - Quick Start
     - Details
   * - **Claude Code**
     - Plugin
     - ``claude plugin install zscaler``
     - `integrations/claude-code-plugin/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/claude-code-plugin>`__
   * - **Cursor**
     - Plugin
     - Settings → Tools & MCP → New MCP Server
     - `integrations/cursor-plugin/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/cursor-plugin>`__
   * - **Gemini CLI**
     - Extension
     - Register ``gemini-extension.json``
     - `integrations/gemini-extension/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/gemini-extension>`__
   * - **Kiro IDE**
     - Power
     - Powers panel → Add Custom Power
     - `integrations/kiro/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/kiro>`__
   * - **Google ADK**
     - Agent
     - ``adk run zscaler_agent``
     - `integrations/adk/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/adk>`__

All integrations share the same MCP server, tools, and skills — they differ only in how they connect the AI platform to the server.

.. _claude-code-plugin:

Claude Code Plugin
------------------

The Zscaler MCP Server is available as a native **Claude Code Plugin**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within `Claude Code <https://docs.anthropic.com/en/docs/claude-code>`__.

**What's Included:**

- Plugin manifest (``.claude-plugin/plugin.json``) — Plugin metadata, MCP entry point, skills, and slash commands
- Marketplace manifest (``.claude-plugin/marketplace.json``) — Claude Code marketplace listing and versioning
- Skills (``skills/``) — 19 guided multi-step workflows for common Zscaler operations
- MCP config (``.mcp.json``) — MCP server connection configuration

**Installation:**

.. code-block:: bash

   # From the Claude Code marketplace
   claude plugin install zscaler

   # Or from a local clone
   git clone https://github.com/zscaler/zscaler-mcp-server.git
   cd zscaler-mcp-server
   claude plugin install .

**Manual MCP configuration:**

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
       }
     }
   }

.. _cursor-plugin:

Cursor Plugin
-------------

The Zscaler MCP Server is available as a native **Cursor Plugin** with 19 guided skills for ZPA, ZIA, ZDX, EASM, Z-Insights, and cross-product workflows.

**What's Included:**

- Plugin manifest (``.cursor-plugin/plugin.json``) — Plugin metadata, version, and entry points
- Skills (``skills/``) — 19 guided multi-step workflows
- MCP config (``mcp.json``) — MCP server connection configuration

**Installation:**

1. Open Cursor
2. Go to **Settings** → **Cursor Settings** → **Tools & MCP** → **New MCP Server**
3. Add the configuration:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
       }
     }
   }

Or edit ``~/.cursor/mcp.json`` (macOS/Linux) / ``%USERPROFILE%\.cursor\mcp.json`` (Windows) directly.

.. _gemini-extension:

Gemini Extension
----------------

The Zscaler MCP Server is available as a **Gemini Extension** for the `Google Gemini CLI <https://github.com/google/gemini-cli>`__.

**What's Included:**

- Extension manifest (``gemini-extension.json``) — Extension metadata, MCP config, and version info
- Extension README (``GEMINI.md``) — Tool discovery guide, critical gotchas, write-safety rules, and skill descriptions

**Installation:**

Clone the repository and register the extension with Gemini CLI:

.. code-block:: bash

   git clone https://github.com/zscaler/zscaler-mcp-server.git
   cd zscaler-mcp-server

The extension manifest configures the MCP server automatically using ``${extensionPath}`` variables resolved by Gemini CLI at runtime.

.. _kiro-power:

Kiro Power
----------

The Zscaler MCP Server is available as a **Kiro Power** for the `AWS Kiro IDE <https://kiro.dev>`__.

**What's Included:**

- Power manifest (``integrations/kiro/POWER.md``) — Power metadata, tool reference, workflows, and best practices
- MCP config (``integrations/kiro/mcp.json``) — MCP server connection configuration
- Steering files (``integrations/kiro/steering/``) — 9 service-specific context files for on-demand loading

**Steering Files:**

Unlike skills (which are guided workflows), Kiro uses **steering files** — service-specific knowledge documents that the AI loads on demand:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - File
     - Service
     - Tools
   * - ``zpa.md``
     - ZPA (Private Access)
     - 59 — app segments, access/forwarding/timeout/isolation policies, connectors, PRA
   * - ``zia.md``
     - ZIA (Internet Access)
     - 76 — cloud firewall, URL filtering, SSL inspection, DLP, locations, sandbox
   * - ``zdx.md``
     - ZDX (Digital Experience)
     - 18 — app scores, device health, alerts, deep traces (read-only)
   * - ``z-insights.md``
     - Z-Insights (Analytics)
     - 16 — web traffic, cyber incidents, shadow IT, firewall analytics (read-only)
   * - ``zcc.md``
     - ZCC (Client Connector)
     - 4 — device enrollment, forwarding profiles (read-only)
   * - ``ztw.md``
     - ZTW (Workload Segmentation)
     - 19 — IP groups, network services, cloud accounts
   * - ``easm.md``
     - EASM (Attack Surface)
     - 7 — findings, lookalike domains, scan evidence (read-only)
   * - ``zid.md``
     - ZIdentity
     - 10 — users, groups, identity management (read-only)
   * - ``cross-product.md``
     - Cross-product
     - ZCC + ZDX + ZPA + ZIA correlation workflow

**Installation:**

1. Open `Kiro IDE <https://kiro.dev>`__
2. Go to the **Powers** panel → **Add Custom Power**
3. Select **Local Directory** or provide the GitHub URL
4. Point to ``integrations/kiro/``

.. _google-adk:

Google ADK (Agent Development Kit)
----------------------------------

The Zscaler MCP Server integrates with `Google ADK <https://google.github.io/adk-docs/>`__ to build autonomous Zscaler security agents powered by Gemini models.

**What's Included:**

- Root ``.env`` (``integrations/adk/.env``) — Zscaler API credentials and write-tool configuration
- Agent ``.env`` (``integrations/adk/zscaler_agent/.env``) — Google ADK config (model, API key, agent prompt, Cloud Run settings)

**How It Works:**

The Google ADK agent connects to the Zscaler MCP Server as an MCP tool provider. The agent starts the MCP server, discovers all 280+ tools, and uses a Gemini model to interpret user requests and invoke the appropriate Zscaler tools.

**Configuration:**

1. Edit ``integrations/adk/.env`` with your Zscaler OneAPI credentials
2. Edit ``integrations/adk/zscaler_agent/.env`` with your Google API key and agent settings

.. code-block:: bash

   # Google ADK Configuration
   GOOGLE_GENAI_USE_VERTEXAI=False
   GOOGLE_API_KEY="your-google-api-key"
   GOOGLE_MODEL=gemini-2.0-flash

   # Agent Configuration
   ZSCALER_AGENT_PROMPT='You are a helpful Zscaler security assistant...'

**Local Development:**

.. code-block:: bash

   cd integrations/adk
   adk run zscaler_agent

**Cloud Run Deployment:**

.. code-block:: bash

   adk deploy cloud_run --project your-gcp-project --region us-central1 zscaler_agent

**Prerequisites:**

- Python 3.11+
- `Google ADK <https://google.github.io/adk-docs/>`__ installed (``pip install google-adk``)
- A Google API key or Vertex AI access
- Zscaler OneAPI credentials

Shared Components
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
     - 19 guided multi-step workflows (ZPA, ZIA, ZDX, EASM, Z-Insights, Cross-product)
   * - MCP Server
     - ``zscaler_mcp/``
     - The MCP server implementation (280+ tools)
   * - Docs
     - ``docs/``
     - Deployment guides, tool references, troubleshooting

Skills Overview
~~~~~~~~~~~~~~~

All plugin/extension integrations include 19 guided multi-step skills:

.. list-table::
   :header-rows: 1
   :widths: 15 10 75

   * - Service
     - Count
     - Skills
   * - **ZPA**
     - 6
     - Onboard application, create access/forwarding/timeout policy rules, create server group, troubleshoot connector
   * - **ZIA**
     - 5
     - Onboard location, audit SSL inspection, investigate URL category, check user access, investigate sandbox
   * - **ZDX**
     - 5
     - Troubleshoot user experience, analyze app health, investigate alerts, diagnose deep trace, audit software
   * - **EASM**
     - 1
     - Review attack surface
   * - **Z-Insights**
     - 1
     - Investigate security incident
   * - **Cross-product**
     - 1
     - Troubleshoot user connectivity (ZCC + ZDX + ZPA + ZIA)

Prerequisites
-------------

All integrations require:

- The respective AI platform installed (Claude Code, Cursor, Gemini CLI, Kiro IDE, or Google ADK)
- `uv <https://docs.astral.sh/uv/>`__ installed (for ``uvx`` method) or Docker
- Zscaler OneAPI credentials configured in ``.env``

Verification
------------

After installing any integration, verify by asking:

   "What Zscaler tools are available?"

or

   "List my ZPA application segments"
