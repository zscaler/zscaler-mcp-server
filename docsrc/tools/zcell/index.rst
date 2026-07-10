Zscaler Cellular (ZCell) Tools
================================

The Zscaler Cellular (ZCell) tools provide read-only visibility into your
Zscaler Cellular deployment: SIM inventory, data-usage analytics, anomaly
policies, audit logs, and network/session events.

.. note::

   **ZCell requires one extra credential.** In addition to the standard OneAPI
   credentials, ZCell tools need your **Zscaler Cellular customer ID**, supplied
   via the ``ZCELL_CUSTOMER_ID`` environment variable (or the ``zcellCustomerId``
   config key). This is **separate** from ``ZSCALER_CUSTOMER_ID`` (used by ZPA) —
   if you use both ZPA and ZCell, set both variables. All other OneAPI
   credentials (``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET`` /
   ``ZSCALER_PRIVATE_KEY``, ``ZSCALER_VANITY_DOMAIN``) are shared across services.

   .. code-block:: bash

      ZSCALER_CLIENT_ID="your_client_id"
      ZSCALER_CLIENT_SECRET="your_client_secret"
      ZSCALER_VANITY_DOMAIN="your_vanity_domain"
      ZCELL_CUSTOMER_ID="your_zscaler_cellular_customer_id"   # required for ZCell

.. important::

   ZCell tools are **read-only** — they only query data and never modify your
   Zscaler Cellular configuration.

Available Tools
---------------

.. list-table:: ZCell Tools
   :header-rows: 1
   :widths: 34 66

   * - Tool Name
     - Description
   * - ``zcell_list_sims``
     - Search the SIM inventory with filters and pagination
   * - ``zcell_get_sim_details``
     - Get the full record for one SIM by ICCID
   * - ``zcell_list_sim_analytics_summary``
     - SIM status summary (total / used / active / inactive)
   * - ``zcell_list_sim_analytics_map``
     - SIM map points (dashboard lat/lng summary)
   * - ``zcell_list_sim_usage_by_sim``
     - Data usage grouped by SIM (top SIMs)
   * - ``zcell_list_sim_usage_by_day``
     - Data usage per day over the window
   * - ``zcell_list_sim_usage_by_country``
     - Data usage grouped by country (top countries)
   * - ``zcell_list_sim_location_groups``
     - List SIM location groups
   * - ``zcell_get_sim_location_group``
     - Get one SIM location group
   * - ``zcell_list_anomaly_policies``
     - List anomaly policies
   * - ``zcell_list_anomaly_policy_logs``
     - List the activity log for one anomaly policy
   * - ``zcell_list_anomaly_policy_violations``
     - List the ICCIDs that violated an anomaly policy
   * - ``zcell_list_iccid_violations``
     - List anomaly-policy violation events for one ICCID
   * - ``zcell_get_customer_data_handling``
     - Get the logged-in customer's profile and SIM totals
   * - ``zcell_list_regions``
     - List the regions available/configured for the customer
   * - ``zcell_list_region_operational_status``
     - List configured regions with their operational status
   * - ``zcell_list_audit_customers_search``
     - Search audit-log entries over a lookback window
   * - ``zcell_list_audit_metadata``
     - List the audit filter vocabulary
   * - ``zcell_list_network_events``
     - Search network/session events over a lookback window
   * - ``zcell_list_tags``
     - List the SIM tags defined for the customer

Toolsets
--------

ZCell tools are split into nine toolsets so you can enable only the surface you
need (for example ``--toolsets zcell_sim_handling,zcell_sim_analytics``):

.. list-table:: ZCell Toolsets
   :header-rows: 1
   :widths: 34 66

   * - Toolset
     - Tools
   * - ``zcell_sim_handling``
     - SIM inventory search + per-SIM detail
   * - ``zcell_sim_analytics``
     - Usage/status analytics (summary, map, by-SIM/day/country)
   * - ``zcell_sim_location_groups``
     - SIM location group list + detail
   * - ``zcell_anomaly_policy``
     - Anomaly policies, logs, and violation lookups
   * - ``zcell_customer_data_handling``
     - Customer profile and SIM totals
   * - ``zcell_customer_region_handling``
     - Region catalog and operational status
   * - ``zcell_audit_data_handling``
     - Audit-log search and filter metadata
   * - ``zcell_network_events``
     - Network/session event search
   * - ``zcell_tag_handling``
     - SIM tag catalog

Time Windows
------------

Time-bounded ZCell queries — analytics, audit search, network events, and
anomaly-policy logs — accept a ``days`` lookback shorthand instead of raw
timestamps. For example, ``days=7`` scopes the query to the last seven days.

Examples
--------

.. code-block:: text

   # How many SIMs are active?
   "Give me the Zscaler Cellular SIM status summary."

   # Investigate one SIM
   "Show me the details and recent violations for ICCID 8988xxxxxxxxxxxxxxx."

   # Data-usage review
   "Which countries consumed the most Zscaler Cellular data in the last 30 days?"

Guided Prompts
--------------

If your MCP client supports prompts, the server offers ZCell playbooks that
chain these tools into a guided workflow:

- ``zcell_investigate_sim`` — investigate a single SIM end to end
- ``zcell_audit_data_usage`` — review data-usage trends and outliers
- ``zcell_review_anomaly_policies`` — review anomaly policies and their violations
