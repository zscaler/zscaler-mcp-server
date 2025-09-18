Getting Started with Zscaler MCP Server
========================================

This guide will help you get up and running with the Zscaler MCP Server quickly.

Prerequisites
-------------

Before you begin, ensure you have:

- Python 3.11 or higher installed
- Access to Zscaler APIs (OneAPI or Legacy credentials)
- Basic understanding of Model Context Protocol (MCP)

Installation
------------

Install the Zscaler MCP Server using pip:

.. code-block:: bash

   pip install zscaler-mcp

Or install from source:

.. code-block:: bash

   git clone https://github.com/zscaler/zscaler-mcp-server.git
   cd zscaler-mcp-server
   pip install -e .

Configuration
-------------

The MCP server requires Zscaler API credentials to function. You can provide these in several ways:

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set the following environment variables for OneAPI authentication:

.. code-block:: bash

   export ZSCALER_CLIENT_ID="your_client_id"
   export ZSCALER_CLIENT_SECRET="your_client_secret"
   export ZSCALER_VANITY_DOMAIN="your_vanity_domain"
   export ZSCALER_CLOUD="zscaler"  # Optional, defaults to zscaler

For Legacy API authentication, set service-specific variables:

.. code-block:: bash

   # ZIA Legacy
   export ZIA_USERNAME="your_username"
   export ZIA_PASSWORD="your_password"
   export ZIA_API_KEY="your_api_key"
   export ZIA_CLOUD="zscaler"

   # ZPA Legacy
   export ZPA_CLIENT_ID="your_client_id"
   export ZPA_CLIENT_SECRET="your_client_secret"
   export ZPA_CUSTOMER_ID="your_customer_id"
   export ZPA_CLOUD="PRODUCTION"

Configuration File
~~~~~~~~~~~~~~~~~~

Create a configuration file (``zscaler.yaml``) in your home directory:

.. code-block:: yaml

   zscaler:
     client:
       clientId: "your_client_id"
       clientSecret: "your_client_secret"
       vanityDomain: "your_vanity_domain"
       cloud: "zscaler"
       logging:
         enabled: true
         verbose: false

Running the Server
------------------

Start the MCP server using the command line:

.. code-block:: bash

   zscaler-mcp-server

Or run it programmatically:

.. code-block:: python

   from zscaler_mcp.server import ZscalerMCPServer

   server = ZscalerMCPServer()
   server.run()

The server will start and listen for MCP protocol connections.

Connecting with AI Assistants
-----------------------------

Claude Desktop
~~~~~~~~~~~~~~

Add the following to your Claude Desktop configuration:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler": {
         "command": "zscaler-mcp-server",
         "args": []
       }
     }
   }

Cursor
~~~~~~

Configure Cursor to use the MCP server by adding it to your MCP configuration file.

Testing the Connection
----------------------

Once the server is running, you can test it by asking your AI assistant to:

- List available Zscaler tools
- Get information about your Zscaler configuration
- Execute a simple query (e.g., list users, devices, etc.)

Example queries:

- "What Zscaler tools are available?"
- "List all ZIA admin roles"
- "Show me ZCC device information"
- "Get ZPA application segments"

Next Steps
----------

- Explore the :doc:`tools documentation <tools/index>` to see all available tools
- Check out the examples guide for more complex usage scenarios
- Refer to the troubleshooting guide if you encounter issues

Troubleshooting
---------------

Common issues and solutions:

1. **Authentication errors**: Verify your credentials and cloud environment
2. **Connection refused**: Ensure the server is running and accessible
3. **Tool not found**: Check that the service is properly configured

For more detailed troubleshooting, see the troubleshooting guide.
