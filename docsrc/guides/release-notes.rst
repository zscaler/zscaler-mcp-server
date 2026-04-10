.. _release-notes:

Release Notes
=============

Zscaler Integrations MCP Server Changelog
------------------------------------------

## 0.9.1 (April 10, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13, v3.14**

### Features

`PR #47 <https://github.com/zscaler/zscaler-mcp-server/pull/47>`_ - Added **GitHub MCP Registry integration** (``server.json``) enabling one-click installation from GitHub Copilot and MCP-compatible clients. Declares PyPI and Docker packages with required Zscaler OneAPI credentials. Version auto-updated by the release pipeline.

### Bug Fixes

`PR #47 <https://github.com/zscaler/zscaler-mcp-server/pull/47>`_ - Upgraded Docker base image from ``python:3.13-alpine`` to ``python:3.14-alpine`` (digest-pinned) and explicitly patched Alpine packages to fix CVE-2026-28390 (openssl), CVE-2026-22184 (zlib). Applied same fixes to AWS ECR Dockerfile, replacing ``curl`` health check with busybox ``wget`` to eliminate 11 additional curl CVEs.

## 0.9.0 (April 9, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Features

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added **Azure Container Apps deployment** via interactive script (``azure_mcp_operations.py``). Pulls image from Docker Hub, supports 5 auth modes (OIDCProxy, JWT, API Key, Zscaler, None), and stores all secrets in Azure Key Vault.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added **Azure Virtual Machine deployment** with Ubuntu 22.04, systemd service, PyPI install, NSG configuration, and SSH access.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added **Azure AI Foundry Agent integration** (``foundry_agent.py``). Creates a managed GPT-4o agent that wraps the deployed MCP server as a tool via ``MCPTool``, with ``require_approval="always"`` for human oversight.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added **Foundry Agent interactive CLI chat** (``agent_chat``) with animated braille spinner, per-response token tracking, wall-clock timing, in-chat commands (``help``, ``status``, ``clear``, ``reset``), and end-of-session summary.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added **OIDCProxy support for Microsoft Entra ID** as an identity provider. Entra ID works as a drop-in replacement for Auth0/Okta with ``audience`` set to the Application (client) ID.

### Enhancements

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Foundry Agent authenticates to MCP server via ``X-Zscaler-Client-ID`` / ``X-Zscaler-Client-Secret`` custom headers, bypassing Foundry's sensitive header restriction on ``Authorization`` and the ``project_connection_id`` URI parsing bug.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Foundry Agent chat implements proper response chaining via ``previous_response_id`` for multi-turn conversations with tool approvals.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Foundry Agent chat displays Zscaler ASCII logo banner on startup with agent name and version.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Foundry Agent chat includes **graceful API error handling** for common failures (DeploymentNotFound, authentication errors, rate limits, connection issues) with actionable remediation steps instead of raw tracebacks.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Azure deployment script uses **provider-neutral OIDC variable names** (``OIDCPROXY_DOMAIN``, ``OIDCPROXY_CLIENT_ID``, etc.) with backward-compatible fallbacks to ``AUTH0_*`` variables.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Azure deployment script auto-configures Claude Desktop and Cursor client configs with correct auth headers and MCP endpoint URL.

### Tests

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added **81 unit tests** for Azure deployment (``test_azure_mcp_operations.py``) and Foundry agent (``test_foundry_agent.py``) covering .env parsing, credential resolution, CLI parser, state management, VM setup script generation, MCP header building, error handling, agent lifecycle, and in-chat commands.

### Documentation

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added **Azure AI Foundry deployment guide** (``docs/deployment/azure-ai-foundry.md``) with end-to-end walkthrough covering both CLI and portal methods, Foundry project creation with screenshots, model deployment prerequisites, in-chat commands, environment variables, and troubleshooting.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added Azure integration README (``integrations/azure/README.md``) with architecture diagrams for Container Apps, VM, and Foundry Agent deployments, all CLI commands, client configuration examples, and troubleshooting guide.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Added Microsoft Entra ID OIDCProxy step-by-step guide (``docs/deployment/entra-id-oidcproxy.md``) with 7 portal screenshots covering app registration, client secret, ID tokens, API permissions, and endpoints.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Updated ``docsrc/integrations/index.rst`` with Azure Deployment, Azure AI Foundry Agent sections, quick start commands, and link to the Foundry deployment guide.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Updated root ``README.md`` with Azure deployment section including Foundry agent commands and platform integrations table.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Updated ``CLAUDE.md`` with Azure deployment architecture, Foundry Agent command reference with flags, in-chat commands, graceful error handling, deployment guide reference, and Entra ID guide reference.

