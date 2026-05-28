.. _toolsets:

Toolsets
========

Tools are grouped into named **toolsets** so you can load only the slice of tools an agent actually needs — for example ``zia_url_filtering`` (5 tools) instead of every tool from every service (~300+). Toolsets are the recommended way to scope what an agent can see when you don't need the full catalog.

Why toolsets exist
------------------

Most MCP clients (Claude Desktop, Cursor, Gemini CLI) use **deferred tool loading** — they don't load all 300+ tools upfront. They search for relevant tools based on the user's prompt. Loading the whole catalog has three costs:

- **Tool search noise.** The client returns the *closest N* tools regardless of relevance. With 300+ tools loaded, many of those matches are unrelated.
- **Context window pressure.** Every loaded tool occupies a slice of the agent's prompt budget.
- **Audit blast radius.** Disabled-by-default narrowing is the cleanest way to keep a server scoped to "this agent only handles ZIA URL filtering."

The toolset system solves all three: pick the toolsets you want, and only those tools are registered.

The catalog
-----------

There are **52 toolsets** today, organized by service:

.. list-table::
   :header-rows: 1
   :widths: 15 10 75

   * - Service
     - Toolsets
     - Identifiers
   * - **ZIA**
     - 21
     - ``zia_url_filtering``, ``zia_cloud_firewall``, ``zia_ssl_inspection``, ``zia_dlp``, ``zia_cloud_app_control``, ``zia_file_type_control``, ``zia_sandbox``, ``zia_locations``, ``zia_url_categories``, ``zia_users``, ``zia_devices``, ``zia_authentication_settings``, ``zia_rule_labels``, ``zia_workload_groups``, ``zia_time_intervals``, ``zia_shadow_it``, ``zia_atp_policy``, ``zia_atp_malware``, ``zia_advanced_settings``, ``zia_admin``, ``zia_misc``
   * - **ZPA**
     - 19
     - ``zpa_app_segments``, ``zpa_access_policies``, ``zpa_policy``, ``zpa_app_connector_groups``, ``zpa_connectors``, ``zpa_server_groups``, ``zpa_segment_groups``, ``zpa_service_edge_groups``, ``zpa_provisioning_keys``, ``zpa_application_servers``, ``zpa_pra``, ``zpa_ba_certificates``, ``zpa_app_protection``, ``zpa_posture``, ``zpa_trusted_networks``, ``zpa_isolation``, ``zpa_idp``, ``zpa_microtenants``, ``zpa_misc``
   * - **ZDX**
     - 5
     - ``zdx_alerts``, ``zdx_locations``, ``zdx_software_inventory``, ``zdx_troubleshooting``, ``zdx_reports``
   * - **ZCC**
     - 1
     - ``zcc``
   * - **ZTW**
     - 1
     - ``ztw``
   * - **ZIdentity**
     - 1
     - ``zid``
   * - **EASM**
     - 1
     - ``zeasm``
   * - **Z-Insights**
     - 1
     - ``zins``
   * - **ZMS**
     - 1
     - ``zms``
   * - **Meta (always-on)**
     - 1
     - ``meta`` — cross-service discovery tools (``zscaler_check_connectivity``, ``zscaler_get_available_services``, ``zscaler_list_toolsets``, ``zscaler_get_toolset_tools``, ``zscaler_enable_toolset``)

The ``meta`` toolset is always loaded regardless of selection — it provides the discovery tools an agent uses to find other toolsets.

Selecting toolsets at startup
-----------------------------

Three layers of selection control which toolsets are registered when the server starts:

1. **Explicit selection** — ``--toolsets`` flag or ``ZSCALER_MCP_TOOLSETS`` env var.
2. **Implicit fallback** — every toolset whose service is in ``--services`` is loaded.
3. **Entitlement filter** — the selection is intersected with the products entitled by your OneAPI bearer token.

The most precise form is a comma-separated list of identifiers:

.. code-block:: bash

   zscaler-mcp --toolsets zia_url_filtering,zpa_app_segments

Two special values:

- ``--toolsets default`` loads a curated default-on subset (the operationally common toolsets for each service).
- ``--toolsets all`` loads every toolset.

When ``--toolsets`` is unset, the server falls back to "every toolset whose service is enabled" — preserving the legacy behaviour where ``--services zia,zpa`` loads every ZIA and ZPA tool.

Selection precedence
--------------------

The filter order is fixed:

