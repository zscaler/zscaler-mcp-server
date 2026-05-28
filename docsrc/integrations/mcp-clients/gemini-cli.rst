.. _integration-gemini-cli:

Gemini CLI
==========

The Zscaler MCP Server is available as a **Gemini Extension**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within `Google Gemini CLI <https://github.com/google/gemini-cli>`__.

What's Included
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Component
     - Location
     - Purpose
   * - Extension manifest
     - ``gemini-extension.json``
     - Extension metadata, MCP config, and version info
   * - Extension README
     - ``GEMINI.md``
     - Tool discovery guide, critical gotchas, write-safety rules, and skill descriptions

How It Works
------------

The Gemini extension uses the same MCP server and tools as other integrations. The ``gemini-extension.json`` manifest tells Gemini CLI how to start the MCP server, and ``GEMINI.md`` provides contextual guidance that Gemini loads to understand tool naming, service prefixes, and common workflows.

Key features in ``GEMINI.md``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Tool naming convention** — All tools follow ``{service}_{verb}_{resource}`` pattern
- **Service prefixes** — ``zia_``, ``zpa_``, ``zdx_``, ``zcc_``, ``easm_``, ``zins_``, ``zid_``, ``ztw_``, ``zms_``
- **Critical gotchas** — ZIA activation requirement, ZPA dependency chains, ZDX read-only behavior
- **Write-safety rules** — Confirm before mutating, list before creating, pagination guidance
- **Skills reference** — Descriptions of all guided workflows organized by service

Installation
------------

Step 1: Clone the repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/zscaler/zscaler-mcp-server.git
   cd zscaler-mcp-server

Step 2: Configure credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``.env`` file with your Zscaler OneAPI credentials:

.. code-block:: bash

   ZSCALER_CLIENT_ID=your-client-id
   ZSCALER_CLIENT_SECRET=your-client-secret
   ZSCALER_CUSTOMER_ID=your-customer-id
   ZSCALER_VANITY_DOMAIN=your-vanity-domain

Step 3: Install the extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Gemini CLI reads ``gemini-extension.json`` from the repository root. Register it following the `Gemini CLI extensions documentation <https://github.com/google/gemini-cli#extensions>`__.

The extension manifest configures the MCP server automatically:

.. code-block:: json

   {
     "name": "zscaler",
     "version": "0.7.0",
     "mcpServers": {
       "zscaler": {
         "command": "uvx",
         "args": [
           "--env-file",
           "${extensionPath}${pathSeparator}.env",
           "zscaler-mcp"
         ]
       }
     }
   }

The ``${extensionPath}`` and ``${pathSeparator}`` variables are resolved by Gemini CLI at runtime, pointing to the repository root where your ``.env`` file lives.

Alternative: Docker
~~~~~~~~~~~~~~~~~~~

Replace the ``mcpServers`` block with Docker:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "--env-file", "${extensionPath}${pathSeparator}.env",
           "zscaler/zscaler-mcp-server:latest"
         ]
       }
     }
   }

Prerequisites
-------------

- `Gemini CLI <https://github.com/google/gemini-cli>`__ installed
- `uv <https://docs.astral.sh/uv/>`__ installed (for ``uvx`` method) or Docker
- Zscaler OneAPI credentials configured in ``.env``

Verification
------------

After installation, verify by asking Gemini:

   *"What Zscaler tools are available?"*

or

   *"List my ZIA firewall rules"*

Resources
---------

- `Gemini CLI documentation <https://github.com/google/gemini-cli>`__
- :doc:`../../skills/index`
- :doc:`../../guides/troubleshooting`