`PR #46 <https://github.com/zscaler/zscaler-mcp-server/pull/46>`_ - Updated ``authentication-and-deployment.md`` with expanded Entra ID app registration instructions and link to the dedicated Entra ID guide.

## 0.8.1 (April 6, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Features

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Added **JMESPath client-side filtering** across all 88 list tools spanning 9 services (ZIA, ZPA, ZDX, ZCC, ZTW, ZID, EASM, ZINS, ZMS). Every list tool now accepts an optional ``query`` parameter for server-side filtering and projection of API results before they reach the AI agent.

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Added ``zscaler_search_tools`` meta-tool for AI agent tool discovery. Supports filtering by ``service``, ``name_contains``, ``description_contains``, and advanced JMESPath queries against the full tool registry. Returns tool name, description, service, and type (read/write) for each match.

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Added **tool-call audit logging** via ``--log-tool-calls`` CLI flag or ``ZSCALER_MCP_LOG_TOOL_CALLS`` environment variable. Logs tool name, sanitized arguments, execution duration, and result summary for every tool invocation. Sensitive parameters (passwords, secrets, tokens) are automatically redacted.

### Enhancements

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Added **ZMS GraphQL filtering and ordering** to 6 tool domains: resources, resource groups, policy rules, app zones, app catalog, and tags. Tools now accept ``filter_by`` parameters (name, status, resource_type, cloud_provider, cloud_region, platform_os) and ``sort_order`` for server-side query refinement.

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Added 3 new ZMS guided skills: ``review-tag-classification`` (tag namespace hierarchy analysis), ``analyze-policy-rules`` (policy rule optimization and conflict detection), and ``assess-workload-protection`` (workload coverage and agent health assessment).

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Created centralized JMESPath utility module (``zscaler_mcp/common/jmespath_utils.py``) shared across all services, with graceful error handling for invalid expressions and consistent return normalization.

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Added ``jmespath>=1.0.0`` as an explicit dependency in ``pyproject.toml``.

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Updated all 88 list tool descriptions in ``services.py`` to advertise JMESPath ``query`` parameter support for AI agent discoverability.

### Documentation

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Updated ``CLAUDE.md`` with JMESPath client-side filtering architecture, syntax reference, cross-service examples, and ``zscaler_search_tools`` usage patterns.

`PR #45 <https://github.com/zscaler/zscaler-mcp-server/pull/45>`_ - Updated ``CLAUDE.md`` with tool-call audit logging section covering CLI flag, environment variable, log format, sensitive parameter redaction, and result summarization.

## 0.8.0 (April 2, 2026)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

### Features

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Added ``GCP Cloud Run deployment`` with automated end-to-end deployment script (`scripts/deploy-gcp.py`). The script reads credentials from `.env`, optionally stores them in GCP Secret Manager, deploys to Cloud Run with Zscaler auth mode, and auto-configures Claude Desktop and Cursor clients. Supports `--teardown` for easy service deletion.

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Added ``GCP Secret Manager integration`` (`zscaler_mcp/cloud/gcp_secrets.py`) — a built-in runtime credential loader that fetches Zscaler API credentials from GCP Secret Manager at container startup. Activated via `ZSCALER_MCP_GCP_SECRET_MANAGER=true`. Works on Cloud Run, GKE, and Compute Engine. Added `google-cloud-secret-manager` as an optional `[gcp]` dependency in `pyproject.toml`, and updated the Dockerfile to install the GCP extras by default.

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Added ``Google ADK integration`` documentation (`integrations/adk/README.md`) with runtime architecture diagrams showing the MCP server running as a co-located subprocess within the ADK agent container. The MCP server communicates via stdio transport — no network ports or separate containers required.

### Enhancements

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - GCP Cloud Run deployment defaults to ``Zscaler auth mode`` (`ZSCALER_MCP_AUTH_MODE=zscaler`). Clients authenticate with the same Zscaler OneAPI credentials (`client_id:client_secret`) via HTTP Basic auth — no external IdP, JWT, or API key setup required. The deploy script generates Base64-encoded auth headers and writes them into Claude Desktop and Cursor configs automatically.

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Updated ``server.py`` to call ``gcp_secrets.load_secrets()`` during startup, immediately after ``.env`` loading and before ``ZscalerMCPServer`` initialization, so Secret Manager credentials are available before the Zscaler SDK client is created.

