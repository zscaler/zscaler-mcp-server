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
   
   # Tool Selection
   export ZSCALER_MCP_TOOLS=""                     # Comma-separated tool names (empty = all tools)

   # Logging
   export ZSCALER_MCP_DEBUG="false"                # Enable debug logging (true/false)

   # HTTP Transport Settings (when using sse or streamable-http)
   export ZSCALER_MCP_HOST="127.0.0.1"             # Host to bind to
   export ZSCALER_MCP_PORT="8000"                  # Port to listen on

   # User Agent
   export ZSCALER_MCP_USER_AGENT_COMMENT="My App"  # Additional User-Agent info

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

- ``ZSCALER_MCP_TRANSPORT`` - Transport protocol (stdio, sse, streamable-http)
- ``ZSCALER_MCP_SERVICES`` - Comma-separated service list (empty = all)
- ``ZSCALER_MCP_TOOLS`` - Comma-separated tool list (empty = all)
- ``ZSCALER_MCP_DEBUG`` - Enable debug logging (true/false)
- ``ZSCALER_MCP_HOST`` - HTTP bind host (default: 127.0.0.1)
- ``ZSCALER_MCP_PORT`` - HTTP port (default: 8000)
- ``ZSCALER_MCP_USER_AGENT_COMMENT`` - Additional User-Agent info

**Write Operations (Security):**

- ``ZSCALER_MCP_WRITE_ENABLED`` - Enable write mode (default: false)
- ``ZSCALER_MCP_WRITE_TOOLS`` - **MANDATORY** allowlist when write enabled

**OneAPI Authentication:**

- ``ZSCALER_CLIENT_ID`` - OAuth client ID (required)
- ``ZSCALER_CLIENT_SECRET`` - OAuth client secret (required)
- ``ZSCALER_CUSTOMER_ID`` - Customer/tenant ID (required)
- ``ZSCALER_VANITY_DOMAIN`` - Vanity domain (required)
- ``ZSCALER_CLOUD`` - Cloud environment (optional)
- ``ZSCALER_PRIVATE_KEY`` - Private key path for JWT (optional)

**Legacy Authentication:**

- ``ZSCALER_USE_LEGACY`` - Enable legacy mode (default: false)
- ``ZPA_CLIENT_ID``, ``ZPA_CLIENT_SECRET``, ``ZPA_CUSTOMER_ID``, ``ZPA_CLOUD``
- ``ZIA_USERNAME``, ``ZIA_PASSWORD``, ``ZIA_API_KEY``, ``ZIA_CLOUD``
- ``ZCC_CLIENT_ID``, ``ZCC_CLIENT_SECRET``, ``ZCC_CLOUD``
- ``ZDX_CLIENT_ID``, ``ZDX_CLIENT_SECRET``, ``ZDX_CLOUD``

Troubleshooting
---------------

**Issue: Write tools not appearing**

Check:

1. Is ``ZSCALER_MCP_WRITE_ENABLED=true`` set?
2. Is ``ZSCALER_MCP_WRITE_TOOLS`` provided with patterns?
3. Do patterns match tool names? (use ``zscaler-mcp --list-tools`` to see all tools)

**Issue: Authentication fails**

Check:

1. For OneAPI: All 4 required variables set (CLIENT_ID, CLIENT_SECRET, CUSTOMER_ID, VANITY_DOMAIN)
2. For Legacy: ``ZSCALER_USE_LEGACY=true`` + service-specific credentials
3. Credentials are valid and not expired

**Issue: Service not available**

Check:

1. Service name is correct: ``zpa``, ``zia``, ``zdx``, ``zcc``, ``zidentity``
2. If using ``ZSCALER_MCP_SERVICES``, service is included in the list
