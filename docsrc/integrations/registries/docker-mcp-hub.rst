.. _docker-mcp-hub:

Docker MCP Hub
==============

Direct link: `hub.docker.com/mcp/server/zscaler-mcp-server <https://hub.docker.com/mcp/server/zscaler-mcp-server/overview>`__

Docker maintains a curated MCP server catalog. The Zscaler image is published with three tag families:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Tag
     - Use case
   * - ``latest``
     - Most recent stable release. **Recommended** for local dev and quick-start tests.
   * - ``X.Y.Z`` (e.g. ``0.12.2``)
     - Each released version. **Recommended** for production — pin to a known version.
   * - ``master``
     - Bleeding edge from the ``master`` branch. Built on every commit. For development only.

The image works with every MCP client that supports the ``docker`` transport pattern:

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

HTTP-transport deployments
--------------------------

When deploying as an HTTP service (Bedrock AgentCore, Cloud Run, Container Apps, Kubernetes), pull the same image and pass ``--transport streamable-http``:

.. code-block:: bash

   docker run -d --name zscaler-mcp-server \
     --env-file /path/to/.env \
     -p 8000:8000 \
     zscaler/zscaler-mcp-server:latest \
     --transport streamable-http --host 0.0.0.0

For full deployment guides, see the per-platform branches under :doc:`../../deployment/index`.

See also
--------

- :doc:`../../deployment/index` — every cloud and Kubernetes deployment target uses this same image.
- :doc:`index` — back to the registries overview.
