.. _guide-entra-id-oidcproxy:

Entra ID OIDC
=============

Deploying the Zscaler MCP Server with **Microsoft Entra ID** as the OIDC identity provider. This is the deployment pattern for Microsoft-shop customers who want enterprise SSO for the MCP client (Claude Desktop, Cursor, etc.) without rolling Auth0 or Okta.

In ``oidc`` mode the server is an OAuth 2.0 **protected resource** (`RFC 9728 <https://www.rfc-editor.org/rfc/rfc9728.html>`_). It issues no tokens and runs no login flow: it publishes one metadata document naming Entra ID as the authorization server, and verifies the tokens clients bring. The MCP client performs the OAuth flow directly against Entra ID.

.. note::

   The server holds **no credential**. Verifying a signature requires Entra ID's public keys, not a secret of ours, so there is no client secret to create, store, or rotate.

Why a dedicated guide
---------------------

Entra ID diverges from Auth0 / Okta in three ways, and each one produces a different confusing failure if you follow a generic OIDC example:

1. **The audience is the client ID**, not a separate API identifier. Configuring an Auth0-style audience causes immediate 401s.
2. **Entra ID issues v1 access tokens by default**, whose ``iss`` claim does not match the issuer published in its own v2.0 discovery document. Every token is rejected until you opt into v2.
3. **The resource identifier must contain a path.** Entra ID matches the OAuth ``resource`` parameter against a registered Application ID URI and refuses to register any URI ending in a slash — which is exactly what a client sends when the resource is a bare origin.

Points 2 and 3 are absolute: no client-side configuration works around either. This guide gives you the exact values that do work.

Prerequisites
-------------

- Microsoft Entra ID tenant (any Entra ID Free, P1, or P2 tier)
- Permission to register an application in Entra ID, and to grant admin consent
- A running MCP server reachable at an HTTPS URL (Cloud Run, Container Apps, ECS, your own ingress, etc.)

Throughout this guide, replace:

- ``<TENANT_ID>`` — your Entra **Directory (tenant) ID**
- ``<CLIENT_ID>`` — the app registration's **Application (client) ID**
- ``https://your-mcp-server.example.com/mcp`` — your server's **full MCP endpoint URL, including the path**

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

   The **Directory (tenant) ID** is not your **Subscription ID**. They are both GUIDs on adjacent portal blades and are easy to confuse. A subscription ID in the discovery URL fails at server startup with ``AADSTS90002: Tenant '<guid>' not found``. Confirm with ``az account show --query tenantId -o tsv``.

.. important::

   The redirect URI belongs to the **client**, not to the server, so it is a ``localhost`` address and stays the same no matter where the server is deployed. Earlier revisions of this guide used ``<server>/auth/callback``, which was correct only while the server itself was the OAuth client.

Step 2 — Allow public client flows
----------------------------------

The MCP client is a public client using the authorization-code flow with PKCE — it holds no secret.

1. **Authentication** → confirm the ``http://localhost:3334/oauth/callback`` redirect URI is listed under **Mobile and desktop applications**
2. Under **Advanced settings**, set **Allow public client flows** to **Yes**
3. **Save**

Step 3 — Expose the server as an API
------------------------------------

This step is **mandatory** and is the one most often missed. Entra ID will only mint an access token whose audience is your application if the client requests a scope belonging to your application. That requires an Application ID URI and at least one delegated scope.

**Entra ID → App registrations → your app → Expose an API**

1. **Application ID URI** → **Add** → replace the suggested ``api://<CLIENT_ID>`` with your server's full MCP endpoint URL:

   .. code-block:: text

      https://your-mcp-server.example.com/mcp

2. **Add a scope**:

   - **Scope name**: ``mcp.access``
   - **Who can consent**: *Admins and users*
   - **Admin consent display name**: ``Access the Zscaler MCP server``
   - **Admin consent description**: ``Allows the signed-in user to call the Zscaler MCP server.``
   - **State**: Enabled

The scope's fully-qualified name is the App ID URI and the scope name joined by a slash — that concatenation is the value the client must request:

.. code-block:: text

   https://your-mcp-server.example.com/mcp/mcp.access

