.. _configuration-guide:

Configuration Guide
===================

Environment Variables
---------------------

The Zscaler MCP Server requires several environment variables to be configured for proper operation.

Required Variables
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   ZSCALER_CLIENT_ID=your_client_id
   ZSCALER_CLIENT_SECRET=your_client_secret
   ZSCALER_CUSTOMER_ID=your_customer_id
   ZSCALER_VANITY_DOMAIN=your_vanity_domain

Optional Variables
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   ZSCALER_CLOUD=zscloud.net
   ZSCALER_DEBUG=false
   ZSCALER_LOG_LEVEL=INFO

Authentication Methods
----------------------

OneAPI Authentication
~~~~~~~~~~~~~~~~~~~~~

For modern OAuth2-based authentication using the OneAPI endpoint.

Legacy Authentication
~~~~~~~~~~~~~~~~~~~~~

For service-specific API key authentication with individual Zscaler services.

Configuration Examples
----------------------

Basic Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Basic OneAPI configuration
   export ZSCALER_CLIENT_ID="your_client_id"
   export ZSCALER_CLIENT_SECRET="your_client_secret"
   export ZSCALER_CUSTOMER_ID="your_customer_id"
   export ZSCALER_VANITY_DOMAIN="your_vanity_domain"

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Advanced configuration with custom settings
   export ZSCALER_CLIENT_ID="your_client_id"
   export ZSCALER_CLIENT_SECRET="your_client_secret"
   export ZSCALER_CUSTOMER_ID="your_customer_id"
   export ZSCALER_VANITY_DOMAIN="your_vanity_domain"
   export ZSCALER_CLOUD="zscloud.net"
   export ZSCALER_DEBUG="true"
   export ZSCALER_LOG_LEVEL="DEBUG"
