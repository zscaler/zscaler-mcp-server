Utils API
=========

Utility functions and helper modules.

.. automodule:: zscaler_mcp.utils.utils
   :members:
   :undoc-members:
   :show-inheritance:

Common Utilities
----------------

The utils module provides common utility functions used across the MCP server.

User Agent Generation
~~~~~~~~~~~~~~~~~~~~~

The `get_combined_user_agent` function generates a custom user agent string for API requests.

Logging Utilities
~~~~~~~~~~~~~~~~~

.. automodule:: zscaler_mcp.common.logging
   :members:
   :undoc-members:
   :show-inheritance:

Configuration Utilities
~~~~~~~~~~~~~~~~~~~~~~~

Helper functions for configuration management and validation.

Data Processing Utilities
~~~~~~~~~~~~~~~~~~~~~~~~~

Common data processing and transformation functions.

Usage Examples
--------------

User Agent Generation
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from zscaler_mcp.utils.utils import get_combined_user_agent

   # Generate custom user agent
   user_agent = get_combined_user_agent()
   print(user_agent)

Logging Setup
~~~~~~~~~~~~~

.. code-block:: python

   from zscaler_mcp.common.logging import setup_logging

   # Setup logging with custom configuration
   setup_logging(level="DEBUG", format="detailed")
