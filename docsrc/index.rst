.. image:: https://raw.githubusercontent.com/zscaler/zscaler-mcp-server/master/docs/media/zscaler.svg
   :alt: Zscaler MCP

|PyPI version| |PyPI - Python Version| |License| |Zscaler Community|

**zscaler-mcp-server** is a Model Context Protocol (MCP) server that connects AI agents with the Zscaler Zero Trust Exchange platform.

Support Disclaimer
------------------

.. warning::
   **Disclaimer:** Please refer to our General Support Statement before proceeding with the use of this provider. You can also refer to our troubleshooting guide for guidance on typical problems.

.. important::
   **🚧 Public Preview**: This project is currently in public preview and under active development. Features and functionality may change before the stable 1.0 release. While we encourage exploration and testing, please avoid production deployments. We welcome your feedback through `GitHub Issues <https://github.com/zscaler/zscaler-mcp-server/issues>`__ to help shape the final release.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Contents

   getting-started
   tools/index
   guides/index
   api/index

Overview
--------

The Zscaler Integrations MCP Server brings context to your agents. Try prompts like:

- "List my ZPA Application segments"
- "List my ZPA Segment Groups"
- "List my ZIA Rule Labels"

Supported Tools
---------------

The Zscaler Integrations MCP Server provides tools for all major Zscaler services. Each service offers specific functionality for managing and querying Zscaler resources.

ZCC Features
~~~~~~~~~~~~

.. list-table:: ZCC Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zcc_list_devices``
     - Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal
   * - ``zcc_devices_csv_exporter``
     - Downloads ZCC device information or service status as a CSV file
   * - ``zcc_list_trusted_networks``
     - Returns the list of Trusted Networks By Company ID in the Client Connector Portal
   * - ``zcc_list_forwarding_profiles``
     - Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal

ZDX Features
~~~~~~~~~~~~

.. list-table:: ZDX Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zdx_administration``
     - Discover ZDX departments or locations
   * - ``zdx_active_devices``
     - Discover ZDX devices using various filters
   * - ``zdx_list_applications``
     - List all active applications configured in ZDX
   * - ``zdx_list_application_score``
     - Get an application's ZDX score or score trend
   * - ``zdx_get_application_metric``
     - Retrieve ZDX metrics for an application (PFT, DNS, availability)
   * - ``zdx_get_application_user``
     - List users/devices for an app or details for a specific user
   * - ``zdx_list_software_inventory``
     - List software inventory or users/devices for a software key
   * - ``zdx_list_alerts``
     - List ongoing alerts, get alert details, or list affected devices
   * - ``zdx_list_historical_alerts``
     - List historical alert rules (ended alerts)
   * - ``zdx_list_deep_traces``
     - Retrieve deep trace information for troubleshooting device connectivity issues

ZIdentity Features
~~~~~~~~~~~~~~~~~~

.. list-table:: ZIdentity Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zidentity_groups``
     - Retrieves Zidentity group information
   * - ``zidentity_users``
     - Retrieves Zidentity user information

ZIA Features
~~~~~~~~~~~~

.. list-table:: ZIA Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zia_activation``
     - Tool to check or activate ZIA configuration changes
   * - ``zia_atp_malicious_urls``
     - Manages the malicious URL denylist in the ZIA Advanced Threat Protection (ATP) policy
   * - ``zia_auth_exempt_urls``
     - Manages the list of cookie authentication exempt URLs in ZIA
   * - ``zia_cloud_applications``
     - Tool for managing ZIA Shadow IT Cloud Applications
   * - ``zia_cloud_firewall_rule``
     - Manages ZIA Cloud Firewall Rules
   * - ``zia_geo_search``
     - Performs geographical lookup actions using the ZIA Locations API
   * - ``zia_gre_range``
     - Tool for discovering available GRE internal IP ranges in ZIA
   * - ``zia_gre_tunnels``
     - Tool for managing ZIA GRE Tunnels and associated static IPs
   * - ``zia_ip_destination_groups``
     - Manages ZIA IP Destination Groups
   * - ``zia_ip_source_group``
     - Performs CRUD operations on ZIA IP Source Groups
   * - ``zia_user_groups``
     - Lists and retrieves ZIA User Groups with pagination, filtering and sorting
   * - ``zia_user_departments``
     - Lists and retrieves ZIA User Departments with pagination, filtering and sorting
   * - ``zia_users``
     - Lists and retrieves ZIA Users with filtering and pagination
   * - ``zia_location_management``
     - Tool for managing ZIA Locations
   * - ``zia_network_app_group``
     - Manages ZIA Network Application Groups
   * - ``zia_rule_labels``
     - Tool for managing ZIA Rule Labels
   * - ``zia_sandbox_info``
     - Tool for retrieving ZIA Sandbox information
   * - ``zia_static_ips``
     - Tool for managing ZIA Static IP addresses
   * - ``zia_url_categories``
     - Tool for managing ZIA URL Categories
   * - ``zia_vpn_credentials``
     - Tool for managing ZIA VPN Credentials
   * - ``zia_ssl_inspection_rules``
     - Tool for managing ZIA SSL Inspection Rules

ZPA Features
~~~~~~~~~~~~

