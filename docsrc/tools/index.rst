Zscaler Integrations MCP Server Tools
======================================

The Zscaler Integrations MCP Server provides a comprehensive set of tools for interacting with Zscaler's security platform. These tools are organized by service and provide both read-only and management capabilities.

Tool Categories
---------------

The tools are organized into the following categories:

.. toctree::
   :maxdepth: 1

   zcc/index
   zia/index
   zpa/index
   zdx/index
   ztw/index
   zidentity/index

Tool Types
----------

Read-Only Tools
~~~~~~~~~~~~~~~

These tools retrieve information from Zscaler services without making changes:

- **List operations**: Retrieve collections of objects (users, devices, policies, etc.)
- **Get operations**: Retrieve specific object details
- **Search operations**: Find objects based on criteria
- **Report operations**: Generate reports and analytics

Management Tools
~~~~~~~~~~~~~~~~

These tools allow you to create, update, and delete Zscaler resources:

- **Create operations**: Add new resources
- **Update operations**: Modify existing resources
- **Delete operations**: Remove resources
- **Activation operations**: Apply configuration changes

Authentication
--------------

All tools require proper authentication to Zscaler services. The MCP server supports:

- **OneAPI Authentication**: Modern OAuth2-based authentication
- **Legacy Authentication**: Service-specific API key authentication

See the getting-started guide for authentication setup.

Tool Parameters
---------------

Most tools accept the following common parameters:

- **use_legacy**: Whether to use legacy API authentication (default: False)
- **service**: The Zscaler service to use (zcc, zia, zpa, zdx, ztw, zidentity)
- **page**: Page number for paginated results
- **page_size**: Number of results per page
- **search**: Search string for filtering results

Error Handling
--------------

All tools return structured responses with error handling:

- **Success**: Returns the requested data
- **Error**: Returns error details with descriptive messages
- **Validation**: Validates parameters before making API calls

Examples
--------

Basic tool usage:

.. code-block:: python

   # List ZIA admin roles
   roles = zia_list_admin_roles()

   # Get specific ZPA application segment
   segment = zpa_get_application_segment(segment_id="12345")

   # Search ZCC devices
   devices = zcc_list_devices(search="laptop")

For more examples, see the individual service documentation pages.
