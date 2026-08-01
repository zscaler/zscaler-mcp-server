# OIDC Setup with Microsoft Entra ID

This guide walks you through configuring **Microsoft Entra ID** (formerly Azure AD) as the identity provider for the Zscaler MCP Server's `oidc` authentication mode. When complete, users will authenticate via their Microsoft account before accessing Zscaler MCP tools.

## Overview

In `oidc` mode the MCP server is an OAuth 2.0 **protected resource** ([RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html)). It issues no tokens and runs no login flow of its own — it publishes a small metadata document naming Entra ID as the authorization server, and verifies the tokens clients present. The flow works as follows:

1. User opens Claude Desktop / Cursor
2. The client gets a `401` from `/mcp` with a `WWW-Authenticate` header pointing at `/.well-known/oauth-protected-resource`
3. It reads that document and learns Entra ID is the authorization server
4. A browser window opens with the Microsoft Entra ID sign-in page — the OAuth flow runs **directly against Entra ID**
5. The client retries `/mcp` with `Authorization: Bearer <token>`; the server verifies the signature, issuer, audience and expiry against Entra ID's public keys
6. The MCP client is authenticated and can call Zscaler tools

The same mechanism works with Auth0, Okta, Keycloak, or any OIDC-compliant provider — only the configuration differs. Entra ID gets its own guide because of one quirk: it sets the `aud` claim to the **client ID**, where Auth0 uses a separate API identifier.

**The server holds no credential.** Verifying a signature requires Entra ID's public keys, not a secret of ours, so there is no client secret to create, store, or rotate for the MCP server.

## Prerequisites

- **Azure subscription** with access to Microsoft Entra ID
- **Global Administrator** or **Application Administrator** role (to create app registrations and grant admin consent)
- **Zscaler MCP Server** source code or installed package
- **Node.js** (for `npx mcp-remote`)

## Step 1: Create an App Registration

1. Go to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** → **App registrations** → **+ New registration**

   ![App Registration](images/entra-id/01-app-registration.png)

3. Fill in the registration form:

   | Field | Value |
   |-------|-------|
   | **Name** | `zscaler-mcp-server` |
   | **Supported account types** | "Accounts in this organizational directory only" (single tenant) |

4. Under **Redirect URI**:
   - **Platform**: Select **Mobile and desktop applications** (a public client)
   - **URI**: Enter `http://localhost:3334/oauth/callback`

   ![Redirect URI](images/entra-id/02-redirect-uri.png)

5. Click **Register**
6. Go to **Authentication → Advanced settings** and set **Allow public client flows** to **Yes**, then **Save**

> **The redirect URI belongs to the MCP client, not to the MCP server.** The screenshot above shows the older value `http://localhost:8000/auth/callback` with platform **Web** — that was correct when the server itself was the OAuth client and handled the callback. It no longer is. The callback is now a loopback address the MCP client listens on. Register whatever URI **your client** uses — the value stays the same even when the server runs remotely.
>
> **You must pin `mcp-remote`'s port, or this URI will not match.** Despite what its README says, `mcp-remote` has no fixed default port: unless you pass one it derives the port from a hash of the server URL (`3335 + hash % 45816`), so it will not choose 3334. Entra ID compares `redirect_uri` byte-for-byte, so a derived port fails every login. Pass `3334` as the first argument after the server URL — as the [Step 7 config](#step-7-configure-claude-desktop) does — and the URI you registered above is the one it uses. An explicitly-passed port is used verbatim with no fallback, so it cannot drift between runs.

## Step 2: Note Your Application IDs

After registration, you'll land on the app's **Overview** page:

![App Overview](images/entra-id/03-app-overview.png)

Note down these two values:

| Field | Example |
|-------|---------|
| **Application (client) ID** | `00000000-1111-2222-3333-444444444444` |
| **Directory (tenant) ID** | `00000000-1111-2222-3333-444444444444` |

You can also find your tenant ID via the Azure CLI:

```bash
az account show --query tenantId -o tsv
```

> **No client secret needed.** Earlier versions of this guide had you create one under **Certificates & secrets**. The server no longer uses it — token verification needs Entra ID's public keys, not a credential of ours. If you created one for a previous deployment, you can delete it.

## Step 3: Enable ID Tokens

1. Go to **Authentication (Preview)** in the left sidebar
2. Click the **Settings** tab
3. Under **Implicit grant and hybrid flows**, check: **ID tokens (used for implicit and hybrid flows)**
4. Click **Save**

![ID Tokens](images/entra-id/05-id-tokens.png)

## Step 4: Configure API Permissions

1. Go to **API permissions** in the left sidebar
2. Click **+ Add a permission** → **Microsoft Graph** → **Delegated permissions**
3. Search and add:
   - `openid`
   - `profile`
   - `email`
4. Click **Add permissions**
5. Click **Grant admin consent for [your organization]**

![API Permissions](images/entra-id/06-api-permissions.png)

