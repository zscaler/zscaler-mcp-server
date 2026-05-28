.. image:: https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/docs/media/zscaler.svg
   :alt: Zscaler MCP

|PyPI version| |PyPI - Python Version| |License| |Zscaler Community| |Documentation| |codecov| |GitHub commit activity| |Automation Hub|

**zscaler-mcp-server** is a Model Context Protocol (MCP) server that connects AI agents with the Zscaler Zero Trust Exchange platform.

.. important::

   **Public Preview**

   This project is currently in **public preview** and under active development. Features and functionality may change before the stable ``1.0`` release. While we encourage exploration and testing, please **avoid production deployments**. We welcome your feedback through `GitHub Issues <https://github.com/zscaler/zscaler-mcp-server/issues>`__ to help shape the final release.

Support Disclaimer
------------------

.. warning::
   **Disclaimer:** Please refer to our General Support Statement before proceeding with the use of this provider. You can also refer to our troubleshooting guide for guidance on typical problems.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Getting Started

   getting-started

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Tools & Toolsets

   tools/index
   toolsets/index

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Skills

   skills/index

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Deployment

   deployment/index

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Integrations

   integrations/index

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Security

   security/index

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Development

   development/index

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Help & Support

   help-and-support/index

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Changelog

   guides/release-notes

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: API Reference

   api/index

Overview
--------

The Zscaler Integrations MCP Server brings context to your agents. Try prompts like:

- "List my ZPA Application segments"
- "List my ZPA Segment Groups"
- "List my ZIA Rule Labels"

Supported Services
------------------

The server exposes **300+ tools** across nine Zscaler services. Tools follow a strict ``{service}_{verb}_{resource}`` naming convention (e.g. ``zia_list_locations``, ``zpa_create_application_segment``, ``zdx_get_application``).

.. list-table::
   :header-rows: 1
   :widths: 18 12 70

   * - Service
     - Tool modules
     - What it covers
   * - :doc:`ZIA <tools/zia/index>`
     - 41
     - Cloud Firewall, URL Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox Rules, Cloud App Control, ATP Policy (incl. malware + advanced settings), Locations, Users, Devices, Authentication Settings, Time Intervals, Shadow IT, Admin & activation.
   * - :doc:`ZPA <tools/zpa/index>`
     - 29
     - Application Segments (standard / BA / PRA), Access / Forwarding / Timeout / Isolation policies, App Connector Groups, Server Groups, Segment Groups, Service Edge Groups, Provisioning Keys, PRA Portals + Credentials, App Protection, Posture, Trusted Networks, IdP / SAML / SCIM, Microtenants.
   * - :doc:`ZDX <tools/zdx/index>`
     - 20
     - Applications, Application Scores & Metrics, Users, Devices, Locations, Departments, Geolocations, Alerts (active + historical), Deep Traces, Software Inventory, CloudPath probes, Web probes.
   * - :doc:`ZCC <tools/zcc/index>`
     - 4
     - Device enrollment, Trusted Networks, Forwarding Profiles, Web App Service.
   * - :doc:`ZTW <tools/ztw/index>`
     - 10
     - Workload Segmentation: IP Groups, Network Services, Cloud Accounts, Admin Roles.
   * - :doc:`ZIdentity <tools/zid/index>`
     - 2
     - Users, Groups.
   * - :doc:`EASM <tools/easm/index>`
     - 3
     - External Attack Surface: Organizations, Findings, Scan Evidence, Lookalike Domains.
   * - :doc:`Z-Insights <tools/zins/index>`
     - 7
     - Analytics across Web Traffic, Threats, Cyber Incidents, Firewall, CASB, Shadow IT, IoT.
   * - :doc:`ZMS <tools/zms/index>`
     - 9
     - Microsegmentation: Agents, Resources, Resource Groups, Policy Rules, App Zones, App Catalog, Tags, Nonces.

For the full alphabetical tool index, see :doc:`tools/index`. For tool *grouping* (load only the slice an agent needs), see :doc:`toolsets/index`.

.. note::

   Tool catalogs in :doc:`tools/index` are organized one tool per page. The :doc:`toolsets <toolsets/index>` system lets you load a curated subset at startup (e.g. ``--toolsets zia_url_filtering``) instead of every tool from every service.

Skills, Toolsets, Security
--------------------------

Three top-level features expand what the server can do beyond raw tool calls:

