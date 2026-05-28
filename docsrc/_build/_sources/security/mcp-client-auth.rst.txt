.. _security-mcp-client-auth:

MCP Client Authentication
=========================

For HTTP transports (``sse`` and ``streamable-http``), the server enforces client authentication before any tool call is dispatched. This is a separate layer from Zscaler API authentication — MCP client auth controls **who can connect to your MCP server**, while OneAPI controls **how your server talks to Zscaler**.

.. important::

   MCP client authentication is **not applicable** when running under the ``stdio`` transport. Stdio sessions are local to the process that spawned them — there is no network surface to authenticate.

Five authentication modes
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 18 38 44

   * - Mode
     - When to use
     - Client header
   * - **API key**
     - Quick test deployments, internal-only services. Auto-generates a key on first run.
     - ``Authorization: Bearer <api-key>``
   * - **JWT**
     - You already have an OIDC IdP issuing JWTs for other services and want the MCP server to validate against the same JWKS.
     - ``Authorization: Bearer <JWT>``
   * - **Zscaler**
     - The same OneAPI credentials that the server uses for Zscaler APIs also gate client access. Cleanest for "ops uses Zscaler creds for everything" deployments.
     - ``Authorization: Basic base64(client_id:client_secret)`` *or* the legacy ``X-Zscaler-Client-ID`` / ``X-Zscaler-Client-Secret`` pair.
   * - **OIDCProxy**
     - OAuth 2.1 with Dynamic Client Registration. Lets clients like ``mcp-remote`` perform the full authorization flow against any OIDC IdP (Auth0, Okta, Microsoft Entra ID, Keycloak, Google, AWS Cognito, PingOne).
     - Handled automatically by the client (``mcp-remote``).
   * - **None**
     - Local development against a localhost bind. The default if no mode is selected and you're on ``127.0.0.1``.
     - No header.

Auto-detection
--------------

The auth subsystem auto-detects the mode from environment variables:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - If you set …
     - … the mode resolves to
   * - ``ZSCALER_MCP_AUTH_API_KEY``
     - ``api-key``
   * - ``ZSCALER_MCP_AUTH_JWKS_URI``
     - ``jwt``
   * - ``ZSCALER_MCP_AUTH_MODE=zscaler`` (no other auth vars)
     - ``zscaler``
   * - ``auth=`` parameter on ``ZscalerMCPServer`` (programmatic only)
     - ``OIDCProxy``

You can force a specific mode with ``ZSCALER_MCP_AUTH_MODE``.

API key mode
------------

The simplest mode. Generate or reuse a key, set it in the env, restart the server:

.. code-block:: bash

   # Auto-generate a fresh key
   zscaler-mcp --generate-auth-token

   # Or set your own
   export ZSCALER_MCP_AUTH_API_KEY="$(openssl rand -hex 32)"

   # Start the server
   zscaler-mcp --transport streamable-http

Client config (Claude Desktop / Cursor / Kiro):

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "https://your-server.example.com/mcp",
           "--header", "Authorization: Bearer YOUR_API_KEY"
         ]
       }
     }
   }

JWT mode
--------

Validate JWTs against an IdP's JWKS endpoint:

.. code-block:: bash

   export ZSCALER_MCP_AUTH_JWKS_URI="https://your-idp.example.com/.well-known/jwks.json"
   export ZSCALER_MCP_AUTH_AUDIENCE="zscaler-mcp"           # optional
   export ZSCALER_MCP_AUTH_ISSUER="https://your-idp.example.com/"  # optional

   zscaler-mcp --transport streamable-http

The server validates: signature, expiry, ``iss`` (if configured), ``aud`` (if configured). The JWKS is cached in-process with the standard ``Cache-Control`` honouring.

Zscaler mode
------------

The same OneAPI credentials used for Zscaler API access gate the MCP server itself. Clients authenticate with ``Authorization: Basic base64(client_id:client_secret)`` — the server validates by calling ``/oauth2/v1/token`` on the Zscaler IdP and caches the result for the token's lifetime (~1 hour).

.. code-block:: bash

   export ZSCALER_MCP_AUTH_MODE=zscaler
   zscaler-mcp --transport streamable-http

Client config:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "https://your-server.example.com/mcp",
           "--header", "Authorization: Basic BASE64_CLIENT_ID_COLON_SECRET"
         ]
       }
     }
   }

The legacy ``X-Zscaler-Client-ID`` + ``X-Zscaler-Client-Secret`` pair is still accepted and hits the same cache.

OIDCProxy mode (OAuth 2.1 + DCR)
--------------------------------

For deployments where the MCP client should perform a full authorization flow against an enterprise IdP. The server wraps any OAuth-conformant provider (Auth0, Okta, Microsoft Entra ID, Keycloak, Google, AWS Cognito, PingOne) and exposes the spec-mandated OAuth metadata endpoints.

The simplest local setup uses the project's bundled orchestration script:

.. code-block:: bash

   python local_dev/scripts/setup-oidcproxy-auth.py

The script reads your Auth0 (or other) credentials from ``.env``, builds the Docker image, starts the server with an inline OIDCProxy entrypoint, verifies the OAuth endpoints, and writes a working ``mcp-remote`` configuration into Claude Desktop and Cursor.

For Entra ID specifically (which sets ``aud`` to the client_id, unlike Auth0 which uses an API identifier), see :doc:`../guides/entra-id-oidcproxy` for the full walkthrough.

The cache
---------

The auth middleware caches successful validations by credential hash. Cache hits avoid the round-trip to the IdP. A credential rotation naturally misses the cache and re-validates against the new value — no restart needed.

When the entitlement filter is also enabled and the mode is ``zscaler``, the entitlement check reuses the same cache instead of issuing a second ``/oauth2/v1/token`` call.

Environment summary
-------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Effect
   * - ``ZSCALER_MCP_AUTH_ENABLED``
     - Master switch. Defaults to ``true`` for HTTP transports.
   * - ``ZSCALER_MCP_AUTH_MODE``
     - Forces a specific mode: ``api-key`` / ``jwt`` / ``zscaler``.
   * - ``ZSCALER_MCP_AUTH_API_KEY``
     - The API key (api-key mode).
   * - ``ZSCALER_MCP_AUTH_JWKS_URI``
     - JWKS URL (jwt mode).
   * - ``ZSCALER_MCP_AUTH_AUDIENCE``
     - Expected ``aud`` claim (jwt mode, optional).
   * - ``ZSCALER_MCP_AUTH_ISSUER``
     - Expected ``iss`` claim (jwt mode, optional).
   * - ``--generate-auth-token``
     - Generate and print a fresh API key, then exit.

See also
--------

- :doc:`tls-and-hardening` — host header allowlist, source-IP ACL, TLS configuration.
- :doc:`write-operations` — limiting what an authenticated agent can do.
- :doc:`../guides/entra-id-oidcproxy` — OIDCProxy deployment with Microsoft Entra ID.
