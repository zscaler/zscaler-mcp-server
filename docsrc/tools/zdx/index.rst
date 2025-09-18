Zscaler Digital Experience (ZDX) Tools
========================================

The Zscaler Digital Experience (ZDX) tools provide functionality for monitoring and analyzing digital experience metrics, applications, and user activities.

Available Tools
---------------

.. list-table:: ZDX Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zdx_administration``
     - Discover ZDX departments or locations
   * - ``zdx_active_devices``
     - Discover ZDX devices using various filters
   * - ``zdx_list_applications``
     - List all active applications configured in ZDX
   * - ``zdx_list_application_score``
     - Get an application's ZDX score or score trend
   * - ``zdx_get_application_metric``
     - Retrieve ZDX metrics for an application (PFT, DNS, availability)
   * - ``zdx_get_application_user``
     - List users/devices for an app or details for a specific user
   * - ``zdx_list_software_inventory``
     - List software inventory or users/devices for a software key
   * - ``zdx_list_alerts``
     - List ongoing alerts, get alert details, or list affected devices
   * - ``zdx_list_historical_alerts``
     - List historical alert rules (ended alerts)
   * - ``zdx_list_deep_traces``
     - Retrieve deep trace information for troubleshooting device connectivity issues

Tool Categories
~~~~~~~~~~~~~~~

.. list-table:: ZDX Tool Categories
   :header-rows: 1
   :widths: 25 75

   * - Category
     - Tools
   * - Application Monitoring
     - Application metrics, scores, user analysis
   * - Device Management
     - Active device monitoring, administration
   * - Alert Management
     - Historical and current alert management
   * - Software Inventory
     - Software inventory tracking
   * - Deep Trace Analysis
     - Network path analysis and troubleshooting

Tool Details
------------

zdx_list_applications
~~~~~~~~~~~~~~~~~~~~~

List all active applications configured in ZDX.

**Parameters:**

:param page: Specifies the page offset
:type page: Optional[int]
:param page_size: Specifies the page size
:type page_size: Optional[int]
:param search: The search string used to partially match
:type search: Optional[str]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zdx")
:type service: str

**Returns:**
- List of application dictionaries

**Example:**
.. code-block:: python

   applications = zdx_list_applications(page=1, page_size=50)

zdx_get_application_metric
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve ZDX metrics for an application (PFT, DNS, availability).

**Parameters:**

:param app_id: The application ID
:type app_id: str
:param metric_type: Type of metric to retrieve
:type metric_type: str
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zdx")
:type service: str

**Returns:**
- Dictionary with application metrics

**Example:**
.. code-block:: python

   metrics = zdx_get_application_metric(app_id="12345", metric_type="pft")

zdx_active_devices
~~~~~~~~~~~~~~~~~~

Discover ZDX devices using various filters.

**Parameters:**

:param page: Specifies the page offset
:type page: Optional[int]
:param page_size: Specifies the page size
:type page_size: Optional[int]
:param search: The search string used to partially match
:type search: Optional[str]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zdx")
:type service: str

**Returns:**
- List of device dictionaries

**Example:**
.. code-block:: python

   devices = zdx_active_devices(page=1, page_size=100)

zdx_list_alerts
~~~~~~~~~~~~~~~~

List ongoing alerts, get alert details, or list affected devices.

**Parameters:**

:param action: The action to perform (e.g., "read", "read_alert", "read_affected_devices")
:type action: str
:param alert_id: The ID of the alert for "read_alert" and "read_affected_devices" actions
:type alert_id: str, optional
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zdx")
:type service: str

**Returns:**
- Dictionary with alert information or list of alerts

**Example:**
.. code-block:: python

   alerts = zdx_list_alerts(action="list")

For complete documentation of all ZDX tools, see the individual tool pages.

Authentication
--------------

ZDX tools support both OneAPI and Legacy authentication methods:

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

  * ``ZDX_CLIENT_ID``
  * ``ZDX_CLIENT_SECRET``
  * ``ZDX_CLOUD``

Common Use Cases
----------------

1. **Performance Monitoring**: Track application performance and user experience
2. **Device Management**: Monitor and manage endpoint devices
3. **Alert Management**: Respond to performance and security alerts
4. **Troubleshooting**: Analyze network paths and performance issues

Error Handling
--------------

All ZDX tools include comprehensive error handling:

- **Authentication errors**: Invalid credentials or expired tokens
- **Permission errors**: Insufficient privileges for the requested operation
- **Validation errors**: Invalid parameters or malformed requests
- **Rate limiting**: Automatic retry with exponential backoff

For detailed error information, check the tool response for error messages and status codes.