- :doc:`Toolsets <toolsets/index>` — 52 named groupings (e.g. ``zia_url_filtering``, ``zpa_app_segments``) that scope which tools are loaded. Use ``--toolsets`` to pick at startup or ``zscaler_enable_toolset`` to enable at runtime.
- :doc:`Skills <skills/index>` — 42 guided multi-step workflows that an AI agent auto-activates when a user's request matches the skill's description (e.g. "block ChatGPT for everyone" → ``zia-create-cloud-app-control-rule``).
- :doc:`Security <security/index>` — write operations + HMAC confirmations, MCP client authentication, TLS / host / source-IP hardening, output sanitization, and process lifecycle management (``reload`` / ``restart`` / ``status`` / ``stop``).

Installation & Setup
--------------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.11 or higher
- `uv <https://docs.astral.sh/uv/>`__ or pip
- Zscaler API credentials (see below)

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Copy the example environment file and configure your credentials:

.. code-block:: bash

   cp .env.example .env

Then edit `.env` with your Zscaler API credentials:

**Required Configuration (OneAPI):**

- ``ZSCALER_CLIENT_ID``: Your Zscaler OAuth client ID
- ``ZSCALER_CLIENT_SECRET``: Your Zscaler OAuth client secret
- ``ZSCALER_CUSTOMER_ID``: Your Zscaler customer ID
- ``ZSCALER_VANITY_DOMAIN``: Your Zscaler vanity domain

**Optional Configuration:**

- ``ZSCALER_CLOUD``: (Optional) Zscaler cloud environment (e.g., ``beta``) - Required when interacting with Beta Tenant ONLY.
- ``ZSCALER_PRIVATE_KEY``: (Optional) PEM-encoded private key for JWT-based OneAPI auth, used in place of ``ZSCALER_CLIENT_SECRET``.
- ``ZSCALER_MCP_SERVICES``: Comma-separated list of services to enable (default: all services)
- ``ZSCALER_MCP_TRANSPORT``: Transport method - ``stdio``, ``sse``, or ``streamable-http`` (default: ``stdio``)
- ``ZSCALER_MCP_DEBUG``: Enable debug logging - ``true`` or ``false`` (default: ``false``)
- ``ZSCALER_MCP_HOST``: Host for HTTP transports (default: ``127.0.0.1``)
- ``ZSCALER_MCP_PORT``: Port for HTTP transports (default: ``8000``)

*Alternatively, you can set these as environment variables instead of using a `.env` file.*

.. important::
   Ensure your API client has the necessary permissions for the services you plan to use. You can always update permissions later in the Zscaler console.

Installation
~~~~~~~~~~~~

