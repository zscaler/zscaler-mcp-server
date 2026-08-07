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
   * - **OIDC**
     - OAuth 2.1 with a browser login. The server is an OAuth 2.0 protected resource (`RFC 9728 <https://www.rfc-editor.org/rfc/rfc9728.html>`_) and clients like ``mcp-remote`` run the authorization flow directly against any OIDC IdP (Auth0, Okta, Microsoft Entra ID, Keycloak, Google, AWS Cognito, PingOne).
     - Handled by the client, which obtains and attaches the Bearer token itself.
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
   * - ``ZSCALER_MCP_AUTH_MODE=oidc`` (``oidcproxy`` / ``oauth-proxy`` are accepted aliases)
     - ``oidc``

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

OIDC mode (OAuth 2.1)
---------------------

For deployments where the MCP client should perform a browser login against an enterprise IdP. The server declares itself an OAuth 2.0 **protected resource** (`RFC 9728 <https://www.rfc-editor.org/rfc/rfc9728.html>`_): it publishes one metadata document naming your IdP as the authorization server, and verifies the tokens clients present against that IdP's public keys.

It is not an authorization server. Two routes exist — ``/.well-known/oauth-protected-resource`` and ``/mcp`` — and ``/authorize``, ``/token`` and ``/register`` deliberately return 404. An unauthenticated request to ``/mcp`` answers ``401`` with a ``WWW-Authenticate`` header naming the metadata URL, which is how the client discovers where to log in.

Configuration is environment variables only:

.. code-block:: bash

   export ZSCALER_MCP_AUTH_ENABLED=true
   export ZSCALER_MCP_AUTH_MODE=oidc

   export OIDCPROXY_CONFIG_URL="https://your-idp.example.com/.well-known/openid-configuration"
   export OIDCPROXY_CLIENT_ID="<client id>"
   export OIDCPROXY_BASE_URL="https://mcp.example.com"

**No client secret.** Verifying a signature needs the IdP's public keys, not a credential of ours, so there is nothing to store or rotate on the server. The issuer and JWKS URI are read from the IdP's discovery document at startup, so they always match what it actually signs with — the server fails fast on a misconfigured IdP rather than on the first request.

The trade-off is that this server no longer proxies Dynamic Client Registration; a client that cannot self-register **at the IdP** needs a client ID from it (``mcp-remote --static-oauth-client-info``). Entra ID never supports DCR, and Auth0 supports it but ships with it disabled, so in practice a static client ID is the common case. When one is used, also pin the client's callback port so its redirect URI can be registered in advance — see :doc:`../guides/entra-id-oidcproxy`.

Entra ID needs more than a different audience value, and none of it is discoverable from an error message. Beyond setting ``aud`` to the client_id (unlike Auth0's API identifier), it issues **v1 access tokens by default** — whose issuer does not match its own v2.0 discovery document — and it matches the OAuth ``resource`` parameter against a registered Application ID URI while refusing to register any URI that ends in a slash, so ``OIDCPROXY_BASE_URL`` has to carry a path rather than being a bare origin. See :doc:`../guides/entra-id-oidcproxy` for the full walkthrough.

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
     - Forces a specific mode: ``api-key`` / ``jwt`` / ``zscaler`` / ``oidc``.
   * - ``ZSCALER_MCP_AUTH_API_KEY``
     - The API key (api-key mode).
   * - ``ZSCALER_MCP_AUTH_JWKS_URI``
     - JWKS URL (jwt mode).
   * - ``ZSCALER_MCP_AUTH_AUDIENCE``
     - Expected ``aud`` claim (jwt mode, optional).
   * - ``ZSCALER_MCP_AUTH_ISSUER``
     - Expected ``iss`` claim (jwt mode, optional).
   * - ``OIDCPROXY_CONFIG_URL``
     - The IdP's OIDC discovery URL (oidc mode).
   * - ``OIDCPROXY_BASE_URL``
     - This server's public URL — the OAuth resource identifier (oidc mode).
   * - ``OIDCPROXY_CLIENT_ID``
     - The app registration's client ID; also supplies the default audience (oidc mode).
   * - ``OIDCPROXY_AUDIENCE``
     - Required ``aud`` claim. Defaults to ``OIDCPROXY_CLIENT_ID`` (oidc mode).
   * - ``OIDCPROXY_REQUIRED_SCOPES``
     - Comma-separated scopes a token must carry (oidc mode, optional).
   * - ``--generate-auth-token``
     - Generate and print a fresh API key, then exit.

See also
--------

- :doc:`tls-and-hardening` — host header allowlist, source-IP ACL, TLS configuration.
- :doc:`write-operations` — limiting what an authenticated agent can do.
- :doc:`../guides/entra-id-oidcproxy` — OIDC deployment with Microsoft Entra ID.
