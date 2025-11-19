.. _release-notes:

Release Notes
=============

Zscaler Integrations MCP Server Changelog
------------------------------------------

0.4.0 (November 19, 2025)
-----------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~~~~~

`PR #16 <https://github.com/zscaler/zscaler-mcp-server/pull/16>`_
 - Split the ZIA sandbox helper into dedicated tools (`zia_get_sandbox_quota`, `zia_get_sandbox_behavioral_analysis`, `zia_get_sandbox_file_hash_count`, `zia_get_sandbox_report`) so MCP clients can directly invoke quota/report endpoints.

`PR #16 <https://github.com/zscaler/zscaler-mcp-server/pull/16>`_
 - Added ZIA SSL Inspection Rules tools (`zia_list_ssl_inspection_rules`, `zia_get_ssl_inspection_rule`, `zia_create_ssl_inspection_rule`, `zia_update_ssl_inspection_rule`, `zia_delete_ssl_inspection_rule`) for managing SSL/TLS traffic decryption and inspection policies.

`PR #16 <https://github.com/zscaler/zscaler-mcp-server/pull/16>`_
 - Added ZTW workload discovery service tool (`ztw_get_discovery_settings`) for retrieving workload discovery service settings.

0.3.2 (November 4, 2025)
-----------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Enhancements
~~~~~~~~~~~~~~~~

`PR #15 <https://github.com/zscaler/zscaler-mcp-server/pull/15>`_
 - Added custom User-Agent header support with format `zscaler-mcp-server/VERSION python/VERSION os/arch`. Users can append AI agent information via `--user-agent-comment` flag or `ZSCALER_MCP_USER_AGENT_COMMENT` environment variable.

0.3.1 (October 28, 2025) - Tool Registration & Naming Updates
--------------------------------------------------------------

Added
------

`PR #14 <https://github.com/zscaler/zscaler-mcp-server/pull/14>`_

- **ZIA Tools**: Added missing read-only tools to services registration
  - `get_zia_dlp_dictionaries` - Manage ZIA DLP dictionaries for data loss prevention
  - `get_zia_dlp_engines` - Manage ZIA DLP engines for rule processing
  - `get_zia_user_departments` - Manage ZIA user departments for organizational structure
  - `get_zia_user_groups` - Manage ZIA user groups for access control
  - `get_zia_users` - Manage ZIA users for authentication and access control

- **ZPA Tools**: Added missing read-only tools to services registration
  - `get_zpa_app_protection_profile` - Manage ZPA App Protection Profiles (Inspection Profiles)
  - `get_zpa_enrollment_certificate` - Manage ZPA Enrollment Certificates
  - `get_zpa_isolation_profile` - Manage ZPA Cloud Browser Isolation (CBI) profiles
  - `get_zpa_posture_profile` - Manage ZPA Posture Profiles
  - `get_zpa_saml_attribute` - Manage ZPA SAML Attributes
  - `get_zpa_scim_attribute` - Manage ZPA SCIM Attributes
  - `get_zpa_scim_group` - Manage ZPA SCIM Groups
  - `get_zpa_app_segments_by_type` - Manage ZPA application segments by type
  - `get_zpa_trusted_network` - Manage ZPA Trusted Networks

### Changed

- **Tool Naming Convention**: Updated tool names to follow consistent `get_*` pattern for read-only operations
  - ZIA tools: `zia_*_manager` → `get_zia_*`
  - ZPA tools: `*_manager` → `get_zpa_*`
  - Maintains backward compatibility with existing `zia_get_*` and `zpa_get_*` patterns

### Fixed

- **Tool Registration**: Resolved missing tool registrations in `zscaler_mcp/services.py`
- **Documentation**: Updated README.md with correct tool names and comprehensive tool listings

0.3.0 (October 27, 2025) - Security & Confirmation Release
-----------------------------------------------------------

Notes
~~~~~

- Python Versions: **v3.11, v3.12, v3.13**

Security Enhancements
~~~~~~~~~~~~~~~~~~~~~

**Multi-Layer Security Model**:

- Default read-only mode (110+ safe tools always available)
- Global ``--enable-write-tools`` flag required for write operations
- **Mandatory allowlist** via ``--write-tools`` (supports wildcards: ``zpa_create_*``, ``zia_delete_*``)
- Tool annotations: ``readOnlyHint=True`` for read operations, ``destructiveHint=True`` for write operations
- **Double-confirmation for DELETE operations**: Permission dialog + server-side confirmation block (33 delete tools)

**Write Tools Allowlist** (Mandatory):

- No write tools registered unless explicit allowlist provided
- Prevents accidental "allow all" scenarios
- Granular control with wildcard patterns

**DELETE Operation Protection**:

- All 33 delete operations require **double confirmation**
- First: AI agent permission dialog (``destructiveHint``)
- Second: Server-side confirmation via hidden ``kwargs`` parameter
- Prevents irreversible actions from being executed accidentally

Added
~~~~~

- ``zscaler_mcp/common/tool_helpers.py``: Registration utilities for read/write tools with annotations
- ``zscaler_mcp/common/elicitation.py``: Confirmation logic for delete operations
- ``--enable-write-tools`` / ``ZSCALER_MCP_WRITE_ENABLED``: Global write mode toggle
- ``--write-tools`` / ``ZSCALER_MCP_WRITE_TOOLS``: Mandatory allowlist (required when write mode enabled)
- ``build_mcpb.sh``: Automated packaging script with bundled Python dependencies
- Hidden ``kwargs`` parameter to all 33 delete functions for server-side confirmation
- ``destructiveHint=True`` annotation to all 93 write operations

Changed
~~~~~~~

- MCPB packages now bundle all Python dependencies (51MB vs 499KB)
- Update operations now fetch current resource state to avoid sending null values to API
- Enhanced server logging with security posture information
- Updated test suite for confirmation-based delete operations (163 tests passing)

Fixed
~~~~~

- Fixed ``MockServer.add_tool()`` missing ``annotations`` parameter for ``--list-tools`` functionality
- Fixed update operations in ZPA segment groups, server groups, app connector groups, service edge groups to handle optional fields correctly
- Fixed Pydantic validation errors in confirmation responses (return string instead of dict)
- Fixed MCPB packaging to include all required dependencies
- Removed problematic ``test_use_legacy_env.py`` (attempted real API calls)
- Fixed 21 orphaned commas causing syntax errors
- Fixed missing Union imports

Documentation
~~~~~~~~~~~~~

- Updated README with comprehensive security model documentation
- Rewrote ``docsrc/guides/configuration.rst`` with clear authentication guide
- Added write tools allowlist examples and usage patterns
- Documented double-confirmation flow for delete operations
- Fixed Sphinx RST title underlines

## 0.2.2 (October 6, 2025)

### Notes

- Python Versions: **v3.11, v3.12, v3.13**

`PR #11 <https://github.com/zscaler/zscaler-mcp-server/pull/11>` Fixed README and other documents to change the name title from "Zscaler MCP Server" to "Zscaler Integrations MCP Server"


0.2.1 (September 18, 2025)
---------------------------

Notes
-----

- Python Versions: **v3.11, v3.12, v3.13**

`PR #10 <https://github.com/zscaler/zscaler-mcp-server/pull/10>`_ Fixed import sorting and markdown linting issues:

- Fixed Ruff import sorting errors in ``client.py``, ``services.py``, and ``utils.py``
- Fixed markdownlint formatting issues in ``docs/guides/release-notes.md``
- Updated GitHub workflows to include linter checks in release process

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