.. _guide-entra-id-oidcproxy:

Entra ID OIDC
=============

Deploying the Zscaler MCP Server with **Microsoft Entra ID** as the OIDC identity provider. This is the deployment pattern for Microsoft-shop customers who want enterprise SSO for the MCP client (Claude Desktop, Cursor, etc.) without rolling Auth0 or Okta.

In ``oidc`` mode the server is an OAuth 2.0 **protected resource** (`RFC 9728 <https://www.rfc-editor.org/rfc/rfc9728.html>`_). It issues no tokens and runs no login flow: it publishes one metadata document naming Entra ID as the authorization server, and verifies the tokens clients bring. The MCP client performs the OAuth flow directly against Entra ID.

.. note::

   The server holds **no credential**. Verifying a signature requires Entra ID's public keys, not a secret of ours, so there is no client secret to create, store, or rotate.

Why a dedicated guide
---------------------

Entra ID's OIDC behavior differs from Auth0 / Okta in one critical way: the ``aud`` (audience) claim is set to the **client_id**, not to a separate API identifier. Most OIDC examples assume Auth0 semantics, where the audience is a distinct API resource. Configuring Entra ID with an Auth0-style audience value causes immediate 401 failures with confusing error messages.

This guide gives you the exact Entra ID values that work.

Prerequisites
-------------

- Microsoft Entra ID tenant (any Entra ID Free, P1, or P2 tier)
- Permission to register an application in Entra ID, and to grant admin consent
- A running MCP server reachable at an HTTPS URL (Cloud Run, Container Apps, ECS, your own ingress, etc.)

Step 1 — Register an Entra ID application
-----------------------------------------

The application represents the **MCP client**, which is the OAuth client in this design. In the Azure portal:

1. **Entra ID → App registrations → New registration**
2. **Name**: ``Zscaler MCP Server``
3. **Supported account types**: usually "Accounts in this organizational directory only (Single tenant)"
4. **Redirect URI**: pick **Mobile and desktop applications** (a public client) with the URI ``http://localhost:3334/oauth/callback``

   - Register whatever URI your client actually uses. For ``mcp-remote`` that means pinning the port: despite what its README says it has no fixed default, and unless you pass one it derives the port from a hash of the server URL (``3335 + hash % 45816``), so it will never choose 3334. Pass ``3334`` as the **first argument after the server URL** — in any other position it is parsed as a port, silently yields ``NaN``, and the derived port is used instead with no warning. Entra ID compares ``redirect_uri`` byte-for-byte, so a derived port fails every login.

5. Click **Register**.
6. On the application overview page, note the **Application (client) ID** and **Directory (tenant) ID** — you'll need both.

.. important::

   The redirect URI belongs to the **client**, not to the server, so it is a ``localhost`` address and stays the same no matter where the server is deployed. Earlier revisions of this guide used ``<server>/auth/callback``, which was correct only while the server itself was the OAuth client.

Step 2 — Allow public client flows
----------------------------------

The MCP client is a public client using the authorization-code flow with PKCE — it holds no secret.

1. **Authentication** → confirm the ``http://localhost:3334/oauth/callback`` redirect URI is listed under **Mobile and desktop applications**
2. Under **Advanced settings**, set **Allow public client flows** to **Yes**
3. **Save**

Step 3 — Configure API permissions
----------------------------------

The token Entra ID issues needs to carry at least the ``openid`` and ``profile`` scopes.

1. **API permissions** → ``Microsoft Graph`` is added by default with ``User.Read``. Leave it.
2. **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions** → check **openid** and **profile** → **Add permissions**.
3. **Grant admin consent for [your organization]**.

Step 4 — Deploy the MCP server
------------------------------

Configuration is environment variables only — no wrapper script and no extra packages:

.. code-block:: bash

   export ZSCALER_MCP_AUTH_ENABLED=true
   export ZSCALER_MCP_AUTH_MODE=oidc

   # The IdP's discovery document. Issuer and JWKS URI are read from it at startup.
   export OIDCPROXY_CONFIG_URL="https://login.microsoftonline.com/<TENANT_ID>/v2.0/.well-known/openid-configuration"

   # The app registration's client ID — also supplies the default audience.
   export OIDCPROXY_CLIENT_ID="<CLIENT_ID>"

   # THIS server's public URL: the OAuth resource identifier clients use.
   export OIDCPROXY_BASE_URL="https://your-mcp-server.example.com"

   export ZSCALER_MCP_ALLOW_HTTP=true     # only if TLS is terminated upstream (Cloud Run, etc.)

