.. _security:

Security
========

The Zscaler MCP Server enforces five independent layers of defense, each with its own configuration and its own audit posture:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Layer
     - What it controls
   * - **Write operations**
     - Whether the server can mutate tenant state at all. Disabled by default; opt-in with ``--enable-write-tools`` and an explicit allowlist.
   * - **HMAC elicitation confirmations**
     - Whether destructive actions require a tamper-proof confirmation token (defaults to on for delete operations).
   * - **MCP Client Authentication**
     - Who can connect to the server over HTTP transports (JWT, API-key, Zscaler OneAPI, or OIDCProxy).
   * - **TLS and hardening**
     - Transport-layer protection, host header validation, source-IP ACL, allowed origins.
   * - **Output sanitization**
     - Stripping prompt-injection payloads (BiDi marks, zero-width chars, HTML, code fences with role tokens) from tool responses before they leave the wire.

This section documents each layer independently — they compose, and you should pick the right combination for your deployment.

.. toctree::
   :maxdepth: 1

   write-operations
   mcp-client-auth
   tls-and-hardening
   output-sanitization
   lifecycle

Security defaults
-----------------

The server's defaults are aggressive:

- **Read-only.** No write tools are registered unless you explicitly turn them on.
- **HTTP transports require auth.** ``ZSCALER_MCP_AUTH_ENABLED`` defaults to ``true`` for SSE and streamable-HTTP.
- **TLS-or-localhost.** Plaintext HTTP is rejected on non-localhost binds unless ``ZSCALER_MCP_ALLOW_HTTP=true`` is set explicitly.
- **Host header allowlist.** Every HTTP request is checked against ``ZSCALER_MCP_ALLOWED_HOSTS`` (defaults to the bind address only).
- **Output sanitization is on.** Every tool response runs through the three-stage sanitizer before serialization.

The fastest path to a known-secure deployment: start with stdio (no HTTP surface, all defaults apply), then layer in HTTP only where you need a remote agent.

What the server does NOT protect
--------------------------------

- The credentials in your ``.env`` file. Use a secrets manager (GCP Secret Manager, Azure Key Vault, AWS Secrets Manager) for production deployments.
- The Zscaler API itself. Tool calls hit the live tenant; an authenticated agent with write tools enabled can change live policy.
- The MCP client's prompt history. Conversation context is the responsibility of whichever AI assistant is connected.

See also
--------

- :doc:`../toolsets/index` — limiting the tool surface area is the cheapest mitigation against an over-privileged agent.
- :doc:`../guides/troubleshooting` — diagnostics for auth failures.