.. list-table:: ZPA Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zpa_access_policy``
     - CRUD handler for ZPA Access Policy Rules
   * - ``zpa_app_connector_groups``
     - CRUD handler for ZPA App Connector Groups
   * - ``zpa_app_protection_policy``
     - CRUD handler for ZPA Inspection Policy Rules
   * - ``zpa_app_protection_profiles``
     - Tool for listing and searching ZPA App Protection Profiles (Inspection Profiles)
   * - ``zpa_app_segments_by_type``
     - Tool to retrieve ZPA application segments by type
   * - ``zpa_application_segments``
     - CRUD handler for ZPA Application Segments
   * - ``zpa_application_servers``
     - Tool for managing ZPA Application Servers
   * - ``zpa_ba_certificates``
     - Tool for managing ZPA Browser Access (BA) Certificates
   * - ``zpa_enrollment_certificates``
     - Get-only tool for retrieving ZPA Enrollment Certificates
   * - ``zpa_forwarding_policy``
     - CRUD handler for ZPA Client Forwarding Policy Rules
   * - ``zpa_isolation_policy``
     - CRUD handler for ZPA Isolation Policy Rules
   * - ``zpa_isolation_profile``
     - Tool for retrieving ZPA Cloud Browser Isolation (CBI) profiles
   * - ``zpa_posture_profiles``
     - Tool for retrieving ZPA Posture Profiles
   * - ``zpa_pra_credentials``
     - Tool for managing ZPA Privileged Remote Access (PRA) Credentials
   * - ``zpa_pra_portals``
     - Tool for managing ZPA Privileged Remote Access (PRA) Portals
   * - ``zpa_provisioning_key``
     - Tool for managing ZPA Provisioning Keys
   * - ``zpa_saml_attributes``
     - Tool for querying ZPA SAML Attributes
   * - ``zpa_scim_attributes``
     - Tool for managing ZPA SCIM Attributes
   * - ``zpa_scim_groups``
     - Tool for retrieving ZPA SCIM groups under a given Identity Provider (IdP)
   * - ``zpa_segment_groups``
     - Tool for managing Segment Groups
   * - ``zpa_server_groups``
     - CRUD handler for ZPA Server Groups
   * - ``zpa_service_edge_groups``
     - CRUD handler for ZPA Service Edge Groups
   * - ``zpa_timeout_policy``
     - CRUD handler for ZPA Timeout Policy Rules
   * - ``zpa_trusted_networks``
     - Tool for retrieving ZPA Trusted Networks

ZTW Features
~~~~~~~~~~~~

.. list-table:: ZTW Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``ztw_ip_destination_groups``
     - Manages ZTW IP Destination Groups
   * - ``ztw_ip_group``
     - Manages ZTW IP Groups
   * - ``ztw_ip_source_groups``
     - Manages ZTW IP Source Groups
   * - ``ztw_network_service_groups``
     - Manages ZTW Network Service Groups
   * - ``ztw_list_roles``
     - List all existing admin roles in Zscaler Cloud & Branch Connector (ZTW)
   * - ``ztw_list_admins``
     - List all existing admin users or get details for a specific admin user in Zscaler Cloud & Branch Connector (ZTW)

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
- ``ZSCALER_USE_LEGACY``: Enable legacy API mode (``true``/``false``, default: ``false``)
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

- `Claude <https://claude.ai/>`__
- `Cursor <https://cursor.so/>`__
- `VS Code <https://code.visualstudio.com/download>`__ or `VS Code Insiders <https://code.visualstudio.com/insiders>`__

Zscaler API Credentials & Authentication
----------------------------------------

The Zscaler Integrations MCP Server supports two authentication methods: OneAPI (recommended) and Legacy API. Choose the method that best fits your setup.

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
   * - ``use_legacy``
     - Whether to use legacy API clients instead of OneAPI. Can be set to ``true`` or ``false``.
     - ``ZSCALER_USE_LEGACY``

Container Usage
---------------

The Zscaler Integrations MCP Server is available as a pre-built container image for easy deployment:

Using Pre-built Image (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Pull the latest pre-built image
   docker pull quay.io/zscaler/zscaler-mcp-server:latest

   # Run with .env file (recommended)
   docker run --rm --env-file /path/to/.env quay.io/zscaler/zscaler-mcp-server:latest

   # Run with .env file and SSE transport
   docker run --rm -p 8000:8000 --env-file /path/to/.env \
     quay.io/zscaler/zscaler-mcp-server:latest --transport sse --host 0.0.0.0

   # Run with .env file and streamable-http transport
   docker run --rm -p 8000:8000 --env-file /path/to/.env \
     quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0

   # Run with .env file and custom port
   docker run --rm -p 8080:8080 --env-file /path/to/.env \
     quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0 --port 8080

   # Run with .env file and specific services
   docker run --rm --env-file /path/to/.env \
     quay.io/zscaler/zscaler-mcp-server:latest --services zia,zpa,zdx

   # Use a specific version instead of latest
   docker run --rm --env-file /path/to/.env \
     quay.io/zscaler/zscaler-mcp-server:1.2.3

   # Alternative: Individual environment variables
   docker run --rm -e ZSCALER_CLIENT_ID=your_client_id -e ZSCALER_CLIENT_SECRET=your_secret \
     -e ZSCALER_CUSTOMER_ID=your_customer_id -e ZSCALER_VANITY_DOMAIN=your_vanity_domain \
     quay.io/zscaler/zscaler-mcp-server:latest

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
           "quay.io/zscaler/zscaler-mcp-server:latest"
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
.. |Zscaler Community| image:: https://img.shields.io/badge/zscaler-community-blue
   :target: https://community.zscaler.com/