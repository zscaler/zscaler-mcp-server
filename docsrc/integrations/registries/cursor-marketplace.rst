.. _cursor-marketplace:

Cursor Marketplace
==================

Direct link: `cursor.com/marketplace/zscaler <https://cursor.com/marketplace/zscaler>`__

The Cursor Marketplace listing publishes a one-click installer that registers the Zscaler MCP Server with your Cursor IDE installation. The marketplace handles:

- Adding the server to your Cursor MCP configuration
- Pulling the latest released version
- Surfacing the bundled Cursor plugin, which adds Zscaler-specific tool guidance and skill prompts

Install
-------

Open the listing in your browser and click **Add to Cursor**:

`cursor.com/marketplace/zscaler <https://cursor.com/marketplace/zscaler>`__

Cursor handles the rest — it adds the server to your ``~/.cursor/mcp.json`` and reloads the MCP runtime. Restart Cursor and verify the server appears under **Settings → Tools & MCP**.

Configure credentials
---------------------

After the marketplace install, edit your ``mcp.json`` to point at the ``.env`` file holding your Zscaler OneAPI credentials:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/absolute/path/to/.env", "zscaler-mcp"]
       }
     }
   }

For manual installation (without the marketplace) and full plugin details, see :ref:`cursor-plugin`.

See also
--------

- :ref:`cursor-plugin` — the underlying Cursor plugin (what the marketplace installs).
- :doc:`index` — back to the registries overview.
