Zscaler Microsegmentation (ZMS) Tools
======================================

The Zscaler Microsegmentation (ZMS) tools provide **read-only** access to the ZMS GraphQL API for querying microsegmentation data. These 20 tools cover agents, agent groups, resources, resource groups, policy rules, app zones, app catalog, nonces, and tags.

.. note::
   All ZMS tools are read-only (queries only — no mutations). ZMS
   authenticates exclusively through OneAPI.

Available Tools
---------------

.. list-table:: ZMS Tools
   :header-rows: 1
   :widths: 40 60

   * - Tool Name
     - Description
   * - ``zms_list_agents``
     - List ZMS agents with pagination and search
   * - ``zms_get_agent_connection_status_statistics``
     - Get aggregated connection status statistics for ZMS agents
   * - ``zms_get_agent_version_statistics``
     - Get aggregated version statistics for ZMS agents
   * - ``zms_list_agent_groups``
     - List ZMS agent groups with pagination and search
   * - ``zms_get_agent_group_totp_secrets``
     - Get TOTP secrets for a specific ZMS agent group
   * - ``zms_list_resources``
     - List ZMS resources with pagination and filtering
   * - ``zms_get_resource_protection_status``
     - Get protection status summary for ZMS resources
   * - ``zms_get_metadata``
     - Get event metadata for ZMS resources
   * - ``zms_list_resource_groups``
     - List ZMS resource groups with pagination and filtering
   * - ``zms_get_resource_group_members``
     - Get members of a specific ZMS resource group
   * - ``zms_get_resource_group_protection_status``
     - Get protection status summary for ZMS resource groups
   * - ``zms_list_policy_rules``
     - List ZMS policy rules with pagination and filtering
   * - ``zms_list_default_policy_rules``
     - List default policy rules for ZMS
   * - ``zms_list_app_zones``
     - List ZMS app zones with pagination and filtering
   * - ``zms_list_app_catalog``
     - List ZMS application catalog entries with pagination and filtering
   * - ``zms_list_nonces``
     - List ZMS nonces (provisioning keys) with pagination
   * - ``zms_get_nonce``
     - Get a specific ZMS nonce by its eyez ID
   * - ``zms_list_tag_namespaces``
     - List ZMS tag namespaces with pagination and filtering
   * - ``zms_list_tag_keys``
     - List tag keys within a specific ZMS tag namespace
   * - ``zms_list_tag_values``
     - List tag values for a specific ZMS tag key

Tool Domains
------------

ZMS tools are organized across nine domains:

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - Domain
     - Tools
     - Description
   * - **Agents**
     - 3
     - Agent inventory, connection status statistics, and version distribution
   * - **Agent Groups**
     - 2
     - Agent group listing and TOTP secret retrieval
   * - **Resources**
     - 3
     - Resource inventory, protection status, and event metadata
   * - **Resource Groups**
     - 3
     - Resource group listing, member enumeration, and protection status
   * - **Policy Rules**
     - 2
     - Custom and default microsegmentation policy rules
   * - **App Zones**
     - 1
     - Application zone listing with filtering
   * - **App Catalog**
     - 1
     - Application catalog entries with category filtering
   * - **Nonces**
     - 2
     - Provisioning key (nonce) listing and detail retrieval
   * - **Tags**
     - 3
     - Tag namespace, key, and value hierarchy navigation

Tool Details
------------

Agents
~~~~~~

zms_list_agents
^^^^^^^^^^^^^^^

List ZMS agents with pagination and search.

**Parameters:**

:param page: Page number for pagination
:type page: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param search: Search string to filter agents
:type search: Optional[str]
:param sort: Field to sort by
:type sort: Optional[str]
:param sort_dir: Sort direction (``asc`` or ``desc``)
:type sort_dir: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   agents = zms_list_agents(page=1, page_size=50, search="prod")

zms_get_agent_connection_status_statistics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get aggregated connection status statistics for ZMS agents.

**Parameters:**

:param search: Search string to filter agents before aggregation
:type search: Optional[str]

**Example:**

.. code-block:: python

   stats = zms_get_agent_connection_status_statistics()

zms_get_agent_version_statistics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get aggregated version statistics for ZMS agents.

**Parameters:**

:param search: Search string to filter agents before aggregation
:type search: Optional[str]

**Example:**

.. code-block:: python

   versions = zms_get_agent_version_statistics()

Agent Groups
~~~~~~~~~~~~