.. warning::

   **The Application ID URI must include the path and must not end in a slash.** Both halves of that sentence are load-bearing.

   The client sends the resource identifier from the server's metadata as the OAuth ``resource`` parameter, serialized through the WHATWG URL parser. That parser normalizes a bare origin by appending a slash, so ``https://host`` becomes ``https://host/``. Entra ID then compares ``resource`` byte-for-byte against your registered Application ID URIs and rejects the request with ``AADSTS9010010`` — while simultaneously refusing to let you register the slashed form at all (``IdentifierUrisEndsWithSlash: ValueCannotEndWithSlash``).

   A URI that already has a path is left alone by the parser: ``https://host/mcp`` stays ``https://host/mcp``. That is why the resource identifier must be the full MCP endpoint URL rather than the server's origin.

Equivalent CLI, if you prefer not to click through the portal:

.. code-block:: bash

   az rest --method PATCH \
     --uri "https://graph.microsoft.com/v1.0/applications(appId='<CLIENT_ID>')" \
     --headers 'Content-Type=application/json' \
     --body '{"identifierUris":["https://your-mcp-server.example.com/mcp"]}'

   az rest --method PATCH \
     --uri "https://graph.microsoft.com/v1.0/applications(appId='<CLIENT_ID>')" \
     --headers 'Content-Type=application/json' \
     --body '{"api":{"oauth2PermissionScopes":[{
        "id":"'"$(uuidgen | tr 'A-Z' 'a-z')"'",
        "value":"mcp.access","type":"User","isEnabled":true,
        "adminConsentDisplayName":"Access the Zscaler MCP server",
        "adminConsentDescription":"Allows the signed-in user to call the Zscaler MCP server.",
        "userConsentDisplayName":"Access the Zscaler MCP server",
        "userConsentDescription":"Allows you to call the Zscaler MCP server."}]}}'

Step 4 — Request v2 access tokens
---------------------------------

Entra ID's ``requestedAccessTokenVersion`` defaults to ``null``, which means **v1**. A v1 access token carries ``iss: https://sts.windows.net/<TENANT_ID>/``, but the server reads its expected issuer from the v2.0 discovery document, which publishes ``https://login.microsoftonline.com/<TENANT_ID>/v2.0``. The mismatch rejects every token with ``401 invalid_token`` even though sign-in succeeded.

**Entra ID → App registrations → your app → Manifest**, then set:

.. code-block:: json

   { "api": { "requestedAccessTokenVersion": 2 } }

In the older AAD manifest view the same setting appears as a top-level ``"accessTokenAcceptedVersion": 2``.

Or via CLI:

.. code-block:: bash

   az rest --method PATCH \
     --uri "https://graph.microsoft.com/v1.0/applications(appId='<CLIENT_ID>')" \
     --headers 'Content-Type=application/json' \
     --body '{"api":{"requestedAccessTokenVersion":2}}'

.. note::

   Entra ID refuses this change while the Application ID URI uses the legacy ``https://<tenant>/<app>`` form. Set the App ID URI as described in Step 3 first, then apply the token version.

.. important::

   With ``requestedAccessTokenVersion: 2``, the ``aud`` claim is the **client ID GUID** — *not* the Application ID URI, even though the client requested a scope named after that URI. This is the Entra-specific behaviour called out at the top of this guide, and it is why the expected audience stays the client ID.

Step 5 — Configure API permissions
----------------------------------

The default ``Microsoft Graph → User.Read`` delegated permission added at registration is sufficient; ``openid`` and ``profile`` are always available and need no grant. Add nothing else — the scope that matters is your own from Step 3, not a Graph permission.

If your tenant requires admin consent for user-consentable scopes, grant it now: **API permissions → Grant admin consent for [your organization]**. Otherwise each user consents once at first sign-in.

Step 6 — Deploy the MCP server
------------------------------

Configuration is environment variables only — no wrapper script and no extra packages:

.. code-block:: bash

   export ZSCALER_MCP_AUTH_ENABLED=true
   export ZSCALER_MCP_AUTH_MODE=oidc

   # The IdP's discovery document. Issuer and JWKS URI are read from it at startup.
   export OIDCPROXY_CONFIG_URL="https://login.microsoftonline.com/<TENANT_ID>/v2.0/.well-known/openid-configuration"

   # The app registration's client ID — also supplies the default audience.
   export OIDCPROXY_CLIENT_ID="<CLIENT_ID>"

   # THIS server's OAuth resource identifier. For Entra ID it MUST include the
   # MCP path and MUST match the Application ID URI from Step 3 exactly.
   export OIDCPROXY_BASE_URL="https://your-mcp-server.example.com/mcp"

   export ZSCALER_MCP_ALLOW_HTTP=true     # only if TLS is terminated upstream (Cloud Run, etc.)

