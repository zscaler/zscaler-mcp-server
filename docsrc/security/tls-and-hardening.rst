.. _security-tls-and-hardening:

TLS and Hardening
=================

The HTTP transports (``sse`` and ``streamable-http``) enforce four independent network-layer defenses:

1. **TLS enforcement** — plaintext HTTP is rejected on non-localhost binds unless explicitly allowed.
2. **Host header validation** — every request must match the ``ZSCALER_MCP_ALLOWED_HOSTS`` allowlist.
3. **Source IP ACL** — optional ``ZSCALER_MCP_ALLOWED_SOURCE_IPS`` allowlist for upstream filtering.
4. **CORS** — controlled by ``ZSCALER_MCP_ALLOWED_ORIGINS``.

TLS
---

When the bind address is anything other than ``127.0.0.1`` / ``::1`` / ``localhost``, the server **requires** TLS by default. The expected configuration:

.. code-block:: bash

   export ZSCALER_MCP_TLS_CERTFILE=/path/to/server.crt
   export ZSCALER_MCP_TLS_KEYFILE=/path/to/server.key

   zscaler-mcp --transport streamable-http --host 0.0.0.0 --port 8443

If you start with a non-localhost bind and no TLS configured, the server refuses to start and prints a security warning. This is the right default for any deployment that isn't a managed platform with its own TLS termination.

When TLS termination is upstream
--------------------------------

Cloud Run, Azure Container Apps, AWS ALB, and most managed Kubernetes ingresses terminate TLS before the request reaches your container. The server still believes it's on plaintext HTTP from inside, so you need to opt out of the enforcement:

.. code-block:: bash

   export ZSCALER_MCP_ALLOW_HTTP=true

   zscaler-mcp --transport streamable-http --host 0.0.0.0

Setting ``ZSCALER_MCP_ALLOW_HTTP=true`` does not disable TLS — it acknowledges that someone else is terminating it. This is the supported configuration for:

- Google Cloud Run
- Azure Container Apps
- AWS Bedrock AgentCore (ALB)
- Any Kubernetes deployment with an Ingress (NGINX, Traefik, AWS LB Controller) terminating TLS

For self-managed deployments (a single container or a single VM), keep TLS on by default and provide your own certificate.

Host header validation
----------------------

Every HTTP request's ``Host`` header is checked against an allowlist. This is a defense against DNS rebinding and reverse-tabnabbing attacks — the server only responds to requests addressed to a hostname you authorized.

The default allowlist is the bind address (``host:port``). To accept other hostnames:

.. code-block:: bash

   export ZSCALER_MCP_ALLOWED_HOSTS="mcp.acme.com,mcp.internal.acme.com,*.cloud.run.app"

Comma-separated, wildcards supported via shell-style globbing.

To disable host validation entirely (development only):

.. code-block:: bash

   export ZSCALER_MCP_DISABLE_HOST_VALIDATION=true

Source-IP ACL
-------------

An optional layer for deployments where the MCP server is reachable but should only respond to a known set of source addresses (typically an upstream proxy or NAT egress):

.. code-block:: bash

   # Single IP
   export ZSCALER_MCP_ALLOWED_SOURCE_IPS="203.0.113.5"

   # Multiple IPs / CIDRs
   export ZSCALER_MCP_ALLOWED_SOURCE_IPS="203.0.113.0/24,198.51.100.5,2001:db8::/32"

Requests from outside the allowlist receive 403 Forbidden before any auth check runs. Useful as an air-gap layer in front of MCP client authentication.

CORS
----

For browser-based MCP clients, the server's CORS policy is controlled by:

.. code-block:: bash

   export ZSCALER_MCP_ALLOWED_ORIGINS="https://app.example.com,https://internal.example.com"

Comma-separated origins. The default is empty (no cross-origin requests allowed). The MCP spec does not require browser clients — most MCP clients today are desktop apps that don't trigger CORS checks.

Output sanitization
-------------------

Independent of network-layer hardening, the server runs every string in every tool response through a three-stage sanitizer before serialization. This is the defense-in-depth layer against prompt injection embedded in admin-editable fields (rule descriptions, label names, location names, custom URL category names). See :doc:`output-sanitization` for the full mechanism.

Defense in depth summary
------------------------

A production deployment typically combines several of these:

.. code-block:: bash

   # ~/zscaler-mcp.env
   ZSCALER_MCP_HOST=0.0.0.0
   ZSCALER_MCP_PORT=8443

   # TLS (or ZSCALER_MCP_ALLOW_HTTP=true if upstream terminates)
   ZSCALER_MCP_TLS_CERTFILE=/etc/ssl/zscaler-mcp.crt
   ZSCALER_MCP_TLS_KEYFILE=/etc/ssl/zscaler-mcp.key

   # Host header allowlist
   ZSCALER_MCP_ALLOWED_HOSTS=mcp.acme.com

   # Source-IP ACL (corporate egress NAT range only)
   ZSCALER_MCP_ALLOWED_SOURCE_IPS=203.0.113.0/24

   # Authentication
   ZSCALER_MCP_AUTH_ENABLED=true
   ZSCALER_MCP_AUTH_MODE=zscaler

   # Writes disabled by default; opt in if needed
   ZSCALER_MCP_WRITE_ENABLED=false

Security posture banner
-----------------------

On startup, the server prints a security posture summary that captures the resolved configuration of every hardening layer:

.. code-block:: text

   [SECURITY] transport=streamable-http  host=0.0.0.0:8443  tls=on
              auth=zscaler (cache_ttl=3600s)  host_validation=on
              source_ip_acl=203.0.113.0/24  write_tools=disabled
              sanitization=on  audit_logging=off

The banner is logged regardless of log level — it gives the operator a single line to confirm what's actually live without rereading the config.

See also
--------

- :doc:`mcp-client-auth` — the authentication layer that runs after host/IP/TLS checks pass.
- :doc:`write-operations` — limiting the blast radius of an authenticated agent.
- :doc:`output-sanitization` — the application-layer defense against prompt injection.
