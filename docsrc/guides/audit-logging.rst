.. _guide-audit-logging:

Tool-Call Audit Logging
=======================

Opt-in logging of every tool invocation. Useful for incident response, change tracking, debugging multi-step agent workflows, and proving exactly what was called against your tenant during an agent session.

Enabling
--------

Two equivalent switches:

.. code-block:: bash

   # CLI flag
   zscaler-mcp --log-tool-calls

   # Env var
   ZSCALER_MCP_LOG_TOOL_CALLS=true zscaler-mcp

Audit logging is intentionally separate from ``--debug`` (which is much more verbose and not safe to leave on in production). You can enable audit logging without turning on debug.

What gets logged
----------------

Every tool call produces two log lines via the ``zscaler_mcp.audit`` logger.

On success:

.. code-block:: text

   [TOOL CALL] zia_list_locations | args: {page: 1, page_size: 50, name: "HQ"}
   [TOOL OK]   zia_list_locations | 342ms | 15 items

On error:

.. code-block:: text

   [TOOL CALL] zms_list_resources | args: {page_num: 1}
   [TOOL ERR]  zms_list_resources | 1204ms | ConnectionError: timeout

The lines contain:

- The tool name.
- The arguments (with sensitive keys redacted — see below).
- The duration in milliseconds.
- On success, a result summary (item count for list tools; "ok" for scalars; HMAC token IDs for confirmation flows).
- On error, the exception class and message.

Full response data is **never** logged — only a summary. That's by design: audit logs should be diff-friendly, not data dumps.

Sensitive argument redaction
----------------------------

Argument values are redacted to ``***REDACTED***`` when the argument **name** contains any of:

- ``password``
- ``secret``
- ``token``
- ``key``
- ``credential``

The match is case-insensitive and substring-based — ``ZSCALER_CLIENT_SECRET``, ``my_api_token``, ``access_credential`` all match. False positives are accepted by design (better to over-redact).

What does NOT get redacted: rule descriptions, resource IDs, hostnames, JMESPath expressions, location names, etc. If your tenant uses sensitive strings in non-credential fields, you should know that — those values *will* appear in audit logs.

Where logs land
---------------

The audit logger uses Python's standard ``logging`` infrastructure. By default, output goes to stderr alongside the rest of the server logs.

To route audit logs to a separate file, configure Python logging via env or config file:

.. code-block:: python

   # Example: route audit logs to /var/log/zscaler-mcp/audit.log
   import logging
   handler = logging.FileHandler("/var/log/zscaler-mcp/audit.log")
   handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
   logging.getLogger("zscaler_mcp.audit").addHandler(handler)
   logging.getLogger("zscaler_mcp.audit").setLevel(logging.INFO)

Using a dedicated logger name means you can pipe audit lines through different sinks than the rest of the server logs (a syslog receiver, a SIEM forwarder, etc.) without entangling them.

In a container, the simplest path is to use ``docker logs`` and tag the lines downstream:

.. code-block:: bash

   docker logs zscaler-mcp-server 2>&1 | grep "^\[TOOL " > audit.log

When logging is off
-------------------

When ``--log-tool-calls`` is not set, the audit wrapper is a **no-op for logging**, but it **still sanitizes** every tool response (see :doc:`../security/output-sanitization`). The wrapper is always installed; only the logging side-effects are conditional.

Implementation
--------------

The audit wrapper lives at ``zscaler_mcp/common/tool_helpers.py::_wrap_with_audit``. It wraps every tool function at registration time, including:

- Service tools (registered via ``register_read_tools`` / ``register_write_tools``)
- The always-on meta tools (``zscaler_check_connectivity``, ``zscaler_get_available_services``, ``zscaler_list_toolsets``, ``zscaler_get_toolset_tools``, ``zscaler_enable_toolset``)

Coverage is uniform — there's no "audit-exempt" tool.

Lifecycle interaction
---------------------

The ``ZSCALER_MCP_LOG_TOOL_CALLS`` env var is re-applied on every SIGHUP soft-reload. To flip audit logging on a running server without restarting:

.. code-block:: bash

   # On the host
   sed -i 's/ZSCALER_MCP_LOG_TOOL_CALLS=false/ZSCALER_MCP_LOG_TOOL_CALLS=true/' /path/to/.env

   # If the .env is bind-mounted (or you docker cp'd it in):
   docker exec zscaler-mcp-server zscaler-mcp reload

The next tool call is logged. No session disruption.

See :doc:`../security/lifecycle` for the full reload model.

Audit log format stability
--------------------------

The line format is a **stable public interface**: ``[TOOL <STATE>] <tool_name> | <key>: <value> | …``. SIEM parsers, log shippers, and downstream analytics rules can rely on the layout. Any change to the format (new field, reordering) is treated as a breaking change and called out in the changelog.

Environment summary
-------------------

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Setting
     - Default
     - Effect
   * - ``--log-tool-calls`` / ``ZSCALER_MCP_LOG_TOOL_CALLS``
     - ``false``
     - Enable per-call audit lines via the ``zscaler_mcp.audit`` logger.

See also
--------

- :doc:`../security/output-sanitization` — runs always, regardless of audit logging.
- :doc:`../security/write-operations` — every write tool invocation produces an audit line when logging is enabled.
- :doc:`../security/lifecycle` — toggling the env var without restart.
