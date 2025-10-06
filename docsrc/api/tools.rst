Tools API
=========

Individual tool implementations and their parameters.

Tool Structure
--------------

Each tool in the Zscaler Integrations MCP Server follows a consistent structure:

.. code-block:: python

   def tool_name(
       action: Literal["read", "read_lite", "create", "update", "delete"],
       # Tool-specific parameters
       param1: Optional[str] = None,
       param2: Optional[int] = None,
       use_legacy: bool = False,
       service: str = "service_name",
   ) -> Union[dict, List[dict]]:
       """
       Tool description and usage examples.
       """
       # Implementation
       pass

Common Parameters
-----------------

All tools share common parameters:

.. list-table:: Common Tool Parameters
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Type
     - Description
   * - ``action``
     - ``Literal``
     - Operation to perform (read, read_lite, create, update, delete)
   * - ``use_legacy``
     - ``bool``
     - Whether to use the legacy API (default: False)
   * - ``service``
     - ``str``
     - The service to use (default: service-specific)

Action Types
------------

Read Actions
~~~~~~~~~~~~

- ``read``: Retrieve full details of resources
- ``read_lite``: Retrieve minimal details for faster performance

Write Actions
~~~~~~~~~~~~~

- ``create``: Create new resources
- ``update``: Update existing resources
- ``delete``: Delete resources

Tool Categories
---------------

ZCC Tools
~~~~~~~~~

.. automodule:: zscaler_mcp.tools.zcc.list_devices
   :members:
   :undoc-members:
   :show-inheritance:

ZIA Tools
~~~~~~~~~

.. automodule:: zscaler_mcp.tools.zia.list_users
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.list_user_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.list_user_departments
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.url_categories
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.url_filtering_rules
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.cloud_firewall_rules
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.ip_destination_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.ip_source_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.location_management
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.network_app_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.cloud_applications
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.atp_malicious_urls
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.auth_exempt_urls
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.list_dlp_dictionaries
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.list_dlp_engines
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zia.web_dlp_rules
   :members:
   :undoc-members:
   :show-inheritance:

ZPA Tools
~~~~~~~~~

.. automodule:: zscaler_mcp.tools.zpa.app_segments
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.segment_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.server_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.app_connector_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.service_edge_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.access_policy_rules
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.access_forwarding_rules
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.access_timeout_rules
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.access_isolation_rules
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zpa.access_app_protection_rules
   :members:
   :undoc-members:
   :show-inheritance:

ZDX Tools
~~~~~~~~~

.. automodule:: zscaler_mcp.tools.zdx.active_devices
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zdx.get_application_user
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zdx.list_alerts
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zdx.list_deep_traces
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zdx.list_software_inventory
   :members:
   :undoc-members:
   :show-inheritance:

ZTW Tools
~~~~~~~~~

.. automodule:: zscaler_mcp.tools.ztw.ip_destination_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.ztw.ip_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.ztw.ip_source_groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.ztw.network_service_groups
   :members:
   :undoc-members:
   :show-inheritance:

ZIdentity Tools
~~~~~~~~~~~~~~~

.. automodule:: zscaler_mcp.tools.zidentity.groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: zscaler_mcp.tools.zidentity.users
   :members:
   :undoc-members:
   :show-inheritance:

Tool Usage Examples
-------------------

Basic Tool Usage
~~~~~~~~~~~~~~~~

.. code-block:: python

   from zscaler_mcp.tools.zia.list_users import zia_user_manager

   # List all users
   users = zia_user_manager(action="read")

   # List users with search
   users = zia_user_manager(action="read", search="admin")

   # Get specific user
   user = zia_user_manager(action="read", user_id="12345")

Advanced Tool Usage
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from zscaler_mcp.tools.zpa.application_segments import zpa_application_segment_manager

   # Create new application segment
   segment = zpa_application_segment_manager(
       action="create",
       name="New App Segment",
       domain_names=["example.com"],
       server_groups=["server-group-id"]
   )

   # Update existing segment
   updated_segment = zpa_application_segment_manager(
       action="update",
       segment_id="segment-id",
       name="Updated App Segment"
   )

Error Handling
--------------

All tools return consistent error information:

.. code-block:: python

   try:
       result = tool_function(action="read")
   except Exception as e:
       print(f"Error: {e}")
       # Handle error appropriately
