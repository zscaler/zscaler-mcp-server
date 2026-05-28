.. _official-mcp-registry:

Official MCP Registry
=====================

Direct link: `registry.modelcontextprotocol.io <https://registry.modelcontextprotocol.io/?q=zscaler>`__

The Model Context Protocol consortium maintains the canonical registry of MCP servers. The Zscaler server is published with both a PyPI package descriptor and a Docker image descriptor.

Packages declared
-----------------

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Type
     - Identifier
     - Runtime hint
   * - **PyPI**
     - ``zscaler-mcp``
     - ``uvx`` — recommended for local-process MCP clients (Claude Desktop, Cursor, Gemini CLI)
   * - **Docker (OCI)**
     - ``docker.io/zscaler/zscaler-mcp-server:latest``
     - ``docker`` — for containerized deployments

Ownership proof
---------------

Publication is driven by ``server.json`` at the repo root and is automated via ``mcp-publisher`` on every release. The package ownership proof lives in:

- ``README.md`` — contains ``<!-- mcp-name: io.github.zscaler/zscaler-mcp-server -->``
- ``Dockerfile`` — contains ``LABEL io.modelcontextprotocol.server.name="io.github.zscaler/zscaler-mcp-server"``

Both files are checked by the registry-publish job in CI.

Install in an MCP-compliant client
----------------------------------

Any spec-compliant MCP client can discover and install the Zscaler server via the registry. Configuration of credentials, transport, and host address is handled by the client itself.

For the publication workflow (manual + automated), see :doc:`github-mcp-registry`.

See also
--------

- :doc:`github-mcp-registry` — covers the same ``server.json`` from the GitHub side.
- :doc:`index` — back to the registries overview.