Replace ``<TENANT_ID>`` with your Entra ID directory ID and ``<CLIENT_ID>`` with the application's client ID from Step 1.

The variables keep their historical ``OIDCPROXY_`` prefix so existing deployments keep working. ``OIDCPROXY_CLIENT_SECRET`` is ignored if it is still set, and can be deleted.

The Entra-specific gotcha
-------------------------

.. warning::

   The expected audience must be **exactly equal to the client_id**, not a separate API identifier. Entra ID issues tokens whose ``aud`` claim is the client_id. Because ``OIDCPROXY_AUDIENCE`` defaults to ``OIDCPROXY_CLIENT_ID``, the correct behaviour is simply to omit it — set it explicitly only on IdPs that use an API identifier, like Auth0.

   The server refuses to start if it can determine neither, because accepting any audience would mean a token your IdP issued for an unrelated application would be honoured here.

Step 5 — Configure the MCP client
---------------------------------

Entra ID does not support Dynamic Client Registration, so the client needs the client ID from Step 1. Claude Desktop (``~/Library/Application Support/Claude/claude_desktop_config.json``):

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "https://your-mcp-server.example.com/mcp", "3334",
           "--static-oauth-client-info", "{\"client_id\":\"<CLIENT_ID>\"}"
         ]
       }
     }
   }

The ``"3334"`` pins the OAuth callback port and has to stay immediately after the URL — that is the only position ``mcp-remote`` reads it from, and elsewhere it is ignored silently, leaving a derived port that Entra ID will reject as an unregistered ``redirect_uri``.

Cursor (``~/.cursor/mcp.json``): same approach — Cursor and Claude Desktop both use the ``mcp-remote`` flow.

Note there is no ``Authorization`` header. Restart the MCP client; on the first MCP call ``mcp-remote`` opens your browser to the Entra ID sign-in page, and after consent it caches the refresh token and won't prompt again until it expires.

Verification
------------

The startup log states exactly what the server will accept:

.. code-block:: text

   OIDC auth configured as a protected resource (issuer=https://login.microsoftonline.com/<TENANT_ID>/v2.0, resource=https://your-mcp-server.example.com, audience=<CLIENT_ID>)

The metadata document should name your tenant as the authorization server:

.. code-block:: bash

   curl -s https://your-mcp-server.example.com/.well-known/oauth-protected-resource

.. code-block:: json

   {
     "resource": "https://your-mcp-server.example.com",
     "authorization_servers": ["https://login.microsoftonline.com/<TENANT_ID>/v2.0"],
     "bearer_methods_supported": ["header"]
   }

``/.well-known/oauth-authorization-server``, ``/register``, ``/authorize`` and ``/token`` are *supposed* to return 404 — this server is a protected resource, not an authorization server.

Common errors
-------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Symptom
     - Likely cause
   * - 401 ``invalid_token`` after a successful sign-in
     - Audience or issuer mismatch. Compare the token's ``aud`` / ``iss`` against the startup log line above. For Entra ID, ``aud`` is the client_id.
   * - Server exits with ``oidc auth mode requires: …``
     - Required configuration is missing. ``OIDCPROXY_BASE_URL`` is *this server's* public URL, not the IdP's.
   * - ``Could not read the IdP's OpenID configuration``
     - Wrong tenant ID in the discovery URL, or no egress from the server's host to ``login.microsoftonline.com``.
   * - ``AADSTS50011: redirect URI … does not match``
     - The client's callback isn't registered. The error names the ``redirect_uri`` received — register exactly that as a public-client URI.
   * - ``AADSTS700016: Application with identifier … was not found``
     - Wrong client ID or tenant ID.
   * - ``AADSTS70001: Application is not allowed for the user``
     - The signing-in user is in a different tenant than the app registration. Check the supported account types in Step 1.
   * - ``/.well-known/oauth-protected-resource`` returns 404
     - The server isn't running in ``oidc`` mode. Check ``ZSCALER_MCP_AUTH_MODE``.

See also
--------

- :doc:`../security/mcp-client-auth` — the full set of authentication modes, including JWT and api-key alternatives.
- :doc:`azure-deployment` — deploying the server to Azure Container Apps / VM / AKS.
- :doc:`../security/lifecycle` — credential rotation without container restart.
