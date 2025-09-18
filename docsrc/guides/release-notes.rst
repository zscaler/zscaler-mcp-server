.. _release-notes:

Release Notes
=============

Zscaler MCP Server Changelog
------------------------------

0.2.0 (September 18, 2025)
---------------------------

Notes
-----

- Python Versions: **v3.11, v3.12, v3.13**

NEW ZCC MCP Tools
~~~~~~~~~~~~~~~~~

`PR #9 <https://github.com/zscaler/zscaler-mcp-server/pull/9>`_ Added the following new tools:

- Added ``zcc_list_trusted_networks`` - List existing trusted networks
- Added ``zcc_list_forwarding_profiles`` - List existing forwarding profiles

NEW ZTW MCP Tools
~~~~~~~~~~~~~~~~~

`PR #9 <https://github.com/zscaler/zscaler-mcp-server/pull/9>`_ Added the following new tools:

- Added ``ztw_ip_destination_groups`` - Manages IP Destination Groups
- Added ``ztw_ip_group`` - Manages IP Pool Groups
- Added ``ztw_ip_source_groups`` - Manages IP Source Groups
- Added ``ztw_network_service_groups`` - Manages Network Service Groups
- Added ``ztw_list_roles`` - List all existing admin roles in Zscaler Cloud & Branch Connector
- Added ``ztw_list_admins`` - List all existing admin users or get details for a specific admin user

`PR #9 <https://github.com/zscaler/zscaler-mcp-server/pull/9>`_ - New documentation portal available in `ReadTheDocs <https://zscaler-mcp-server.readthedocs.io/>`

0.1.0 (August 15, 2025) - Initial Release
------------------------------------------

Notes
-----

- Python Versions: **v3.11, v3.12, v3.13**

Added
~~~~~

- Initial implementation for the zscaler-mcp server (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Support for Zscaler services: ``zcc``, ``zdx``, ``zia``, ``zpa``, ``zidentity`` (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Flexible per service initialization (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Streamable-http transport with Docker support (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Debug option (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Docker support (`#1 <https://github.com/zscaler/zscaler-mcp/issues/1>`_)
- Comprehensive end-to-end testing framework with 44+ tests
- Test runner script with multi-model testing support
- Mock API strategy for realistic testing scenarios
- ZIA tools for user management via the Python SDK:

  - ``zia_user_groups``: Lists and retrieves ZIA User Groups with pagination, filtering, and sorting
  - ``zia_user_departments``: Lists and retrieves ZIA User Departments with pagination, filtering, and sorting
  - ``zia_users``: Lists and retrieves ZIA Users with filtering and pagination

Changed
~~~~~~~

- Fixed import sorting and linting issues
- Simplified project structure by removing unnecessary nesting
- Updated test organization for better maintainability

Documentation
~~~~~~~~~~~~~

- Updated README ZIA Features to include the new tools (``zia_user_groups``, ``zia_user_departments``, ``zia_users``).