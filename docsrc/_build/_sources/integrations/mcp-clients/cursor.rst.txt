.. _integration-cursor:
.. _cursor-plugin:

Cursor
======

The Zscaler MCP Server is available as a native **Cursor Plugin**, providing AI-assisted management of the Zscaler Zero Trust Exchange platform directly within `Cursor <https://cursor.so/>`__. The plugin is also discoverable from the `Cursor Marketplace <https://cursor.com/marketplace/zscaler>`__.

What's Included
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Component
     - Location
     - Purpose
   * - Plugin manifest
     - ``.cursor-plugin/plugin.json``
     - Plugin metadata, version, and entry points
   * - Skills
     - ``skills/``
     - 42 guided multi-step workflows for common Zscaler operations
   * - MCP config
     - ``mcp.json``
     - MCP server connection configuration

Skills (42 guided workflows)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The plugin bundles service-specific skills that Cursor auto-activates based on your prompt. See the :doc:`Skills catalog <../../skills/index>` for the full per-service list.

Installation
------------

Option 1: Cursor Settings UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open Cursor
2. Go to **Settings** → **Cursor Settings** → **Tools & MCP** → **New MCP Server**
3. Add the following configuration:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
       }
     }
   }

Option 2: Edit ``mcp.json`` directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add to ``~/.cursor/mcp.json`` (macOS/Linux) or ``%USERPROFILE%\.cursor\mcp.json`` (Windows):

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
       }
     }
   }

Option 3: Docker
~~~~~~~~~~~~~~~~

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

Prerequisites
-------------

- `Cursor <https://cursor.so/>`__ installed
- `uv <https://docs.astral.sh/uv/>`__ installed (for ``uvx`` method) or Docker
- Zscaler OneAPI credentials configured in ``.env``

Configuration
-------------

The plugin manifest at ``.cursor-plugin/plugin.json`` defines:

- **Name**: ``zscaler``
- **Category**: Security
- **Skills path**: ``./skills/``
- **MCP config**: ``./mcp.json``

Verification
------------

After installation, verify by asking Cursor:

   *"What Zscaler tools are available?"*

or

   *"List my ZPA application segments"*

Resources
---------

- `Cursor Marketplace listing <https://cursor.com/marketplace/zscaler>`__
- :doc:`../../skills/index`
- :doc:`../../guides/troubleshooting`