The variables keep their historical ``OIDCPROXY_`` prefix so existing deployments keep working. ``OIDCPROXY_CLIENT_SECRET`` is ignored if it is still set, and can be deleted.

.. warning::

   ``OIDCPROXY_BASE_URL`` must be the **full MCP endpoint URL including the path**, and must be byte-identical to the Application ID URI registered in Step 3. On other IdPs the server's origin is a fine resource identifier; on Entra ID it cannot work, for the trailing-slash reason explained in Step 3.

   Setting the path also moves the metadata document, by design: it is published at ``/.well-known/oauth-protected-resource/mcp`` rather than ``/.well-known/oauth-protected-resource``. Clients find it either way — they probe the path-suffixed form first, and the 401 challenge names the exact URL in its ``resource_metadata`` parameter.

.. warning::

   **Do not set** ``OIDCPROXY_REQUIRED_SCOPES`` on Entra ID. That variable does double duty: it is published as ``scopes_supported`` in the metadata document *and* enforced against the token by exact string match. Entra ID advertises the fully-qualified ``https://your-mcp-server.example.com/mcp/mcp.access`` but issues ``scp: "mcp.access"`` — the short name only. Setting it therefore gets a user past sign-in and then fails the call with ``403 insufficient_scope``. Supply the scope from the client instead, as in Step 7.

Step 7 — Configure the MCP client
---------------------------------

Entra ID does not support Dynamic Client Registration, so the client needs the client ID from Step 1. It also needs to be told which scope to request, because the server does not advertise one (see the second warning in Step 6). Claude Desktop (``~/Library/Application Support/Claude/claude_desktop_config.json``):

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "npx",
         "args": [
           "-y", "mcp-remote",
           "https://your-mcp-server.example.com/mcp", "3334",
           "--static-oauth-client-info", "{\"client_id\":\"<CLIENT_ID>\"}",
           "--static-oauth-client-metadata", "{\"scope\":\"https://your-mcp-server.example.com/mcp/mcp.access\"}"
         ]
       }
     }
   }

Three details, each of which fails the login on its own if wrong:

- ``"3334"`` pins the OAuth callback port and has to stay immediately after the URL — that is the only position ``mcp-remote`` reads it from, and elsewhere it is ignored silently, leaving a derived port that Entra ID will reject as an unregistered ``redirect_uri``.
- ``--static-oauth-client-info`` supplies the client ID that DCR would otherwise have obtained.
- ``--static-oauth-client-metadata`` supplies the scope. ``mcp-remote`` resolves the scope in the order *static client metadata → the* ``WWW-Authenticate`` *header →* ``scopes_supported`` *from the metadata document*, so this is the highest-priority source and the only one available here. Without it the client falls back to generic scopes such as ``openid profile offline_access``, which do not name your resource, and Entra ID rejects the request with ``AADSTS9010010``.

Cursor (``~/.cursor/mcp.json``): same approach — Cursor and Claude Desktop both use the ``mcp-remote`` flow.

Note there is no ``Authorization`` header. Restart the MCP client; on the first MCP call ``mcp-remote`` opens your browser to the Entra ID sign-in page, and after consent it caches the refresh token and won't prompt again until it expires.

.. tip::

   ``mcp-remote`` caches OAuth state per server URL under ``~/.mcp-auth``. After changing any value in this guide, delete that directory and kill stray processes (``rm -rf ~/.mcp-auth && pkill -f mcp-remote``) before retrying, or the client will replay the old configuration.

Verification
------------

The startup log states exactly what the server will accept:

.. code-block:: text

   OIDC auth configured as a protected resource (issuer=https://login.microsoftonline.com/<TENANT_ID>/v2.0, resource=https://your-mcp-server.example.com/mcp, audience=<CLIENT_ID>)

The metadata document should name your tenant as the authorization server. Note the path suffix:

.. code-block:: bash

   curl -s https://your-mcp-server.example.com/.well-known/oauth-protected-resource/mcp

.. code-block:: json

   {
     "resource": "https://your-mcp-server.example.com/mcp",
     "authorization_servers": ["https://login.microsoftonline.com/<TENANT_ID>/v2.0"],
     "bearer_methods_supported": ["header"]
   }

An unauthenticated call must return 401 and point at that document:

.. code-block:: bash

   curl -si -X POST https://your-mcp-server.example.com/mcp \
     -H 'Content-Type: application/json' \
     -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"c","version":"1"}}}' \
     | grep -i 'www-authenticate'

