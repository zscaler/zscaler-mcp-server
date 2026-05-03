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
   * - **Google Cloud (Cloud Run / GKE / VM)**
     - Deployment
     - ``python gcp_mcp_operations.py deploy``
     - :doc:`Cloud Run <../guides/gcp-cloud-run>` · :doc:`GKE <../guides/gcp-gke>` · :doc:`VM <../guides/gcp-compute-engine-vm>` · `Source <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/google>`__
   * - **Google ADK Agent**
     - Agent
     - ``python adk_agent_operations.py deploy``
     - :doc:`Guide <../guides/gcp-adk-agent>` · `Source <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/google/adk>`__
   * - **Azure (Container Apps / VM / AKS)**
     - Deployment
     - ``python azure_mcp_operations.py deploy``
     - :doc:`Guide <../guides/azure-deployment>` · `Source <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/azure>`__
   * - **Azure AI Foundry**
     - Agent
     - ``python azure_mcp_operations.py agent_create``
     - :doc:`Guide <../guides/azure-deployment>` · `Source <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/azure/foundry_agent.py>`__
   * - **GitHub MCP Registry**
     - Registry
     - ``mcp-publisher publish``
     - `integrations/github/ <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/github>`__

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

- Root ``.env`` (``integrations/google/adk/.env``) — Zscaler API credentials and write-tool configuration
- Agent ``.env`` (``integrations/google/adk/zscaler_agent/.env``) — Google ADK config (model, API key, agent prompt, Cloud Run settings)

**How It Works:**

The Google ADK agent connects to the Zscaler MCP Server as an MCP tool provider. The agent starts the MCP server, discovers all 280+ tools, and uses a Gemini model to interpret user requests and invoke the appropriate Zscaler tools.

**Configuration:**

1. Edit ``integrations/google/adk/.env`` with your Zscaler OneAPI credentials
2. Edit ``integrations/google/adk/zscaler_agent/.env`` with your Google API key and agent settings

.. code-block:: bash

   # Google ADK Configuration
   GOOGLE_GENAI_USE_VERTEXAI=False
   GOOGLE_API_KEY="your-google-api-key"
   GOOGLE_MODEL=gemini-2.0-flash

   # Agent Configuration
   ZSCALER_AGENT_PROMPT='You are a helpful Zscaler security assistant...'

**Local Development:**

.. code-block:: bash

   cd integrations/google/adk
   python adk_agent_operations.py local_run

**Cloud Run Deployment:**

.. code-block:: bash

   adk deploy cloud_run --project your-gcp-project --region us-central1 zscaler_agent

**Prerequisites:**

- Python 3.11+
- `Google ADK <https://google.github.io/adk-docs/>`__ installed (``pip install google-adk``)
- A Google API key or Vertex AI access
- Zscaler OneAPI credentials

.. _azure-deployment:

Azure Deployment
----------------

The Zscaler MCP Server can be deployed to **Azure Container Apps** (managed, serverless), an **Azure Virtual Machine** (Ubuntu 22.04), or **Azure Kubernetes Service** (Preview) using the interactive ``azure_mcp_operations.py`` script. Full walkthrough: :doc:`../guides/azure-deployment`.

**What's Included:**

- Deployment script (``azure_mcp_operations.py``) — Interactive guided deployment with ``deploy``, ``destroy``, ``status``, ``logs``, and ``ssh`` commands
- Foundry agent (``foundry_agent.py``) — Azure AI Foundry integration for creating GPT-4o agents backed by Zscaler MCP tools
- Environment template (``.env``) — Pre-configured credential templates for all authentication modes

**Deployment Targets:**

.. list-table::
   :header-rows: 1
   :widths: 25 35 30 10

   * - Target
     - Description
     - Image / Package
     - Status
   * - **Container Apps**
     - Managed serverless containers
     - Docker Hub: ``zscaler/zscaler-mcp-server:latest``
     - GA
   * - **Virtual Machine**
     - Ubuntu 22.04, self-managed
     - PyPI: ``zscaler-mcp``
     - GA
   * - **Azure Kubernetes Service**
     - Kubernetes ``Deployment`` + ``LoadBalancer`` Service, Key Vault via Workload Identity Federation
     - Docker Hub: ``zscaler/zscaler-mcp-server:latest``
     - **Preview**

**Authentication Modes:**

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Mode
     - Description
     - Client Auth Header
   * - **OIDCProxy**
     - OAuth 2.1 + DCR via OIDC provider (Entra ID, Okta, etc.)
     - Handled automatically by ``mcp-remote``
   * - **JWT**
     - Validate JWTs against a JWKS endpoint
     - ``Authorization: Bearer <JWT>``
   * - **API Key**
     - Shared secret (auto-generated if not provided)
     - ``Authorization: Bearer <api-key>``
   * - **Zscaler**
     - Validate via OneAPI client credentials
     - ``Authorization: Basic base64(id:secret)``
   * - **None**
     - No authentication (development only)
     - No header

