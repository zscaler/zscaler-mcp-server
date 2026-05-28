.. _guide-setup-script:

One-step setup script
=====================

`scripts/setup-mcp-server.py <https://github.com/zscaler/zscaler-mcp-server/blob/master/scripts/setup-mcp-server.py>`__ is the fastest way to get a working local Zscaler MCP Server. One command pulls the latest Docker image, starts the container with the right entrypoint for your chosen auth mode, verifies the endpoint, and writes the correct MCP server entry into every AI agent it can detect on your machine.

If you've never deployed an MCP server before, **start here**. Compared to running raw ``docker run`` commands (see :doc:`docker`), this script makes every decision interactively and never asks you to copy/paste a JSON snippet into a client config — it does that for you.

What it does
------------

1. Prompts for an **authentication mode** — ``jwt``, ``zscaler``, ``api-key``, ``oidcproxy``, or ``none``.
2. Prompts for a **transport** — ``streamable-http`` or ``stdio``. Incompatible combinations (anything other than ``none`` with ``stdio``) are rejected at the prompt with an explanation.
3. Prompts for a **``.env`` file** path, or collects credentials interactively if you don't have one.
4. **Pulls** ``zscaler/zscaler-mcp-server:latest`` from Docker Hub. No local build, no image modifications.
5. **Starts** the container with the right entrypoint and env wiring for the chosen auth mode. (For ``oidcproxy``, the entrypoint is replaced with an inline Python program that constructs the OIDCProxy auth provider — still using the same upstream image.)
6. **Verifies** the endpoint responds correctly for the chosen auth mode (HTTP transports only).
7. **Auto-detects installed AI agents** and offers to configure each one for you. Existing entries with the name ``zscaler-mcp-server`` are overwritten; nothing else in the config is touched.

Supported on macOS, Linux, and Windows.

Quick start
-----------

From a checkout of the repo:

.. code-block:: bash

   python3 scripts/setup-mcp-server.py

That's it. Follow the prompts.

The script is **idempotent** — re-run anytime to switch auth modes, refresh credentials, pick up a new image, or add a newly-installed AI agent to the configured set. Each re-run stops the old container, starts a fresh one, and rewrites the ``zscaler-mcp-server`` entry in every agent config.

Authentication modes
--------------------

.. list-table::
   :header-rows: 1
   :widths: 15 30 30 25

   * - Mode
     - What it is
     - Client sends
     - Image override
   * - ``jwt``
     - OAuth 2.0 client_credentials against an external IdP (Auth0). Server validates via JWKS.
     - ``Authorization: Bearer <jwt>``
     - None
   * - ``zscaler``
     - Server validates the request's Zscaler OneAPI credentials against ``/oauth2/v1/token`` (cached).
     - ``Authorization: Basic base64(client_id:client_secret)``
     - None
   * - ``api-key``
     - Static shared secret. Simplest to set up, weakest model.
     - ``Authorization: Bearer <api-key>``
     - None
   * - ``oidcproxy``
     - Full OAuth 2.1 + Dynamic Client Registration via FastMCP's ``OIDCProxy``. The MCP client (e.g. ``mcp-remote``) discovers ``/.well-known/...`` and runs the browser flow.
     - (none — handled by the client)
     - **Yes** — entrypoint replaced with an inline Python program
   * - ``none``
     - No authentication. Single-user local development only.
     - (nothing)
     - None

Transport modes
---------------

.. list-table::
   :header-rows: 1
   :widths: 22 50 28

   * - Transport
     - When to use
     - Compatible auth modes
   * - ``streamable-http``
     - The container runs as a long-lived HTTP server (recommended).
     - All modes
   * - ``stdio``
     - The AI agent spawns the container per session via ``docker run -i``.
     - ``none`` only

``stdio`` + any HTTP-bound auth mode is **rejected** at the prompt — there's no HTTP boundary for the auth middleware to enforce when the agent is talking to the container's stdio directly.

Common invocations
------------------

Fully interactive (recommended for the first run):

.. code-block:: bash

   python3 scripts/setup-mcp-server.py

Skip prompts when you already know the mode (great for re-runs and CI):

.. code-block:: bash

   python3 scripts/setup-mcp-server.py \
     --auth-mode zscaler \
     --transport streamable-http \
     --env-file .env

Refresh a JWT without re-pulling the image:

.. code-block:: bash

   python3 scripts/setup-mcp-server.py \
     --auth-mode jwt \
     --transport streamable-http \
     --env-file .env \
     --skip-pull

Test the configuration without touching any AI agent configs:

.. code-block:: bash

   python3 scripts/setup-mcp-server.py --skip-agent-config

CLI flags
---------

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Flag
     - Default
     - Purpose
   * - ``--auth-mode {jwt,zscaler,api-key,oidcproxy,none}``
     - (prompt)
     - Skip the auth-mode prompt.
   * - ``--transport {streamable-http,stdio}``
     - (prompt)
     - Skip the transport prompt.
   * - ``--env-file <path>``
     - (prompt)
     - Path to a ``.env`` file. The script auto-detects ``./.env`` and ``<repo>/.env`` if not specified.
   * - ``--port <port>``
     - ``8000``
     - HTTP port for the server.
   * - ``--container-name <name>``
     - ``zscaler-mcp-server``
     - Docker container name. Change this if you want to run multiple instances on the same host.
   * - ``--debug``
     - off
     - Enable ``FASTMCP_DEBUG`` inside the container.
   * - ``--skip-pull``
     - off
     - Skip ``docker pull`` and reuse the locally cached image.
   * - ``--skip-verify``
     - off
     - Skip endpoint verification (the HTTP smoke check).
   * - ``--skip-agent-config``
     - off
     - Don't touch any AI agent configs.
   * - ``--legacy-env-file``
     - off
     - Use the original ``--env-file``-only behaviour. By default the script also bind-mounts ``.env`` into ``/app/.env`` so ``zscaler-mcp restart`` inside the container can re-read host edits.