Install using uv (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   uv tool install zscaler-mcp-server

.. note::
   This method requires the package to be published to PyPI. Currently, this package is in development and not yet published. Use one of the source installation methods below.

Install from source using uv (development)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   uv pip install -e .

Install from source using pip
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install -e .

Install using make (convenience)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   make install-dev

.. tip::
   If ``zscaler-mcp-server`` isn't found, update your shell PATH.

For installation via code editors/assistants, see the :ref:`using-the-mcp-server-with-agents` section below.

Usage
-----

Command Line
~~~~~~~~~~~~

Run the server with default settings (stdio transport):

.. code-block:: bash

   zscaler-mcp

Run with SSE transport:

.. code-block:: bash

   zscaler-mcp --transport sse

Run with streamable-http transport:

.. code-block:: bash

   zscaler-mcp --transport streamable-http

Run with streamable-http transport on custom port:

.. code-block:: bash

   zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8080

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

The Zscaler Integrations MCP Server supports multiple ways to specify which services to enable:

1. Command Line Arguments (highest priority)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Specify services using comma-separated lists:

.. code-block:: bash

   # Enable specific services
   zscaler-mcp --services zia,zpa,zdx

   # Enable only one service
   zscaler-mcp --services zia

2. Environment Variable (fallback)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Set the ``ZSCALER_MCP_SERVICES`` environment variable:

.. code-block:: bash

   # Export environment variable
   export ZSCALER_MCP_SERVICES=zia,zpa,zdx
   zscaler-mcp

   # Or set inline
   ZSCALER_MCP_SERVICES=zia,zpa,zdx zscaler-mcp

3. Default Behavior (all services)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If no services are specified via command line or environment variable, all available services are enabled by default.

**Service Priority Order:**

1. Command line ``--services`` argument (overrides all)
2. ``ZSCALER_MCP_SERVICES`` environment variable (fallback)
3. All services (default when none specified)

Additional Command Line Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For all available options:

.. code-block:: bash

   zscaler-mcp --help

Supported Agents
~~~~~~~~~~~~~~~~

- `Claude Desktop <https://claude.ai/>`__ — Drag-and-drop ``.mcpb`` extension (see :doc:`guides/claude-desktop-extension`) or manual MCP configuration
- `Claude Code <https://docs.anthropic.com/en/docs/claude-code>`__ — Native plugin (``claude plugin install zscaler``)
- `Cursor <https://cursor.so/>`__ — Native plugin with guided skills (also available via the `Cursor Marketplace <https://cursor.com/marketplace/zscaler>`__)
- `Gemini CLI <https://github.com/google/gemini-cli>`__ — Extension with contextual tool guidance
- `Kiro IDE <https://kiro.dev>`__ — Power with service-specific steering files
- `VS Code <https://code.visualstudio.com/download>`__ + GitHub Copilot — MCP configuration via Agent Mode

See :ref:`platform-integrations` for IDE plugins, :ref:`registries` for the published registry / marketplace listings, and :doc:`guides/claude-desktop-extension` for the Claude Desktop extension walkthrough.

Zscaler API Credentials & Authentication
----------------------------------------

The Zscaler Integrations MCP Server uses **OneAPI** authentication exclusively. A single set of ZIdentity credentials authenticates the server to every Zscaler product.

Zscaler OneAPI Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before using the Zscaler Integrations MCP Server, you need to create API credentials in your Zidentity console. The Zscaler Integrations MCP Server supports Zscaler's OneAPI authentication via OAuth2.0 as the default and preferred method.

- `OneAPI <https://help.zscaler.com/oneapi/understanding-oneapi>`__: If you are using the OneAPI entrypoint you must have a API Client created in the `Zidentity platform <https://help.zscaler.com/zidentity/about-api-clients>`__

Create a `.env` file in your project root with the following:

.. code-block:: bash

   ZSCALER_CLIENT_ID=your_client_id
   ZSCALER_CLIENT_SECRET=your_client_secret
   ZSCALER_CUSTOMER_ID=your_customer_id
   ZSCALER_VANITY_DOMAIN=your_vanity_domain
   ZSCALER_CLOUD=beta

.. warning::
   Do not commit `.env` to source control. Add it to your `.gitignore`.

You can provide credentials via the ``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_VANITY_DOMAIN``, ``ZSCALER_CLOUD`` environment variables, representing your Zidentity OneAPI credentials ``clientId``, ``clientSecret``, ``vanityDomain`` and ``cloud`` respectively.

.. list-table:: OneAPI Authentication Parameters
   :header-rows: 1
   :widths: 20 40 40

   * - Argument
     - Description
     - Environment variable
   * - ``clientId``
     - Zscaler API Client ID, used with ``clientSecret`` or ``PrivateKey`` OAuth auth mode.
     - ``ZSCALER_CLIENT_ID``
   * - ``clientSecret``
     - A string that contains the password for the API admin.
     - ``ZSCALER_CLIENT_SECRET``
   * - ``vanityDomain``
     - Refers to the domain name used by your organization i.e ``acme``
     - ``ZSCALER_VANITY_DOMAIN``
   * - ``cloud``
     - The Zidentity cloud to authenticate to i.e ``beta``
     - ``ZSCALER_CLOUD``

Container Usage
---------------

The Zscaler Integrations MCP Server is available as a pre-built container image for easy deployment:

Using Pre-built Image (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Pull the latest pre-built image
   docker pull zscaler/zscaler-mcp-server:latest

   # Run with .env file (recommended)
   docker run --rm --env-file /path/to/.env zscaler/zscaler-mcp-server:latest

   # Run with .env file and SSE transport
   docker run --rm -p 8000:8000 --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest --transport sse --host 0.0.0.0

   # Run with .env file and streamable-http transport
   docker run --rm -p 8000:8000 --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0

   # Run with .env file and custom port
   docker run --rm -p 8080:8080 --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0 --port 8080

   # Run with .env file and specific services
   docker run --rm --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest --services zia,zpa,zdx

   # Use a specific version instead of latest
   docker run --rm --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:1.2.3

   # Alternative: Individual environment variables
   docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
     -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain \
     zscaler/zscaler-mcp-server:latest

Building Locally (Development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For development or customization purposes, you can build the image locally:

.. code-block:: bash

   # Build the Docker image
   docker build -t zscaler-mcp-server .

   # Run the locally built image
   docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
     -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain zscaler-mcp-server

.. note::
   When using HTTP transports in Docker, always set ``--host 0.0.0.0`` to allow external connections to the container.

Editor/Assistant Integration
----------------------------

You can integrate the Zscaler Integrations MCP Server with your editor or AI assistant. Here are configuration examples for popular MCP clients:

Using `uvx` (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/path/to/.env", "zscaler-mcp-server"]
       }
     }
   }

With Service Selection
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": [
           "--env-file", "/path/to/.env",
           "zscaler-mcp-server",
           "--services", "zia,zpa,zdx"
         ]
       }
     }
   }

