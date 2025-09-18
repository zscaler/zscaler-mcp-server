Client API
==========

The Zscaler client wrapper and authentication handling.

.. automodule:: zscaler_mcp.client
   :members:
   :undoc-members:
   :show-inheritance:

Client Configuration
--------------------

The client supports both OneAPI and Legacy API authentication methods.

OneAPI Authentication
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: OneAPI Authentication Parameters
   :header-rows: 1
   :widths: 20 40 40

   * - Parameter
     - Description
     - Environment Variable
   * - ``client_id``
     - Zscaler API Client ID
     - ``ZSCALER_CLIENT_ID``
   * - ``client_secret``
     - Zscaler API Client Secret
     - ``ZSCALER_CLIENT_SECRET``
   * - ``customer_id``
     - Zscaler Customer ID
     - ``ZSCALER_CUSTOMER_ID``
   * - ``vanity_domain``
     - Zscaler Vanity Domain
     - ``ZSCALER_VANITY_DOMAIN``
   * - ``private_key``
     - OAuth Private Key (alternative to client_secret)
     - ``ZSCALER_PRIVATE_KEY``
   * - ``cloud``
     - Zscaler Cloud Environment
     - ``ZSCALER_CLOUD``

Legacy API Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~

Legacy authentication supports individual service credentials:

ZIA Legacy
^^^^^^^^^^

.. list-table:: ZIA Legacy Authentication
   :header-rows: 1
   :widths: 20 40 40

   * - Parameter
     - Description
     - Environment Variable
   * - ``username``
     - ZIA Username
     - ``ZIA_USERNAME``
   * - ``password``
     - ZIA Password
     - ``ZIA_PASSWORD``
   * - ``api_key``
     - ZIA API Key
     - ``ZIA_API_KEY``
   * - ``cloud``
     - ZIA Cloud Environment
     - ``ZIA_CLOUD``

ZPA Legacy
^^^^^^^^^^

.. list-table:: ZPA Legacy Authentication
   :header-rows: 1
   :widths: 20 40 40

   * - Parameter
     - Description
     - Environment Variable
   * - ``client_id``
     - ZPA Client ID
     - ``ZPA_CLIENT_ID``
   * - ``client_secret``
     - ZPA Client Secret
     - ``ZPA_CLIENT_SECRET``
   * - ``customer_id``
     - ZPA Customer ID
     - ``ZPA_CUSTOMER_ID``
   * - ``cloud``
     - ZPA Cloud Environment
     - ``ZPA_CLOUD``

ZCC Legacy
^^^^^^^^^^

.. list-table:: ZCC Legacy Authentication
   :header-rows: 1
   :widths: 20 40 40

   * - Parameter
     - Description
     - Environment Variable
   * - ``api_key``
     - ZCC API Key
     - ``ZCC_CLIENT_ID``
   * - ``secret_key``
     - ZCC Secret Key
     - ``ZCC_CLIENT_ID``
   * - ``cloud``
     - ZCC Cloud Environment
     - ``ZCC_CLOUD``

ZDX Legacy
^^^^^^^^^^

.. list-table:: ZDX Legacy Authentication
   :header-rows: 1
   :widths: 20 40 40

   * - Parameter
     - Description
     - Environment Variable
   * - ``key_id``
     - ZDX Key ID
     - ``ZDX_CLIENT_ID``
   * - ``key_secret``
     - ZDX Key Secret
     - ``ZDX_CLIENT_SECRET``
   * - ``cloud``
     - ZDX Cloud Environment
     - ``ZDX_CLOUD``

ZTW Legacy
^^^^^^^^^^

.. list-table:: ZTW Legacy Authentication
   :header-rows: 1
   :widths: 20 40 40

   * - Parameter
     - Description
     - Environment Variable
   * - ``username``
     - ZTW Username
     - ``ZTW_USERNAME``
   * - ``password``
     - ZTW Password
     - ``ZTW_PASSWORD``
   * - ``api_key``
     - ZTW API Key
     - ``ZTW_API_KEY``
   * - ``cloud``
     - ZTW Cloud Environment
     - ``ZTW_CLOUD``

Usage Examples
--------------

OneAPI Client
~~~~~~~~~~~~~

.. code-block:: python

   from zscaler_mcp.client import get_zscaler_client

   # Using environment variables
   client = get_zscaler_client()

   # Using explicit parameters
   client = get_zscaler_client(
       client_id="your_client_id",
       client_secret="your_client_secret",
       customer_id="your_customer_id",
       vanity_domain="your_vanity_domain"
   )

Legacy Client
~~~~~~~~~~~~~

.. code-block:: python

   from zscaler_mcp.client import get_zscaler_client

   # ZIA Legacy
   client = get_zscaler_client(
       use_legacy=True,
       service="zia",
       username="your_username",
       password="your_password",
       api_key="your_api_key",
       cloud="your_cloud"
   )

   # ZPA Legacy
   client = get_zscaler_client(
       use_legacy=True,
       service="zpa",
       client_id="your_client_id",
       client_secret="your_client_secret",
       customer_id="your_customer_id",
       cloud="your_cloud"
   )
