Services API
============

Service classes for each Zscaler product (ZCC, ZIA, ZPA, ZDX, ZTW, Zidentity).

.. automodule:: zscaler_mcp.services
   :members:
   :undoc-members:
   :show-inheritance:

Service Overview
----------------

The Zscaler MCP Server provides service classes for each Zscaler product:

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
   * - ``sandbox_info``
     - Retrieve sandbox information
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