.. code-block:: text

   www-authenticate: Bearer error="invalid_token", error_description="Authentication required",
     resource_metadata="https://your-mcp-server.example.com/.well-known/oauth-protected-resource/mcp"

``/.well-known/oauth-authorization-server``, ``/register``, ``/authorize`` and ``/token`` are *supposed* to return 404 — this server is a protected resource, not an authorization server.

To confirm the Entra side without launching a browser, check the app registration directly. All four values below must be as shown:

.. code-block:: bash

   az rest --method GET \
     --uri "https://graph.microsoft.com/v1.0/applications(appId='<CLIENT_ID>')?\$select=identifierUris,api,publicClient,isFallbackPublicClient"

.. code-block:: text

   identifierUris          ["https://your-mcp-server.example.com/mcp"]   # path, no trailing slash
   api.requestedAccessTokenVersion   2                                   # v2 issuer
   api.oauth2PermissionScopes        [{ "value": "mcp.access", … }]      # the scope clients request
   publicClient.redirectUris         ["http://localhost:3334/oauth/callback"]
   isFallbackPublicClient            true                                # public client flows allowed

A successful sign-in looks like this in the server log — a 401 challenge, metadata discovery, then authenticated traffic:

.. code-block:: text

   "GET  /.well-known/oauth-protected-resource/mcp HTTP/1.1" 200 OK
   "POST /mcp HTTP/1.1" 401 Unauthorized
   "GET  /.well-known/oauth-protected-resource/mcp HTTP/1.1" 200 OK
   "POST /mcp HTTP/1.1" 200 OK

Common errors
-------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Symptom
     - Likely cause
   * - ``AADSTS9010010: The resource parameter provided in the request doesn't match with the requested scopes``
     - The ``resource`` the client sent is not a registered Application ID URI, or the requested scope doesn't belong to it. Almost always the trailing-slash problem: ``OIDCPROXY_BASE_URL`` is a bare origin, so the client sends ``https://host/``. Set it to the full ``/mcp`` URL and register that as the App ID URI (Step 3). The other cause is a missing ``--static-oauth-client-metadata`` scope (Step 7).
   * - 401 ``invalid_token`` after a successful sign-in, with the token's ``iss`` starting ``https://sts.windows.net/``
     - The app is still issuing v1 tokens. Set ``requestedAccessTokenVersion`` to ``2`` (Step 4).
   * - 401 ``invalid_token`` after a successful sign-in, with an ``aud`` that is neither the client ID nor your resource
     - The client requested a generic scope, so Entra ID issued a Microsoft Graph token. Supply your own scope via ``--static-oauth-client-metadata`` (Step 7).
   * - 403 ``insufficient_scope``
     - ``OIDCPROXY_REQUIRED_SCOPES`` is set to the fully-qualified scope while Entra ID issues only the short name in ``scp``. Unset it (Step 6).
   * - ``AADSTS90002: Tenant '<guid>' not found``
     - A Subscription ID was used where the Directory (tenant) ID belongs. Get the right one with ``az account show --query tenantId -o tsv``.
   * - ``IdentifierUrisEndsWithSlash`` / ``ValueCannotEndWithSlash`` when saving the App ID URI
     - Entra ID never accepts an Application ID URI ending in ``/``. Use the un-slashed ``…/mcp`` form; this is why the resource identifier needs a path.
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
   * - ``AADSTS900144: The request body must contain the following parameter: 'scope'``
     - The client sent a ``resource`` with no ``scope``. Supply the scope as in Step 7.
   * - ``/.well-known/oauth-protected-resource/mcp`` returns 404
     - The server isn't running in ``oidc`` mode (check ``ZSCALER_MCP_AUTH_MODE``), or ``OIDCPROXY_BASE_URL`` has no path, in which case the document is at ``/.well-known/oauth-protected-resource`` instead.
   * - Login succeeds but the client keeps re-prompting or replays old settings
     - Stale ``mcp-remote`` cache. ``rm -rf ~/.mcp-auth && pkill -f mcp-remote``, then restart the client.

See also
--------

- :doc:`../security/mcp-client-auth` — the full set of authentication modes, including JWT and api-key alternatives.
- :doc:`azure-deployment` — deploying the server to Azure Container Apps / VM / AKS.
- :doc:`../security/lifecycle` — credential rotation without container restart.