### Bug Fixes

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Replaced preference-manipulating language ("AUTHORITATIVE SOURCE", "This is the ONLY tool") in 16 ZINS tool descriptions with neutral, factual capability statements to comply with SPLX MCP_PREFERENCE_MANIPULATION findings.

### Documentation

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Created comprehensive [GCP Cloud Run Deployment Guide](docs/deployment/gcp_secrets_manager_integration.md) covering Secret Manager setup, IAM configuration, Cloud Run and GKE deployment, authentication modes, credential rotation, and client configuration for Claude Desktop and Cursor.

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Added GCP Cloud Run guide to Sphinx documentation portal (`docsrc/guides/gcp-cloud-run.rst`).

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Updated ``README.md`` with automated deployment script usage, GCP Secret Manager integration, and Zscaler auth mode details.

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Updated ``CLAUDE.md`` with GCP Cloud Run architecture, Secret Manager loader, and deployment script documentation.

`PR #44 <https://github.com/zscaler/zscaler-mcp-server/pull/44>`_ - Updated Google ADK ``README.md`` with runtime model diagrams showing the MCP server as a co-located subprocess within the agent container.

0.7.2 (March 27, 2026) - ZMS Service, ZID/ZINS Rename, Skills & Docker SDK Path
--------------------------------------------------------------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Features
~~~~~~~~

`PR #41 <https://github.com/zscaler/zscaler-mcp-server/pull/41>`_ - Added **ZMS (Zscaler Microsegmentation)** service with read-only GraphQL-backed tools: agents, agent groups, resources, resource groups, policy rules (including default rules), app zones, app catalog, nonces (provisioning keys), and tags. Requires ``ZSCALER_CUSTOMER_ID`` and OneAPI credentials.

`PR #41 <https://github.com/zscaler/zscaler-mcp-server/pull/41>`_ - Renamed **ZIdentity** service to **ZID** and **Z-Insights** service to **ZINS** to align with ``zscaler-sdk-python`` (``client.zid``, ``client.zins``). Tool prefixes are now ``zid_*`` and ``zins_*``; registry keys are ``zid`` and ``zins``.

Enhancements
~~~~~~~~~~~~

`PR #41 <https://github.com/zscaler/zscaler-mcp-server/pull/41>`_ - Added guided **skills** for ZINS (``analyze-web-traffic``, ``audit-shadow-it``, ``assess-network-security``) and ZMS (``audit-microsegmentation-posture``, ``troubleshoot-agent-deployment``), plus expanded ZMS skill content using the Microsegmentation API GraphQL schema reference (Query vs Mutation, managed/unmanaged/recommended resource groups, error handling).

`PR #41 <https://github.com/zscaler/zscaler-mcp-server/pull/41>`_ - **Dockerfile** (temporary dev path): optional install of a local ``zscaler_sdk_python`` tarball after ``uv sync`` to test against an unpublished SDK build; **``.dockerignore``** exception so ``local_dev/zscaler_sdk_python-*.tar.gz`` is included in the build context.

Fixes
~~~~~

`PR #41 <https://github.com/zscaler/zscaler-mcp-server/pull/41>`_ - **CWE-345 — HMAC confirmation token replay vulnerability.** Fixed 31 delete operations across ZPA, ZIA, and ZTW that passed empty parameters (``{}``) to ``check_confirmation()``, producing fungible HMAC-SHA256 tokens that could be replayed across different resources of the same type. All delete operations now bind the specific resource identifier into the HMAC payload, preventing cross-resource token replay. Added 6 regression tests including AST-based static analysis to prevent future occurrences.

`PR #41 <https://github.com/zscaler/zscaler-mcp-server/pull/41>`_ - Resolved **ruff** ``I001`` import-sorting issues in ZMS tool modules, ``services.py`` (ZMSService imports), and ZMS tests.

Documentation
~~~~~~~~~~~~~

`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Updated ``CLAUDE.md``, ``README.md``, ``docs/guides/supported-tools.md``, ``codecov.yml``, Sphinx ``docsrc/``, integrations, and tests for ZMS, ZID, and ZINS naming.

0.7.1 (March 26, 2026) - Tool & Service Exclusion, OIDCProxy Improvements
---------------------------------------------------------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Features
~~~~~~~~

`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Added ``--disabled-tools`` CLI flag and ``ZSCALER_MCP_DISABLED_TOOLS`` environment variable to exclude specific tools from registration. Supports ``fnmatch`` wildcard patterns (e.g., ``zcc_list_*`` disables all ZCC list tools).
`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_- Added ``--disabled-services`` CLI flag and ``ZSCALER_MCP_DISABLED_SERVICES`` environment variable to exclude entire services from loading. Accepts service names: ``zcc``, ``zdx``, ``zia``, ``zpa``, ``ztw``, ``zid``.
`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Combined ``--disabled-tools`` and ``--disabled-services`` for fine-grained control: disable an entire service to prevent loading, or selectively exclude individual tools while keeping the rest of the service active.

