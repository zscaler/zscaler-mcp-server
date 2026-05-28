.. _guide-claude-desktop-extension:

Claude Desktop Extension
========================

The Zscaler MCP Server is distributed to **Claude Desktop** as a single-file ``.mcpb`` bundle. Unlike the marketplace flow (which targets Claude Code, the CLI), Claude Desktop extensions install via drag-and-drop of a single artifact.

.. note::

   Claude Desktop extensions support **local MCP servers only**. The extension launches the Zscaler MCP Server on your machine via ``uvx``. Remote-only deployments (Cloud Run, Container Apps, Bedrock AgentCore) are not addressable through this extension format — for those, use ``mcp-remote`` and the relevant MCP client config.

Prerequisites
-------------

The extension launches the server via ``uvx``, which itself runs Python. You need both:

- **Python 3.11 or higher** installed on the system path
- **uv (and uvx)** installed: ``curl -LsSf https://astral.sh/uv/install.sh | sh``

Verify both work before installing the extension:

.. code-block:: bash

   python --version    # 3.11+
   uvx --version       # any recent version

Zscaler OneAPI credentials (from the ZIdentity console):

- ``ZSCALER_CLIENT_ID``
- ``ZSCALER_CLIENT_SECRET``
- ``ZSCALER_VANITY_DOMAIN``
- ``ZSCALER_CUSTOMER_ID`` (required for ZPA tools)

Installation
------------

1. **Download the bundle.**

   The latest bundle is available from the project's `GitHub releases <https://github.com/zscaler/zscaler-mcp-server/releases>`_ as ``zscaler-mcp-server-<VERSION>.mcpb``.

2. **Open Claude Desktop's Extensions panel.**

   ``Claude → Settings → Extensions`` (or the equivalent menu on Linux/Windows).

3. **Drag the ``.mcpb`` file** into the Extensions panel. Claude Desktop validates the bundle's manifest and shows a confirmation dialog.

4. **Configure credentials.** The extension prompts for the four OneAPI environment variables. They're stored in Claude Desktop's secure credential store — not in the manifest, not in a config file on disk.

5. **Restart Claude Desktop** when prompted. The MCP server is registered automatically; on next launch, Zscaler tools are available.

Verifying the install
---------------------

In a Claude Desktop conversation, ask:

   *"What Zscaler tools are available?"*

Claude lists the registered tool categories. If the credentials work, it will mention each Zscaler service that's currently entitled on your tenant.

If the tools don't appear:

- **No tools listed at all.** Likely a ``uvx`` PATH issue — the extension can't find ``uvx``. Open a terminal, run ``which uvx``, and confirm the binary is on the system PATH that Claude Desktop inherits.
- **"Authentication failed" mentioned.** The credentials in the prompt are wrong, or the OneAPI client doesn't have permission against the tenant. Re-verify in the ZIdentity console.
- **Service-specific tools missing** (e.g. no ZMS tools). The entitlement filter has decided your tenant isn't licensed for that product. Run ``zscaler-mcp --no-entitlement-filter`` from a terminal to confirm — if the tools appear there, it's a licensing issue, not an extension issue.

Updating
--------

To update to a newer release:

1. Download the new ``.mcpb`` file.
2. In Claude Desktop's Extensions panel, drag the new file in. It replaces the existing extension.
3. Credentials are preserved across the update.

Uninstalling
------------

Open the Extensions panel and select ``Remove`` next to the Zscaler extension. Credentials in Claude Desktop's secure store are purged as part of the removal.

What's in the bundle
--------------------

The ``.mcpb`` file is a ZIP containing:

- ``manifest.json`` — Anthropic MCP-bundle manifest declaring the server entry point, every supported tool, prompts, and required environment variables.
- ``assets/icon.png`` — extension icon.
- The server source code itself is **not** bundled; the manifest declares ``uvx zscaler-mcp`` as the entry point, so the runtime pulls the package from PyPI on first launch.

This means the bundle is small (a few KB) and always tracks the latest published PyPI release.

Manifest generation
-------------------

The bundle is generated from the live tool inventory by:

.. code-block:: bash

   make build-mcpb

This runs ``--generate-docs`` (which refreshes ``manifest.json`` to track every currently-registered tool) and then packages the bundle as ``zscaler-mcp-server-<VERSION>.mcpb`` in the repo root. The bundle version always matches the ``zscaler_mcp.__version__`` string — no separate bump needed.

The Anthropic submission process
--------------------------------

Anthropic distributes Claude Desktop extensions via a curated approval workflow. To submit a new release:

1. Build the bundle: ``make build-mcpb``
2. Submit the resulting ``.mcpb`` file to Anthropic via the `Claude Extensions submission form <https://docs.anthropic.com/en/docs/claude-extensions/submitting-extensions>`_.

The submission is reviewed by an Anthropic engineer who validates the manifest and tests the install flow. There is no automated publication path today — every release requires a manual submission. This is consistent with how every other MCP extension is published to Claude Desktop.

References
----------

- `Claude Desktop Extensions docs <https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop>`_ — Anthropic's official documentation for the extension format.
- `MCP bundle spec <https://github.com/modelcontextprotocol/mcpb>`_ — the bundle format specification.

See also
--------

- :ref:`registries` — the broader catalog of registries where the server is published.
- :doc:`../security/mcp-client-auth` — for remote-server deployments (not addressable through this extension).
- :doc:`docker` — alternative local deployment via Docker.