Using Individual Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["zscaler-mcp-server"],
         "env": {
           "ZSCALER_CLIENT_ID": "your-client-id",
           "ZSCALER_CLIENT_SECRET": "your-client-secret",
           "ZSCALER_CUSTOMER_ID": "your-customer-id",
           "ZSCALER_VANITY_DOMAIN": "your-vanity-domain"
         }
       }
     }
   }

Docker Version
~~~~~~~~~~~~~~

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "--env-file", "/full/path/to/.env",
           "zscaler/zscaler-mcp-server:latest"
         ]
       }
     }
   }

.. _using-the-mcp-server-with-agents:

Using the MCP Server with Agents
--------------------------------

Once your server is running (via Docker or source), you can access its tools through AI-integrated editors or platforms.

Claude
~~~~~~

1. Open Claude
2. In Chat, select the "Search & Tools"
3. The server appears in the tools list ``zscaler-mcp-server``
4. Try prompts like "List ZPA Segment Groups" or "List ZIA Rule Labels"
5. Select the tool and click "Submit"

Cursor
~~~~~~

1. Open Cursor, then settings
2. In Cursor Settings, select "Tools & Integrations"
3. In the MCP Tools section, turn on ``zscaler-mcp-server``
4. Select ``View`` and ``Command Palette`` and ``Chat: Open Chat Agent``
5. In chat, switch to `Agent Mode <https://docs.cursor.com/chat/agent>`__.
6. Try prompts like "List ZPA Segment Groups" or "List ZIA Rule Labels"
7. Click "Submit"

Visual Studio Code + GitHub Copilot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install

After installation, select GitHub Copilot Agent Mode and refresh the tools list. Learn more about Agent Mode in the `VS Code Documentation <https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode>`__.

1. Open VS Code and launch GitHub Copilot
2. Switch to Agent Mode (via the gear menu)
3. Start the MCP Server
4. Refresh the tools list
5. Try a prompt like: ``Create a ZPA segment group named "DevServices"``

📚 Learn more about Agent Mode in the `VS Code Copilot documentation <https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode>`__

Troubleshooting
---------------

See the Troubleshooting guide for help with common issues and logging.

Contributing
------------

Getting Started for Contributors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/zscaler/zscaler-mcp-server.git
      cd zscaler-mcp-server

2. Install in development mode:

   .. code-block:: bash

      # Create .venv and install dependencies
      uv sync --all-extras

      # Activate the venv
      source .venv/bin/activate

.. important::
   This project uses `Conventional Commits <https://www.conventionalcommits.org/>`__ for automated releases and semantic versioning. Please follow the commit message format outlined in our Contributing Guide when submitting changes.

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run end-to-end tests
   pytest --run-e2e tests/e2e/

   # Run end-to-end tests with verbose output (note: -s is required to see output)
   pytest --run-e2e -v -s tests/e2e/

License
-------

Copyright (c) 2025 `Zscaler <https://github.com/zscaler>`__

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

.. |PyPI version| image:: https://badge.fury.io/py/zscaler-mcp.svg
   :target: https://badge.fury.io/py/zscaler-mcp
.. |PyPI - Python Version| image:: https://img.shields.io/pypi/pyversions/zscaler-mcp
   :target: https://pypi.org/project/zscaler-mcp/
.. |License| image:: https://img.shields.io/github/license/zscaler/zscaler-mcp-server.svg
   :target: https://github.com/zscaler/zscaler-mcp-server
.. |Documentation| image:: https://img.shields.io/badge/docs-GitHub%20Pages-blue
   :target: https://zscaler-mcp-server.readthedocs.io/en/latest/index.html
.. |codecov| image:: https://codecov.io/gh/zscaler/zscaler-mcp-server/graph/badge.svg?token=9HwNcw4Q4h
   :target: https://codecov.io/gh/zscaler/zscaler-mcp-server
.. |GitHub commit activity| image:: https://img.shields.io/badge/commit-activity-blue
   :target: https://github.com/zscaler/zscaler-mcp-server/graphs/commit-activity
.. |Zscaler Community| image:: https://img.shields.io/badge/zscaler-community-blue
   :target: https://community.zscaler.com/
.. |Automation Hub| image:: https://img.shields.io/badge/automation-hub-blue
   :target: https://automate.zscaler.com/docs/tools/sdk-documentation/sdk-getting-started