zms_list_agent_groups
^^^^^^^^^^^^^^^^^^^^^

List ZMS agent groups with pagination and search.

**Parameters:**

:param page: Page number for pagination
:type page: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param search: Search string to filter agent groups
:type search: Optional[str]
:param sort: Field to sort by
:type sort: Optional[str]
:param sort_dir: Sort direction (``asc`` or ``desc``)
:type sort_dir: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   groups = zms_list_agent_groups(page=1, page_size=20)

zms_get_agent_group_totp_secrets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get TOTP secrets for a specific ZMS agent group.

**Parameters:**

:param eyez_id: The unique eyez identifier for the agent group (required)
:type eyez_id: str

**Example:**

.. code-block:: python

   secrets = zms_get_agent_group_totp_secrets(eyez_id="abc123-def456")

Resources
~~~~~~~~~

zms_list_resources
^^^^^^^^^^^^^^^^^^

List ZMS resources with pagination and filtering.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param include_deleted: Include deleted resources
:type include_deleted: Optional[bool]
:param name: Filter by resource name
:type name: Optional[str]
:param status: Filter by resource status
:type status: Optional[str]
:param resource_type: Filter by resource type
:type resource_type: Optional[str]
:param cloud_provider: Filter by cloud provider
:type cloud_provider: Optional[str]
:param cloud_region: Filter by cloud region
:type cloud_region: Optional[str]
:param platform_os: Filter by operating system
:type platform_os: Optional[str]
:param sort_order: Sort order
:type sort_order: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   resources = zms_list_resources(
       page_num=1, page_size=50,
       cloud_provider="AWS", status="active"
   )

zms_get_resource_protection_status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get protection status summary for ZMS resources.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]

**Example:**

.. code-block:: python

   status = zms_get_resource_protection_status()

zms_get_metadata
^^^^^^^^^^^^^^^^

Get event metadata for ZMS resources.

**Example:**

.. code-block:: python

   metadata = zms_get_metadata()

Resource Groups
~~~~~~~~~~~~~~~

zms_list_resource_groups
^^^^^^^^^^^^^^^^^^^^^^^^

List ZMS resource groups with pagination and filtering.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param name: Filter by resource group name
:type name: Optional[str]
:param resource_hostname: Filter by resource hostname
:type resource_hostname: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   groups = zms_list_resource_groups(page_num=1, page_size=20, name="prod")

zms_get_resource_group_members
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get members of a specific ZMS resource group.

**Parameters:**

:param group_id: The unique identifier for the resource group (required)
:type group_id: str
:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]

**Example:**

.. code-block:: python

   members = zms_get_resource_group_members(group_id="12345", page_num=1)

zms_get_resource_group_protection_status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get protection status summary for ZMS resource groups.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]

**Example:**

.. code-block:: python

   status = zms_get_resource_group_protection_status()

Policy Rules
~~~~~~~~~~~~

zms_list_policy_rules
^^^^^^^^^^^^^^^^^^^^^

List ZMS policy rules with pagination and filtering.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param fetch_all: Bypass pagination and fetch all rules (use sparingly on large tenants)
:type fetch_all: Optional[bool]
:param name: Filter by rule name
:type name: Optional[str]
:param action: Filter by rule action
:type action: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   rules = zms_list_policy_rules(page_num=1, page_size=50, action="allow")

zms_list_default_policy_rules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

List default policy rules for ZMS.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   defaults = zms_list_default_policy_rules()

App Zones
~~~~~~~~~

zms_list_app_zones
^^^^^^^^^^^^^^^^^^

List ZMS app zones with pagination and filtering.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param name: Filter by app zone name
:type name: Optional[str]
:param sort_order: Sort order
:type sort_order: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   zones = zms_list_app_zones(page_num=1, page_size=20)

App Catalog
~~~~~~~~~~~

zms_list_app_catalog
^^^^^^^^^^^^^^^^^^^^

List ZMS application catalog entries with pagination and filtering.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param name: Filter by application name
:type name: Optional[str]
:param category: Filter by application category
:type category: Optional[str]
:param sort_by: Field to sort by
:type sort_by: Optional[str]
:param sort_order: Sort order
:type sort_order: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   apps = zms_list_app_catalog(page_num=1, page_size=50, category="database")

Nonces
~~~~~~

zms_list_nonces
^^^^^^^^^^^^^^^

List ZMS nonces (provisioning keys) with pagination.

**Parameters:**

