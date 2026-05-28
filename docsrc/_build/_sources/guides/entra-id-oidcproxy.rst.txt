.. _guide-entra-id-oidcproxy:

Entra ID OIDCProxy
==================

Deploying the Zscaler MCP Server with **Microsoft Entra ID** as the OIDCProxy IdP. This is the deployment pattern for Microsoft-shop customers who want enterprise SSO for the MCP client (Claude Desktop, Cursor, etc.) without rolling Auth0 or Okta.

Why a dedicated guide
---------------------

Entra ID's OIDC behavior differs from Auth0 / Okta in one critical way: the ``aud`` (audience) claim in **ID tokens** is set to the **client_id**, not to a separate API identifier. Most OIDCProxy examples assume Auth0 semantics, where ``audience`` is a separate API resource. Configuring Entra ID with an Auth0-style ``audience`` value causes immediate 401 failures with confusing error messages.

This guide gives you the exact Entra ID values that work.

Prerequisites
-------------

- Microsoft Entra ID tenant (any Entra ID Free, P1, or P2 tier)
- Permission to register an application in Entra ID
- A running MCP server reachable at an HTTPS URL (Cloud Run, Container Apps, ECS, your own ingress, etc.)

Step 1 — Register an Entra ID application
-----------------------------------------

In the Azure portal:

1. **Entra ID → App registrations → New registration**
2. **Name**: ``Zscaler MCP Server``
3. **Supported account types**: usually "Accounts in this organizational directory only (Single tenant)"
4. **Redirect URI**: pick **Public client/native (mobile & desktop)** with the URI ``http://localhost:6274/callback``

   - This is the redirect URI that the ``mcp-remote`` CLI uses by default. Don't change it unless you've also overridden it in the client config.

5. Click **Register**.
6. On the application overview page, note the **Application (client) ID** and **Directory (tenant) ID** — you'll need both.

Step 2 — Enable the device code flow
------------------------------------

OIDCProxy delegates the auth flow to the MCP client. For ``mcp-remote``, that flow is the OAuth authorization-code flow with PKCE.

1. **Authentication** → **Add a platform** → **Mobile and desktop applications** (if not already added)
2. Check the box for the ``http://localhost:6274/callback`` redirect URI you registered
3. Under **Advanced settings**, enable **Allow public client flows** (set to **Yes**)
4. **Save**

Step 3 — Configure API permissions
----------------------------------

The token Entra ID issues needs to carry at least the ``openid`` and ``profile`` scopes.

1. **API permissions** → ``Microsoft Graph`` is added by default with ``User.Read``. Leave it.
2. **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions** → check **openid** and **profile** → **Add permissions**.

Step 4 — Deploy the MCP server with OIDCProxy
---------------------------------------------

Set the OIDCProxy environment variables on your MCP server deployment:

.. code-block:: bash

   # Entra ID values
   export OIDCPROXY_AUTH_ISSUER="https://login.microsoftonline.com/<TENANT_ID>/v2.0"
   export OIDCPROXY_AUTH_AUTHORIZATION_ENDPOINT="https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/authorize"
   export OIDCPROXY_AUTH_TOKEN_ENDPOINT="https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token"
   export OIDCPROXY_AUTH_JWKS_URI="https://login.microsoftonline.com/<TENANT_ID>/discovery/v2.0/keys"

   # The key Entra ID difference: audience MUST equal client_id
   export OIDCPROXY_AUTH_AUDIENCE="<CLIENT_ID>"

   # Standard OIDC scopes
   export OIDCPROXY_AUTH_SCOPES="openid profile offline_access"

   # MCP server settings (HTTP transport + auth disabled, since OIDCProxy is the auth)
   export ZSCALER_MCP_AUTH_ENABLED=false
   export ZSCALER_MCP_ALLOW_HTTP=true     # if TLS is terminated upstream (Cloud Run, etc.)

Replace ``<TENANT_ID>`` with your Entra ID directory ID and ``<CLIENT_ID>`` with the application's client ID from Step 1.

The Entra-specific gotcha
-------------------------

.. warning::

   ``OIDCPROXY_AUTH_AUDIENCE`` must be **exactly equal to the client_id**, not a separate API identifier. Entra ID issues ID tokens whose ``aud`` claim is the client_id. If you set ``OIDCPROXY_AUTH_AUDIENCE`` to anything else, every token validation fails with a misleading ``invalid_audience`` error.

   This is the inverse of the Auth0 convention, where ``audience`` is a distinct API identifier and the client_id is *not* the right value.

Step 5 — Configure the MCP client
---------------------------------

Claude Desktop (``~/Library/Application Support/Claude/claude_desktop_config.json``):

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "https://your-mcp-server.example.com/mcp"
         ]
       }
     }
   }

Cursor (``~/.cursor/mcp.json``): same config — Cursor and Claude Desktop use the same ``mcp-remote`` flow for OIDCProxy auth.

Restart the MCP client. On the first MCP call, ``mcp-remote`` opens your browser to the Entra ID sign-in page; after consent, the client caches the refresh token and won't prompt again until it expires.

Verification
------------

Once configured, the server's startup banner should show:

.. code-block:: text

   [SECURITY] transport=streamable-http  auth=OIDCProxy (issuer=https://login.microsoftonline.com/<TENANT_ID>/v2.0)

And the first tool call from the MCP client should succeed without an additional credential prompt (after the initial browser-based sign-in).

Common errors
-------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Symptom
     - Likely cause
   * - 401 ``invalid_audience``
     - ``OIDCPROXY_AUTH_AUDIENCE`` is not equal to the client_id. See the warning above.
   * - 400 ``AADSTS70001: Application is not allowed for the user``
     - The user signing in is in a different Entra ID tenant than the app registration. Verify the supported account types in Step 1.
   * - Browser redirect fails to ``localhost:6274``
     - The redirect URI in the Entra ID app doesn't match the URI ``mcp-remote`` expects. Re-register the public-client redirect URI in Step 1.
   * - 403 from the MCP server after Entra ID sign-in succeeds
     - The auth middleware is still trying to validate the original Entra token. Make sure ``ZSCALER_MCP_AUTH_ENABLED=false`` is set — OIDCProxy is the auth layer; the standard middleware should be off.

See also
--------

- :doc:`../security/mcp-client-auth` — the full set of authentication modes, including JWT and api-key alternatives.
- :doc:`azure-deployment` — deploying the server to Azure Container Apps / VM / AKS.
- :doc:`../security/lifecycle` — credential rotation without container restart.
