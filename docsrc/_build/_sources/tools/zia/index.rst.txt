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
   * - ``zia_cloud_applications``
     - Tool for managing ZIA Shadow IT Cloud Applications
   * - ``zia_cloud_firewall_rule``
     - Manages ZIA Cloud Firewall Rules
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

:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
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
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
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
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
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
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
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

:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zia")
:type service: str

**Returns:**
- Dictionary with sandbox analysis information

**Example:**
.. code-block:: python

   sandbox_info = zia_sandbox_info()

For complete documentation of all ZIA tools, see the individual tool pages.

Authentication
--------------

ZIA tools support both OneAPI and Legacy authentication methods:

**OneAPI Authentication:**
- Uses OAuth2 client credentials
- Requires the following environment variables:

  * ``ZSCALER_CLIENT_ID``
  * ``ZSCALER_CLIENT_SECRET``
  * ``ZSCALER_VANITY_DOMAIN``
  * ``ZSCALER_CLOUD``

**Legacy Authentication:**
- Uses username, password, and API key
- Requires the following environment variables:

  * ``ZIA_USERNAME``
  * ``ZIA_PASSWORD``
  * ``ZIA_API_KEY``
  * ``ZIA_CLOUD``

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
