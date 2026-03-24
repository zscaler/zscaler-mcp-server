.. _troubleshooting-guide:

Troubleshooting Guide
======================

This guide covers common issues and solutions when using the Zscaler Integrations MCP Server.

.. tip::

   For the most up-to-date troubleshooting information, see the `Troubleshooting Guide on GitHub <https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/TROUBLESHOOTING.md>`__.

Installation Issues
--------------------

**"Command not found: zscaler-mcp"**

Install ``uv`` and use ``uvx`` to run the server:

.. code-block:: bash

   curl -LsSf https://astral.sh/uv/install.sh | sh
   uvx zscaler-mcp

Or install directly:

.. code-block:: bash

   uv tool install zscaler-mcp

If installed but not found, update your shell PATH.

**".env file not found"**

- Use **absolute paths**, not relative paths, when specifying the ``.env`` file location
- Verify the file exists: ``ls -la /path/to/.env``
- Check file permissions (should be readable)

Zscaler API Authentication
---------------------------

**"Authentication failed" / 401 Unauthorized**

1. Verify all 4 required OneAPI variables are set:

   - ``ZSCALER_CLIENT_ID``
   - ``ZSCALER_CLIENT_SECRET``
   - ``ZSCALER_CUSTOMER_ID``
   - ``ZSCALER_VANITY_DOMAIN``

2. Check that credentials are not expired
3. Ensure the API client has the necessary scopes in the ZIdentity console
4. For legacy auth: ``ZSCALER_USE_LEGACY=true`` must be set along with service-specific credentials

**"ZSCALER_CUSTOMER_ID required"**

``ZSCALER_CUSTOMER_ID`` is required for ZPA operations. If you only use ZIA/ZDX/ZCC, this can be omitted.

MCP Client Authentication
--------------------------

**Client receives 401 when connecting over HTTP**

1. Check ``ZSCALER_MCP_AUTH_ENABLED`` is ``true``
2. Verify ``ZSCALER_MCP_AUTH_MODE`` matches the client's authentication method
3. For ``api-key`` mode: Client must send ``Authorization: Bearer <key>`` with the correct key
4. For ``jwt`` mode: Verify the JWKS URI is reachable, issuer/audience match, and the token is not expired
5. For ``zscaler`` mode: Client must send valid Basic Auth or ``X-Zscaler-Client-ID``/``X-Zscaler-Client-Secret`` headers

**JWT token validation fails**

- Ensure ``ZSCALER_MCP_AUTH_JWKS_URI`` points to a reachable JWKS endpoint
- Verify ``ZSCALER_MCP_AUTH_ISSUER`` exactly matches the ``iss`` claim in your tokens
- Verify ``ZSCALER_MCP_AUTH_AUDIENCE`` exactly matches the ``aud`` claim
- Check that ``ZSCALER_MCP_AUTH_ALGORITHMS`` includes the algorithm used by your IdP (default: ``RS256``)

**Generate a test token:**

.. code-block:: bash

   zscaler-mcp --generate-auth-token

Network Security
-----------------

**Connection refused on non-localhost**

By default, the server blocks plaintext HTTP on non-localhost interfaces. Either:

- Configure TLS: Set ``ZSCALER_MCP_TLS_CERT_FILE`` and ``ZSCALER_MCP_TLS_KEY_FILE``
- Or allow HTTP explicitly: Set ``ZSCALER_MCP_ALLOW_HTTP=true`` (only if TLS is handled upstream)

**421 Misdirected Request / "Invalid Host header"**

The server validates ``Host`` headers to prevent DNS rebinding attacks. Fix:

- Add your hostname to ``ZSCALER_MCP_ALLOWED_HOSTS``: ``export ZSCALER_MCP_ALLOWED_HOSTS="myserver.example.com"``
- Or disable validation (not recommended): ``export ZSCALER_MCP_DISABLE_HOST_VALIDATION=true``
- Localhost variants (``localhost``, ``127.0.0.1``, ``::1``) are always allowed

**Client IP rejected / 403 Forbidden**

If ``ZSCALER_MCP_ALLOWED_SOURCE_IPS`` is configured:

