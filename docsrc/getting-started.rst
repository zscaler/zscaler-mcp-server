Getting Started with Zscaler Integrations MCP Server
=====================================================

This guide will help you get up and running with the Zscaler Integrations MCP Server quickly.

Prerequisites
-------------

Before you begin, ensure you have:

- Python 3.11 or higher installed
- `uv <https://docs.astral.sh/uv/>`__ installed (recommended) or pip
- Access to Zscaler APIs (OneAPI credentials)
- Basic understanding of Model Context Protocol (MCP)

Installation
------------

Install using uv (recommended):

.. code-block:: bash

   uv tool install zscaler-mcp

Or install using pip:

.. code-block:: bash

   pip install zscaler-mcp

Or install from source:

.. code-block:: bash

   git clone https://github.com/zscaler/zscaler-mcp-server.git
   cd zscaler-mcp-server
   pip install -e .

Configuration
-------------

The MCP server requires Zscaler API credentials to function. Create a ``.env`` file with your credentials:

OneAPI Authentication
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   ZSCALER_CLIENT_ID="your_client_id"
   ZSCALER_CLIENT_SECRET="your_client_secret"
   ZSCALER_CUSTOMER_ID="your_customer_id"  # required only for ZPA tools
   ZSCALER_VANITY_DOMAIN="your_vanity_domain"

For JWT-based auth, set ``ZSCALER_PRIVATE_KEY`` (PEM-encoded) in place of
``ZSCALER_CLIENT_SECRET``.

.. warning::
   Do not commit ``.env`` to source control. Add it to your ``.gitignore``.

For the full list of environment variables (including MCP Client Authentication and Network Security), see the :ref:`configuration-guide`.

Running the Server
------------------

Start the MCP server using the command line:

.. code-block:: bash

   # Default (stdio transport)
   zscaler-mcp

   # With SSE transport
   zscaler-mcp --transport sse

   # With streamable-http transport
   zscaler-mcp --transport streamable-http

   # With specific services
   zscaler-mcp --services zia,zpa,zdx

   # With a narrow toolset selection (loads only those tools, on every transport)
   zscaler-mcp --toolsets zia_url_filtering,zpa_app_segments

   # With write operations enabled
   zscaler-mcp --enable-write-tools --write-tools "zpa_create_*,zia_update_*"

For all available options:

.. code-block:: bash

   zscaler-mcp --help

Connecting with AI Assistants
-----------------------------

The Zscaler MCP Server integrates with multiple AI development platforms. Native plugin/extension support is available for:

- **Claude Code** — Native plugin with marketplace support (``claude plugin install zscaler``)
- **Claude Desktop** — Manual MCP configuration or one-click extension install
- **Cursor** — Native plugin with guided skills
- **Gemini CLI** — Extension with contextual tool guidance
- **Kiro IDE** — Power with service-specific steering files
- **VS Code + GitHub Copilot** — MCP configuration via Agent Mode

For detailed setup instructions for each platform, see the :ref:`platform-integrations` page.

Quick Configuration (Any MCP Client)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using ``uvx`` (recommended):

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
       }
     }
   }

Using Docker:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "--env-file", "/absolute/path/to/.env",
           "zscaler/zscaler-mcp-server:latest"
         ]
       }
     }
   }

Testing the Connection
----------------------

Once the server is running, you can test it by asking your AI assistant:

- "What Zscaler tools are available?"
- "List my ZPA application segments"
- "List all ZIA rule labels"
- "Show me ZCC device information"
- "List my ZDX applications"

Next Steps
----------

- Explore the :doc:`tools documentation <tools/index>` to see all available tools
- Review the :ref:`configuration-guide` for authentication, security, and advanced options
- Check out the :doc:`examples guide <guides/examples>` for service-specific prompts
- See :ref:`platform-integrations` for native IDE/editor integrations
- Refer to the :doc:`troubleshooting guide <guides/troubleshooting>` if you encounter issues

Troubleshooting
---------------

Common issues and solutions:

1. **"Command not found: zscaler-mcp"** — Install ``uv``: ``curl -LsSf https://astral.sh/uv/install.sh | sh`` then ``uv tool install zscaler-mcp``
2. **Authentication errors** — Verify your credentials and cloud environment in ``.env``
3. **Connection refused** — Ensure the server is running and accessible; check ``ZSCALER_MCP_ALLOW_HTTP`` if connecting over HTTP
4. **Tools not appearing** — Check that the service is enabled (``ZSCALER_MCP_SERVICES``) and write tools are explicitly allowed (``--enable-write-tools`` + ``--write-tools``)

For more detailed troubleshooting, see the :doc:`troubleshooting guide <guides/troubleshooting>`.