Environment file
----------------

The script accepts any ``.env`` file with ``KEY=value`` lines. ``#`` and ``;`` comments are tolerated, and so is ``export FOO=bar`` shell syntax — the script writes a sanitized copy for ``docker --env-file`` because Docker's parser is much stricter than typical ``.env`` loaders.

If you don't have a ``.env`` and don't want to make one, the script prompts for each required value interactively and writes a temporary ``.env`` that's deleted on exit.

Live reload (``.env`` bind-mount)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default the script **bind-mounts** the host ``.env`` at ``/app/.env`` inside the container, in addition to passing it via ``--env-file``. The ``--env-file`` seeds ``os.environ`` at container boot; the bind-mount makes the file re-readable from inside the container at runtime, so the lifecycle subcommands below pick up edits you make on the host without needing to recreate the container.

Reconfigure a running container
-------------------------------

The ``zscaler-mcp`` CLI inside the container exposes four lifecycle subcommands:

.. code-block:: bash

   $EDITOR .env

   docker exec zscaler-mcp-server zscaler-mcp reload
   docker exec zscaler-mcp-server zscaler-mcp restart
   docker exec zscaler-mcp-server zscaler-mcp status
   docker exec zscaler-mcp-server zscaler-mcp stop

.. list-table::
   :header-rows: 1
   :widths: 18 18 44 20

   * - Subcommand
     - Signal
     - What it does
     - Sessions
   * - ``reload``
     - SIGHUP
     - Re-reads the bind-mounted ``.env`` with ``override=True`` and re-applies env-driven toggles. The listening socket and active MCP sessions survive.
     - Survive
   * - ``restart``
     - SIGUSR2
     - Re-reads ``.env``, then ``os.execvp`` a fresh Python interpreter with the original argv — same PID (Docker doesn't notice), fresh memory, fresh env.
     - Drop — clients reconnect
   * - ``status``
     - (none)
     - Prints PID, uptime, transport, ``.env`` path, and whether reload/restart will actually pick up env changes.
     - Unaffected
   * - ``stop``
     - SIGTERM
     - Clean shutdown, no respawn — same path ``docker stop`` uses.
     - Drop

Important: env vars are only "live" when ``.env`` is bind-mounted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Env vars passed via ``--env-file`` are read **once** by Docker at ``docker run`` time and copied into the container's ``Config.Env`` metadata. After that moment, PID 1's ``os.environ`` is fixed for the life of that container — ``docker stop && docker start`` re-uses the same ``Config.Env``, it does NOT re-read your host's ``.env``.

What gets written to your AI agents
-----------------------------------

Each detected agent gets an ``mcpServers`` entry (or ``servers`` for VS Code) called ``zscaler-mcp-server``. Existing entries with that name are overwritten; nothing else in the config is touched.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Agent
     - Config path (macOS)
   * - Claude Desktop
     - ``~/Library/Application Support/Claude/claude_desktop_config.json``
   * - Claude Code (CLI)
     - ``~/.claude.json``
   * - Cursor
     - ``~/.cursor/mcp.json``
   * - Gemini CLI
     - ``~/.gemini/settings.json``
   * - VS Code
     - ``~/Library/Application Support/Code/User/mcp.json``
   * - Windsurf
     - ``~/.codeium/windsurf/mcp_config.json``
   * - GitHub Copilot CLI
     - ``~/Library/Application Support/github-copilot/mcp.json``

Windows and Linux paths follow each agent's standard locations.

After the script finishes
~~~~~~~~~~~~~~~~~~~~~~~~~

**Restart any AI agent it configured.** Most agents only read MCP config at startup. For CLI-based agents (Claude Code, Gemini CLI, Copilot CLI) it's usually enough to open a fresh shell.

Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Symptom
     - Fix
   * - ``Docker is not installed``
     - Install Docker Desktop: https://docs.docker.com/get-docker/
   * - ``docker pull`` fails
     - Check network access to Docker Hub. Use ``--skip-pull`` if you've cached the image.
   * - ``Endpoint returned 401``
     - Credentials don't match what the server expects. Re-check the ``.env`` and re-run.
   * - ``Could not reach localhost:8000``
     - Container failed to stay running. Inspect: ``docker logs zscaler-mcp-server``
   * - Agent doesn't see the server after restart
     - Confirm the agent reads from the path the script printed. Some agents (VS Code) need an MCP-aware extension installed.

When to use raw ``docker run`` instead
--------------------------------------

The setup script optimizes for "the agent should just work on the first try." If you want to integrate the server into existing infrastructure (Compose, Kubernetes, systemd, an init container), skip the script and use the raw :doc:`docker` reference instead — it shows every flag the container actually needs.