- Ensure the client's IP is in the allowed list
- Use CIDR notation for ranges: ``10.0.0.0/8,192.168.1.0/24``
- Check if the client is behind a proxy (the server sees the proxy's IP)

Write Operations
-----------------

**Write tools not appearing**

1. Is ``ZSCALER_MCP_WRITE_ENABLED=true`` set?
2. Is ``ZSCALER_MCP_WRITE_TOOLS`` provided? This is **mandatory** — if empty, 0 write tools are registered
3. Do patterns match tool names? Use ``zscaler-mcp --list-tools`` to see all registered tools
4. Wildcards are supported: ``zpa_create_*``, ``zia_*``, ``zpa_delete_application_segment``

**Delete operations require confirmation**

All 33 delete operations require double confirmation:

1. AI agent permission dialog (``destructiveHint``)
2. Server-side confirmation via hidden ``kwargs`` parameter

To skip confirmations (advanced/CI use only): Set ``ZSCALER_MCP_SKIP_CONFIRMATIONS`` with an HMAC-SHA256 token. The confirmation window is controlled by ``ZSCALER_MCP_CONFIRMATION_TTL`` (default: 300 seconds).

Agent/Editor Issues
--------------------

**Claude Desktop: "MCP server not found"**

- Verify the ``.env`` file path is absolute and correct
- Check Claude Desktop logs: Help → View Logs
- Restart Claude Desktop completely (quit and reopen)

**Claude Desktop: Extension not working on Windows**

The one-click extension bundles macOS/Linux binaries. Use manual configuration with ``uvx`` instead:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "C:\\Users\\You\\.env", "zscaler-mcp"]
       }
     }
   }

**Windows: "'C:\\Program' is not recognized" (npx path issue)**

Paths with spaces break ``npx`` when called directly. Use ``cmd /c``:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "cmd",
         "args": ["/c", "npx", "-y", "mcp-remote", "http://server:8000/mcp"]
       }
     }
   }

**"Non-HTTPS URLs are only allowed for localhost" (mcp-remote)**

``mcp-remote`` enforces HTTPS for non-localhost URLs. Add ``--allow-http`` to the args:

.. code-block:: json

   {
     "args": ["-y", "mcp-remote", "http://server:8000/mcp", "--allow-http", "--header", "Authorization: Bearer sk-key"]
   }

**Self-signed certificate rejected (mcp-remote)**

When using self-signed certificates, add to the MCP server config:

.. code-block:: json

   {
     "env": { "NODE_TLS_REJECT_UNAUTHORIZED": "0" }
   }

**Cursor: Tools not appearing**

- Check Cursor's MCP logs: View → Output → MCP
- Verify the ``.env`` file path is absolute
- Config file location: ``~/.cursor/mcp.json`` (macOS/Linux) or ``%USERPROFILE%\.cursor\mcp.json`` (Windows)

Docker Issues
--------------

**"Server connection timeout" with Docker**

When using HTTP transports in Docker, always bind to ``0.0.0.0``:

.. code-block:: bash

   docker run --rm -p 8000:8000 --env-file /path/to/.env \
     quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0

**Port conflicts**

Change the port with ``--port``:

.. code-block:: bash

   docker run --rm -p 8001:8001 --env-file /path/to/.env \
     quay.io/zscaler/zscaler-mcp-server:latest --transport streamable-http --host 0.0.0.0 --port 8001

Debugging
----------

**Enable debug logging:**

.. code-block:: bash

   export ZSCALER_MCP_DEBUG="true"
   zscaler-mcp

**List all registered tools:**

.. code-block:: bash

   zscaler-mcp --list-tools

**Test the server manually:**

.. code-block:: bash

   # Start server with HTTP transport
   zscaler-mcp --transport streamable-http --host 127.0.0.1 --port 8000

   # Test health (in another terminal)
   curl http://127.0.0.1:8000/mcp

Getting Help
-------------

- `GitHub Issues <https://github.com/zscaler/zscaler-mcp-server/issues>`__
- `Zscaler Community <https://community.zscaler.com/>`__
- `Full Troubleshooting Guide (GitHub) <https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/guides/TROUBLESHOOTING.md>`__
