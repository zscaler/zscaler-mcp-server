Zscaler Cloud & Branch Connector (ZTW) Tools
==============================================

The Zscaler Cloud & Branch Connector (ZTW) tools provide functionality for managing network resources, IP groups, and administrative functions.

Available Tools
---------------

.. list-table:: ZTW Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``ztw_ip_destination_groups``
     - Manages ZTW IP Destination Groups (create, read, update, delete)
   * - ``ztw_ip_group``
     - Manages ZTW IP Pool Groups (create, read, update, delete)
   * - ``ztw_ip_source_groups``
     - Manages ZTW IP Source Groups (create, read, update, delete)
   * - ``ztw_network_service_groups``
     - Manages ZTW Network Service Groups (create, read, update, delete)
   * - ``ztw_list_roles``
     - List all existing admin roles in Zscaler Cloud & Branch Connector
   * - ``ztw_list_admins``
     - List all existing admin users or get details for a specific admin user

Tool Details
------------

ztw_ip_destination_groups
~~~~~~~~~~~~~~~~~~~~~~~~~~

Manages ZTW IP Destination Groups with full CRUD operations.

**Parameters:**

:param action: Action to perform ("create", "read", "update", "delete")
:type action: str
:param group_id: Group ID for read, update, delete operations
:type group_id: Optional[str]
:param name: Group name for create/update operations
:type name: Optional[str]
:param description: Group description for create/update operations
:type description: Optional[str]
:param ip_addresses: List of IP addresses for create/update operations
:type ip_addresses: Optional[List[str]]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "ztw")
:type service: str

**Returns:**
- Dictionary with group information or list of groups

**Example:**

.. code-block:: python

   # Create a new IP destination group
   group = ztw_ip_destination_groups(
       action="create",
       name="Office Network",
       description="Office IP addresses",
       ip_addresses=["192.168.1.0/24", "10.0.0.0/8"]
   )

ztw_ip_group
~~~~~~~~~~~~

Manages ZTW IP Pool Groups with full CRUD operations.

**Parameters:**

:param action: Action to perform ("create", "read", "update", "delete")
:type action: str
:param group_id: Group ID for read, update, delete operations
:type group_id: Optional[str]
:param name: Group name for create/update operations
:type name: Optional[str]
:param description: Group description for create/update operations
:type description: Optional[str]
:param ip_addresses: List of IP addresses for create/update operations
:type ip_addresses: Optional[List[str]]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "ztw")
:type service: str

**Returns:**
- Dictionary with group information or list of groups

**Example:**

.. code-block:: python

   # List all IP groups
   groups = ztw_ip_group(action="list")

ztw_ip_source_groups
~~~~~~~~~~~~~~~~~~~~

Manages ZTW IP Source Groups with full CRUD operations.

**Parameters:**

:param action: Action to perform ("create", "read", "update", "delete")
:type action: str
:param group_id: Group ID for read, update, delete operations
:type group_id: Optional[str]
:param name: Group name for create/update operations
:type name: Optional[str]
:param description: Group description for create/update operations
:type description: Optional[str]
:param ip_addresses: List of IP addresses for create/update operations
:type ip_addresses: Optional[List[str]]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "ztw")
:type service: str

**Returns:**
- Dictionary with group information or list of groups

**Example:**

.. code-block:: python

   # Update an existing IP source group
   group = ztw_ip_source_groups(
       action="update",
       group_id="12345",
       name="Updated Source Group",
       description="Updated description"
   )

ztw_network_service_groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manages ZTW Network Service Groups with full CRUD operations.

**Parameters:**

:param action: Action to perform ("create", "read", "update", "delete")
:type action: str
:param group_id: Group ID for read, update, delete operations
:type group_id: Optional[str]
:param name: Group name for create/update operations
:type name: Optional[str]
:param description: Group description for create/update operations
:type description: Optional[str]
:param services: List of network services for create/update operations
:type services: Optional[List[dict]]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "ztw")
:type service: str

**Returns:**
- Dictionary with group information or list of groups

**Example:**

.. code-block:: python

   # Create a network service group
   group = ztw_network_service_groups(
       action="create",
       name="Web Services",
       description="Common web services",
       services=[
           {"port": 80, "protocol": "TCP"},
           {"port": 443, "protocol": "TCP"}
       ]
   )

ztw_list_roles
~~~~~~~~~~~~~~~

List all existing admin roles in Zscaler Cloud & Branch Connector (ZTW).

**Parameters:**

:param include_auditor_role: Include or exclude auditor user information
:type include_auditor_role: Optional[bool]
:param include_partner_role: Include or exclude admin user information
:type include_partner_role: Optional[bool]
:param include_api_roles: Include or exclude API role information
:type include_api_roles: Optional[bool]
:param role_ids: Include or exclude role ID information
:type role_ids: Optional[List[str]]
:param search: Search string to filter roles by name
:type search: Optional[str]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "ztw")
:type service: str

**Returns:**
- List of role dictionaries

**Example:**

.. code-block:: python

   # List all roles with search filter
   roles = ztw_list_roles(search="admin", include_api_roles=True)

ztw_list_admins
~~~~~~~~~~~~~~~~

List all existing admin users or get details for a specific admin user in Zscaler Cloud & Branch Connector (ZTW).

**Parameters:**

:param action: Action to perform ("list_admins" or "get_admin")
:type action: str
:param admin_id: Admin ID for get_admin action
:type admin_id: Optional[str]
:param include_auditor_users: Include/exclude auditor users
:type include_auditor_users: Optional[bool]
:param include_admin_users: Include/exclude admin users
:type include_admin_users: Optional[bool]
:param include_api_roles: Include/exclude API roles
:type include_api_roles: Optional[bool]
:param search: Search string to filter by
:type search: Optional[str]
:param page: Page offset to return
:type page: Optional[int]
:param page_size: Number of records per page
:type page_size: Optional[int]
:param version: Specifies admins from a backup version
:type version: Optional[int]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "ztw")
:type service: str

**Returns:**
- List of admin dictionaries or single admin dictionary

**Example:**

.. code-block:: python

   # List all admins
   admins = ztw_list_admins(action="list_admins", page_size=50)
   
   # Get specific admin
   admin = ztw_list_admins(action="get_admin", admin_id="12345")

Authentication
--------------

ZTW tools support both OneAPI and Legacy authentication methods:

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

  * ``ZTW_USERNAME``
  * ``ZTW_PASSWORD``
  * ``ZTW_API_KEY``
  * ``ZTW_CLOUD``

Common Use Cases
----------------

1. **Network Management**: Create and manage IP groups for network segmentation
2. **Service Configuration**: Define network service groups for traffic management
3. **Administrative Control**: Manage admin roles and user permissions
4. **Resource Organization**: Organize network resources for better management

Error Handling
--------------

All ZTW tools include comprehensive error handling:

- **Authentication errors**: Invalid credentials or expired tokens
- **Permission errors**: Insufficient privileges for the requested operation
- **Validation errors**: Invalid parameters or malformed requests
- **Rate limiting**: Automatic retry with exponential backoff

For detailed error information, check the tool response for error messages and status codes.
