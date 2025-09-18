Zscaler Client Connector (ZCC) Tools
=====================================

The Zscaler Client Connector (ZCC) tools provide functionality for managing and monitoring client devices, trusted networks, and forwarding profiles.

Available Tools
---------------

.. list-table:: ZCC Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zcc_list_devices``
     - Retrieves ZCC device enrollment information from the Client Connector Portal
   * - ``zcc_devices_csv_exporter``
     - Downloads ZCC device information or service status as a CSV file
   * - ``zcc_list_trusted_networks``
     - Returns the list of Trusted Networks By Company ID in the Client Connector Portal
   * - ``zcc_list_forwarding_profiles``
     - Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal

Tool Details
------------

zcc_list_devices
~~~~~~~~~~~~~~~~

Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal.

**Parameters:**

:param page: Specifies the page offset
:type page: Optional[int]
:param page_size: Specifies the page size
:type page_size: Optional[int]
:param search: The search string used to partially match
:type search: Optional[str]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zcc")
:type service: str

**Returns:**
- List of device dictionaries with enrollment information

**Example:**
.. code-block:: python

   devices = zcc_list_devices(page=1, page_size=50, search="laptop")

zcc_devices_csv_exporter
~~~~~~~~~~~~~~~~~~~~~~~~

Downloads ZCC device information or service status as a CSV file.

**Parameters:**

:param export_type: Type of export ("devices" or "service_status")
:type export_type: str
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zcc")
:type service: str

**Returns:**
- CSV file content as string

**Example:**
.. code-block:: python

   csv_data = zcc_devices_csv_exporter(export_type="devices")

zcc_list_trusted_networks
~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the list of Trusted Networks By Company ID in the Client Connector Portal.

**Parameters:**

:param page: Specifies the page offset
:type page: Optional[int]
:param page_size: Specifies the page size
:type page_size: Optional[int]
:param search: The search string used to partially match
:type search: Optional[str]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zcc")
:type service: str

**Returns:**
- List of trusted network dictionaries

**Example:**
.. code-block:: python

   networks = zcc_list_trusted_networks(search="office")

zcc_list_forwarding_profiles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal.

**Parameters:**

:param page: Specifies the page offset
:type page: Optional[int]
:param page_size: Specifies the page size
:type page_size: Optional[int]
:param search: The search string used to partially match
:type search: Optional[str]
:param use_legacy: Whether to use the legacy API (default: False)
:type use_legacy: bool
:param service: The service to use (default: "zcc")
:type service: str

**Returns:**
- List of forwarding profile dictionaries

**Example:**
.. code-block:: python

   profiles = zcc_list_forwarding_profiles(page_size=100)

Authentication
--------------

ZCC tools support both OneAPI and Legacy authentication methods:

**OneAPI Authentication:**
- Uses OAuth2 client credentials
- Requires the following environment variables:

  * ``ZSCALER_CLIENT_ID``
  * ``ZSCALER_CLIENT_SECRET``
  * ``ZSCALER_VANITY_DOMAIN``
  * ``ZSCALER_CLOUD``

**Legacy Authentication:**
- Uses API key and secret key
- Requires the following environment variables:

  * ``ZCC_CLIENT_ID``
  * ``ZCC_CLIENT_SECRET``
  * ``ZCC_CLOUD``

Common Use Cases
----------------

1. **Device Management**: Monitor enrolled devices and their status
2. **Network Configuration**: Manage trusted networks for client access
3. **Traffic Routing**: Configure forwarding profiles for traffic management
4. **Reporting**: Export device and service status data for analysis

Error Handling
--------------

All ZCC tools include comprehensive error handling:

- **Authentication errors**: Invalid credentials or expired tokens
- **Permission errors**: Insufficient privileges for the requested operation
- **Validation errors**: Invalid parameters or malformed requests
- **Rate limiting**: Automatic retry with exponential backoff

For detailed error information, check the tool response for error messages and status codes.