Enhancements
~~~~~~~~~~~~

`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_- Removed ``zcc_devices_csv_exporter`` tool — ``zcc_list_devices`` already returns equivalent data without file I/O overhead.
`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Added ``verify_id_token=True`` to OIDCProxy setup for cross-platform compatibility. Auth0 may return opaque access tokens that fail JWT validation on certain platforms (e.g., Windows Docker). Verifying the OIDC ``id_token`` instead ensures consistent behavior across macOS and Windows.
`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Added ``--debug`` CLI flag to ``setup-oidcproxy-auth.py`` for verbose token validation diagnostics (``FASTMCP_DEBUG=true``).
`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Added Step 2b to ``setup-oidcproxy-auth.py`` to clear stale ``mcp-remote`` OAuth caches and orphaned processes before server start, preventing ``EADDRINUSE`` and ``invalid_token`` errors after container restarts.

Documentation
~~~~~~~~~~~~~

`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Updated README with "Excluding Services and Tools" section documenting ``fnmatch`` wildcard syntax and combined usage examples.
`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Updated Authentication & Deployment Guide with troubleshooting entry for persistent 401 ``invalid_token`` on Windows Docker.
`PR #38 <https://github.com/zscaler/zscaler-mcp-server/pull/38>`_ - Added tip about prompt specificity for large tool catalogs.

0.7.0 (March 25, 2026) - Authentication, Security & Platform Integrations
--------------------------------------------------------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

MCP Client Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added multi-mode authentication for MCP clients connecting over HTTP transports (``sse``, ``streamable-http``). Authentication is disabled by default for backward compatibility and does not apply to ``stdio`` transport.

**Four authentication modes:**

- **api-key** — Simple shared secret. Client sends ``Authorization: Bearer <key>``. Best for quick setup and internal environments.
- **jwt** — External Identity Provider via JWKS. Tokens are validated locally using the IdP's public keys. Supports Auth0, Okta, Azure AD, Keycloak, AWS Cognito, PingOne, and Google Cloud Identity.
- **zscaler** — Zscaler OneAPI credential validation. Client sends Basic Auth (``client_id:client_secret``) or custom headers (``X-Zscaler-Client-ID`` / ``X-Zscaler-Client-Secret``). Server validates against Zscaler's ``/oauth2/v1/token`` endpoint.

**Architecture:**

- Implemented as ASGI middleware (``zscaler_mcp/auth.py``) that wraps HTTP transport apps before they reach FastMCP
- Two independent security layers: Layer 1 (MCP Client Auth) controls who can connect; Layer 2 (Zscaler API Auth) controls how the server authenticates to Zscaler APIs
- Zero overhead when authentication is disabled — middleware returns the app unchanged

Network Security
~~~~~~~~~~~~~~~~~

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added defense-in-depth network security controls for HTTP transports:

- **HTTPS / TLS Configuration** — Optional TLS termination at the server with ``ZSCALER_MCP_TLS_CERT_FILE`` and ``ZSCALER_MCP_TLS_KEY_FILE``
- **HTTPS Policy Enforcement** — ``ZSCALER_MCP_ALLOW_HTTP=false`` (default) blocks plaintext HTTP on non-localhost interfaces when TLS is not configured
- **Host Header Validation** — ``ZSCALER_MCP_ALLOWED_HOSTS`` restricts accepted ``Host`` headers to prevent DNS rebinding attacks; auto-configured for localhost
- **Source IP Access Control** — ``ZSCALER_MCP_ALLOWED_SOURCE_IPS`` restricts which client IPs can connect (CIDR notation supported)

Platform Integrations
~~~~~~~~~~~~~~~~~~~~~~

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added native platform integrations for AI development environments:

- **Claude Code Plugin** (``.claude-plugin/``) — Plugin manifest with marketplace support, 19 guided skills, and slash commands
- **Cursor Plugin** (``.cursor-plugin/``) — Plugin manifest with 19 guided skills for Cursor IDE
- **Gemini Extension** (``gemini-extension.json``, ``GEMINI.md``) — Google Gemini CLI extension with contextual tool guidance
- **Google ADK** (``integrations/adk/``) — Google Agent Development Kit integration for building autonomous Zscaler security agents powered by Gemini models
- **Integration documentation** (``integrations/``) — Dedicated README per platform with installation, configuration, and verification instructions

