Zscaler Internet Access (ZIA) Tools
====================================

The Zscaler Internet Access (ZIA) tools provide comprehensive functionality for managing internet security policies, user administration, and network configuration.

Available Tools
---------------

.. list-table:: ZIA Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zia_activation``
     - Tool to check or activate ZIA configuration changes
   * - ``zia_atp_malicious_urls``
     - Manages the malicious URL denylist in the ZIA Advanced Threat Protection (ATP) policy
   * - ``zia_auth_exempt_urls``
     - Manages the list of cookie authentication exempt URLs in ZIA
   * - ``zia_list_shadow_it_apps``
     - List ZIA Shadow IT cloud applications (analytics catalog with numeric IDs and friendly names)
   * - ``zia_list_shadow_it_custom_tags``
     - List ZIA Shadow IT custom tags
   * - ``zia_bulk_update_shadow_it_apps``
     - Bulk update sanction state and/or custom tags on ZIA Shadow IT applications
   * - ``zia_list_cloud_app_policy``
     - List the ZIA policy-engine cloud-application catalog (canonical enum strings used by Web DLP, Cloud App Control, File Type Control, Bandwidth Classes, Advanced Settings)
   * - ``zia_list_cloud_app_ssl_policy``
     - List the ZIA cloud-application catalog scoped to SSL Inspection rules (canonical enum strings used by ``cloud_applications`` on SSL Inspection rules)
   * - ``zia_cloud_firewall_rule``
     - Manages ZIA Cloud Firewall Rules
   * - ``zia_cloud_firewall_dns_rule``
     - Manages ZIA Cloud Firewall DNS Rules (list/get/create/update/delete)
   * - ``zia_cloud_firewall_ips_rule``
     - Manages ZIA Cloud Firewall IPS Rules (list/get/create/update/delete)
   * - ``zia_file_type_control_rule``
     - Manages ZIA File Type Control Rules (list/get/create/update/delete) plus ``zia_list_file_type_categories``. Friendly cloud-application names on ``cloud_applications`` are auto-resolved to canonical enums.
   * - ``zia_sandbox_rule``
     - Manages ZIA Sandbox Rules (list/get/create/update/delete). Distinct from ``zia_sandbox_info`` (read-only sandbox reports/quotas).
   * - ``zia_time_interval``
     - Manages ZIA Time Intervals (list/get/create/update/delete). Reusable schedule objects (``start_time``/``end_time`` in minutes from midnight; ``days_of_week`` accepts ``EVERYDAY``, ``SUN``-``SAT``) referenced by policy rules via the ``time_windows`` field.
   * - ``zia_geo_search``
     - Performs geographical lookup actions using the ZIA Locations API
   * - ``zia_gre_range``
     - Tool for discovering available GRE internal IP ranges in ZIA
   * - ``zia_gre_tunnels``
     - Tool for managing ZIA GRE Tunnels and associated static IPs
   * - ``zia_ip_destination_groups``
     - Manages ZIA IP Destination Groups
   * - ``zia_ip_source_group``
     - Performs CRUD operations on ZIA IP Source Groups
   * - ``zia_user_groups``
     - Lists and retrieves ZIA User Groups with pagination, filtering and sorting
   * - ``zia_user_departments``
     - Lists and retrieves ZIA User Departments with pagination, filtering and sorting
   * - ``zia_users``
     - Lists and retrieves ZIA Users with filtering and pagination
   * - ``zia_location_management``
     - Tool for managing ZIA Locations
   * - ``zia_network_app_group``
     - Manages ZIA Network Application Groups
   * - ``zia_rule_labels``
     - Tool for managing ZIA Rule Labels
   * - ``zia_sandbox_info``
     - Tool for retrieving ZIA Sandbox information
   * - ``zia_static_ips``
     - Tool for managing ZIA Static IP addresses
   * - ``zia_url_categories``
     - Tool for managing ZIA URL Categories
   * - ``zia_vpn_credentials``
     - Tool for managing ZIA VPN Credentials
   * - ``zia_ssl_inspection_rules``
     - Tool for managing ZIA SSL Inspection Rules

Tool Categories
~~~~~~~~~~~~~~~

.. list-table:: ZIA Tool Categories
   :header-rows: 1
   :widths: 25 75

   * - Category
     - Tools
   * - User Management
     - Admin roles, user groups, departments, users
   * - Policy Management
     - URL filtering rules, firewall rules, DLP engines/dictionaries
   * - Network Configuration
     - GRE tunnels, static IPs, location management, IP groups
   * - Security Features
     - Sandbox analysis, ATP malicious URLs, cloud applications
   * - Reporting
     - Various reporting and analytics tools

Tool Details
------------

zia_activation
~~~~~~~~~~~~~~

Tool to check or activate ZIA configuration changes.

