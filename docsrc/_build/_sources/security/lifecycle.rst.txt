.. _security-lifecycle:

Process Lifecycle Management
============================

Operators can reconfigure a running server — locally or inside a Docker container — without recreating the container. Four CLI subcommands cover the full lifecycle:

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Command
     - Signal
     - What it does
   * - ``zscaler-mcp reload``
     - ``SIGHUP``
     - **Soft reload.** Re-reads ``.env`` and re-applies env-driven toggles. MCP sessions and the listening socket survive.
   * - ``zscaler-mcp restart``
     - ``SIGUSR2``
     - **Hard restart.** Re-reads ``.env``, then ``os.execvp``'s a fresh Python interpreter with the original argv. Same PID, fresh memory, fresh env, fresh module imports.
   * - ``zscaler-mcp status``
     - *(read-only)*
     - Print PID, uptime, transport, port, and ``.env`` path of the running server (or report none running).
   * - ``zscaler-mcp stop``
     - ``SIGTERM``
     - Clean shutdown. Same signal Docker uses. No respawn.

Lifecycle subcommands are **mutually exclusive** with the serve path — running ``zscaler-mcp`` with no subcommand starts the server as before.

When to reload vs restart
-------------------------

- **Reload (SIGHUP)** when you only flipped a runtime toggle: ``ZSCALER_MCP_LOG_TOOL_CALLS``, log level, or a non-credential env var. The Zscaler SDK client has no module-level cache — it's created on every tool call — so credential rotations land naturally on the next call. The auth middleware token cache is keyed by credential hash, so old entries miss the cache and re-validate against new values. MCP sessions survive.
- **Restart (SIGUSR2)** when you changed something read once at startup: rotated credentials, changed ``--toolsets`` selection, flipped ``--enable-write-tools``, swapped vanity domain, or anything that resolves the entitlement filter. Sessions die — clients reconnect.

The state of the server (sessions, sockets, in-flight requests) is preserved across reload and discarded across restart. Choose by **what you changed**, not by what's convenient.

The PID file
------------

When the server starts (after ``parse_args()`` succeeds, before ``server.run()``), it writes a JSON PID file containing the running PID, start time, transport, host:port, the resolved ``.env`` path, the original argv, and the Python interpreter path. The PID file is the source of truth for ``status``, ``reload``, ``restart``, and ``stop``.

Location priority:

1. ``--pid-file <path>`` / ``ZSCALER_MCP_PID_FILE``
2. ``/var/run/zscaler-mcp.pid`` (typical inside containers with write access)
3. ``/tmp/zscaler-mcp.pid``
4. ``~/.zscaler-mcp/server.pid`` (auto-created)

For multiple instances on the same host (e.g. one per port), set ``ZSCALER_MCP_PID_FILE=/tmp/zscaler-mcp-<port>.pid`` per instance.

Env-source classification
-------------------------

The ``status`` / ``reload`` / ``restart`` commands need to be honest about whether re-reading ``.env`` will actually change anything. The CLI classifies the env source on every invocation:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Label
     - What it means
   * - ``live``
     - ``.env`` is at the recorded path and exists. ``reload`` / ``restart`` will re-read it and pick up host-side edits.
   * - ``live (bind-mounted)``
     - Same as above but the path is ``/app/.env`` — i.e. you bind-mounted the file into the container.
   * - ``fresh-discovery``
     - The originally-recorded ``.env`` is gone but a new one is present at a default search path. ``restart`` will pick it up; ``reload`` will no-op.
   * - ``missing``
     - The originally-recorded ``.env`` is gone and no replacement exists. ``reload`` / ``restart`` will still run but won't change credentials. Typical of containers started with ``--env-file`` only.
   * - ``none``
     - No ``.env`` was ever discovered. Typical of AgentCore deployments using Secrets Manager.

The classifier surfaces this in the ``status`` output so operators don't have to guess.

The ``docker cp`` workflow
---------------------------

For a container already running without a bind mount, you can drop a ``.env`` in at any time:

.. code-block:: bash

   docker cp ./.env <container>:/app/.env
   docker exec <container> zscaler-mcp restart

The classifier reports ``fresh-discovery`` and ``restart`` execs a fresh process that picks up the newly-placed file. No container recreate needed.

Bind-mount workflow (recommended)
---------------------------------

For long-lived deployments, bind-mount the ``.env`` once at container start and you can edit it on the host whenever you want:

.. code-block:: bash

   docker run -d --name zscaler-mcp-server \
     --env-file /path/to/.env \              # boot-time injection
     -v /path/to/.env:/app/.env:ro \         # live re-read on restart
     -e ZSCALER_MCP_DOTENV_PATH=/app/.env \
     zscaler/zscaler-mcp-server:latest --transport streamable-http

   # Edit the file on the host
   $EDITOR /path/to/.env

   # Apply changes
   docker exec zscaler-mcp-server zscaler-mcp restart

Why ``--env-file`` alone doesn't work for live edits
----------------------------------------------------

``docker run --env-file=./.env …`` reads the host file **once** at ``docker run`` time and copies the values into the container's ``Config.Env`` metadata. After that moment, the container has no link to the host file — you could delete it on the host and the container still holds the values. ``docker stop && docker start <ctr>`` reuses ``Config.Env`` from metadata; it does **not** re-read the host file.

The only ways to change a running container's environment are:

1. ``docker rm`` + ``docker run`` (full recreate)
2. Bind-mount the file inside so PID 1 can re-read it on reload/restart
3. ``docker cp`` the file in, then ``zscaler-mcp restart``

The lifecycle subcommands work with (2) and (3). (1) is always available but disrupts sessions.

Cross-platform notes
--------------------

- **Linux / macOS**: full support.
- **Windows**: SIGHUP and SIGUSR2 don't exist. ``reload`` / ``restart`` print a clear error and exit ``2``. ``status`` reads the PID file. ``stop`` falls back to SIGTERM. Native Windows operators restart their supervisor (Docker Desktop, NSSM, etc.) directly. Container deployments are unaffected — the container OS is Linux regardless of host.

Signal summary
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Signal
     - Handler
     - Behaviour
   * - ``SIGHUP``
     - Custom
     - Soft reload. Re-reads ``.env``, re-applies env-driven toggles.
   * - ``SIGUSR2``
     - Custom
     - Hard restart via ``os.execvp``. Same PID, fresh process.
   * - ``SIGTERM``
     - Default (uvicorn)
     - Clean shutdown. Used by ``docker stop`` and ``zscaler-mcp stop``.
   * - ``SIGINT``
     - Default (uvicorn)
     - Same as SIGTERM. Used by Ctrl+C.

Environment summary
-------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Effect
   * - ``--pid-file`` / ``ZSCALER_MCP_PID_FILE``
     - Override the PID file location. Set per-instance when running multiple servers on the same host.
   * - ``--dotenv-path`` / ``ZSCALER_MCP_DOTENV_PATH``
     - Explicit path to the ``.env`` file. Recorded in the PID file so ``reload`` / ``restart`` re-read the same source.

See also
--------

- :doc:`../guides/audit-logging` — captures every tool call that lands during the session.
- :doc:`mcp-client-auth` — the auth middleware cache survives soft reloads and is re-keyed by credential hash.
- :doc:`../guides/troubleshooting` — diagnosing reload / restart failures.