Enhancements
~~~~~~~~~~~~

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added ``--generate-auth-token`` CLI argument for generating authorization tokens from configured credentials

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added ``--write-tools``, ``--user-agent-comment``, ``--list-tools``, and ``--version`` CLI flags

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added ``ZSCALER_MCP_CONFIRMATION_TTL`` environment variable for configurable confirmation window on destructive operations

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added ``ZSCALER_MCP_AUTH_ALGORITHMS`` environment variable for restricting JWT validation algorithms

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added ``docker-run-http``, ``docker-stop``, and ``docker-generate-auth-token`` Makefile targets for HTTP transport and authentication workflows

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Added ``PyJWT[crypto]>=2.8.0`` dependency for JWT token validation

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Updated ``.env.example`` with MCP Client Authentication and network security environment variables

Documentation
~~~~~~~~~~~~~

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Created comprehensive `Authentication & Deployment Guide <https://github.com/zscaler/zscaler-mcp-server/blob/master/docs/deployment/authentication-and-deployment.md>`__ covering transport modes, authentication architecture, IdP-specific JWKS setup, Docker/Python deployment, client configuration, and troubleshooting

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Updated ``README.md`` with MCP Client Authentication section, network security features, and Platform Integrations reference

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Created ``integrations/README.md`` as central index for all platform integrations

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Created dedicated integration READMEs for Claude Code Plugin, Cursor Plugin, Gemini Extension, and Kiro Power

`PR #31 <https://github.com/zscaler/zscaler-mcp-server/pull/31>`_ - Updated Sphinx documentation portal (``docsrc/``) with platform integrations page and release notes for v0.7.0

0.6.2 (February 18, 2026)
--------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~

`PR #29 <https://github.com/zscaler/zscaler-mcp-server/pull/29>`_ - Added new ZIA tools:

- ``network_apps``
- ``network_services_group``
- ``network_services``
- ``zia_url_lookup``
- ``zia_list_cloud_app_control_actions``

`PR #29 <https://github.com/zscaler/zscaler-mcp-server/pull/29>`_ - Improved search capabilities in the ZIA tool:

- ``device_management``

0.6.1 (December 16, 2025) - Z-Insights Analytics Integration
------------------------------------------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~

`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - ✨ Added Z-Insights Analytics service with 16 read-only tools for Zscaler analytics via GraphQL API
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_web_traffic_by_location`` - Get web traffic analytics grouped by location
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_web_traffic_no_grouping`` - Get overall web traffic volume metrics
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_web_protocols`` - Get web traffic by protocol (HTTP, HTTPS, SSL)
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_threat_super_categories`` - Get threat super categories (malware, phishing, spyware)
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_threat_class`` - Get detailed threat class breakdown
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_cyber_incidents`` - Get cybersecurity incidents by category
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_cyber_incidents_by_location`` - Get cybersecurity incidents grouped by location
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_cyber_incidents_daily`` - Get daily cybersecurity incident trends
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_cyber_incidents_by_threat_and_app`` - Get incidents correlated by threat and application
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_firewall_by_action`` - Get Zero Trust Firewall traffic by action (allow/block)
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_firewall_by_location`` - Get firewall traffic grouped by location
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_firewall_network_services`` - Get firewall network service usage
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_casb_app_report`` - Get CASB SaaS application usage report
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_shadow_it_apps`` - Get discovered shadow IT applications with risk scores
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_shadow_it_summary`` - Get shadow IT summary statistics and groupings
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added ``zins_get_iot_device_stats`` - Get IoT device statistics and classifications

Bug Fixes
~~~~~~~~~

`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Fixed Z-Insights time interval defaults - changed from invalid intervals (5-day, 12-day) to valid 7 or 14-day intervals required by the API
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Fixed Z-Insights tools to return structured "no data" responses instead of throwing exceptions when API returns empty results
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Fixed Z-Insights tools to handle GraphQL errors gracefully (checking response body for errors even with HTTP 200 status)
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Fixed Z-Insights time range validation to ensure ``end_time`` is at least 1 day in the past for data availability
`PR #22 <https://github.com/zscaler/zscaler-mcp-server/pull/22>`_ - Added auto-adjustment logic for Z-Insights time intervals to automatically correct invalid intervals to nearest valid 7 or 14-day interval

0.6.0 (December 8, 2025) - AWS Kiro Power Integration
-----------------------------------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~