All four permissions (`User.Read`, `openid`, `profile`, `email`) should show green checkmarks under the **Status** column.

## Step 5: Verify Endpoints

Click **Endpoints** in the top bar of your app registration to view the OIDC endpoints:

![Endpoints](images/entra-id/07-endpoints.png)

The key URL you need is the **OpenID Connect metadata document**:

```text
https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration
```

You can verify it works:

```bash
curl -s "https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration" | head -1
```

## Step 6: Run the MCP Server

No extra packages and no wrapper script — `oidc` mode is configured with environment variables and uses the normal entrypoint.

```bash
# .env
ZSCALER_MCP_AUTH_ENABLED=true
ZSCALER_MCP_AUTH_MODE=oidc

OIDCPROXY_CONFIG_URL=https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
OIDCPROXY_CLIENT_ID=<app-client-id>
OIDCPROXY_BASE_URL=http://localhost:8000

ZSCALER_MCP_ALLOW_HTTP=true          # local development only, no TLS
```

```bash
zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

> **Note:** `OIDCPROXY_AUDIENCE` defaults to `OIDCPROXY_CLIENT_ID`, which is exactly right for Entra ID — it sets the `aud` claim to the app's client ID rather than to a separate API identifier. You only need to set it explicitly on IdPs that use an API identifier, like Auth0.

The variables keep their `OIDCPROXY_` prefix so existing deployments keep working. `OIDCPROXY_CLIENT_SECRET` is ignored if present.

Confirm the server is publishing Entra ID as the authorization server:

```bash
curl -s http://localhost:8000/.well-known/oauth-protected-resource | jq
```

```json
{
  "resource": "http://localhost:8000",
  "authorization_servers": [
    "https://login.microsoftonline.com/<tenant-id>/v2.0"
  ],
  "bearer_methods_supported": ["header"]
}
```

The startup log states exactly what the server will accept, which is the fastest way to diagnose a token rejection later:

```text
OIDC auth configured as a protected resource (issuer=…, resource=…, audience=…)
```

## Step 7: Configure Claude Desktop

Update your Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "zscaler-mcp-server": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote", "http://localhost:8000/mcp", "3334",
        "--static-oauth-client-info", "{\"client_id\":\"<app-client-id>\"}"
      ]
    }
  }
}
```

No `--header` flag needed — `mcp-remote` discovers the metadata document and runs the OAuth flow against Entra ID via the browser. Two arguments are doing load-bearing work, and the flow fails without either:

- **`"3334"`** pins the OAuth callback port, and **must be the first argument after the URL.** `mcp-remote` reads the port from that exact position; anything else there (a flag, for example) is parsed as a port, silently yields `NaN`, and it falls back to a port derived from a hash of the server URL. There is no warning — the only symptom is Entra ID rejecting a `redirect_uri` you never chose. This is why the port comes before the flags rather than after.
- **`--static-oauth-client-info`** supplies the client ID from Step 2. Entra ID does not support Dynamic Client Registration, so a client that tries to register itself gets an error the bridge reports only as `ServerError`.

## Step 8: Test the Connection

1. Start the MCP server (Step 6)
2. Open Claude Desktop
3. A browser window will open with the Microsoft sign-in page
4. Sign in with your organizational account
5. Accept the consent prompt (first time only)
6. Claude Desktop is now connected and authenticated

The server logs will show the successful authentication flow. Note that the token exchange happens between the client and Entra ID — the server only fetches the signing keys:

```text
GET https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys "HTTP/1.1 200 OK"
Processing request of type ListToolsRequest
```

## Configuration Reference

### Entra ID vs Auth0 Comparison

| Setting | Auth0 | Entra ID |
|---------|-------|----------|
| `OIDCPROXY_CONFIG_URL` | `https://{domain}.auth0.com/.well-known/openid-configuration` | `https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration` |
| `OIDCPROXY_CLIENT_ID` | Auth0 Application Client ID | Entra App Registration Client ID |
| `OIDCPROXY_AUDIENCE` | API Identifier (e.g., `zscaler-mcp-server`) — must be set explicitly | **Client ID** (Entra uses client_id as `aud`) — can be omitted, it defaults to the client ID |
| Client secret | Not needed | Not needed |
| Callback URL | Belongs to the client — `http://localhost:3334/oauth/callback` once `mcp-remote` is pinned to that port | Same |
| Dynamic Client Registration | Supported | Not supported — pass the client ID with `--static-oauth-client-info` |
| Admin consent | Not required | Required for organizational access |
| Scopes | `openid profile email` | `openid profile email` |

### Environment Variable Mapping

| Variable | Source |
|----------|--------|
| `OIDCPROXY_CONFIG_URL` | Endpoints page → OpenID Connect metadata document |
| `OIDCPROXY_CLIENT_ID` | Overview page → Application (client) ID |
| `OIDCPROXY_BASE_URL` | Your MCP server's public URL (e.g., `http://localhost:8000`) |
| `OIDCPROXY_AUDIENCE` | Optional for Entra ID — defaults to `OIDCPROXY_CLIENT_ID` |

