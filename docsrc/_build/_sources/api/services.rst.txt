Services API
============

Service classes for each Zscaler product (ZCC, ZIA, ZPA, ZDX, ZTW, ZIdentity, EASM, Z-Insights).

.. automodule:: zscaler_mcp.services
   :members:
   :undoc-members:
   :show-inheritance:

Service Overview
----------------

The Zscaler Integrations MCP Server provides service classes for each Zscaler product:

ZCC Service
~~~~~~~~~~~

Zscaler Client Connector service for device management.

.. list-table:: ZCC Service Methods
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``list_devices``
     - List ZCC devices
   * - ``devices_csv_exporter``
     - Export device data to CSV
   * - ``list_trusted_networks``
     - List trusted networks
   * - ``list_forwarding_profiles``
     - List forwarding profiles

ZIA Service
~~~~~~~~~~~

Zscaler Internet Access service for web security and policy management.

.. list-table:: ZIA Service Methods
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``activation``
     - Check or activate configuration changes
   * - ``atp_malicious_urls``
     - Manage malicious URL denylist
   * - ``auth_exempt_urls``
     - Manage authentication exempt URLs
   * - ``cloud_applications``
     - Manage Shadow IT cloud applications
   * - ``cloud_firewall_rule``
     - Manage cloud firewall rules
   * - ``geo_search``
     - Perform geographical lookups
   * - ``gre_range``
     - Discover GRE internal IP ranges
   * - ``gre_tunnels``
     - Manage GRE tunnels
   * - ``ip_destination_groups``
     - Manage IP destination groups
   * - ``ip_source_group``
     - Manage IP source groups
   * - ``user_groups``
     - List and retrieve user groups
   * - ``user_departments``
     - List and retrieve user departments
   * - ``users``
     - List and retrieve users
   * - ``location_management``
     - Manage locations
   * - ``network_app_group``
     - Manage network application groups
   * - ``rule_labels``
     - Manage rule labels
   * - ``ssl_inspection_rules``
     - Manage SSL inspection rules
   * - ``get_sandbox_quota``
     - Retrieve current sandbox quota usage
   * - ``get_sandbox_behavioral_analysis``
     - Retrieve sandbox behavioral analysis hash list
   * - ``get_sandbox_file_hash_count``
     - Retrieve sandbox file hash usage counts
   * - ``get_sandbox_report``
     - Retrieve sandbox analysis report for a specific hash
   * - ``static_ips``
     - Manage static IP addresses
   * - ``url_categories``
     - Manage URL categories
   * - ``vpn_credentials``
     - Manage VPN credentials

ZPA Service
~~~~~~~~~~~

Zscaler Private Access service for zero trust network access.

.. list-table:: ZPA Service Methods
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``access_policy``
     - Manage access policy rules
   * - ``app_connector_groups``
     - Manage app connector groups
   * - ``app_protection_policy``
     - Manage inspection policy rules
   * - ``app_protection_profiles``
     - List and search app protection profiles
   * - ``app_segments_by_type``
     - Retrieve application segments by type
   * - ``application_segments``
     - Manage application segments
   * - ``application_servers``
     - Manage application servers
   * - ``ba_certificates``
     - Manage browser access certificates
   * - ``enrollment_certificates``
     - Retrieve enrollment certificates
   * - ``forwarding_policy``
     - Manage client forwarding policy rules
   * - ``isolation_policy``
     - Manage isolation policy rules
   * - ``isolation_profile``
     - Retrieve cloud browser isolation profiles
   * - ``posture_profiles``
     - Retrieve posture profiles
   * - ``pra_credentials``
     - Manage privileged remote access credentials
   * - ``pra_portals``
     - Manage privileged remote access portals
   * - ``provisioning_key``
     - Manage provisioning keys
   * - ``saml_attributes``
     - Query SAML attributes
   * - ``scim_attributes``
     - Manage SCIM attributes
   * - ``scim_groups``
     - Retrieve SCIM groups
   * - ``segment_groups``
     - Manage segment groups
   * - ``server_groups``
     - Manage server groups
   * - ``service_edge_groups``
     - Manage service edge groups
   * - ``timeout_policy``
     - Manage timeout policy rules
   * - ``trusted_networks``
     - Retrieve trusted networks

ZDX Service
~~~~~~~~~~~

Zscaler Digital Experience service for application performance monitoring.

.. list-table:: ZDX Service Methods
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``administration``
     - Discover departments or locations
   * - ``active_devices``
     - Discover devices using filters
   * - ``list_applications``
     - List active applications
   * - ``list_application_score``
     - Get application scores or trends
   * - ``get_application_metric``
     - Retrieve application metrics
   * - ``get_application_user``
     - List users/devices for applications
   * - ``list_software_inventory``
     - List software inventory
   * - ``list_alerts``
     - List ongoing alerts
   * - ``list_historical_alerts``
     - List historical alert rules
   * - ``list_deep_traces``
     - Retrieve deep trace information

ZTW Service
~~~~~~~~~~~

Zscaler Cloud & Branch Connector service for branch connectivity.

.. list-table:: ZTW Service Methods
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``ip_destination_groups``
     - Manage IP destination groups
   * - ``ip_group``
     - Manage IP groups
   * - ``ip_source_groups``
     - Manage IP source groups
   * - ``network_service_groups``
     - Manage network service groups
   * - ``list_roles``
     - List admin roles
   * - ``list_admins``
     - List admin users
   * - ``discovery_service``
     - Manage workload discovery service settings

ZIdentity Service
~~~~~~~~~~~~~~~~~

Zscaler Identity service for user and group management.

.. list-table:: ZIdentity Service Methods
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``groups``
     - Retrieve group information
   * - ``users``
     - Retrieve user information