`PR #21 <https://github.com/zscaler/zscaler-mcp-server/pull/21>`_ - ✨ Added AWS Kiro Power integration for AI-assisted Zscaler platform management within the Kiro IDE. Includes POWER.md, mcp.json, and service-specific steering files for ZPA, ZIA, ZDX, ZCC, ZTW, EASM, and ZIdentity.

0.5.0 (November 22, 2025) - AWS Bedrock AgentCore Security Enhancement
-----------------------------------------------------------------------

.. note::

   This release contains enhancements specific to **AWS Bedrock AgentCore deployments only**. These changes are maintained in a separate private AWS-specific repository and do **not** modify the core Zscaler MCP Server in this repository. Standard MCP server functionality remains unchanged.

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - 🔐 AWS Bedrock AgentCore Security Enhancements

**Container-Based Secrets Manager Integration:**

- Container retrieves Zscaler API credentials from AWS Secrets Manager at runtime
- **Zero credentials exposed** in AgentCore configuration, CloudFormation templates, or deployment scripts
- Secrets encrypted at rest with AWS KMS and in transit via TLS
- Full CloudTrail audit logging for all secret access
- Backward compatible - supports both Secrets Manager and direct environment variable approaches

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - **CloudFormation Automation:**

- One-click deployment via Launch Stack button
- Automated AgentCore runtime deployment with conditional secret creation
- IAM execution roles with Secrets Manager permissions automatically configured

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Added ZEASM (External Attack Surface Management) service with 7 read-only tools:

- ``zeasm_list_organizations`` - List all EASM organizations configured for the tenant
- ``zeasm_list_findings`` - List all findings for an organization's internet-facing assets
- ``zeasm_get_finding_details`` - Get detailed information for a specific finding
- ``zeasm_get_finding_evidence`` - Get scan evidence attributed to a specific finding
- ``zeasm_get_finding_scan_output`` - Get complete scan output for a specific finding
- ``zeasm_list_lookalike_domains`` - List all lookalike domains detected for an organization
- ``zeasm_get_lookalike_domain`` - Get details for a specific lookalike domain

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Updated README.md with EASM tools documentation

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Created EASM documentation in ``docsrc/tools/easm/index.rst``

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Updated ``docsrc/tools/index.rst`` with EASM service reference

Bug Fixes
~~~~~~~~~

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ZDX ``zdx_list_alerts`` calling wrong SDK method (``alerts.read`` → ``alerts.list_ongoing``)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ZDX ``zdx_list_alert_affected_devices`` calling wrong SDK method (``alerts.read_affected_devices`` → ``alerts.list_affected_devices``)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ZDX ``zdx_list_application_users`` calling wrong SDK method (``apps.list_users`` → ``apps.list_app_users``)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ZDX ``zdx_get_application_user`` calling wrong SDK method and incorrect return handling (``apps.get_user`` → ``apps.get_app_user``)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ZDX ``zdx_list_software`` calling wrong SDK method and incorrect return handling (``inventory.list_software`` → ``inventory.list_softwares``)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ZDX ``zdx_get_software_details`` calling wrong SDK method (``inventory.get_software`` → ``inventory.list_software_keys``)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ZDX ``zdx_get_device_deep_trace`` incorrect return handling (SDK returns list, not single object)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed syntax error in ``services.py`` ZIdentityService (missing ``description`` key in tool registration)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed EASM tools incorrect ``use_legacy`` parameter handling (removed invalid syntax)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Fixed ``ZSCALER_CUSTOMER_ID`` incorrectly required for non-ZPA services (now only required for ZPA)

`PR #20 <https://github.com/zscaler/zscaler-mcp-server/pull/20>`_ - Updated ZDX unit tests to match corrected SDK method names (42 tests)

0.4.0 (November 19, 2025)
-----------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~~~~~

`PR #16 <https://github.com/zscaler/zscaler-mcp-server/pull/16>`_
 - Split the ZIA sandbox helper into dedicated tools (`zia_get_sandbox_quota`, `zia_get_sandbox_behavioral_analysis`, `zia_get_sandbox_file_hash_count`, `zia_get_sandbox_report`) so MCP clients can directly invoke quota/report endpoints.

`PR #16 <https://github.com/zscaler/zscaler-mcp-server/pull/16>`_
 - Added ZIA SSL Inspection Rules tools (`zia_list_ssl_inspection_rules`, `zia_get_ssl_inspection_rule`, `zia_create_ssl_inspection_rule`, `zia_update_ssl_inspection_rule`, `zia_delete_ssl_inspection_rule`) for managing SSL/TLS traffic decryption and inspection policies.