:param page: Page number for pagination
:type page: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param search: Search string to filter nonces
:type search: Optional[str]
:param sort: Field to sort by
:type sort: Optional[str]
:param sort_dir: Sort direction (``asc`` or ``desc``)
:type sort_dir: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   nonces = zms_list_nonces(page=1, page_size=20)

zms_get_nonce
^^^^^^^^^^^^^

Get a specific ZMS nonce (provisioning key) by its eyez ID.

**Parameters:**

:param eyez_id: The unique eyez identifier for the nonce (required)
:type eyez_id: str

**Example:**

.. code-block:: python

   nonce = zms_get_nonce(eyez_id="abc123-def456")

Tags
~~~~

ZMS tags follow a three-level hierarchy: **namespace → key → value**. Navigate top-down
to discover tag values.

zms_list_tag_namespaces
^^^^^^^^^^^^^^^^^^^^^^^

List ZMS tag namespaces with pagination and filtering.

**Parameters:**

:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param name: Filter by namespace name
:type name: Optional[str]
:param origin: Filter by namespace origin (``CUSTOM``, ``EXTERNAL``, ``ML``, ``UNKNOWN``)
:type origin: Optional[str]
:param sort_order: Sort order
:type sort_order: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   namespaces = zms_list_tag_namespaces(page_num=1, page_size=20)

zms_list_tag_keys
^^^^^^^^^^^^^^^^^

List tag keys within a specific ZMS tag namespace.

**Parameters:**

:param namespace_id: The unique identifier for the tag namespace (required)
:type namespace_id: str
:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param key_name: Filter by key name
:type key_name: Optional[str]
:param sort_order: Sort order
:type sort_order: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   keys = zms_list_tag_keys(namespace_id="ns-123", page_num=1, page_size=50)

zms_list_tag_values
^^^^^^^^^^^^^^^^^^^

List tag values for a specific ZMS tag key.

**Parameters:**

:param tag_id: The unique identifier for the tag key (required)
:type tag_id: str
:param namespace_origin: The origin of the namespace (required). Must be one of: ``CUSTOM``, ``EXTERNAL``, ``ML``, ``UNKNOWN``
:type namespace_origin: str
:param page_num: Page number for pagination
:type page_num: Optional[int]
:param page_size: Number of results per page
:type page_size: Optional[int]
:param name: Filter by tag value name
:type name: Optional[str]
:param sort_order: Sort order
:type sort_order: Optional[str]
:param query: JMESPath expression for client-side filtering
:type query: Optional[str]

**Example:**

.. code-block:: python

   values = zms_list_tag_values(
       tag_id="tag-456",
       namespace_origin="CUSTOM",
       page_num=1, page_size=50
   )

Pagination
----------

ZMS tools use two pagination patterns depending on the domain:

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Pattern
     - Parameters
     - Used By
   * - ``page`` / ``page_size``
     - ``page``, ``page_size``
     - Agents, Agent Groups, Nonces
   * - ``page_num`` / ``page_size``
     - ``page_num``, ``page_size``
     - Resources, Resource Groups, Policy Rules, App Zones, App Catalog, Tags

All paginated responses include ``pageInfo`` with ``pageNumber``, ``pageSize``, ``totalCount``, and ``totalPages``.

Authentication
--------------

ZMS tools authenticate through OneAPI:

- ``ZSCALER_CLIENT_ID``
- ``ZSCALER_CLIENT_SECRET``
- ``ZSCALER_VANITY_DOMAIN``
- ``ZSCALER_CUSTOMER_ID``

.. important::
   ``ZSCALER_CUSTOMER_ID`` is always required for ZMS. It is automatically resolved from the
   environment variable.

Common Use Cases
----------------

1. **Agent Inventory** — List and search microsegmentation agents across your environment
2. **Protection Assessment** — Check resource and resource group protection status
3. **Policy Review** — List and filter microsegmentation policy rules
4. **Tag Navigation** — Navigate the tag hierarchy (namespace → key → value) for asset classification
5. **App Zone Management** — Review application zone configurations
6. **Provisioning** — List and retrieve nonce (provisioning key) details

Error Handling
--------------

All ZMS tools include comprehensive error handling:

- **Authentication errors**: Invalid credentials or expired tokens
- **Permission errors**: Insufficient privileges for the requested operation
- **Validation errors**: Invalid parameters or malformed requests
- **Missing customer ID**: ``ZSCALER_CUSTOMER_ID`` is required for all ZMS operations

For detailed error information, check the tool response for error messages and status codes.