EASM Service
~~~~~~~~~~~~

Zscaler External Attack Surface Management service for monitoring external assets.

.. list-table:: EASM Service Methods
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``list_organizations``
     - List all EASM organizations
   * - ``list_findings``
     - List security findings for an organization
   * - ``get_finding``
     - Get details for a specific finding
   * - ``get_finding_evidence``
     - Get evidence for a finding
   * - ``get_finding_scan_output``
     - Get complete scan output for a finding
   * - ``list_lookalike_domains``
     - List lookalike domains for an organization
   * - ``get_lookalike_domain``
     - Get details for a specific lookalike domain

Z-Insights Service
~~~~~~~~~~~~~~~~~~

Zscaler Z-Insights Analytics service for traffic and threat analytics.

Z-Insights provides read-only analytics through Zscaler's GraphQL-based analytics API.
All tools in this service query historical data with a 24-48 hour processing delay.

.. note::

   Z-Insights requires OneAPI authentication (OAuth2). Legacy API keys are not supported.
   Data queries should use time ranges that end at least 2 days ago.

**Available Domains:**

- WEB_TRAFFIC: Web traffic analytics and threat data
- CYBER_SECURITY: Cybersecurity incidents and threat analysis
- ZERO_TRUST_FIREWALL: Firewall activity and rule analytics
- SAAS_SECURITY: Cloud Access Security Broker (CASB) data
- SHADOW_IT: Unsanctioned application discovery
- IOT: IoT device visibility and statistics

.. list-table:: Z-Insights Service Methods (16 tools)
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``get_web_traffic_by_location``
     - Get web traffic analytics grouped by location
   * - ``get_web_traffic_no_grouping``
     - Get total/overall web traffic volume
   * - ``get_web_protocols``
     - Get web protocol distribution (HTTP, HTTPS, etc.)
   * - ``get_threat_super_categories``
     - Get threat category analytics (malware, phishing, spyware)
   * - ``get_threat_class``
     - Get threat class analytics (virus, trojan, ransomware)
   * - ``get_cyber_incidents``
     - Get cybersecurity incidents by category
   * - ``get_cyber_incidents_by_location``
     - Get incidents grouped by location, user, app, or department
   * - ``get_cyber_incidents_daily``
     - Get daily cybersecurity incident trends
   * - ``get_cyber_incidents_by_threat_and_app``
     - Get incidents correlated by threat category and application
   * - ``get_firewall_by_action``
     - Get firewall traffic by action (allow/block)
   * - ``get_firewall_by_location``
     - Get firewall traffic grouped by location
   * - ``get_firewall_network_services``
     - Get firewall network service usage
   * - ``get_casb_app_report``
     - Get CASB SaaS application usage report
   * - ``get_shadow_it_apps``
     - Get discovered shadow IT applications
   * - ``get_shadow_it_summary``
     - Get shadow IT summary statistics
   * - ``get_iot_device_stats``
     - Get IoT device statistics and classifications

**Key Parameters:**

- ``start_days_ago`` / ``end_days_ago``: Recommended way to specify time range (e.g., 7 to 2 for last week)
- ``start_time`` / ``end_time``: Alternative epoch milliseconds for specific timestamps
- ``traffic_unit``: TRANSACTIONS (request counts) or BYTES (data volume)
- ``include_trend``: Include time series trend data
- ``trend_interval``: DAY or HOUR for trend granularity

Usage Examples
--------------

Accessing Services
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from zscaler_mcp.client import get_zscaler_client

   client = get_zscaler_client()

   # Access ZIA service
   zia_service = client.zia

   # Access ZPA service
   zpa_service = client.zpa

   # Access ZDX service
   zdx_service = client.zdx

   # Access ZCC service
   zcc_service = client.zcc

   # Access ZTW service
   ztw_service = client.ztw

   # Access ZIdentity service
   zidentity_service = client.zidentity

Service Methods
~~~~~~~~~~~~~~~

.. code-block:: python

   # ZIA example
   from zscaler_mcp.client import get_zscaler_client

   client = get_zscaler_client()

   # List users
   users = client.zia.users.list_users()

   # List URL categories
   categories = client.zia.url_categories.list_categories()

   # ZPA example
   # List application segments
   segments = client.zpa.application_segments.list_segments()

   # List segment groups
   groups = client.zpa.segment_groups.list_groups()

Z-Insights Analytics
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Z-Insights requires OneAPI (OAuth2) authentication
   from zscaler_mcp.client import get_zscaler_client

   # Get client with OneAPI (not legacy)
   client = get_zscaler_client(use_legacy=False, service="zinsights")

   # Get web traffic by location for the past week
   # Using days_ago approach (recommended)
   import time

   # Calculate timestamps: 7 days ago to 2 days ago
   current_time_ms = int(time.time() * 1000)
   end_time = current_time_ms - (2 * 24 * 60 * 60 * 1000)   # 2 days ago
   start_time = current_time_ms - (7 * 24 * 60 * 60 * 1000)  # 7 days ago

   # Get traffic by location
   entries, response, err = client.zinsights.web_traffic.get_traffic_by_location(
       start_time=start_time,
       end_time=end_time,
       traffic_unit="TRANSACTIONS",
       limit=10
   )

   # Get threat categories
   entries, response, err = client.zinsights.web_traffic.get_threat_super_categories(
       start_time=start_time,
       end_time=end_time,
       traffic_unit="TRANSACTIONS",
       limit=50
   )

   # Get web protocols distribution
   entries, response, err = client.zinsights.web_traffic.get_protocols(
       start_time=start_time,
       end_time=end_time,
       traffic_unit="BYTES",
       limit=20
   )
