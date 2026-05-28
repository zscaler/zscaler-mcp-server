.. _claude-marketplace:

Claude Marketplace
==================

Direct link: `claude.com/plugins/zscaler <https://claude.com/plugins/zscaler>`__

The Claude plugin marketplace publishes the Zscaler plugin for **Claude Code** (the CLI). It bundles the MCP server registration and the 42 guided skills in one install command.

Install
-------

.. code-block:: bash

   claude plugin install zscaler

The plugin auto-registers the MCP server and installs the bundled Claude Code skills.

Configure credentials
---------------------

The plugin reads OneAPI credentials from ``~/.zscaler/.env`` by default. Create that file (or symlink your existing ``.env``):

.. code-block:: bash

   mkdir -p ~/.zscaler
   cat > ~/.zscaler/.env <<EOF
   ZSCALER_CLIENT_ID=your-client-id
   ZSCALER_CLIENT_SECRET=your-client-secret
   ZSCALER_CUSTOMER_ID=your-customer-id
   ZSCALER_VANITY_DOMAIN=your-vanity-domain
   EOF

For configuration details and the manual installation path, see :ref:`claude-code-plugin`.

Claude Desktop Extension (separate from this marketplace)
---------------------------------------------------------

The Claude **Desktop** application uses a different distribution mechanism — a single ``.mcpb`` bundle file that you drag into Claude Desktop. The Claude Marketplace listing above is specifically for **Claude Code** (the CLI). For the Desktop install path, see :doc:`../../guides/claude-desktop-extension`.

See also
--------

- :ref:`claude-code-plugin` — the underlying Claude Code (CLI) plugin.
- :doc:`../../guides/claude-desktop-extension` — drag-and-drop install for Claude Desktop.
- :doc:`index` — back to the registries overview.
