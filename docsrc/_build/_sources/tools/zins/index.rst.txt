Zscaler Z-Insights Analytics Tools
====================================

The Z-Insights Analytics tools provide **read-only** access to Zscaler's analytics and reporting capabilities via the GraphQL-based analytics API. These 16 tools cover web traffic, cybersecurity incidents, firewall analytics, SaaS security, shadow IT, and IoT device visibility.

.. note::
   Z-Insights data has a 24-48 hour processing delay. When querying data, use time ranges
   that end at least 2 days ago for accurate results. Use ``start_days_ago`` and ``end_days_ago``
   parameters for easy time range specification.

Available Tools
---------------

.. list-table:: Z-Insights Tools
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``zins_get_web_traffic_by_location``
     - Get web traffic analytics grouped by location
   * - ``zins_get_web_traffic_no_grouping``
     - Get overall web traffic volume metrics
   * - ``zins_get_web_protocols``
     - Get web traffic by protocol (HTTP, HTTPS, SSL)
   * - ``zins_get_threat_super_categories``
     - Get threat super categories (malware, phishing, spyware)
   * - ``zins_get_threat_class``
     - Get detailed threat class breakdown
   * - ``zins_get_cyber_incidents``
     - Get cybersecurity incidents by category
   * - ``zins_get_cyber_incidents_by_location``
     - Get cybersecurity incidents grouped by location
   * - ``zins_get_cyber_incidents_daily``
     - Get daily cybersecurity incident trends
   * - ``zins_get_cyber_incidents_by_threat_and_app``
     - Get incidents correlated by threat and application
   * - ``zins_get_firewall_by_action``
     - Get Zero Trust Firewall traffic by action (allow/block)
   * - ``zins_get_firewall_by_location``
     - Get firewall traffic grouped by location
   * - ``zins_get_firewall_network_services``
     - Get firewall network service usage
   * - ``zins_get_casb_app_report``
     - Get CASB SaaS application usage report
   * - ``zins_get_shadow_it_apps``
     - Get discovered shadow IT applications with risk scores
   * - ``zins_get_shadow_it_summary``
     - Get shadow IT summary statistics and groupings
   * - ``zins_get_iot_device_stats``
     - Get IoT device statistics and classifications

Analytics Domains
-----------------

Z-Insights tools are organized across six analytics domains:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Domain
     - Tools
     - Description
   * - **WEB_TRAFFIC**
     - 3
     - Web traffic volume, location distribution, and protocol analysis
   * - **CYBER_SECURITY**
     - 4
     - Cybersecurity incidents by category, location, daily trend, and threat-app correlation
   * - **ZERO_TRUST_FIREWALL**
     - 3
     - Firewall traffic by action (allow/block), location, and network services
   * - **SAAS_SECURITY**
     - 1
     - CASB SaaS application usage report
   * - **SHADOW_IT**
     - 2
     - Discovered shadow IT applications and summary statistics
   * - **IOT**
     - 1
     - IoT device statistics and classifications

Common Parameters
-----------------

Most Z-Insights tools accept these filtering parameters:

- **start_days_ago** (int): How many days back to start the time range (default varies by tool)
- **end_days_ago** (int): How many days back to end the time range (minimum 1 for data availability)
- **interval** (str): Aggregation interval — must be ``7d`` or ``14d``
- **metric** (str): Metric type — ``transactions`` (default) or ``total_bytes``

.. important::
   The ``interval`` parameter must be either ``7d`` or ``14d``. Other values will be auto-corrected to the nearest valid interval.

Authentication
--------------

Z-Insights tools use OneAPI authentication:

- ``ZSCALER_CLIENT_ID``
- ``ZSCALER_CLIENT_SECRET``
- ``ZSCALER_VANITY_DOMAIN``
- ``ZSCALER_CUSTOMER_ID``

Common Use Cases
----------------

1. **Traffic Analysis** — Monitor web traffic volume and distribution across locations
2. **Threat Investigation** — Investigate cybersecurity incidents and threat categories
3. **Firewall Monitoring** — Analyze firewall allow/block rates and service usage
4. **Shadow IT Discovery** — Find unsanctioned applications and assess risk
5. **SaaS Visibility** — Monitor cloud application usage across the organization
6. **IoT Inventory** — Discover and classify IoT devices on the network