**Parameters:**

:param service: The service to use (default: "zia")
:type service: str

**Returns:**
- Dictionary with activation status information

**Example:**
.. code-block:: python

   status = zia_activation()

zia_user_groups
~~~~~~~~~~~~~~~

Lists and retrieves ZIA User Groups with pagination, filtering and sorting.

**Parameters:**

:param page: Specifies the page offset
:type page: Optional[int]
:param page_size: Specifies the page size
:type page_size: Optional[int]
:param search: The search string used to partially match
:type search: Optional[str]
:param service: The service to use (default: "zia")
:type service: str

**Returns:**
- List of user group dictionaries

**Example:**
.. code-block:: python

   groups = zia_user_groups(page=1, page_size=50, search="admin")

zia_url_categories
~~~~~~~~~~~~~~~~~~

Tool for managing ZIA URL Categories.

**Parameters:**

:param action: The action to perform (e.g., "read", "create", "update", "delete")
:type action: str
:param category_id: The ID of the category for "read", "update", "delete" actions
:type category_id: str, optional
:param service: The service to use (default: "zia")
:type service: str

**Returns:**
- Dictionary with category information or list of categories

**Example:**
.. code-block:: python

   categories = zia_url_categories(action="list")

zia_cloud_firewall_rule
~~~~~~~~~~~~~~~~~~~~~~~

Manages ZIA Cloud Firewall Rules.

**Parameters:**

:param action: The action to perform (e.g., "read", "create", "update", "delete")
:type action: str
:param rule_id: The ID of the rule for "read", "update", "delete" actions
:type rule_id: str, optional
:param service: The service to use (default: "zia")
:type service: str

**Returns:**
- Dictionary with rule information or list of rules

**Example:**
.. code-block:: python

   rules = zia_cloud_firewall_rule(action="list")

zia_sandbox_info
~~~~~~~~~~~~~~~~

Tool for retrieving ZIA Sandbox information.

**Parameters:**

:param service: The service to use (default: "zia")
:type service: str

**Returns:**
- Dictionary with sandbox analysis information

**Example:**
.. code-block:: python

   sandbox_info = zia_sandbox_info()

Two Cloud-Application Catalogs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ZIA exposes the cloud-application catalog through two distinct API surfaces.
Picking the right tool matters — the catalogs are not interchangeable.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Catalog
     - Tools
     - Identifier returned
   * - **Shadow IT analytics**
     - ``zia_list_shadow_it_apps``, ``zia_list_shadow_it_custom_tags``, ``zia_bulk_update_shadow_it_apps``
     - Numeric ``id`` (e.g. ``655377``), friendly ``name`` (e.g. ``Sharepoint Online``)
   * - **Policy-engine catalog**
     - ``zia_list_cloud_app_policy``, ``zia_list_cloud_app_ssl_policy``
     - Canonical ``app`` enum (e.g. ``SHAREPOINT_ONLINE``), display ``app_name``

Policy resources — SSL Inspection, Web DLP, Cloud App Control, File Type
Control, Bandwidth Classes, Advanced Settings — accept **only** the canonical
``app`` enum from the policy-engine catalog in their ``cloud_applications``
field. Passing a Shadow IT numeric ID or a friendly display name causes ZIA
to silently coerce the value to ``NONE``.

The SSL Inspection create/update tools (``zia_create_ssl_inspection_rule``,
``zia_update_ssl_inspection_rule``) include an in-process resolver that
auto-translates friendly names to canonical enums via
``zia_list_cloud_app_ssl_policy`` before sending the API call. The resolution
is cached for 5 minutes and surfaced back to the caller in a
``_cloud_applications_resolution`` field on the response. Set
``resolve_cloud_apps=False`` to opt out.

For complete documentation of all ZIA tools, see the individual tool pages.

Authentication
--------------

ZIA tools authenticate through **OneAPI** (OAuth2 client credentials).
Required environment variables:

  * ``ZSCALER_CLIENT_ID``
  * ``ZSCALER_CLIENT_SECRET``
  * ``ZSCALER_VANITY_DOMAIN``
  * ``ZSCALER_CLOUD``

Common Use Cases
----------------

1. **Policy Management**: Configure URL filtering and firewall rules
2. **User Administration**: Manage admin roles and user groups
3. **Network Security**: Configure GRE tunnels and static IPs
4. **Threat Protection**: Analyze files with sandbox and ATP features

Error Handling
--------------

All ZIA tools include comprehensive error handling:

- **Authentication errors**: Invalid credentials or expired tokens
- **Permission errors**: Insufficient privileges for the requested operation
- **Validation errors**: Invalid parameters or malformed requests
- **Rate limiting**: Automatic retry with exponential backoff

For detailed error information, check the tool response for error messages and status codes.
