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

Confirmed destructive actions
-----------------------------

For destructive operations — every ``delete`` tool — the server requires a confirmation
step before it touches the Zscaler API. Two mechanisms exist and the server chooses
between them **per call**:

.. list-table::
   :header-rows: 1
   :widths: 14 30 28 28

   * -
     - Mechanism
     - Used when
     - Who decides
   * - **Primary**
     - Native MCP elicitation (SEP-2322)
     - The client advertises the ``elicitation`` capability
     - A **human**, in a client-rendered prompt
   * - Fallback
     - HMAC confirmation token
     - Any other caller
     - The **agent**, echoing a server-issued token

Native elicitation (preferred)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the connected client supports elicitation — Claude Desktop and Cursor both do —
the server issues an ``elicitation/create`` request mid-call. The client renders a
prompt naming the resource with two choices, ``delete`` and ``cancel``, and a human
answers. Choosing ``delete`` executes; anything else returns a "NOT performed" result
without calling the Zscaler API. A failed round trip fails **closed**.

The agent never sees or handles a token in this path. That is the point: the approval
arrives as a protocol field the client fills, not as tool-call arguments the model
authors, so a model that has been talked into calling a delete has no way to also
produce the approval.

HMAC token fallback
~~~~~~~~~~~~~~~~~~~

Used only when the caller cannot be prompted — a client that does not advertise the
capability, or a direct in-process call with no MCP session. The flow:

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

   The token fallback is **not, by itself, a defense against prompt injection**.
   It protects the window between approval and execution (tamper, replay, reuse,
   forgery). An agent that has been hijacked into calling a delete also receives the
   token and can redeem it in the same turn — which is exactly the gap native
   elicitation closes, and why it is preferred. Keeping write tools disabled by
   default and scoping ``--write-tools`` narrowly remains the strongest control on
   deployments whose clients lack elicitation support. See
   :doc:`the MCP protocol posture guide </guides/mcp-protocol>` for the full threat
   model.

Multi-replica deployments
~~~~~~~~~~~~~~~~~~~~~~~~~

.. important::

   Two separate things are per-process by default, and both matter here.

   The **token fallback** is single-process and cannot be shared: run a single
   replica if any of your clients lack elicitation support.

   For clients that *do* support elicitation, the encrypted confirmation state is
   also per-process **unless** you set ``ZSCALER_MCP_REQUEST_STATE_KEYS`` to a
   shared key ring. Session affinity is not an alternative — requests on the
   ``2026-07-28`` revision carry no session ID for a load balancer to pin on.

The signing key and the single-use ledger both live in process memory. Behind a load
balancer with more than one replica, a fallback confirmation retry that lands on a
different replica is rejected as a parameter mismatch, and the same happens across a
restart. The native elicitation path keeps no server-side state between the prompt and
the answer, so it scales out normally.

There is deliberately no Zscaler-specific setting to share the key. The MCP protocol
defines the answer in SEP-2322: the server returns an ``InputRequiredResult`` carrying
an opaque ``requestState`` that the SDK's ``RequestStateSecurity`` seals with a
rotating key ring built for multi-instance deployments. Adding a bespoke shared-secret
variable would duplicate that with a weaker primitive. See
:doc:`the MCP protocol posture guide </guides/mcp-protocol>` for the adoption plan.

Implementation: ``src/zscaler_mcp/security/elicitation.py`` —
``gate_destructive_operation()`` selects the path, ``confirm_via_elicitation()`` runs
the native flow, ``check_confirmation()`` runs the fallback.

Confirmations cannot be disabled
--------------------------------

There is no flag and no environment variable that skips the confirmation. A delete
against a live tenant is irreversible, so a security product should not ship a
supported way around its own guardrail on destructive actions.

For an automation pipeline whose approval gate is upstream, the right control is the
allowlist — grant the writes the pipeline needs and no deletes at all:

.. code-block:: bash

   zscaler-mcp \
     --enable-write-tools \
     --write-tools "zpa_create_*,zpa_update_*"

If the pipeline genuinely must delete, it drives the same two-step exchange every
other non-elicitation client does: call the tool, read the token out of the result,
call again with ``kwargs='{"confirmation_token": "<token>"}'``. That is a few lines of
client code, and it keeps the operation auditable.

.. note::

   A ``ZSCALER_MCP_SKIP_CONFIRMATIONS`` variable existed briefly and was removed
   before release. It is now inert: setting it has no effect, so it is safe to
   delete from any environment file still carrying it.

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
   * - ``ZSCALER_MCP_CONFIRMATION_TTL``
     - ``300`` (sec)
     - HMAC token expiry window. Nothing switches the confirmation itself off.

See also
--------

- :doc:`mcp-client-auth` — controlling who can connect in the first place.
- :doc:`../guides/audit-logging` — observability for every tool invocation.
- :doc:`output-sanitization` — defense against prompt-injection embedded in tool responses.