`PR #16 <https://github.com/zscaler/zscaler-mcp-server/pull/16>`_
 - Added ZTW workload discovery service tool (`ztw_get_discovery_settings`) for retrieving workload discovery service settings.

0.3.2 (November 4, 2025)
-----------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~~~~~

`PR #15 <https://github.com/zscaler/zscaler-mcp-server/pull/15>`_
 - Added custom User-Agent header support with format `zscaler-mcp-server/VERSION python/VERSION os/arch`. Users can append AI agent information via `--user-agent-comment` flag or `ZSCALER_MCP_USER_AGENT_COMMENT` environment variable.

0.3.1 (October 28, 2025) - Tool Registration & Naming Updates
--------------------------------------------------------------

Added
------

`PR #14 <https://github.com/zscaler/zscaler-mcp-server/pull/14>`_

- **ZIA Tools**: Added missing read-only tools to services registration
  - `get_zia_dlp_dictionaries` - Manage ZIA DLP dictionaries for data loss prevention
  - `get_zia_dlp_engines` - Manage ZIA DLP engines for rule processing
  - `get_zia_user_departments` - Manage ZIA user departments for organizational structure
  - `get_zia_user_groups` - Manage ZIA user groups for access control
  - `get_zia_users` - Manage ZIA users for authentication and access control

- **ZPA Tools**: Added missing read-only tools to services registration
  - `get_zpa_app_protection_profile` - Manage ZPA App Protection Profiles (Inspection Profiles)
  - `get_zpa_enrollment_certificate` - Manage ZPA Enrollment Certificates
  - `get_zpa_isolation_profile` - Manage ZPA Cloud Browser Isolation (CBI) profiles
  - `get_zpa_posture_profile` - Manage ZPA Posture Profiles
  - `get_zpa_saml_attribute` - Manage ZPA SAML Attributes
  - `get_zpa_scim_attribute` - Manage ZPA SCIM Attributes
  - `get_zpa_scim_group` - Manage ZPA SCIM Groups
  - `get_zpa_app_segments_by_type` - Manage ZPA application segments by type
  - `get_zpa_trusted_network` - Manage ZPA Trusted Networks

### Changed

- **Tool Naming Convention**: Updated tool names to follow consistent `get_*` pattern for read-only operations
  - ZIA tools: `zia_*_manager` → `get_zia_*`
  - ZPA tools: `*_manager` → `get_zpa_*`
  - Maintains backward compatibility with existing `zia_get_*` and `zpa_get_*` patterns

### Fixed

- **Tool Registration**: Resolved missing tool registrations in `zscaler_mcp/services.py`
- **Documentation**: Updated README.md with correct tool names and comprehensive tool listings

0.3.0 (October 27, 2025) - Security & Confirmation Release
-----------------------------------------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Security Enhancements
~~~~~~~~~~~~~~~~~~~~~

**Multi-Layer Security Model**:

- Default read-only mode (110+ safe tools always available)
- Global ``--enable-write-tools`` flag required for write operations
- **Mandatory allowlist** via ``--write-tools`` (supports wildcards: ``zpa_create_*``, ``zia_delete_*``)
- Tool annotations: ``readOnlyHint=True`` for read operations, ``destructiveHint=True`` for write operations
- **Double-confirmation for DELETE operations**: Permission dialog + server-side confirmation block (33 delete tools)

**Write Tools Allowlist** (Mandatory):

- No write tools registered unless explicit allowlist provided
- Prevents accidental "allow all" scenarios
- Granular control with wildcard patterns

**DELETE Operation Protection**:

- All 33 delete operations require **double confirmation**
- First: AI agent permission dialog (``destructiveHint``)
- Second: Server-side confirmation via hidden ``kwargs`` parameter
- Prevents irreversible actions from being executed accidentally

Added
~~~~~

- ``zscaler_mcp/common/tool_helpers.py``: Registration utilities for read/write tools with annotations
- ``zscaler_mcp/common/elicitation.py``: Confirmation logic for delete operations
- ``--enable-write-tools`` / ``ZSCALER_MCP_WRITE_ENABLED``: Global write mode toggle
- ``--write-tools`` / ``ZSCALER_MCP_WRITE_TOOLS``: Mandatory allowlist (required when write mode enabled)
- ``build_mcpb.sh``: Automated packaging script with bundled Python dependencies
- Hidden ``kwargs`` parameter to all 33 delete functions for server-side confirmation
- ``destructiveHint=True`` annotation to all 93 write operations

