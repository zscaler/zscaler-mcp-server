Client API
==========

The Zscaler client wrapper and authentication handling.

.. automodule:: zscaler_mcp.client
   :members:
   :undoc-members:
   :show-inheritance:

Client Configuration
--------------------

The client uses **OneAPI** authentication through ZIdentity. All Zscaler
products are reached through the unified ``zscaler.ZscalerClient``.

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
     - Zscaler Customer ID (required when calling ZPA tools)
     - ``ZSCALER_CUSTOMER_ID``
   * - ``vanity_domain``
     - Zscaler Vanity Domain
     - ``ZSCALER_VANITY_DOMAIN``
   * - ``private_key``
     - PEM-encoded private key for JWT auth (alternative to ``client_secret``)
     - ``ZSCALER_PRIVATE_KEY``
   * - ``cloud``
     - Cloud override (e.g. ``BETA``, ``zscalertwo``); omit for production
     - ``ZSCALER_CLOUD``

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
       vanity_domain="your_vanity_domain",
   )

   # JWT-based auth (private key in place of client secret)
   client = get_zscaler_client(
       client_id="your_client_id",
       private_key="-----BEGIN PRIVATE KEY-----...",
       customer_id="your_customer_id",
       vanity_domain="your_vanity_domain",
   )
