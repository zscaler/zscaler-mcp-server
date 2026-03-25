.. _configuration-guide:

Configuration Guide
===================

This guide explains all supported authentication methods and configuration options for the Zscaler Integrations MCP Server.

Authentication Methods
----------------------

The server supports two authentication frameworks:

1. **OneAPI Authentication** (Recommended) - Modern OAuth2-based unified authentication
2. **Legacy Authentication** - Service-specific API key authentication (per service)

OneAPI Authentication (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OneAPI provides unified authentication across all Zscaler services using a single set of OAuth2 credentials.

**Required Environment Variables:**

.. code-block:: bash

   # OneAPI OAuth2 Credentials
   export ZSCALER_CLIENT_ID="your_client_id"           # OAuth client ID
   export ZSCALER_CLIENT_SECRET="your_client_secret"   # OAuth client secret
   export ZSCALER_CUSTOMER_ID="your_customer_id"       # Customer/tenant ID
   export ZSCALER_VANITY_DOMAIN="your_vanity_domain"   # Your vanity domain

**Optional Environment Variables:**

.. code-block:: bash

   export ZSCALER_CLOUD="production"        # Cloud environment (production, beta, zscalerone.net, etc.)
   export ZSCALER_PRIVATE_KEY="path/to/key" # Path to private key for JWT authentication

**When to Use OneAPI:**

- ✅ Modern deployments (recommended)
- ✅ Unified authentication across all services
- ✅ OAuth2-based security
- ✅ Works with ZPA, ZIA, ZDX, ZCC, ZIdentity

Legacy Authentication (Per-Service)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Legacy authentication uses service-specific API keys and credentials.

**Enable Legacy Mode:**

.. code-block:: bash

   export ZSCALER_USE_LEGACY="true"

**ZPA Legacy Authentication:**

.. code-block:: bash

   export ZSCALER_USE_LEGACY="true"
   export ZPA_CLIENT_ID="your_zpa_client_id"       # ZPA API client ID
   export ZPA_CLIENT_SECRET="your_zpa_secret"      # ZPA API client secret
   export ZPA_CUSTOMER_ID="your_customer_id"       # ZPA customer ID
   export ZPA_CLOUD="production"                   # ZPA cloud (production, beta, etc.)

**ZIA Legacy Authentication:**

.. code-block:: bash

   export ZSCALER_USE_LEGACY="true"
   export ZIA_USERNAME="admin@company.com"         # ZIA admin email
   export ZIA_PASSWORD="your_password"             # ZIA admin password
   export ZIA_API_KEY="your_api_key"               # ZIA obfuscated API key
   export ZIA_CLOUD="zscalertwo"               # ZIA cloud

**ZCC Legacy Authentication:**

.. code-block:: bash

   export ZSCALER_USE_LEGACY="true"
   export ZCC_CLIENT_ID="your_api_key"             # ZCC API key
   export ZCC_CLIENT_SECRET="your_secret_key"      # ZCC secret key
   export ZCC_CLOUD="zscalertwo"               # ZCC cloud

**ZDX Legacy Authentication:**

.. code-block:: bash

   export ZSCALER_USE_LEGACY="true"
   export ZDX_CLIENT_ID="your_key_id"              # ZDX key ID
   export ZDX_CLIENT_SECRET="your_secret_key"      # ZDX secret key

**When to Use Legacy:**

- Legacy deployments with existing service-specific credentials
- Services not yet migrated to OneAPI
- Gradual migration scenarios

Server Configuration
--------------------

General Server Settings
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Transport Protocol
   export ZSCALER_MCP_TRANSPORT="stdio"            # stdio, sse, or streamable-http

   # Service Selection
   export ZSCALER_MCP_SERVICES="zpa,zia,zdx"       # Comma-separated (empty = all services)
   export ZSCALER_MCP_DISABLED_SERVICES=""          # Comma-separated services to exclude

   # Tool Selection
   export ZSCALER_MCP_TOOLS=""                     # Comma-separated tool names (empty = all tools)
   export ZSCALER_MCP_DISABLED_TOOLS=""            # Comma-separated tools to exclude (supports wildcards)

   # Logging
   export ZSCALER_MCP_DEBUG="false"                # Enable debug logging (true/false)

   # HTTP Transport Settings (when using sse or streamable-http)
   export ZSCALER_MCP_HOST="127.0.0.1"             # Host to bind to
   export ZSCALER_MCP_PORT="8000"                  # Port to listen on

   # User Agent
   export ZSCALER_MCP_USER_AGENT_COMMENT="My App"  # Additional User-Agent info

.. _mcp-client-authentication:

MCP Client Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. important::

   MCP Client Authentication applies only to HTTP transports (``sse``, ``streamable-http``). The ``stdio`` transport does not support or require client authentication.

The MCP server supports three environment-variable-based authentication modes and a library-level ``auth=`` parameter for controlling which clients can connect:

**1. API Key (Simple Shared Secret)**

.. code-block:: bash

   export ZSCALER_MCP_AUTH_ENABLED="true"
   export ZSCALER_MCP_AUTH_MODE="api-key"
   export ZSCALER_MCP_AUTH_API_KEY="sk-your-secret-key-here"

Clients authenticate with ``Authorization: Bearer sk-your-secret-key-here``.

**2. JWT (External Identity Provider via JWKS)**

.. code-block:: bash

   export ZSCALER_MCP_AUTH_ENABLED="true"
   export ZSCALER_MCP_AUTH_MODE="jwt"
   export ZSCALER_MCP_AUTH_JWKS_URI="https://your-idp.auth0.com/.well-known/jwks.json"
   export ZSCALER_MCP_AUTH_ISSUER="https://your-idp.auth0.com/"
   export ZSCALER_MCP_AUTH_AUDIENCE="zscaler-mcp-server"
   export ZSCALER_MCP_AUTH_ALGORITHMS="RS256"   # Optional, default: RS256

Supports Auth0, Okta, Azure AD, Keycloak, AWS Cognito, PingOne, and Google Cloud Identity. Tokens are validated locally using the IdP's public keys.

**3. Zscaler (OneAPI Credential Validation)**

.. code-block:: bash

   export ZSCALER_MCP_AUTH_ENABLED="true"
   export ZSCALER_MCP_AUTH_MODE="zscaler"

Clients authenticate via Basic Auth (``client_id:client_secret``) or custom headers (``X-Zscaler-Client-ID`` / ``X-Zscaler-Client-Secret``). The server validates against Zscaler's ``/oauth2/v1/token`` endpoint.

**4. Library-Level OAuth 2.1 — OIDCProxy (auth= Parameter)**

When using ``ZscalerMCPServer`` as a Python library, pass a ``fastmcp.server.auth.AuthProvider`` (e.g. ``OIDCProxy``) directly to the constructor. This provides full MCP-spec-compliant OAuth 2.1 with Dynamic Client Registration (DCR) and works with any OIDC-compliant IdP (Auth0, Okta, Azure AD, Keycloak, Google, etc.).

.. code-block:: python

   import os
   from fastmcp.server.auth.oidc_proxy import OIDCProxy
   from zscaler_mcp.server import ZscalerMCPServer

   auth = OIDCProxy(
       config_url="https://your-tenant.auth0.com/.well-known/openid-configuration",
       client_id=os.getenv("OIDCPROXY_CLIENT_ID"),
       client_secret=os.getenv("OIDCPROXY_CLIENT_SECRET"),
       base_url="http://localhost:8000",
       audience="zscaler-mcp-server",
   )

   # Allow standard OIDC scopes for Dynamic Client Registration
   if auth.client_registration_options:
       auth.client_registration_options.valid_scopes = [
           "openid", "profile", "email",
       ]

   server = ZscalerMCPServer(auth=auth)
   server.run("streamable-http", host="0.0.0.0", port=8000)

When ``auth=`` is provided, the env-var-based auth middleware (``ZSCALER_MCP_AUTH_*``) is automatically skipped. The server exposes standard OAuth endpoints (``/.well-known/*``, ``/register``, ``/authorize``, ``/token``) and MCP clients handle the authorization flow automatically — no static tokens or shared secrets required.

**IdP requirements:** Your Identity Provider must have a **Regular Web Application** (not M2M) with the callback URL ``http://localhost:8000/auth/callback`` registered, and an API/resource server with an identifier matching the ``audience`` value.

See the `Authentication & Deployment Guide <../docs/deployment/authentication-and-deployment.md#oidcproxy-setup-oauth-21--dcr>`_ for detailed IdP-specific setup instructions, Docker deployment, and troubleshooting.

**Token Generation:**

Use the ``--generate-auth-token`` CLI flag to generate a token for testing:

.. code-block:: bash

   zscaler-mcp --generate-auth-token

.. _network-security:

Network Security
~~~~~~~~~~~~~~~~~

The server provides defense-in-depth network security controls for HTTP transports.

**HTTPS / TLS Configuration:**

.. code-block:: bash

   export ZSCALER_MCP_TLS_CERT_FILE="/path/to/cert.pem"
   export ZSCALER_MCP_TLS_KEY_FILE="/path/to/key.pem"

When both are set, the server starts with TLS enabled, serving over HTTPS.

**HTTPS Policy Enforcement:**

.. code-block:: bash

   export ZSCALER_MCP_ALLOW_HTTP="false"    # Default: false

When ``false`` (default), the server blocks plaintext HTTP on non-localhost interfaces if TLS is not configured. Set to ``true`` only if you have TLS termination handled upstream (e.g., a reverse proxy).

**Host Header Validation:**

.. code-block:: bash

   export ZSCALER_MCP_ALLOWED_HOSTS="myhost.example.com,api.internal"
   export ZSCALER_MCP_DISABLE_HOST_VALIDATION="false"   # Default: false

Restricts accepted ``Host`` headers to prevent DNS rebinding attacks. Localhost variants (``localhost``, ``127.0.0.1``, ``::1``) are always allowed. Set ``ZSCALER_MCP_DISABLE_HOST_VALIDATION=true`` to disable (not recommended).

**Source IP Access Control:**

.. code-block:: bash

   export ZSCALER_MCP_ALLOWED_SOURCE_IPS="10.0.0.0/8,192.168.1.0/24,203.0.113.42"

Restricts which client IP addresses can connect. Supports individual IPs and CIDR notation. When unset, all source IPs are allowed.

Write Operations Configuration (Security)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the server operates in **read-only mode** for safety. To enable write operations:

.. code-block:: bash

   # Step 1: Enable write tools globally
   export ZSCALER_MCP_WRITE_ENABLED="true"

   # Step 2: MANDATORY - Specify allowlist (no backdoor to "enable all")
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_*,zpa_delete_*,zia_update_*"

**Security Note:**

- ⚠️ ``ZSCALER_MCP_WRITE_TOOLS`` is **MANDATORY** when ``ZSCALER_MCP_WRITE_ENABLED=true``
- If empty, **0 write tools will be registered** (by design for security)
- Supports wildcards: ``zpa_create_*``, ``zia_delete_*``, ``zpa_*``
- No backdoor exists to bypass the allowlist

**Wildcard Examples:**

.. code-block:: bash

   # Allow all ZPA create operations
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_*"

   # Allow ZPA create and delete
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_*,zpa_delete_*"

   # Allow all ZPA write tools
   export ZSCALER_MCP_WRITE_TOOLS="zpa_*"

   # Allow specific tool (no wildcard)
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_application_segment"

   # Allow multiple services
   export ZSCALER_MCP_WRITE_TOOLS="zpa_*,zia_*,ztw_*"

Complete Configuration Examples
--------------------------------

Read-Only Mode (Default - Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # OneAPI Authentication - Read-Only
   export ZSCALER_CLIENT_ID="your_client_id"
   export ZSCALER_CLIENT_SECRET="your_client_secret"
   export ZSCALER_CUSTOMER_ID="your_customer_id"
   export ZSCALER_VANITY_DOMAIN="your_vanity_domain"
   export ZSCALER_CLOUD="production"
   
   # No write flags needed - read-only by default
   # Only list_* and get_* operations available

Write Mode with Allowlist (Advanced)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # OneAPI Authentication + Write Operations
   export ZSCALER_CLIENT_ID="your_client_id"
   export ZSCALER_CLIENT_SECRET="your_client_secret"
   export ZSCALER_CUSTOMER_ID="your_customer_id"
   export ZSCALER_VANITY_DOMAIN="your_vanity_domain"
   export ZSCALER_CLOUD="production"
   
   # Enable write mode
   export ZSCALER_MCP_WRITE_ENABLED="true"
   
   # MANDATORY: Specify allowlist
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_*,zpa_update_*,zia_create_rule_label"

Legacy Mode Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Enable Legacy Mode
   export ZSCALER_USE_LEGACY="true"
   
   # ZPA Legacy Credentials
   export ZPA_CLIENT_ID="your_zpa_client_id"
   export ZPA_CLIENT_SECRET="your_zpa_secret"
   export ZPA_CUSTOMER_ID="your_customer_id"
   export ZPA_CLOUD="production"
   
   # ZIA Legacy Credentials
   export ZIA_USERNAME="admin@company.com"
   export ZIA_PASSWORD="your_password"
   export ZIA_API_KEY="your_api_key"
   export ZIA_CLOUD="zscalertwo"
   
   # Optional: Enable write mode with allowlist
   export ZSCALER_MCP_WRITE_ENABLED="true"
   export ZSCALER_MCP_WRITE_TOOLS="zpa_*,zia_*"

Security Best Practices
------------------------

**For Production:**

.. code-block:: bash

   # ✅ DO: Use read-only mode by default
   # (No ZSCALER_MCP_WRITE_ENABLED needed)
   
   # ✅ DO: Use specific allowlists when write mode needed
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_application_segment,zpa_update_application_segment"
   
   # ❌ DON'T: Enable write mode without allowlist
   # This will register 0 write tools (blocked by design)
   export ZSCALER_MCP_WRITE_ENABLED="true"  # ← Without allowlist = 0 tools

**For Development:**

.. code-block:: bash

   # Safe: Read-only mode for exploration
   export ZSCALER_MCP_DEBUG="true"
   
   # When testing write operations:
   export ZSCALER_MCP_WRITE_ENABLED="true"
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_*,zpa_delete_*"  # Specific patterns

**For CI/CD:**

.. code-block:: bash

   # Minimal permissions for automation
   export ZSCALER_MCP_WRITE_ENABLED="true"
   export ZSCALER_MCP_WRITE_TOOLS="zpa_create_application_segment"  # Only what's needed
   
   # Use service accounts with limited permissions
   # Store credentials in secure secrets management

Environment Variables Reference
--------------------------------

Complete List of All Supported Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Server Configuration:**

- ``ZSCALER_MCP_TRANSPORT`` - Transport protocol (``stdio``, ``sse``, ``streamable-http``)
- ``ZSCALER_MCP_SERVICES`` - Comma-separated service list (empty = all)
- ``ZSCALER_MCP_TOOLS`` - Comma-separated tool list (empty = all)
- ``ZSCALER_MCP_DISABLED_SERVICES`` - Comma-separated services to exclude (e.g., ``zcc,zdx``)
- ``ZSCALER_MCP_DISABLED_TOOLS`` - Comma-separated tools to exclude, supports wildcards (e.g., ``zcc_*,zcc_devices_csv_exporter``)
- ``ZSCALER_MCP_DEBUG`` - Enable debug logging (``true``/``false``)
- ``ZSCALER_MCP_HOST`` - HTTP bind host (default: ``127.0.0.1``)
- ``ZSCALER_MCP_PORT`` - HTTP port (default: ``8000``)
- ``ZSCALER_MCP_USER_AGENT_COMMENT`` - Additional User-Agent info

**Write Operations (Security):**

- ``ZSCALER_MCP_WRITE_ENABLED`` - Enable write mode (default: ``false``)
- ``ZSCALER_MCP_WRITE_TOOLS`` - **MANDATORY** allowlist when write enabled
- ``ZSCALER_MCP_SKIP_CONFIRMATIONS`` - Skip delete confirmations with HMAC token (advanced)
- ``ZSCALER_MCP_CONFIRMATION_TTL`` - Confirmation window in seconds (default: ``300``)

**MCP Client Authentication (HTTP transports only):**

- ``ZSCALER_MCP_AUTH_ENABLED`` - Enable client authentication (default: ``false``)
- ``ZSCALER_MCP_AUTH_MODE`` - Authentication mode: ``api-key``, ``jwt``, or ``zscaler``
- ``ZSCALER_MCP_AUTH_API_KEY`` - Shared secret for ``api-key`` mode
- ``ZSCALER_MCP_AUTH_JWKS_URI`` - JWKS endpoint URL for ``jwt`` mode
- ``ZSCALER_MCP_AUTH_ISSUER`` - Expected JWT issuer for ``jwt`` mode
- ``ZSCALER_MCP_AUTH_AUDIENCE`` - Expected JWT audience for ``jwt`` mode
- ``ZSCALER_MCP_AUTH_ALGORITHMS`` - Allowed JWT algorithms (default: ``RS256``)

**Network Security (HTTP transports only):**

- ``ZSCALER_MCP_TLS_CERT_FILE`` - Path to TLS certificate file
- ``ZSCALER_MCP_TLS_KEY_FILE`` - Path to TLS private key file
- ``ZSCALER_MCP_ALLOW_HTTP`` - Allow plaintext HTTP on non-localhost (default: ``false``)
- ``ZSCALER_MCP_ALLOWED_HOSTS`` - Comma-separated list of allowed Host header values
- ``ZSCALER_MCP_DISABLE_HOST_VALIDATION`` - Disable host header validation (default: ``false``)
- ``ZSCALER_MCP_ALLOWED_SOURCE_IPS`` - Comma-separated list of allowed client IPs/CIDRs

**OneAPI Authentication (Zscaler API credentials):**

- ``ZSCALER_CLIENT_ID`` - OAuth client ID (required)
- ``ZSCALER_CLIENT_SECRET`` - OAuth client secret (required)
- ``ZSCALER_CUSTOMER_ID`` - Customer/tenant ID (required for ZPA)
- ``ZSCALER_VANITY_DOMAIN`` - Vanity domain (required)
- ``ZSCALER_CLOUD`` - Cloud environment (optional)
- ``ZSCALER_PRIVATE_KEY`` - Private key path for JWT (optional)

**Legacy Authentication:**

- ``ZSCALER_USE_LEGACY`` - Enable legacy mode (default: ``false``)
- ``ZPA_CLIENT_ID``, ``ZPA_CLIENT_SECRET``, ``ZPA_CUSTOMER_ID``, ``ZPA_CLOUD``
- ``ZIA_USERNAME``, ``ZIA_PASSWORD``, ``ZIA_API_KEY``, ``ZIA_CLOUD``
- ``ZCC_CLIENT_ID``, ``ZCC_CLIENT_SECRET``, ``ZCC_CLOUD``
- ``ZDX_CLIENT_ID``, ``ZDX_CLIENT_SECRET``, ``ZDX_CLOUD``

CLI Flags Reference
--------------------

.. code-block:: text

   --transport           Transport protocol: stdio, sse, streamable-http (default: stdio)
   --host                Host to bind to for HTTP transports (default: 127.0.0.1)
   --port                Port for HTTP transports (default: 8000)
   --services            Comma-separated list of services to enable
   --enable-write-tools  Enable write (create/update/delete) tools
   --write-tools         Mandatory allowlist of write tools (supports wildcards)
   --generate-auth-token Generate an authorization token from configured credentials
   --list-tools          List all registered tools and exit
   --user-agent-comment  Additional comment appended to the User-Agent header
   --version             Show server version and exit
   --debug               Enable debug logging

Troubleshooting
---------------

**Issue: Write tools not appearing**

Check:

1. Is ``ZSCALER_MCP_WRITE_ENABLED=true`` set?
2. Is ``ZSCALER_MCP_WRITE_TOOLS`` provided with patterns?
3. Do patterns match tool names? (use ``zscaler-mcp --list-tools`` to see all tools)

**Issue: Zscaler API authentication fails**

Check:

1. For OneAPI: All 4 required variables set (CLIENT_ID, CLIENT_SECRET, CUSTOMER_ID, VANITY_DOMAIN)
2. For Legacy: ``ZSCALER_USE_LEGACY=true`` + service-specific credentials
3. Credentials are valid and not expired

**Issue: MCP Client Authentication fails**

Check:

1. ``ZSCALER_MCP_AUTH_ENABLED=true`` is set
2. ``ZSCALER_MCP_AUTH_MODE`` matches your client's authentication method
3. For ``api-key``: Client sends ``Authorization: Bearer <key>`` with the correct key
4. For ``jwt``: JWKS URI is reachable, issuer/audience match, token is not expired
5. For ``zscaler``: Client sends valid Basic Auth or ``X-Zscaler-Client-ID``/``X-Zscaler-Client-Secret`` headers

**Issue: Connection refused on non-localhost**

Check:

1. ``ZSCALER_MCP_ALLOW_HTTP`` — If ``false`` (default) and TLS is not configured, HTTP is blocked on non-localhost
2. Either configure TLS (``ZSCALER_MCP_TLS_CERT_FILE`` + ``ZSCALER_MCP_TLS_KEY_FILE``) or set ``ZSCALER_MCP_ALLOW_HTTP=true``

**Issue: 421 Misdirected Request (Host header rejected)**

Check:

1. Add your server's hostname to ``ZSCALER_MCP_ALLOWED_HOSTS``
2. Or set ``ZSCALER_MCP_DISABLE_HOST_VALIDATION=true`` (not recommended for production)

**Issue: Client IP rejected**

Check:

1. If ``ZSCALER_MCP_ALLOWED_SOURCE_IPS`` is set, ensure the client's IP is in the list
2. Use CIDR notation for ranges (e.g., ``10.0.0.0/8``)

**Issue: Service not available**

Check:

1. Service name is correct: ``zpa``, ``zia``, ``zdx``, ``zcc``, ``zidentity``, ``ztw``, ``zeasm``, ``zinsights``
2. If using ``ZSCALER_MCP_SERVICES``, service is included in the list