1. ``--disabled-tools`` / ``ZSCALER_MCP_DISABLED_TOOLS`` (negative blocklist with ``fnmatch`` wildcards)
2. Toolset selection (from ``--toolsets`` or ``ZSCALER_MCP_TOOLSETS``)
3. ``--enabled-tools`` (positive allowlist, if set)
4. ``--write-tools`` (write-specific allowlist)

So ``--disabled-tools "zia_*"`` always wins, regardless of toolset selection. This is the right precedence — you can revoke a specific tool that the toolset would otherwise include.

The OneAPI entitlement filter
-----------------------------

After the operator-driven ``selected_toolsets`` is resolved, the server intersects the selection with the products listed in the OneAPI bearer token's ``service-info[].prd`` claim. The practical effect: if your tenant isn't entitled to ZMS, the ``zms`` toolset is silently dropped from the selection even if you asked for it.

The filter is **on by default** and is non-fatal — missing credentials, decode failure, network error, or empty ``service-info`` all log a single WARN line and the selection passes through unchanged. To opt out:

.. code-block:: bash

   # CLI flag
   zscaler-mcp --no-entitlement-filter

   # Or env var
   ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true zscaler-mcp

The ``meta`` toolset is always preserved regardless of entitlement.

Runtime toolset enable
----------------------

Toolset selection happens at server startup, but an agent can also enable a toolset on the fly by calling the always-on meta tool:

.. code-block:: text

   zscaler_enable_toolset(toolset="zia_url_filtering")

This registers every tool in the toolset using the same filter precedence as startup, so all rules (``disabled_tools``, ``write_tools``) still apply. Useful when the agent encounters a request that needs tools it wasn't initially given.

Discovery
---------

Three always-loaded meta tools cover toolset discovery:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Tool
     - Purpose
   * - ``zscaler_list_toolsets``
     - List the catalog with ``currently_enabled``, ``tool_count``, ``can_enable``, and (when ``can_enable: false``) ``unavailable_reason`` for each row. Filterable by ``name_contains`` / ``description_contains`` / ``service``.
   * - ``zscaler_get_toolset_tools``
     - List the member tools of a specific toolset with ``available`` and (when ``available: false``) ``unavailable_reason`` per row.
   * - ``zscaler_enable_toolset``
     - Register a toolset's tools at runtime (see above).

A toolset whose service is currently disabled returns ``can_enable: false`` with a reason explaining why — instead of leaving the agent to guess.

Per-toolset instructions
------------------------

Each toolset can carry an ``instructions`` snippet that's only sent to the agent **when the matching tools are loaded**. Snippets shared across multiple toolsets (for example the rule-family ``order``/``rank`` reminder bound to all five ZIA rule toolsets) are de-duplicated at compose time.

This keeps the model's prompt focused: if you're loaded with ``zpa_app_segments``, you get ZPA segment-onboarding context; you don't also get ZIA cloud-firewall rule-ordering guidance.

Helm chart and Kubernetes deployments
-------------------------------------

The Helm chart accepts a comma-separated ``--set toolsets=zia_url_filtering,zpa_app_segments`` value and forwards it to the container as ``ZSCALER_MCP_TOOLSETS``. See the chart README at `integrations/helm-chart <https://github.com/zscaler/zscaler-mcp-server/tree/master/integrations/helm-chart>`_ for the full Helm story.

Environment summary
-------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Variable / flag
     - Effect
   * - ``--toolsets`` / ``ZSCALER_MCP_TOOLSETS``
     - Comma-separated toolset identifiers. ``default`` and ``all`` are accepted as special values.
   * - ``--services`` / ``ZSCALER_MCP_SERVICES``
     - When ``--toolsets`` is unset, every toolset whose service appears here is loaded.
   * - ``--no-entitlement-filter`` / ``ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER``
     - Skip the OneAPI entitlement-product intersection (emergency override).
   * - ``--disabled-tools`` / ``ZSCALER_MCP_DISABLED_TOOLS``
     - Negative blocklist applied after toolset selection. Supports ``fnmatch`` wildcards (``zcc_*``, ``zia_list_device*``).
   * - ``--enabled-tools``
     - Positive allowlist applied after toolset selection.
   * - ``--write-tools`` / ``ZSCALER_MCP_WRITE_TOOLS``
     - Write-specific allowlist. Wildcards supported.

See also
--------

- :doc:`../tools/index` — full catalog of underlying tools
- :doc:`../skills/index` — guided multi-step workflows
- :ref:`platform-integrations` — wiring the server into specific MCP clients