## Remote Deployment

For Azure VM or Container Apps deployments:

1. **Base URL**: Set `OIDCPROXY_BASE_URL` to the public URL of the deployment (e.g. `https://<FQDN>`). This is the OAuth resource identifier clients use, so it must match the URL they connect to.
2. **Redirect URI**: Unchanged. The callback belongs to the MCP client, which still runs on the user's machine, so it stays a `localhost` URI no matter where the server lives. This is a simplification over the old proxy design, which needed a new redirect URI registered for every deployment URL.
3. Use the Azure deployment script and select the OIDC auth mode:

```bash
cd integrations/azure
python azure_mcp_operations.py deploy
# Select OIDC → provide the Entra ID config URL and client ID
```

The deployment script reads the configuration from the `.env` file:

```env
OIDCPROXY_DOMAIN=login.microsoftonline.com/<tenant-id>/v2.0
OIDCPROXY_CLIENT_ID=<app-client-id>
OIDCPROXY_AUDIENCE=<app-client-id>
```

> **Note:** `OIDCPROXY_DOMAIN` is used to construct the OpenID Connect discovery URL as `https://{OIDCPROXY_DOMAIN}/.well-known/openid-configuration`. These variables work with any OIDC provider (Entra ID, Okta, Auth0, Keycloak, etc.).

## Troubleshooting

### "Application with identifier was not found in the directory"

**Error:** `AADSTS700016: Application with identifier '{client-id}' was not found in the directory '{tenant}'.`

**Cause:** The client ID or tenant ID is incorrect.

**Fix:**

- Verify the Application (client) ID on the app registration Overview page
- Verify the tenant ID with `az account show --query tenantId -o tsv`
- Ensure the app is in the correct directory (tenant)

### "400 Bad Request" on OIDC Configuration URL

**Error:** `HTTPStatusError: Client error '400 Bad Request' for url 'https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration'`

**Cause:** Invalid tenant ID in the URL.

**Fix:** Verify your tenant ID:

```bash
az account show --query tenantId -o tsv
```

### `AADSTS50011: The redirect URI specified in the request does not match`

**Cause:** The URI your MCP client used is not registered on the app registration. The callback belongs to the client, so it is a `localhost` URI — not your server's address.

**Fix:** The error message names the `redirect_uri` Entra ID received. If its port is not the one you registered, `mcp-remote` is choosing its own: it has no fixed default and derives the port from a hash of the server URL. Pass `3334` as the **first argument after the URL** (see Step 7) — in any other position it is ignored without a warning. Then confirm `http://localhost:3334/oauth/callback` is registered under **Authentication → Add a platform → Mobile and desktop applications**.

### "Consent required" or permissions error

**Cause:** Admin consent was not granted for the API permissions.

**Fix:** Go to API permissions → click "Grant admin consent for [organization]". Requires Global Administrator or Application Administrator role.

### Browser doesn't open for authentication

**Cause:** `mcp-remote` may not be triggering the OAuth flow.

**Fix:**

- Ensure the server is running and accessible at `http://localhost:8000`
- Verify Claude Desktop config points to `http://localhost:8000/mcp`
- `--allow-http` is not needed for a `localhost` URL — `mcp-remote` exempts loopback addresses. Add it only when pointing at a remote server over plain HTTP
- Open `http://localhost:8000/.well-known/oauth-protected-resource` in your browser — it should return JSON naming your Entra ID tenant. If it 404s, the server is not running in `oidc` mode; check `ZSCALER_MCP_AUTH_MODE`
- `/.well-known/oauth-authorization-server` and `/register` are *supposed* to 404 — this server is a protected resource, not an authorization server

### `401 invalid_token` after signing in successfully

**Cause:** Almost always an audience or issuer mismatch.

**Fix:** Compare the startup log line with the token the client received:

```text
OIDC auth configured as a protected resource (issuer=…, resource=…, audience=…)
```

Decode the token (e.g. at [jwt.io](https://jwt.io)) and check that `aud` equals your Application (client) ID and `iss` equals `https://login.microsoftonline.com/{tenant-id}/v2.0`. Entra ID's issuer is not a prefix of its discovery URL, which is why the server reads it from the discovery document rather than deriving it.

### `Could not read the IdP's OpenID configuration from …`

**Cause:** The server could not fetch Entra ID's discovery document at startup — wrong tenant ID, or no network path from the host to `login.microsoftonline.com`.

**Fix:** Verify the URL with `curl`, and confirm egress to Entra ID is permitted from wherever the server runs.

### Non-secure cookies warning

**Message:** `WARNING: Using non-secure cookies for development; deploy with HTTPS for production.`

This is expected for `http://localhost` and safe for local development. For production, deploy with HTTPS (Container Apps provides this automatically).
