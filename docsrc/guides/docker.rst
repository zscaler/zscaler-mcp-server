.. _guide-docker:

Docker
======

The Zscaler MCP Server publishes an official Docker image to `Docker Hub <https://hub.docker.com/r/zscaler/zscaler-mcp-server>`_ and to the `Docker MCP Hub <https://hub.docker.com/mcp/server/zscaler-mcp-server/overview>`_. The image is the recommended deployment artifact for:

- Local development without polluting the host's Python environment
- Any HTTP-transport deployment (Cloud Run, Container Apps, Bedrock AgentCore, Kubernetes)
- Reproducible CI / test environments

The image
---------

The published image is:

.. code-block:: text

   zscaler/zscaler-mcp-server:latest      # most recent release
   zscaler/zscaler-mcp-server:0.12.2      # specific release
   zscaler/zscaler-mcp-server:master      # bleeding edge

Both ``amd64`` and ``arm64`` architectures are built — pull whichever your host runs.

Stdio transport (local MCP client)
----------------------------------

The classic local-development pattern. Your MCP client (Claude Desktop, Cursor, etc.) spawns ``docker run`` as the MCP server command:

.. code-block:: bash

   docker run -i --rm \
     --env-file /absolute/path/to/.env \
     zscaler/zscaler-mcp-server:latest

Equivalent MCP client config:

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

The ``-i`` keeps stdin open so the MCP client can speak over it. ``--rm`` cleans up the container when the client disconnects.

Streamable-HTTP transport (remote agent)
----------------------------------------

For a long-running server that any number of MCP clients can connect to:

.. code-block:: bash

   docker run -d --restart=unless-stopped \
     --name zscaler-mcp-server \
     -p 8000:8000 \
     --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest \
     --transport streamable-http --host 0.0.0.0 --port 8000

The server listens on ``http://localhost:8000/mcp``. From here, layer in authentication (:doc:`../security/mcp-client-auth`) and TLS (:doc:`../security/tls-and-hardening`) for any deployment that isn't localhost-only.

Making ``.env`` editable inside the container
---------------------------------------------

``docker run --env-file=./.env`` reads the host file **once** at ``docker run`` time and copies the values into the container's ``Config.Env`` metadata. The host file is no longer linked to the running container — you could delete it and the container still holds the values.

For deployments where you want to update credentials without recreating the container, **bind-mount** the file:

.. code-block:: bash

   docker run -d --restart=unless-stopped \
     --name zscaler-mcp-server \
     -p 8000:8000 \
     --env-file /path/to/.env \                # boot-time injection
     -v /path/to/.env:/app/.env:ro \           # live re-read on restart
     -e ZSCALER_MCP_DOTENV_PATH=/app/.env \
     zscaler/zscaler-mcp-server:latest \
     --transport streamable-http --host 0.0.0.0 --port 8000

To pick up host-side edits:

.. code-block:: bash

   $EDITOR /path/to/.env
   docker exec zscaler-mcp-server zscaler-mcp restart

See :doc:`../security/lifecycle` for the full lifecycle model.

The ``docker cp`` workflow
--------------------------

For a container already running without a bind mount, drop a ``.env`` in via ``docker cp``:

.. code-block:: bash

   docker cp ./.env zscaler-mcp-server:/app/.env
   docker exec zscaler-mcp-server zscaler-mcp restart

The lifecycle subsystem detects the freshly-placed file (env-source classification: ``fresh-discovery``) and the restart picks up the new credentials.

Generating an auth token from the image
---------------------------------------

For api-key mode deployments, the image can generate a fresh API key without you needing the package installed locally:

.. code-block:: bash

   docker run --rm \
     --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest \
     --generate-auth-token

Or via the Makefile shortcut on a clone of the repo:

.. code-block:: bash

   make docker-generate-auth-token

Listing available tools
-----------------------

The image responds to ``--list-tools`` like any other invocation:

.. code-block:: bash

   docker run --rm \
     --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest \
     --list-tools

Useful for auditing what an image version exposes before connecting an agent.

Toolset selection
-----------------

Toolset selection works exactly like the CLI — pass ``--toolsets`` or set ``ZSCALER_MCP_TOOLSETS`` in the env file:

.. code-block:: bash

   docker run -i --rm \
     --env-file /path/to/.env \
     zscaler/zscaler-mcp-server:latest \
     --toolsets zia_url_filtering,zpa_app_segments

See :doc:`../toolsets/index` for the full toolset catalog.

Health and readiness
--------------------

The HTTP transport exposes a health endpoint at ``GET /healthz`` (returns ``200 OK`` if the server is up). Use it for Kubernetes ``livenessProbe`` / ``readinessProbe`` and for Cloud Run minimum-instance keep-alive.

Image hardening
---------------

The published image:

- Runs as a non-root user
- Includes only the Python runtime + the ``zscaler-mcp`` distribution
- Does not bundle build tools, package managers, or shells beyond ``sh``
- Embeds the registry ownership label (``io.modelcontextprotocol.server.name``) for downstream registry checks

See also
--------

- :doc:`../security/tls-and-hardening` — TLS, host header, source-IP ACL
- :doc:`../security/mcp-client-auth` — adding authentication on top of HTTP transports
- :doc:`../security/lifecycle` — ``reload`` / ``restart`` / ``status`` / ``stop`` workflow inside the container
- :ref:`registries` — registry listings, including the Docker MCP Hub