**Quick Start:**

.. code-block:: bash

   cd integrations/azure
   python azure_mcp_operations.py deploy

The script prompts for deployment target, credential source (``.env`` file or manual entry), Zscaler API credentials, MCP auth mode, and Azure options. All secrets are stored in Azure Key Vault.

.. _azure-foundry:

Azure AI Foundry Agent
----------------------

The Zscaler MCP Server integrates with `Azure AI Foundry <https://ai.azure.com>`__ to create autonomous security agents powered by GPT-4o that use Zscaler MCP tools.

There are two ways to configure the Foundry agent:

- **API (CLI):** Create and manage the agent via ``azure_mcp_operations.py`` commands — ideal for automation and scripted deployments.
- **UI (Portal):** Configure the agent through the Azure AI Foundry portal at `ai.azure.com <https://ai.azure.com>`__ — ideal for visual setup and exploration.

For the complete end-to-end walkthrough (both methods), see :doc:`../guides/azure-deployment`.

**What's Included:**

- Agent lifecycle commands (``agent_create``, ``agent_chat``, ``agent_status``, ``agent_destroy``)
- Interactive chat session with tool approval handling and in-chat commands (``help``, ``status``, ``clear``, ``reset``)
- Multi-turn response chaining for conversation continuity
- Per-response token usage tracking and end-of-session summary
- Graceful API error handling with actionable remediation steps

**Prerequisites:**

- Azure AI Foundry project (https://ai.azure.com)
- Azure OpenAI deployment (GPT-4o or GPT-4)
- Deployed Zscaler MCP Server (Container Apps, VM, or AKS Preview)
- Python packages: ``azure-ai-projects``, ``azure-ai-agents``, ``azure-identity``

**Authentication — one-time portal step required:**

Foundry no longer accepts auth headers inlined in ``MCPTool.headers``. The supported pattern is to register a **Custom keys connection** in the project that holds the headers, and reference it via ``MCPTool.project_connection_id``. ``agent_create`` will probe the connection at runtime, print copy-paste-ready portal instructions if it's missing, and exit before mutating Foundry. See :ref:`azure-deployment-guide` for the exact portal steps and the per-auth-mode key list.

**Quick Start (CLI):**

.. code-block:: bash

   # Step 1: Deploy the MCP server
   python azure_mcp_operations.py deploy

   # Step 2: One-time — create the "Custom keys" connection in the Foundry portal
   #         (Management center -> Connected resources -> + New connection -> Custom keys)

   # Step 3: Create the Foundry agent
   python azure_mcp_operations.py agent_create

   # Step 4: Start chatting
   python azure_mcp_operations.py agent_chat

**All Agent Commands:**

.. code-block:: bash

   python azure_mcp_operations.py agent_create    # create agent
   python azure_mcp_operations.py agent_chat      # interactive chat
   python azure_mcp_operations.py agent_chat -m "query"  # single query
   python azure_mcp_operations.py agent_status    # show agent info
   python azure_mcp_operations.py agent_destroy   # delete agent

**Finding the agent in the portal:** Foundry agents created by this script are **Prompt Agents** in the new Foundry experience. Open `ai.azure.com <https://ai.azure.com>`__, ensure the *New Foundry* toggle (top-right) is on, then go to **Build → Agents → Agents** tab and select ``zscaler-mcp-agent``. ``agent_create`` also prints a deep link straight to the agent on success.

.. _github-mcp-registry:

GitHub MCP Registry
-------------------

The Zscaler MCP Server is listed on the `GitHub MCP Registry <https://github.com/modelcontextprotocol/registry>`__, enabling one-click installation from GitHub Copilot and any MCP-compatible client.

**What's Included:**

- Registry manifest (``server.json``) — Server metadata, PyPI and Docker packages, required env vars
- PyPI ownership proof in ``README.md`` — ``<!-- mcp-name: io.github.zscaler/zscaler-mcp-server -->``
- Docker ownership proof in ``Dockerfile`` — ``LABEL io.modelcontextprotocol.server.name``

**Two Package Types:**

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Package
     - Runtime
     - Identifier
   * - **PyPI**
     - ``uvx``
     - ``zscaler-mcp``
   * - **Docker (OCI)**
     - ``docker``
     - ``docker.io/zscaler/zscaler-mcp-server:latest``

**Required Credentials (4 env vars):**

- ``ZSCALER_CLIENT_ID`` (secret) — OneAPI Client ID
- ``ZSCALER_CLIENT_SECRET`` (secret) — OneAPI Client Secret
- ``ZSCALER_CUSTOMER_ID`` — Customer ID
- ``ZSCALER_VANITY_DOMAIN`` — Vanity domain (e.g. ``mycompany.zscloud.net``)

**Publishing:**

.. code-block:: bash

   mcp-publisher login github
   mcp-publisher publish

**Config files at repo root:** ``server.json``

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
