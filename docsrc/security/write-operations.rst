.. _security-write-operations:

Write Operations
================

Write tools (create / update / delete / activate / bulk-mutate) are **disabled by default**. Every Zscaler MCP Server deployment ships as read-only until an operator explicitly opts in. This is the most important security control in the product.

Two-step opt-in
---------------

Enabling writes requires both a flag and an allowlist:

1. ``--enable-write-tools`` (or ``ZSCALER_MCP_WRITE_ENABLED=true``) turns the write subsystem on.
2. ``--write-tools "pattern1,pattern2,…"`` (or ``ZSCALER_MCP_WRITE_TOOLS``) declares which write tools are registered.

The second flag is intentionally **required** — there is no "enable all writes" shortcut. The minimum viable enablement:

.. code-block:: bash

   zscaler-mcp \
     --enable-write-tools \
     --write-tools "zpa_create_*,zia_update_*"

The patterns use ``fnmatch`` glob syntax. Concrete examples:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Pattern
     - What it allows
   * - ``zpa_create_*``
     - Every ZPA create-* tool (segments, server groups, policies, …)
   * - ``zia_update_*_rule``
     - Every ZIA rule-update tool (firewall, URL filtering, SSL inspection, …) but **not** create or delete
   * - ``zpa_*``
     - Every ZPA write tool — broadest pattern, use sparingly
   * - ``zia_create_url_filtering_rule``
     - One specific tool — narrowest pattern, audit-friendly

The patterns intersect with the toolset selection: a write tool that's outside the loaded toolsets won't be registered even if it matches a write pattern.

HMAC-confirmed destructive actions
----------------------------------

For destructive operations — every ``delete`` tool — the server requires a second, cryptographically signed confirmation step. The flow:

1. The agent calls the destructive tool (e.g. ``zpa_delete_application_segment(segment_id="123")``).
2. Instead of executing, the server returns a plain-text confirmation prompt naming the operation and the target resource, and carrying the token:

   .. code-block:: text

      DESTRUCTIVE OPERATION - CONFIRMATION REQUIRED

      Operation: DELETE Application Segment
      Resource ID/Name: 123 (segment_id)

      WARNING: This action CANNOT be undone!

      To proceed, please confirm that you want to delete this resource.
      To proceed, retry this tool call with: kwargs='{"confirmation_token": "<token>"}'

3. The agent surfaces the message to the human operator.
4. The operator approves, the agent calls the same tool again with the token in ``kwargs``, and only then does the delete execute.

The token is:

- **Bound to the tool name and every call parameter**, plus its expiry and a per-issue nonce. Changing any parameter between approval and execution invalidates the signature, so an approval for one resource can never be spent on another.
- **Single-use**: a redeemed signature is recorded until it expires, so one approval authorizes exactly one execution. The ledger is per process (see the caveat below).
- **Time-bounded**: default TTL is 300 seconds (configurable via ``ZSCALER_MCP_CONFIRMATION_TTL``).
- **HMAC-SHA256-signed** with a server-side key, so the token cannot be forged without a server round-trip.

.. warning::

   The confirmation token is **not, by itself, a defense against prompt injection**.
   It protects the window between approval and execution (tamper, replay, reuse,
   forgery). An agent that has been hijacked into calling a delete also receives the
   token and can redeem it in the same turn. The controls that actually contain that
   case are keeping write tools disabled by default and scoping ``--write-tools``
   narrowly. See :doc:`the MCP protocol posture guide </guides/mcp-protocol>` for the
   full threat model.

Multi-replica deployments
~~~~~~~~~~~~~~~~~~~~~~~~~

By default the signing key is **ephemeral and per-process**. Behind a load balancer
with more than one replica, a confirmation retry that lands on a different replica is
rejected as a parameter mismatch. Set ``ZSCALER_MCP_CONFIRMATION_SECRET`` to the same
value on every replica:

.. code-block:: bash

   ZSCALER_MCP_CONFIRMATION_SECRET="$(openssl rand -hex 32)"

The server logs a warning at startup when write tools are enabled on an HTTP transport
without it. Note that the single-use ledger remains per process, so with a shared
secret a token is spendable once per replica rather than once globally.

Implementation: ``src/zscaler_mcp/security/elicitation.py`` — ``check_confirmation()``.

Disabling confirmations
-----------------------

For automation pipelines where the operator approval is upstream (CI, a separate workflow engine), confirmations can be skipped:

.. code-block:: bash

   ZSCALER_MCP_SKIP_CONFIRMATIONS=true zscaler-mcp \
     --enable-write-tools \
     --write-tools "zpa_delete_*"

This is **production-disabling** for agent-driven flows — the whole point of the confirmation step is to make the AI agent's intent visible to a human before the API call executes. Only set ``ZSCALER_MCP_SKIP_CONFIRMATIONS=true`` when the calling system already has its own approval gate.

ZIA activation is its own gate
------------------------------

Every ZIA write tool stages changes in the pending bucket. Until ``zia_activate_configuration`` is called, the change is not live. The activation tool is itself a write tool — it must be in the ``--write-tools`` allowlist to be available.

In practice you want both, so a typical ZIA write deployment looks like:

.. code-block:: bash

   zscaler-mcp \
     --enable-write-tools \
     --write-tools "zia_create_*,zia_update_*,zia_delete_*,zia_activate_configuration"

If the agent forgets to call ``zia_activate_configuration`` after a batch of changes, nothing happens at the API level — the tenant view stays as it was. That's the safest failure mode.

What's considered a write tool
------------------------------

The registry is explicit. Every tool function is declared as either a read tool or a write tool in ``zscaler_mcp/services.py`` via the service class's ``read_tools`` / ``write_tools`` lists. The categorization is conservative:

- **Read**: list, get, search, count, lookup, validate, dry-run-style operations.
- **Write**: create, update, delete, activate, bulk-update, enroll, deauthorize, reset.

A read tool can never mutate tenant state — that's enforced at the service-class level, not by convention.

Audit
-----

To audit the write surface of a running server:

.. code-block:: bash

   # List every registered write tool
   zscaler-mcp --list-tools | grep -E "(create|update|delete|activate)"

   # Same, but limited to one service
   zscaler-mcp --list-tools | grep "zia_" | grep -E "(create|update|delete)"

When tool-call audit logging is enabled (``--log-tool-calls``), every write tool invocation produces a ``[TOOL CALL]`` / ``[TOOL OK]`` / ``[TOOL ERR]`` log line including the (redacted) arguments and result summary. See :doc:`../guides/audit-logging`.

Environment summary
-------------------

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Setting
     - Default
     - Purpose
   * - ``--enable-write-tools`` / ``ZSCALER_MCP_WRITE_ENABLED``
     - ``false``
     - Master switch for the write subsystem.
   * - ``--write-tools`` / ``ZSCALER_MCP_WRITE_TOOLS``
     - *(unset)*
     - Comma-separated ``fnmatch`` patterns. Required when writes are enabled.
   * - ``ZSCALER_MCP_SKIP_CONFIRMATIONS``
     - ``false``
     - Bypass HMAC confirmations for destructive tools. Use only when an upstream approval gate exists.
   * - ``ZSCALER_MCP_CONFIRMATION_TTL``
     - ``300`` (sec)
     - HMAC token expiry window.
   * - ``ZSCALER_MCP_CONFIRMATION_SECRET``
     - *(ephemeral per-process)*
     - Shared HMAC signing key. Set to the same value on every replica when running more than one, otherwise a confirmation retry landing on a different replica is rejected.

See also
--------

- :doc:`mcp-client-auth` — controlling who can connect in the first place.
- :doc:`../guides/audit-logging` — observability for every tool invocation.
- :doc:`output-sanitization` — defense against prompt-injection embedded in tool responses.