Changed
~~~~~~~

- MCPB packages now bundle all Python dependencies (51MB vs 499KB)
- Update operations now fetch current resource state to avoid sending null values to API
- Enhanced server logging with security posture information
- Updated test suite for confirmation-based delete operations (163 tests passing)

Fixed
~~~~~

- Fixed ``MockServer.add_tool()`` missing ``annotations`` parameter for ``--list-tools`` functionality
- Fixed update operations in ZPA segment groups, server groups, app connector groups, service edge groups to handle optional fields correctly
- Fixed Pydantic validation errors in confirmation responses (return string instead of dict)
- Fixed MCPB packaging to include all required dependencies
- Removed problematic ``test_use_legacy_env.py`` (attempted real API calls)
- Fixed 21 orphaned commas causing syntax errors
- Fixed missing Union imports

Documentation
~~~~~~~~~~~~~

- Updated README with comprehensive security model documentation
- Rewrote ``docsrc/guides/configuration.rst`` with clear authentication guide
- Added write tools allowlist examples and usage patterns
- Documented double-confirmation flow for delete operations
- Fixed Sphinx RST title underlines

## 0.2.2 (October 6, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

`PR #11 <https://github.com/zscaler/zscaler-mcp-server/pull/11>` Fixed README and other documents to change the name title from "Zscaler MCP Server" to "Zscaler Integrations MCP Server"


0.2.1 (September 18, 2025)
---------------------------

Notes
-----

- Python Versions: **v3.11, v3.12, v3.13**

`PR #10 <https://github.com/zscaler/zscaler-mcp-server/pull/10>`_ Fixed import sorting and markdown linting issues:

- Fixed Ruff import sorting errors in ``client.py``, ``services.py``, and ``utils.py``
- Fixed markdownlint formatting issues in ``docs/guides/release-notes.md``
- Updated GitHub workflows to include linter checks in release process

0.2.0 (September 18, 2025)
---------------------------

Notes
-----

- Python Versions: **v3.11, v3.12, v3.13**

NEW ZCC MCP Tools
~~~~~~~~~~~~~~~~~

`PR #9 <https://github.com/zscaler/zscaler-mcp-server/pull/9>`_ Added the following new tools:

- Added ``zcc_list_trusted_networks`` - List existing trusted networks
- Added ``zcc_list_forwarding_profiles`` - List existing forwarding profiles

NEW ZTW MCP Tools
~~~~~~~~~~~~~~~~~

`PR #9 <https://github.com/zscaler/zscaler-mcp-server/pull/9>`_ Added the following new tools:

- Added ``ztw_ip_destination_groups`` - Manages IP Destination Groups
- Added ``ztw_ip_group`` - Manages IP Pool Groups
- Added ``ztw_ip_source_groups`` - Manages IP Source Groups
- Added ``ztw_network_service_groups`` - Manages Network Service Groups
- Added ``ztw_list_roles`` - List all existing admin roles in Zscaler Cloud & Branch Connector
- Added ``ztw_list_admins`` - List all existing admin users or get details for a specific admin user

`PR #9 <https://github.com/zscaler/zscaler-mcp-server/pull/9>`_ - New documentation portal available in `ReadTheDocs <https://zscaler-mcp-server.readthedocs.io/>`

0.1.0 (August 15, 2025) - Initial Release
------------------------------------------

Notes
-----

- Python Versions: **v3.11, v3.12, v3.13**

Added
~~~~~

- Initial implementation for the zscaler-mcp server (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Support for Zscaler services: ``zcc``, ``zdx``, ``zia``, ``zpa``, ``zid`` (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Flexible per service initialization (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Streamable-http transport with Docker support (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Debug option (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Docker support (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Comprehensive end-to-end testing framework with 44+ tests
- Test runner script with multi-model testing support
- Mock API strategy for realistic testing scenarios
- ZIA tools for user management via the Python SDK:

  - ``zia_user_groups``: Lists and retrieves ZIA User Groups with pagination, filtering, and sorting
  - ``zia_user_departments``: Lists and retrieves ZIA User Departments with pagination, filtering, and sorting
  - ``zia_users``: Lists and retrieves ZIA Users with filtering and pagination

Changed
~~~~~~~

- Fixed import sorting and linting issues
- Simplified project structure by removing unnecessary nesting
- Updated test organization for better maintainability

Documentation
~~~~~~~~~~~~~

- Updated README ZIA Features to include the new tools (``zia_user_groups``, ``zia_user_departments``, ``zia_users``).