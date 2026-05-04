"""
Zscaler Integrations MCP Server Services

This module provides the service classes for the Zscaler Integrations MCP Server.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for all Zscaler services."""

    def __init__(self, zscaler_client):
        """Initialize the service with a Zscaler client.

        Args:
            zscaler_client: The Zscaler OneAPI client instance, or ``None``.
                The server does not eagerly construct a client at startup;
                tools call :func:`zscaler_mcp.client.get_zscaler_client`
                lazily on first invocation, so a missing client at register
                time is expected and not an error.
        """
        self.zscaler_client = zscaler_client
        self.tools = []  # Kept for backward compatibility during migration
        self.read_tools = []  # NEW: Read-only tools (with annotations)
        self.write_tools = []  # NEW: Write tools (with annotations)
        self.resources = []

    @abstractmethod
    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register tools with the MCP server.

        Args:
            server: The MCP server instance
            enabled_tools: Set of enabled tool names (if None, all tools are enabled)
            enable_write_tools: Whether to enable write tools (default: False)
            write_tools: Explicit allowlist of write tools (supports wildcards). Requires enable_write_tools=True.
            disabled_tools: Set of tool name patterns to exclude (supports wildcards via fnmatch).
            selected_toolsets: Set of toolset ids (e.g. ``{"zia_url_filtering"}``) that
                this service is allowed to register tools for. ``None`` disables
                toolset filtering. The ``meta`` toolset is always exempt. See
                :mod:`zscaler_mcp.common.toolsets`.
        """
        pass

    def register_resources(self, server):
        """Register resources with the MCP server.

        Args:
            server: The MCP server instance
        """
        # Default implementation - override in subclasses if needed
        pass


class ZCCService(BaseService):
    """Zscaler Client Connector (ZCC) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import ZCC tools (all read-only)
        from .tools.zcc.list_devices import zcc_list_devices
        from .tools.zcc.list_forwarding_profiles import zcc_list_forwarding_profiles
        from .tools.zcc.list_trusted_networks import zcc_list_trusted_networks

        # All ZCC tools are read-only
        self.read_tools = [
            {
                "func": zcc_list_devices,
                "name": "zcc_list_devices",
                "description": "Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zcc_list_trusted_networks,
                "name": "zcc_list_trusted_networks",
                "description": "Returns the list of Trusted Networks By Company ID in the Client Connector Portal (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zcc_list_forwarding_profiles,
                "name": "zcc_list_forwarding_profiles",
                "description": "Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
        ]

        self.write_tools = []  # ZCC has no write operations

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register ZCC tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations (all read-only)
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(f"ZCC Service: Registered {read_count} read tools, {write_count} write tools")


class ZDXService(BaseService):
    """Zscaler Digital Experience (ZDX) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import verb-based ZDX tools (all read-only)
        from .tools.zdx.active_devices import zdx_get_device, zdx_list_devices
        from .tools.zdx.administration import zdx_list_departments, zdx_list_locations
        from .tools.zdx.deeptrace_analysis import (
            zdx_delete_analysis,
            zdx_get_analysis,
            zdx_start_analysis,
        )
        from .tools.zdx.deeptrace_cloudpath import zdx_get_deeptrace_cloudpath
        from .tools.zdx.deeptrace_cloudpath_metrics import zdx_get_deeptrace_cloudpath_metrics
        from .tools.zdx.deeptrace_events import zdx_get_deeptrace_events
        from .tools.zdx.deeptrace_health_metrics import zdx_get_deeptrace_health_metrics
        from .tools.zdx.deeptrace_manage import zdx_delete_deeptrace, zdx_start_deeptrace
        from .tools.zdx.deeptrace_top_processes import zdx_list_deeptrace_top_processes
        from .tools.zdx.deeptrace_webprobe_metrics import zdx_get_deeptrace_webprobe_metrics
        from .tools.zdx.device_cloudpath_probes import zdx_list_cloudpath_probes
        from .tools.zdx.device_web_probes import zdx_get_web_probes
        from .tools.zdx.get_application_metric import zdx_get_application_metric
        from .tools.zdx.get_application_score import (
            zdx_get_application,
            zdx_get_application_score_trend,
        )
        from .tools.zdx.get_application_user import (
            zdx_get_application_user,
            zdx_list_application_users,
        )
        from .tools.zdx.list_alerts import (
            zdx_get_alert,
            zdx_list_alert_affected_devices,
            zdx_list_alerts,
        )
        from .tools.zdx.list_applications import zdx_list_applications
        from .tools.zdx.list_deep_traces import (
            zdx_get_device_deep_trace,
            zdx_list_device_deep_traces,
        )
        from .tools.zdx.list_historical_alerts import zdx_list_historical_alerts
        from .tools.zdx.list_software_inventory import zdx_get_software_details, zdx_list_software

        self.read_tools = [
            {
                "func": zdx_list_devices,
                "name": "zdx_list_devices",
                "description": "List ZDX devices with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_get_device,
                "name": "zdx_get_device",
                "description": "Get a specific ZDX device by ID (read-only)",
            },
            {
                "func": zdx_list_departments,
                "name": "zdx_list_departments",
                "description": "List ZDX departments (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_list_locations,
                "name": "zdx_list_locations",
                "description": "List ZDX locations (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_get_application_metric,
                "name": "zdx_get_application_metric",
                "description": "Get ZDX metrics for a specified application (read-only)",
            },
            {
                "func": zdx_get_application,
                "name": "zdx_get_application",
                "description": "Get ZDX application details (read-only)",
            },
            {
                "func": zdx_get_application_score_trend,
                "name": "zdx_get_application_score_trend",
                "description": "Get ZDX application score trend (read-only)",
            },
            {
                "func": zdx_list_application_users,
                "name": "zdx_list_application_users",
                "description": "List users for a ZDX application (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_get_application_user,
                "name": "zdx_get_application_user",
                "description": "Get a specific ZDX application user (read-only)",
            },
            {
                "func": zdx_list_alerts,
                "name": "zdx_list_alerts",
                "description": "List ZDX alerts (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_get_alert,
                "name": "zdx_get_alert",
                "description": "Get a specific ZDX alert by ID (read-only)",
            },
            {
                "func": zdx_list_alert_affected_devices,
                "name": "zdx_list_alert_affected_devices",
                "description": "List devices affected by a ZDX alert (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_list_applications,
                "name": "zdx_list_applications",
                "description": "List ZDX applications (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_list_device_deep_traces,
                "name": "zdx_list_device_deep_traces",
                "description": "List ZDX deep traces for a device (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_get_device_deep_trace,
                "name": "zdx_get_device_deep_trace",
                "description": "Get a specific ZDX deep trace by ID (read-only)",
            },
            {
                "func": zdx_list_deeptrace_top_processes,
                "name": "zdx_list_deeptrace_top_processes",
                "description": "Get top processes from a ZDX deep trace session (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_get_deeptrace_webprobe_metrics,
                "name": "zdx_get_deeptrace_webprobe_metrics",
                "description": "Get web probe metrics from a ZDX deep trace session (read-only)",
            },
            {
                "func": zdx_get_deeptrace_cloudpath_metrics,
                "name": "zdx_get_deeptrace_cloudpath_metrics",
                "description": "Get cloud path metrics from a ZDX deep trace session (read-only)",
            },
            {
                "func": zdx_get_deeptrace_cloudpath,
                "name": "zdx_get_deeptrace_cloudpath",
                "description": "Get cloud path topology from a ZDX deep trace session (read-only)",
            },
            {
                "func": zdx_get_deeptrace_health_metrics,
                "name": "zdx_get_deeptrace_health_metrics",
                "description": "Get health metrics from a ZDX deep trace session (read-only)",
            },
            {
                "func": zdx_get_deeptrace_events,
                "name": "zdx_get_deeptrace_events",
                "description": "Get events from a ZDX deep trace session (read-only)",
            },
            {
                "func": zdx_get_analysis,
                "name": "zdx_get_analysis",
                "description": "Get status of a ZDX score analysis (read-only)",
            },
            {
                "func": zdx_get_web_probes,
                "name": "zdx_get_web_probes",
                "description": "Get web probes for an app on a device - returns web_probe_id needed for zdx_start_deeptrace (read-only)",
            },
            {
                "func": zdx_list_cloudpath_probes,
                "name": "zdx_list_cloudpath_probes",
                "description": "List cloud path probes for an app on a device - returns cloudpath_probe_id needed for zdx_start_deeptrace (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_list_historical_alerts,
                "name": "zdx_list_historical_alerts",
                "description": "List ZDX historical alerts (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_list_software,
                "name": "zdx_list_software",
                "description": "List ZDX software inventory (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zdx_get_software_details,
                "name": "zdx_get_software_details",
                "description": "Get details for specific ZDX software (read-only)",
            },
        ]

        self.write_tools = [
            {
                "func": zdx_start_deeptrace,
                "name": "zdx_start_deeptrace",
                "description": "Start a deep trace for a ZDX device (write operation)",
            },
            {
                "func": zdx_delete_deeptrace,
                "name": "zdx_delete_deeptrace",
                "description": "Delete a ZDX deep trace session (destructive operation)",
            },
            {
                "func": zdx_start_analysis,
                "name": "zdx_start_analysis",
                "description": "Start a ZDX score analysis on a device (write operation)",
            },
            {
                "func": zdx_delete_analysis,
                "name": "zdx_delete_analysis",
                "description": "Stop a running ZDX score analysis (destructive operation)",
            },
        ]

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register ZDX tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations (all read-only)
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(f"ZDX Service: Registered {read_count} read tools, {write_count} write tools")


class ZPAService(BaseService):
    """Zscaler Private Access (ZPA) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import all verb-based ZPA tools
        from .tools.zpa.access_app_protection_rules import (
            zpa_create_app_protection_rule,
            zpa_delete_app_protection_rule,
            zpa_get_app_protection_rule,
            zpa_list_app_protection_rules,
            zpa_update_app_protection_rule,
        )
        from .tools.zpa.access_forwarding_rules import (
            zpa_create_forwarding_policy_rule,
            zpa_delete_forwarding_policy_rule,
            zpa_get_forwarding_policy_rule,
            zpa_list_forwarding_policy_rules,
            zpa_update_forwarding_policy_rule,
        )
        from .tools.zpa.access_isolation_rules import (
            zpa_create_isolation_policy_rule,
            zpa_delete_isolation_policy_rule,
            zpa_get_isolation_policy_rule,
            zpa_list_isolation_policy_rules,
            zpa_update_isolation_policy_rule,
        )
        from .tools.zpa.access_policy_rules import (
            zpa_create_access_policy_rule,
            zpa_delete_access_policy_rule,
            zpa_get_access_policy_rule,
            zpa_list_access_policy_rules,
            zpa_update_access_policy_rule,
        )
        from .tools.zpa.access_timeout_rules import (
            zpa_create_timeout_policy_rule,
            zpa_delete_timeout_policy_rule,
            zpa_get_timeout_policy_rule,
            zpa_list_timeout_policy_rules,
            zpa_update_timeout_policy_rule,
        )
        from .tools.zpa.app_connector_groups import (
            zpa_create_app_connector_group,
            zpa_delete_app_connector_group,
            zpa_get_app_connector_group,
            zpa_list_app_connector_groups,
            zpa_update_app_connector_group,
        )
        from .tools.zpa.app_connectors import (
            zpa_bulk_delete_app_connectors,
            zpa_delete_app_connector,
            zpa_get_app_connector,
            zpa_list_app_connectors,
            zpa_update_app_connector,
        )
        from .tools.zpa.app_segments import (
            zpa_create_application_segment,
            zpa_delete_application_segment,
            zpa_get_application_segment,
            zpa_list_application_segments,
            zpa_update_application_segment,
        )
        from .tools.zpa.application_servers import (
            zpa_create_application_server,
            zpa_delete_application_server,
            zpa_get_application_server,
            zpa_list_application_servers,
            zpa_update_application_server,
        )
        from .tools.zpa.ba_certificate import (
            zpa_create_ba_certificate,
            zpa_delete_ba_certificate,
            zpa_get_ba_certificate,
            zpa_list_ba_certificates,
        )
        from .tools.zpa.get_app_protection_profile import app_protection_profile_manager
        from .tools.zpa.get_enrollment_certificate import enrollment_certificate_manager
        from .tools.zpa.get_isolation_profile import isolation_profile_manager
        from .tools.zpa.get_posture_profiles import posture_profile_manager
        from .tools.zpa.get_saml_attributes import saml_attribute_manager
        from .tools.zpa.get_scim_attributes import scim_attribute_manager
        from .tools.zpa.get_scim_groups import scim_group_manager
        from .tools.zpa.get_segments_by_type import app_segments_by_type_manager
        from .tools.zpa.get_trusted_networks import trusted_network_manager
        from .tools.zpa.pra_credential import (
            zpa_create_pra_credential,
            zpa_delete_pra_credential,
            zpa_get_pra_credential,
            zpa_list_pra_credentials,
            zpa_update_pra_credential,
        )
        from .tools.zpa.pra_portal import (
            zpa_create_pra_portal,
            zpa_delete_pra_portal,
            zpa_get_pra_portal,
            zpa_list_pra_portals,
            zpa_update_pra_portal,
        )
        from .tools.zpa.provisioning_key import (
            zpa_create_provisioning_key,
            zpa_delete_provisioning_key,
            zpa_get_provisioning_key,
            zpa_list_provisioning_keys,
            zpa_update_provisioning_key,
        )
        from .tools.zpa.segment_groups import (
            zpa_create_segment_group,
            zpa_delete_segment_group,
            zpa_get_segment_group,
            zpa_list_segment_groups,
            zpa_update_segment_group,
        )
        from .tools.zpa.server_groups import (
            zpa_create_server_group,
            zpa_delete_server_group,
            zpa_get_server_group,
            zpa_list_server_groups,
            zpa_update_server_group,
        )
        from .tools.zpa.service_edge_groups import (
            zpa_create_service_edge_group,
            zpa_delete_service_edge_group,
            zpa_get_service_edge_group,
            zpa_list_service_edge_groups,
            zpa_update_service_edge_group,
        )

        # Define read-only tools
        self.read_tools = [
            {
                "func": zpa_list_application_segments,
                "name": "zpa_list_application_segments",
                "description": "List ZPA application segments with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_application_segment,
                "name": "zpa_get_application_segment",
                "description": "Get a specific ZPA application segment by ID (read-only)",
            },
            {
                "func": zpa_list_app_connector_groups,
                "name": "zpa_list_app_connector_groups",
                "description": "List ZPA App Connector Groups (read-only). Returns every connector group in the tenant — id, name, location, country, enrollment cert, server-group memberships. Use this to discover existing connector groups before creating server groups (which require an app_connector_group_id) or before onboarding an application. Supports name search and JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_app_connector_group,
                "name": "zpa_get_app_connector_group",
                "description": "Get a specific ZPA App Connector Group by ID (read-only). Returns the full record including the enrollmentCertId, server-group memberships, and connector membership.",
            },
            {
                "func": zpa_list_app_connectors,
                "name": "zpa_list_app_connectors",
                "description": "List ZPA app connectors with status, version, and health information (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_app_connector,
                "name": "zpa_get_app_connector",
                "description": "Get a specific ZPA app connector by ID with runtime status and control connection state (read-only)",
            },
            {
                "func": zpa_list_server_groups,
                "name": "zpa_list_server_groups",
                "description": "List ZPA server groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_server_group,
                "name": "zpa_get_server_group",
                "description": "Get a specific ZPA server group by ID (read-only)",
            },
            {
                "func": zpa_list_segment_groups,
                "name": "zpa_list_segment_groups",
                "description": "List ZPA segment groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_segment_group,
                "name": "zpa_get_segment_group",
                "description": "Get a specific ZPA segment group by ID (read-only)",
            },
            {
                "func": zpa_list_application_servers,
                "name": "zpa_list_application_servers",
                "description": "List ZPA application servers (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_application_server,
                "name": "zpa_get_application_server",
                "description": "Get a specific ZPA application server by ID (read-only)",
            },
            {
                "func": zpa_list_service_edge_groups,
                "name": "zpa_list_service_edge_groups",
                "description": "List ZPA service edge groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_service_edge_group,
                "name": "zpa_get_service_edge_group",
                "description": "Get a specific ZPA service edge group by ID (read-only)",
            },
            {
                "func": zpa_list_ba_certificates,
                "name": "zpa_list_ba_certificates",
                "description": "List ZPA browser access certificates (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_ba_certificate,
                "name": "zpa_get_ba_certificate",
                "description": "Get a specific ZPA browser access certificate by ID (read-only)",
            },
            {
                "func": zpa_list_access_policy_rules,
                "name": "zpa_list_access_policy_rules",
                "description": "List ZPA access policy rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_access_policy_rule,
                "name": "zpa_get_access_policy_rule",
                "description": "Get a specific ZPA access policy rule by ID (read-only)",
            },
            {
                "func": zpa_list_forwarding_policy_rules,
                "name": "zpa_list_forwarding_policy_rules",
                "description": "List ZPA forwarding policy rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_forwarding_policy_rule,
                "name": "zpa_get_forwarding_policy_rule",
                "description": "Get a specific ZPA forwarding policy rule by ID (read-only)",
            },
            {
                "func": zpa_list_timeout_policy_rules,
                "name": "zpa_list_timeout_policy_rules",
                "description": "List ZPA timeout policy rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_timeout_policy_rule,
                "name": "zpa_get_timeout_policy_rule",
                "description": "Get a specific ZPA timeout policy rule by ID (read-only)",
            },
            {
                "func": zpa_list_isolation_policy_rules,
                "name": "zpa_list_isolation_policy_rules",
                "description": "List ZPA isolation policy rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_isolation_policy_rule,
                "name": "zpa_get_isolation_policy_rule",
                "description": "Get a specific ZPA isolation policy rule by ID (read-only)",
            },
            {
                "func": zpa_list_app_protection_rules,
                "name": "zpa_list_app_protection_rules",
                "description": "List ZPA app protection rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_app_protection_rule,
                "name": "zpa_get_app_protection_rule",
                "description": "Get a specific ZPA app protection rule by ID (read-only)",
            },
            {
                "func": zpa_list_provisioning_keys,
                "name": "zpa_list_provisioning_keys",
                "description": "List ZPA provisioning keys (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_provisioning_key,
                "name": "zpa_get_provisioning_key",
                "description": "Get a specific ZPA provisioning key by ID (read-only)",
            },
            {
                "func": zpa_list_pra_portals,
                "name": "zpa_list_pra_portals",
                "description": "List ZPA PRA portals (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_pra_portal,
                "name": "zpa_get_pra_portal",
                "description": "Get a specific ZPA PRA portal by ID (read-only)",
            },
            {
                "func": zpa_list_pra_credentials,
                "name": "zpa_list_pra_credentials",
                "description": "List ZPA PRA credentials (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zpa_get_pra_credential,
                "name": "zpa_get_pra_credential",
                "description": "Get a specific ZPA PRA credential by ID (read-only)",
            },
            # Profile and Certificate Management
            {
                "func": app_protection_profile_manager,
                "name": "get_zpa_app_protection_profile",
                "description": "Manage ZPA App Protection Profiles (Inspection Profiles) (read-only)",
            },
            {
                "func": enrollment_certificate_manager,
                "name": "get_zpa_enrollment_certificate",
                "description": "Manage ZPA Enrollment Certificates (read-only)",
            },
            {
                "func": isolation_profile_manager,
                "name": "get_zpa_isolation_profile",
                "description": "Manage ZPA Cloud Browser Isolation (CBI) profiles (read-only)",
            },
            {
                "func": posture_profile_manager,
                "name": "get_zpa_posture_profile",
                "description": "Manage ZPA Posture Profiles (read-only)",
            },
            # Identity and Access Management
            {
                "func": saml_attribute_manager,
                "name": "get_zpa_saml_attribute",
                "description": "Manage ZPA SAML Attributes (read-only)",
            },
            {
                "func": scim_attribute_manager,
                "name": "get_zpa_scim_attribute",
                "description": "Manage ZPA SCIM Attributes (read-only)",
            },
            {
                "func": scim_group_manager,
                "name": "get_zpa_scim_group",
                "description": "Manage ZPA SCIM Groups (read-only)",
            },
            # Network and Segment Management
            {
                "func": app_segments_by_type_manager,
                "name": "get_zpa_app_segments_by_type",
                "description": "Manage ZPA application segments by type (read-only)",
            },
            {
                "func": trusted_network_manager,
                "name": "get_zpa_trusted_network",
                "description": "Manage ZPA Trusted Networks (read-only)",
            },
        ]

        # Define write tools
        self.write_tools = [
            {
                "func": zpa_create_application_segment,
                "name": "zpa_create_application_segment",
                "description": "Create a new ZPA application segment (write operation)",
            },
            {
                "func": zpa_update_application_segment,
                "name": "zpa_update_application_segment",
                "description": "Update an existing ZPA application segment (write operation)",
            },
            {
                "func": zpa_delete_application_segment,
                "name": "zpa_delete_application_segment",
                "description": "Delete a ZPA application segment (destructive operation)",
            },
            {
                "func": zpa_create_app_connector_group,
                "name": "zpa_create_app_connector_group",
                "description": "Create a new ZPA app connector group (write operation)",
            },
            {
                "func": zpa_update_app_connector_group,
                "name": "zpa_update_app_connector_group",
                "description": "Update an existing ZPA app connector group (write operation)",
            },
            {
                "func": zpa_delete_app_connector_group,
                "name": "zpa_delete_app_connector_group",
                "description": "Delete a ZPA app connector group (destructive operation)",
            },
            {
                "func": zpa_update_app_connector,
                "name": "zpa_update_app_connector",
                "description": "Update a ZPA app connector (enable/disable, rename) (write operation)",
            },
            {
                "func": zpa_delete_app_connector,
                "name": "zpa_delete_app_connector",
                "description": "Delete a ZPA app connector (destructive operation)",
            },
            {
                "func": zpa_bulk_delete_app_connectors,
                "name": "zpa_bulk_delete_app_connectors",
                "description": "Bulk delete multiple ZPA app connectors (destructive operation)",
            },
            {
                "func": zpa_create_server_group,
                "name": "zpa_create_server_group",
                "description": "Create a new ZPA server group (write operation)",
            },
            {
                "func": zpa_update_server_group,
                "name": "zpa_update_server_group",
                "description": "Update an existing ZPA server group (write operation)",
            },
            {
                "func": zpa_delete_server_group,
                "name": "zpa_delete_server_group",
                "description": "Delete a ZPA server group (destructive operation)",
            },
            {
                "func": zpa_create_segment_group,
                "name": "zpa_create_segment_group",
                "description": "Create a new ZPA segment group (write operation)",
            },
            {
                "func": zpa_update_segment_group,
                "name": "zpa_update_segment_group",
                "description": "Update an existing ZPA segment group (write operation)",
            },
            {
                "func": zpa_delete_segment_group,
                "name": "zpa_delete_segment_group",
                "description": "Delete a ZPA segment group (destructive operation)",
            },
            {
                "func": zpa_create_application_server,
                "name": "zpa_create_application_server",
                "description": "Create a new ZPA application server (write operation)",
            },
            {
                "func": zpa_update_application_server,
                "name": "zpa_update_application_server",
                "description": "Update an existing ZPA application server (write operation)",
            },
            {
                "func": zpa_delete_application_server,
                "name": "zpa_delete_application_server",
                "description": "Delete a ZPA application server (destructive operation)",
            },
            {
                "func": zpa_create_service_edge_group,
                "name": "zpa_create_service_edge_group",
                "description": "Create a new ZPA service edge group (write operation)",
            },
            {
                "func": zpa_update_service_edge_group,
                "name": "zpa_update_service_edge_group",
                "description": "Update an existing ZPA service edge group (write operation)",
            },
            {
                "func": zpa_delete_service_edge_group,
                "name": "zpa_delete_service_edge_group",
                "description": "Delete a ZPA service edge group (destructive operation)",
            },
            {
                "func": zpa_create_ba_certificate,
                "name": "zpa_create_ba_certificate",
                "description": "Create a new ZPA browser access certificate (write operation)",
            },
            {
                "func": zpa_delete_ba_certificate,
                "name": "zpa_delete_ba_certificate",
                "description": "Delete a ZPA browser access certificate (destructive operation)",
            },
            {
                "func": zpa_create_access_policy_rule,
                "name": "zpa_create_access_policy_rule",
                "description": "Create a new ZPA access policy rule (write operation)",
            },
            {
                "func": zpa_update_access_policy_rule,
                "name": "zpa_update_access_policy_rule",
                "description": "Update an existing ZPA access policy rule (write operation)",
            },
            {
                "func": zpa_delete_access_policy_rule,
                "name": "zpa_delete_access_policy_rule",
                "description": "Delete a ZPA access policy rule (destructive operation)",
            },
            {
                "func": zpa_create_forwarding_policy_rule,
                "name": "zpa_create_forwarding_policy_rule",
                "description": "Create a new ZPA forwarding policy rule (write operation)",
            },
            {
                "func": zpa_update_forwarding_policy_rule,
                "name": "zpa_update_forwarding_policy_rule",
                "description": "Update an existing ZPA forwarding policy rule (write operation)",
            },
            {
                "func": zpa_delete_forwarding_policy_rule,
                "name": "zpa_delete_forwarding_policy_rule",
                "description": "Delete a ZPA forwarding policy rule (destructive operation)",
            },
            {
                "func": zpa_create_timeout_policy_rule,
                "name": "zpa_create_timeout_policy_rule",
                "description": "Create a new ZPA timeout policy rule (write operation)",
            },
            {
                "func": zpa_update_timeout_policy_rule,
                "name": "zpa_update_timeout_policy_rule",
                "description": "Update an existing ZPA timeout policy rule (write operation)",
            },
            {
                "func": zpa_delete_timeout_policy_rule,
                "name": "zpa_delete_timeout_policy_rule",
                "description": "Delete a ZPA timeout policy rule (destructive operation)",
            },
            {
                "func": zpa_create_isolation_policy_rule,
                "name": "zpa_create_isolation_policy_rule",
                "description": "Create a new ZPA isolation policy rule (write operation)",
            },
            {
                "func": zpa_update_isolation_policy_rule,
                "name": "zpa_update_isolation_policy_rule",
                "description": "Update an existing ZPA isolation policy rule (write operation)",
            },
            {
                "func": zpa_delete_isolation_policy_rule,
                "name": "zpa_delete_isolation_policy_rule",
                "description": "Delete a ZPA isolation policy rule (destructive operation)",
            },
            {
                "func": zpa_create_app_protection_rule,
                "name": "zpa_create_app_protection_rule",
                "description": "Create a new ZPA app protection rule (write operation)",
            },
            {
                "func": zpa_update_app_protection_rule,
                "name": "zpa_update_app_protection_rule",
                "description": "Update an existing ZPA app protection rule (write operation)",
            },
            {
                "func": zpa_delete_app_protection_rule,
                "name": "zpa_delete_app_protection_rule",
                "description": "Delete a ZPA app protection rule (destructive operation)",
            },
            {
                "func": zpa_create_provisioning_key,
                "name": "zpa_create_provisioning_key",
                "description": "Create a new ZPA provisioning key (write operation)",
            },
            {
                "func": zpa_update_provisioning_key,
                "name": "zpa_update_provisioning_key",
                "description": "Update an existing ZPA provisioning key (write operation)",
            },
            {
                "func": zpa_delete_provisioning_key,
                "name": "zpa_delete_provisioning_key",
                "description": "Delete a ZPA provisioning key (destructive operation)",
            },
            {
                "func": zpa_create_pra_portal,
                "name": "zpa_create_pra_portal",
                "description": "Create a new ZPA PRA portal (write operation)",
            },
            {
                "func": zpa_update_pra_portal,
                "name": "zpa_update_pra_portal",
                "description": "Update an existing ZPA PRA portal (write operation)",
            },
            {
                "func": zpa_delete_pra_portal,
                "name": "zpa_delete_pra_portal",
                "description": "Delete a ZPA PRA portal (destructive operation)",
            },
            {
                "func": zpa_create_pra_credential,
                "name": "zpa_create_pra_credential",
                "description": "Create a new ZPA PRA credential (write operation)",
            },
            {
                "func": zpa_update_pra_credential,
                "name": "zpa_update_pra_credential",
                "description": "Update an existing ZPA PRA credential (write operation)",
            },
            {
                "func": zpa_delete_pra_credential,
                "name": "zpa_delete_pra_credential",
                "description": "Delete a ZPA PRA credential (destructive operation)",
            },
        ]

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register ZPA tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(f"ZPA Service: Registered {read_count} read tools, {write_count} write tools")


class ZIAService(BaseService):
    """Zscaler Internet Access (ZIA) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import all verb-based ZIA tools
        from .tools.zia.activation import zia_activate_configuration, zia_get_activation_status
        from .tools.zia.atp_malicious_urls import (
            zia_add_atp_malicious_urls,
            zia_delete_atp_malicious_urls,
            zia_list_atp_malicious_urls,
        )
        from .tools.zia.auth_exempt_urls import (
            zia_add_auth_exempt_urls,
            zia_delete_auth_exempt_urls,
            zia_list_auth_exempt_urls,
        )
        from .tools.zia.cloud_app_control import (
            zia_create_cloud_app_control_rule,
            zia_delete_cloud_app_control_rule,
            zia_get_cloud_app_control_rule,
            zia_list_cloud_app_control_actions,
            zia_list_cloud_app_control_rules,
            zia_update_cloud_app_control_rule,
        )
        from .tools.zia.cloud_applications import (
            zia_list_cloud_app_policy,
            zia_list_cloud_app_ssl_policy,
        )
        from .tools.zia.cloud_firewall_dns_rules import (
            zia_create_cloud_firewall_dns_rule,
            zia_delete_cloud_firewall_dns_rule,
            zia_get_cloud_firewall_dns_rule,
            zia_list_cloud_firewall_dns_rules,
            zia_update_cloud_firewall_dns_rule,
        )
        from .tools.zia.cloud_firewall_ips_rules import (
            zia_create_cloud_firewall_ips_rule,
            zia_delete_cloud_firewall_ips_rule,
            zia_get_cloud_firewall_ips_rule,
            zia_list_cloud_firewall_ips_rules,
            zia_update_cloud_firewall_ips_rule,
        )
        from .tools.zia.cloud_firewall_rules import (
            zia_create_cloud_firewall_rule,
            zia_delete_cloud_firewall_rule,
            zia_get_cloud_firewall_rule,
            zia_list_cloud_firewall_rules,
            zia_update_cloud_firewall_rule,
        )
        from .tools.zia.device_management import (
            zia_list_device_groups,
            zia_list_devices,
            zia_list_devices_lite,
        )
        from .tools.zia.file_type_control_rules import (
            zia_create_file_type_control_rule,
            zia_delete_file_type_control_rule,
            zia_get_file_type_control_rule,
            zia_list_file_type_categories,
            zia_list_file_type_control_rules,
            zia_update_file_type_control_rule,
        )
        from .tools.zia.geo_search import zia_geo_search_tool
        from .tools.zia.get_sandbox_info import (
            zia_get_sandbox_behavioral_analysis,
            zia_get_sandbox_file_hash_count,
            zia_get_sandbox_quota,
            zia_get_sandbox_report,
        )
        from .tools.zia.gre_ranges import zia_list_gre_ranges
        from .tools.zia.gre_tunnels import (
            zia_create_gre_tunnel,
            zia_delete_gre_tunnel,
            zia_get_gre_tunnel,
            zia_list_gre_tunnels,
        )
        from .tools.zia.ip_destination_groups import (
            zia_create_ip_destination_group,
            zia_delete_ip_destination_group,
            zia_get_ip_destination_group,
            zia_list_ip_destination_groups,
            zia_update_ip_destination_group,
        )
        from .tools.zia.ip_source_groups import (
            zia_create_ip_source_group,
            zia_delete_ip_source_group,
            zia_get_ip_source_group,
            zia_list_ip_source_groups,
            zia_update_ip_source_group,
        )
        from .tools.zia.list_dlp_dictionaries import zia_dlp_dictionary_manager
        from .tools.zia.list_dlp_engines import zia_dlp_engine_manager
        from .tools.zia.list_user_departments import zia_user_department_manager
        from .tools.zia.list_user_groups import zia_user_group_manager
        from .tools.zia.list_users import zia_users_manager
        from .tools.zia.location_management import (
            zia_create_location,
            zia_delete_location,
            zia_get_location,
            zia_get_location_group,
            zia_list_location_groups,
            zia_list_locations,
            zia_update_location,
        )
        from .tools.zia.network_app_groups import (
            zia_create_network_app_group,
            zia_delete_network_app_group,
            zia_get_network_app_group,
            zia_list_network_app_groups,
            zia_update_network_app_group,
        )
        from .tools.zia.network_apps import (
            zia_get_network_app,
            zia_list_network_apps,
        )
        from .tools.zia.network_services import (
            zia_create_network_service,
            zia_delete_network_service,
            zia_get_network_service,
            zia_list_network_services,
            zia_update_network_service,
        )
        from .tools.zia.network_services_group import (
            zia_create_network_svc_group,
            zia_delete_network_svc_group,
            zia_get_network_svc_group,
            zia_list_network_svc_groups,
            zia_update_network_svc_group,
        )
        from .tools.zia.rule_labels import (
            zia_create_rule_label,
            zia_delete_rule_label,
            zia_get_rule_label,
            zia_list_rule_labels,
            zia_update_rule_label,
        )
        from .tools.zia.sandbox_rules import (
            zia_create_sandbox_rule,
            zia_delete_sandbox_rule,
            zia_get_sandbox_rule,
            zia_list_sandbox_rules,
            zia_update_sandbox_rule,
        )
        from .tools.zia.shadow_it_report import (
            zia_bulk_update_shadow_it_apps,
            zia_list_shadow_it_apps,
            zia_list_shadow_it_custom_tags,
        )
        from .tools.zia.ssl_inspection import (
            zia_create_ssl_inspection_rule,
            zia_delete_ssl_inspection_rule,
            zia_get_ssl_inspection_rule,
            zia_list_ssl_inspection_rules,
            zia_update_ssl_inspection_rule,
        )
        from .tools.zia.static_ips import (
            zia_create_static_ip,
            zia_delete_static_ip,
            zia_get_static_ip,
            zia_list_static_ips,
            zia_update_static_ip,
        )
        from .tools.zia.time_intervals import (
            zia_create_time_interval,
            zia_delete_time_interval,
            zia_get_time_interval,
            zia_list_time_intervals,
            zia_update_time_interval,
        )
        from .tools.zia.url_categories import (
            zia_add_urls_to_category,
            zia_create_url_category,
            zia_delete_url_category,
            zia_get_url_category,
            zia_get_url_category_predefined,
            zia_list_url_categories,
            zia_remove_urls_from_category,
            zia_update_url_category,
            zia_update_url_category_predefined,
            zia_url_lookup,
        )
        from .tools.zia.url_filtering_rules import (
            zia_create_url_filtering_rule,
            zia_delete_url_filtering_rule,
            zia_get_url_filtering_rule,
            zia_list_url_filtering_rules,
            zia_update_url_filtering_rule,
        )
        from .tools.zia.vpn_credentials import (
            zia_create_vpn_credential,
            zia_delete_vpn_credential,
            zia_get_vpn_credential,
            zia_list_vpn_credentials,
            zia_update_vpn_credential,
        )
        from .tools.zia.web_dlp_rules import (
            zia_create_web_dlp_rule,
            zia_delete_web_dlp_rule,
            zia_get_web_dlp_rule,
            zia_list_web_dlp_rules,
            zia_list_web_dlp_rules_lite,
            zia_update_web_dlp_rule,
        )
        from .tools.zia.workload_groups import (
            zia_get_workload_group,
            zia_list_workload_groups,
        )

        # Read-only tools
        self.read_tools = [
            # Cloud Firewall Rules
            {
                "func": zia_list_cloud_firewall_rules,
                "name": "zia_list_cloud_firewall_rules",
                "description": "List ZIA cloud firewall rules with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_cloud_firewall_rule,
                "name": "zia_get_cloud_firewall_rule",
                "description": "Get a specific ZIA cloud firewall rule by ID (read-only)",
            },
            # URL Filtering Rules
            {
                "func": zia_list_url_filtering_rules,
                "name": "zia_list_url_filtering_rules",
                "description": "List ZIA URL filtering rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_url_filtering_rule,
                "name": "zia_get_url_filtering_rule",
                "description": "Get a specific ZIA URL filtering rule by ID (read-only)",
            },
            # Web DLP Rules
            {
                "func": zia_list_web_dlp_rules,
                "name": "zia_list_web_dlp_rules",
                "description": "List ZIA web DLP rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_list_web_dlp_rules_lite,
                "name": "zia_list_web_dlp_rules_lite",
                "description": "List ZIA web DLP rules in lite format (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_web_dlp_rule,
                "name": "zia_get_web_dlp_rule",
                "description": "Get a specific ZIA web DLP rule by ID (read-only)",
            },
            # SSL Inspection Rules
            {
                "func": zia_list_ssl_inspection_rules,
                "name": "zia_list_ssl_inspection_rules",
                "description": "List ZIA SSL inspection rules (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_ssl_inspection_rule,
                "name": "zia_get_ssl_inspection_rule",
                "description": "Get a specific ZIA SSL inspection rule by ID (read-only)",
            },
            # DLP Dictionaries
            {
                "func": zia_dlp_dictionary_manager,
                "name": "get_zia_dlp_dictionaries",
                "description": "Manage ZIA DLP dictionaries for data loss prevention pattern and phrase matching (read-only)",
            },
            # DLP Engines
            {
                "func": zia_dlp_engine_manager,
                "name": "get_zia_dlp_engines",
                "description": "Manage ZIA DLP engines for data loss prevention rule processing (read-only)",
            },
            # User Management
            {
                "func": zia_user_department_manager,
                "name": "get_zia_user_departments",
                "description": "Manage ZIA user departments for organizational structure (read-only)",
            },
            {
                "func": zia_user_group_manager,
                "name": "get_zia_user_groups",
                "description": (
                    "Read ZIA user groups for access control and policy assignment. "
                    "Pass `name=\"<literal admin-supplied name>\"` (e.g. `name=\"A000\"`) "
                    "for a case-insensitive substring match resolved client-side — "
                    "this is the right knob for find-by-name workflows. "
                    "Pass `group_id=` to fetch a single group. The `search` "
                    "parameter forwards to the ZIA API and is unreliable for "
                    "name-based lookups; prefer `name`."
                ),
            },
            {
                "func": zia_users_manager,
                "name": "get_zia_users",
                "description": "Manage ZIA users for authentication and access control (read-only)",
            },
            # IP Source Groups
            {
                "func": zia_list_ip_source_groups,
                "name": "zia_list_ip_source_groups",
                "description": "List ZIA IP source groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_ip_source_group,
                "name": "zia_get_ip_source_group",
                "description": "Get a specific ZIA IP source group by ID (read-only)",
            },
            # IP Destination Groups
            {
                "func": zia_list_ip_destination_groups,
                "name": "zia_list_ip_destination_groups",
                "description": "List ZIA IP destination groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_ip_destination_group,
                "name": "zia_get_ip_destination_group",
                "description": "Get a specific ZIA IP destination group by ID (read-only)",
            },
            # Network App Groups
            {
                "func": zia_list_network_app_groups,
                "name": "zia_list_network_app_groups",
                "description": "List ZIA network application groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_network_app_group,
                "name": "zia_get_network_app_group",
                "description": "Get a specific ZIA network application group by ID (read-only)",
            },
            # Network Applications
            {
                "func": zia_list_network_apps,
                "name": "zia_list_network_apps",
                "description": "List ZIA network applications with optional filtering by search or locale (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_network_app,
                "name": "zia_get_network_app",
                "description": "Get a specific ZIA network application by ID (read-only)",
            },
            # Network Services
            {
                "func": zia_list_network_services,
                "name": "zia_list_network_services",
                "description": (
                    "List ZIA network services (read-only). Pass "
                    "`name=\"<friendly admin-supplied name>\"` (e.g. `name=\"http\"`, "
                    "`name=\"ftp\"`, `name=\"dns\"`) for a case-insensitive "
                    "substring match resolved client-side — this is the right "
                    "knob when the admin gives a service name in any casing. "
                    "ZIA's canonical service names are uppercase enums "
                    "(`HTTP`, `FTP`, `DNS`, ...), so server-side `search` is "
                    "case-sensitive and unreliable for friendly inputs. Also "
                    "supports `protocol` / `locale` filters and JMESPath "
                    "projection via `query`."
                ),
            },
            {
                "func": zia_get_network_service,
                "name": "zia_get_network_service",
                "description": "Get a specific ZIA network service by ID (read-only)",
            },
            # Network Service Groups
            {
                "func": zia_list_network_svc_groups,
                "name": "zia_list_network_svc_groups",
                "description": "List ZIA network service groups with optional filtering (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_network_svc_group,
                "name": "zia_get_network_svc_group",
                "description": "Get a specific ZIA network service group by ID (read-only)",
            },
            # URL Categories
            {
                "func": zia_list_url_categories,
                "name": "zia_list_url_categories",
                "description": "List ZIA URL categories (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_url_category,
                "name": "zia_get_url_category",
                "description": "Get a specific ZIA URL category by ID (read-only)",
            },
            {
                "func": zia_get_url_category_predefined,
                "name": "zia_get_url_category_predefined",
                "description": (
                    "Get a Zscaler-curated predefined URL category by canonical ID "
                    "(e.g. 'FINANCE') or display name (e.g. 'Finance'). "
                    "Case-insensitive. Refuses custom categories — use "
                    "zia_get_url_category for those (read-only)."
                ),
            },
            {
                "func": zia_url_lookup,
                "name": "zia_url_lookup",
                "description": "Look up URL category for given URLs (read-only)",
            },
            # Rule Labels
            {
                "func": zia_list_rule_labels,
                "name": "zia_list_rule_labels",
                "description": "List ZIA rule labels (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_rule_label,
                "name": "zia_get_rule_label",
                "description": "Get a specific ZIA rule label by ID (read-only)",
            },
            # Locations
            {
                "func": zia_list_locations,
                "name": "zia_list_locations",
                "description": "List ZIA locations (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_location,
                "name": "zia_get_location",
                "description": "Get a specific ZIA location by ID (read-only)",
            },
            # Location Groups (referenced as location_groups operand on every ZIA rule resource)
            {
                "func": zia_list_location_groups,
                "name": "zia_list_location_groups",
                "description": (
                    "List ZIA location groups, referenced by ID on the location_groups "
                    "operand of every ZIA rule resource (Cloud Firewall, DNS, IPS, URL "
                    "Filtering, SSL Inspection, Web DLP, File Type Control, Sandbox, "
                    "Cloud App Control). Read-only — the public ZIA API does not expose "
                    "location group create/update/delete. Supports name/search/group_type "
                    "filters and JMESPath via the query parameter."
                ),
            },
            {
                "func": zia_get_location_group,
                "name": "zia_get_location_group",
                "description": "Get a specific ZIA location group by ID (read-only)",
            },
            # Workload Groups (referenced as workload_groups operand on Cloud Firewall, URL Filtering, SSL Inspection, Web DLP)
            {
                "func": zia_list_workload_groups,
                "name": "zia_list_workload_groups",
                "description": (
                    "List ZIA workload groups, referenced by ID on the workload_groups "
                    "operand of Cloud Firewall, URL Filtering, SSL Inspection, and "
                    "Web DLP rules. Read-only — workload group authoring (with its "
                    "expression DSL) is intentionally left to the ZIA UI. The ZIA list "
                    "endpoint has no server-side name filter; pair with JMESPath query "
                    "(e.g. \"[?name=='WG-AWS-Prod']\") to look up a group by name."
                ),
            },
            {
                "func": zia_get_workload_group,
                "name": "zia_get_workload_group",
                "description": "Get a specific ZIA workload group by ID (read-only)",
            },
            # VPN Credentials
            {
                "func": zia_list_vpn_credentials,
                "name": "zia_list_vpn_credentials",
                "description": "List ZIA VPN credentials (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_vpn_credential,
                "name": "zia_get_vpn_credential",
                "description": "Get a specific ZIA VPN credential by ID (read-only)",
            },
            # Static IPs
            {
                "func": zia_list_static_ips,
                "name": "zia_list_static_ips",
                "description": "List ZIA static IPs (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_static_ip,
                "name": "zia_get_static_ip",
                "description": "Get a specific ZIA static IP by ID (read-only)",
            },
            # GRE Tunnels
            {
                "func": zia_list_gre_tunnels,
                "name": "zia_list_gre_tunnels",
                "description": "List ZIA GRE tunnels (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_gre_tunnel,
                "name": "zia_get_gre_tunnel",
                "description": "Get a specific ZIA GRE tunnel by ID (read-only)",
            },
            {
                "func": zia_list_gre_ranges,
                "name": "zia_list_gre_ranges",
                "description": "List available ZIA GRE IP ranges (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            # Activation
            {
                "func": zia_get_activation_status,
                "name": "zia_get_activation_status",
                "description": "Get ZIA configuration activation status (read-only)",
            },
            # ATP Malicious URLs
            {
                "func": zia_list_atp_malicious_urls,
                "name": "zia_list_atp_malicious_urls",
                "description": "List ZIA ATP malicious URLs (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            # Auth Exempt URLs
            {
                "func": zia_list_auth_exempt_urls,
                "name": "zia_list_auth_exempt_urls",
                "description": "List ZIA authentication exempt URLs (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            # Shadow IT Report (analytics catalog: numeric IDs, friendly names, custom tags)
            {
                "func": zia_list_shadow_it_apps,
                "name": "zia_list_shadow_it_apps",
                "description": "List ZIA Shadow IT cloud applications — analytics catalog with numeric IDs and friendly names (e.g. 'Sharepoint Online', id 655377). NOT the policy-engine enum catalog. Use zia_list_cloud_app_policy / zia_list_cloud_app_ssl_policy for the canonical enum strings consumed by SSL inspection / DLP / Cloud App Control rules. Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_list_shadow_it_custom_tags,
                "name": "zia_list_shadow_it_custom_tags",
                "description": "List ZIA Shadow IT custom tags (read-only). Supports JMESPath client-side filtering via the query parameter.",
            },
            # Cloud Applications (policy-engine catalog: canonical enum strings for rules)
            {
                "func": zia_list_cloud_app_policy,
                "name": "zia_list_cloud_app_policy",
                "description": "List the ZIA policy-engine cloud-application catalog — canonical enum strings (e.g. ONEDRIVE, ONEDRIVE_PERSONAL, SHAREPOINT_ONLINE) consumed by Web DLP, Cloud App Control, File Type Control, Bandwidth Classes, and Advanced Settings. Use this when you need the exact enum to pass into a policy rule's cloud_applications field. Supports server-side filtering (search, app_class, group_results) and JMESPath via the query parameter. Pass app_class to narrow the catalog by category when the user describes a kind of app instead of a specific one — valid values: SOCIAL_NETWORKING, STREAMING_MEDIA, WEBMAIL, INSTANT_MESSAGING, BUSINESS_PRODUCTIVITY, ENTERPRISE_COLLABORATION, SALES_AND_MARKETING, SYSTEM_AND_DEVELOPMENT, CONSUMER, HOSTING_PROVIDER, IT_SERVICES, FILE_SHARE, DNS_OVER_HTTPS, HUMAN_RESOURCES, LEGAL, HEALTH_CARE, FINANCE, CUSTOM_CAPP, AI_ML.",
            },
            {
                "func": zia_list_cloud_app_ssl_policy,
                "name": "zia_list_cloud_app_ssl_policy",
                "description": "List the ZIA cloud-application catalog scoped to SSL Inspection rules — returns the canonical enum strings the SSL Inspection API will accept in the cloud_applications field (e.g. ONEDRIVE, SHAREPOINT_ONLINE). Use this to resolve enum names before creating or updating SSL Inspection rules. Supports server-side filtering (search, app_class, group_results) and JMESPath via the query parameter. Pass app_class to narrow the catalog by category when the user describes a kind of app — valid values: SOCIAL_NETWORKING, STREAMING_MEDIA, WEBMAIL, INSTANT_MESSAGING, BUSINESS_PRODUCTIVITY, ENTERPRISE_COLLABORATION, SALES_AND_MARKETING, SYSTEM_AND_DEVELOPMENT, CONSUMER, HOSTING_PROVIDER, IT_SERVICES, FILE_SHARE, DNS_OVER_HTTPS, HUMAN_RESOURCES, LEGAL, HEALTH_CARE, FINANCE, CUSTOM_CAPP, AI_ML.",
            },
            # Cloud App Control
            {
                "func": zia_list_cloud_app_control_actions,
                "name": "zia_list_cloud_app_control_actions",
                "description": "List the granular Cloud App Control (CAC) actions available for a cloud application — answers 'what actions can I control for <app>?', 'list actions for Azure DevOps', 'what can I block on Dropbox', 'show me available actions for ChatGPT'. Takes a single cloud_app (canonical enum like AZURE_DEVOPS or friendly name like 'Azure DevOps'); the tool auto-resolves the name, looks up its category (rule type), and returns the category's full action set. Actions are CATEGORY-LEVEL not per-app — every app in SYSTEM_AND_DEVELOPMENT shares the same actions, every app in AI_ML shares its own set, etc. The tool also handles a ZIA API quirk where calling list_available_actions(rule_type, [some_app]) sometimes returns empty because not every app is a 'representative' for its category — when that happens, it transparently walks other apps in the same category until one surfaces the action set. Returns a dict with: cloud_app, resolved_app, category, category_name, actions, actions_surfaced_via (which app finally produced the actions), and probe_attempts. Use the optional rule_type parameter only to override the auto-detected category; use query (JMESPath) to project just the actions list (e.g. 'actions') or filter them (e.g. 'actions[?contains(@, ``BLOCK``)]').",
            },
            {
                "func": zia_list_cloud_app_control_rules,
                "name": "zia_list_cloud_app_control_rules",
                "description": "List ZIA Cloud App Control rules for a specific rule_type (category). The CAC API is category-scoped, so rule_type is REQUIRED — pass one of WEBMAIL, STREAMING_MEDIA, FILE_SHARE, AI_ML, SYSTEM_AND_DEVELOPMENT, SOCIAL_NETWORKING, INSTANT_MESSAGING, BUSINESS_PRODUCTIVITY, ENTERPRISE_COLLABORATION, etc. To list across multiple categories, call this once per category. If the user names an app instead of a category, call zia_list_cloud_app_control_actions(cloud_app=...) first to discover the right rule_type. Supports server-side `search` (substring on rule name) and JMESPath client-side filtering via the `query` parameter.",
            },
            {
                "func": zia_get_cloud_app_control_rule,
                "name": "zia_get_cloud_app_control_rule",
                "description": "Get a specific ZIA Cloud App Control rule by rule_type AND rule_id (read-only). Both arguments are required because the CAC API is category-scoped — rule_id alone is not sufficient. If you only know the app name, call zia_list_cloud_app_control_actions(cloud_app=...) first to discover the rule_type.",
            },
            # Device Management
            {
                "func": zia_list_device_groups,
                "name": "zia_list_device_groups",
                "description": "List ZIA device groups with optional device info and pseudo group filtering (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_list_devices,
                "name": "zia_list_devices",
                "description": "List ZIA devices with filtering by name, user, pagination support (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_list_devices_lite,
                "name": "zia_list_devices_lite",
                "description": "List ZIA devices in lightweight format (ID, name, owner only) (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            # Utilities
            {
                "func": zia_geo_search_tool,
                "name": "zia_geo_search",
                "description": "Perform ZIA geographic lookups (coordinates, IP, or city prefix) (read-only)",
            },
            {
                "func": zia_get_sandbox_quota,
                "name": "zia_get_sandbox_quota",
                "description": "Retrieve current ZIA sandbox quota information (read-only)",
            },
            {
                "func": zia_get_sandbox_behavioral_analysis,
                "name": "zia_get_sandbox_behavioral_analysis",
                "description": "Retrieve sandbox behavioral analysis hash list (read-only)",
            },
            {
                "func": zia_get_sandbox_file_hash_count,
                "name": "zia_get_sandbox_file_hash_count",
                "description": "Retrieve sandbox file hash usage counts (read-only)",
            },
            {
                "func": zia_get_sandbox_report,
                "name": "zia_get_sandbox_report",
                "description": "Retrieve sandbox analysis report for a specific MD5 hash (read-only)",
            },
            # Cloud Firewall DNS Rules
            {
                "func": zia_list_cloud_firewall_dns_rules,
                "name": "zia_list_cloud_firewall_dns_rules",
                "description": "List ZIA cloud firewall DNS rules (read-only). Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_cloud_firewall_dns_rule,
                "name": "zia_get_cloud_firewall_dns_rule",
                "description": "Get a specific ZIA cloud firewall DNS rule by ID (read-only)",
            },
            # Cloud Firewall IPS Rules
            {
                "func": zia_list_cloud_firewall_ips_rules,
                "name": "zia_list_cloud_firewall_ips_rules",
                "description": "List ZIA cloud firewall IPS rules (read-only). Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_cloud_firewall_ips_rule,
                "name": "zia_get_cloud_firewall_ips_rule",
                "description": "Get a specific ZIA cloud firewall IPS rule by ID (read-only)",
            },
            # File Type Control Rules
            {
                "func": zia_list_file_type_control_rules,
                "name": "zia_list_file_type_control_rules",
                "description": "List ZIA File Type Control rules (read-only). Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_file_type_control_rule,
                "name": "zia_get_file_type_control_rule",
                "description": "Get a specific ZIA File Type Control rule by ID (read-only)",
            },
            {
                "func": zia_list_file_type_categories,
                "name": "zia_list_file_type_categories",
                "description": "List ZIA file-type categories (predefined and custom) used by File Type Control and Web DLP rules (read-only).",
            },
            # Sandbox Rules
            {
                "func": zia_list_sandbox_rules,
                "name": "zia_list_sandbox_rules",
                "description": "List ZIA Sandbox rules (read-only). Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_sandbox_rule,
                "name": "zia_get_sandbox_rule",
                "description": "Get a specific ZIA Sandbox rule by ID (read-only)",
            },
            # Time Intervals
            {
                "func": zia_list_time_intervals,
                "name": "zia_list_time_intervals",
                "description": "List ZIA Time Intervals (recurring time-of-day / day-of-week schedules referenced by policy rules via the time_windows field). Read-only. Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zia_get_time_interval,
                "name": "zia_get_time_interval",
                "description": "Get a specific ZIA Time Interval by ID (read-only).",
            },
        ]

        # Write tools
        self.write_tools = [
            # Cloud Firewall Rules
            {
                "func": zia_create_cloud_firewall_rule,
                "name": "zia_create_cloud_firewall_rule",
                "description": "Create a new ZIA cloud firewall rule (write operation)",
            },
            {
                "func": zia_update_cloud_firewall_rule,
                "name": "zia_update_cloud_firewall_rule",
                "description": "Update an existing ZIA cloud firewall rule (write operation)",
            },
            {
                "func": zia_delete_cloud_firewall_rule,
                "name": "zia_delete_cloud_firewall_rule",
                "description": "Delete a ZIA cloud firewall rule (destructive operation)",
            },
            # URL Filtering Rules
            {
                "func": zia_create_url_filtering_rule,
                "name": "zia_create_url_filtering_rule",
                "description": "Create a new ZIA URL filtering rule (write operation)",
            },
            {
                "func": zia_update_url_filtering_rule,
                "name": "zia_update_url_filtering_rule",
                "description": "Update an existing ZIA URL filtering rule (write operation)",
            },
            {
                "func": zia_delete_url_filtering_rule,
                "name": "zia_delete_url_filtering_rule",
                "description": "Delete a ZIA URL filtering rule (destructive operation)",
            },
            # SSL Inspection Rules
            {
                "func": zia_create_ssl_inspection_rule,
                "name": "zia_create_ssl_inspection_rule",
                "description": "Create a new ZIA SSL inspection rule (write operation)",
            },
            {
                "func": zia_update_ssl_inspection_rule,
                "name": "zia_update_ssl_inspection_rule",
                "description": "Update an existing ZIA SSL inspection rule (write operation)",
            },
            {
                "func": zia_delete_ssl_inspection_rule,
                "name": "zia_delete_ssl_inspection_rule",
                "description": "Delete a ZIA SSL inspection rule (destructive operation)",
            },
            # Web DLP Rules
            {
                "func": zia_create_web_dlp_rule,
                "name": "zia_create_web_dlp_rule",
                "description": "Create a new ZIA web DLP rule (write operation)",
            },
            {
                "func": zia_update_web_dlp_rule,
                "name": "zia_update_web_dlp_rule",
                "description": "Update an existing ZIA web DLP rule (write operation)",
            },
            {
                "func": zia_delete_web_dlp_rule,
                "name": "zia_delete_web_dlp_rule",
                "description": "Delete a ZIA web DLP rule (destructive operation)",
            },
            # IP Source Groups
            {
                "func": zia_create_ip_source_group,
                "name": "zia_create_ip_source_group",
                "description": "Create a new ZIA IP source group (write operation)",
            },
            {
                "func": zia_update_ip_source_group,
                "name": "zia_update_ip_source_group",
                "description": "Update an existing ZIA IP source group (write operation)",
            },
            {
                "func": zia_delete_ip_source_group,
                "name": "zia_delete_ip_source_group",
                "description": "Delete a ZIA IP source group (destructive operation)",
            },
            # IP Destination Groups
            {
                "func": zia_create_ip_destination_group,
                "name": "zia_create_ip_destination_group",
                "description": "Create a new ZIA IP destination group (write operation)",
            },
            {
                "func": zia_update_ip_destination_group,
                "name": "zia_update_ip_destination_group",
                "description": "Update an existing ZIA IP destination group (write operation)",
            },
            {
                "func": zia_delete_ip_destination_group,
                "name": "zia_delete_ip_destination_group",
                "description": "Delete a ZIA IP destination group (destructive operation)",
            },
            # Network App Groups
            {
                "func": zia_create_network_app_group,
                "name": "zia_create_network_app_group",
                "description": "Create a new ZIA network application group (write operation)",
            },
            {
                "func": zia_update_network_app_group,
                "name": "zia_update_network_app_group",
                "description": "Update an existing ZIA network application group (write operation)",
            },
            {
                "func": zia_delete_network_app_group,
                "name": "zia_delete_network_app_group",
                "description": "Delete a ZIA network application group (destructive operation)",
            },
            # Network Services
            {
                "func": zia_create_network_service,
                "name": "zia_create_network_service",
                "description": "Create a new ZIA network service with custom TCP/UDP ports (write operation)",
            },
            {
                "func": zia_update_network_service,
                "name": "zia_update_network_service",
                "description": "Update an existing ZIA network service (write operation)",
            },
            {
                "func": zia_delete_network_service,
                "name": "zia_delete_network_service",
                "description": "Delete a ZIA network service (destructive operation)",
            },
            # Network Service Groups
            {
                "func": zia_create_network_svc_group,
                "name": "zia_create_network_svc_group",
                "description": "Create a new ZIA network service group (write operation)",
            },
            {
                "func": zia_update_network_svc_group,
                "name": "zia_update_network_svc_group",
                "description": "Update an existing ZIA network service group (write operation)",
            },
            {
                "func": zia_delete_network_svc_group,
                "name": "zia_delete_network_svc_group",
                "description": "Delete a ZIA network service group (destructive operation)",
            },
            # URL Categories
            {
                "func": zia_create_url_category,
                "name": "zia_create_url_category",
                "description": "Create a new ZIA URL category (write operation)",
            },
            {
                "func": zia_update_url_category,
                "name": "zia_update_url_category",
                "description": (
                    "Update an existing custom ZIA URL category (full PUT, write "
                    "operation). Refuses predefined categories — use "
                    "zia_update_url_category_predefined for those, or "
                    "zia_add_urls_to_category / zia_remove_urls_from_category for "
                    "incremental URL/IP-range changes."
                ),
            },
            {
                "func": zia_update_url_category_predefined,
                "name": "zia_update_url_category_predefined",
                "description": (
                    "Update a Zscaler-curated predefined URL category (full PUT, "
                    "write operation). Same field surface as zia_update_url_category. "
                    "Resolves the category by canonical ID ('FINANCE') or display "
                    "name ('Finance') and silently backfills configured_name from "
                    "the existing category when omitted. For incremental URL/IP-range "
                    "mutations prefer zia_add_urls_to_category / "
                    "zia_remove_urls_from_category — both work on predefined IDs."
                ),
            },
            {
                "func": zia_delete_url_category,
                "name": "zia_delete_url_category",
                "description": (
                    "Delete a custom ZIA URL category (destructive operation). "
                    "Refuses predefined categories — those are Zscaler-curated and "
                    "cannot be deleted via the API."
                ),
            },
            {
                "func": zia_add_urls_to_category,
                "name": "zia_add_urls_to_category",
                "description": "Add URLs to a ZIA URL category (write operation)",
            },
            {
                "func": zia_remove_urls_from_category,
                "name": "zia_remove_urls_from_category",
                "description": "Remove URLs from a ZIA URL category (write operation)",
            },
            # Rule Labels
            {
                "func": zia_create_rule_label,
                "name": "zia_create_rule_label",
                "description": "Create a new ZIA rule label (write operation)",
            },
            {
                "func": zia_update_rule_label,
                "name": "zia_update_rule_label",
                "description": "Update an existing ZIA rule label (write operation)",
            },
            {
                "func": zia_delete_rule_label,
                "name": "zia_delete_rule_label",
                "description": "Delete a ZIA rule label (destructive operation)",
            },
            # Locations
            {
                "func": zia_create_location,
                "name": "zia_create_location",
                "description": "Create a new ZIA location (write operation)",
            },
            {
                "func": zia_update_location,
                "name": "zia_update_location",
                "description": "Update an existing ZIA location (write operation)",
            },
            {
                "func": zia_delete_location,
                "name": "zia_delete_location",
                "description": "Delete a ZIA location (destructive operation)",
            },
            # VPN Credentials
            {
                "func": zia_create_vpn_credential,
                "name": "zia_create_vpn_credential",
                "description": "Create a new ZIA VPN credential (write operation)",
            },
            {
                "func": zia_update_vpn_credential,
                "name": "zia_update_vpn_credential",
                "description": "Update an existing ZIA VPN credential (write operation)",
            },
            {
                "func": zia_delete_vpn_credential,
                "name": "zia_delete_vpn_credential",
                "description": "Delete a ZIA VPN credential (destructive operation)",
            },
            # Static IPs
            {
                "func": zia_create_static_ip,
                "name": "zia_create_static_ip",
                "description": "Create a new ZIA static IP (write operation)",
            },
            {
                "func": zia_update_static_ip,
                "name": "zia_update_static_ip",
                "description": "Update an existing ZIA static IP (write operation)",
            },
            {
                "func": zia_delete_static_ip,
                "name": "zia_delete_static_ip",
                "description": "Delete a ZIA static IP (destructive operation)",
            },
            # GRE Tunnels
            {
                "func": zia_create_gre_tunnel,
                "name": "zia_create_gre_tunnel",
                "description": "Create a new ZIA GRE tunnel (write operation)",
            },
            {
                "func": zia_delete_gre_tunnel,
                "name": "zia_delete_gre_tunnel",
                "description": "Delete a ZIA GRE tunnel (destructive operation)",
            },
            # Activation
            {
                "func": zia_activate_configuration,
                "name": "zia_activate_configuration",
                "description": "Activate ZIA configuration changes (write operation)",
            },
            # ATP Malicious URLs
            {
                "func": zia_add_atp_malicious_urls,
                "name": "zia_add_atp_malicious_urls",
                "description": "Add URLs to ZIA ATP malicious URL list (write operation)",
            },
            {
                "func": zia_delete_atp_malicious_urls,
                "name": "zia_delete_atp_malicious_urls",
                "description": "Delete URLs from ZIA ATP malicious URL list (destructive operation)",
            },
            # Auth Exempt URLs
            {
                "func": zia_add_auth_exempt_urls,
                "name": "zia_add_auth_exempt_urls",
                "description": "Add URLs to ZIA authentication exempt list (write operation)",
            },
            {
                "func": zia_delete_auth_exempt_urls,
                "name": "zia_delete_auth_exempt_urls",
                "description": "Delete URLs from ZIA authentication exempt list (destructive operation)",
            },
            # Shadow IT Report (write)
            {
                "func": zia_bulk_update_shadow_it_apps,
                "name": "zia_bulk_update_shadow_it_apps",
                "description": "Bulk update sanction state and/or custom tags on ZIA Shadow IT cloud applications (write operation).",
            },
            # Cloud Firewall DNS Rules
            {
                "func": zia_create_cloud_firewall_dns_rule,
                "name": "zia_create_cloud_firewall_dns_rule",
                "description": "Create a new ZIA cloud firewall DNS rule (write operation). The `applications` field accepts the same canonical ZIA cloud-app names used by SSL Inspection / Web DLP / FTC / CAC in their `cloud_applications` field — DNS just exposes the field as `applications`. Friendly names (e.g. \"OneDrive\", \"Cloudflare DoH\") are auto-resolved.",
            },
            {
                "func": zia_update_cloud_firewall_dns_rule,
                "name": "zia_update_cloud_firewall_dns_rule",
                "description": "Update an existing ZIA cloud firewall DNS rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied. The `applications` field accepts canonical ZIA cloud-app names (same catalog as SSL/DLP/FTC/CAC's `cloud_applications`) and auto-resolves friendly names.",
            },
            {
                "func": zia_delete_cloud_firewall_dns_rule,
                "name": "zia_delete_cloud_firewall_dns_rule",
                "description": "Delete a ZIA cloud firewall DNS rule (destructive operation)",
            },
            # Cloud Firewall IPS Rules
            {
                "func": zia_create_cloud_firewall_ips_rule,
                "name": "zia_create_cloud_firewall_ips_rule",
                "description": "Create a new ZIA cloud firewall IPS rule (write operation)",
            },
            {
                "func": zia_update_cloud_firewall_ips_rule,
                "name": "zia_update_cloud_firewall_ips_rule",
                "description": "Update an existing ZIA cloud firewall IPS rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied.",
            },
            {
                "func": zia_delete_cloud_firewall_ips_rule,
                "name": "zia_delete_cloud_firewall_ips_rule",
                "description": "Delete a ZIA cloud firewall IPS rule (destructive operation)",
            },
            # Cloud App Control Rules
            {
                "func": zia_create_cloud_app_control_rule,
                "name": "zia_create_cloud_app_control_rule",
                "description": "Create a new ZIA Cloud App Control (CAC) rule (write operation). The CAC API is category-scoped — rule_type is REQUIRED (e.g. WEBMAIL, FILE_SHARE, AI_ML, SYSTEM_AND_DEVELOPMENT). Workflow: first call zia_list_cloud_app_control_actions(cloud_app=<app>) to discover both the correct rule_type (returned as `category`) AND the valid `actions` enums for that app, then pass those into this tool together with `name`, `cloud_applications`, and any scoping fields (groups, departments, locations, etc.). Friendly cloud-application names like 'Dropbox' are auto-resolved to canonical enums (DROPBOX). Note: the SDK kwarg for the apps list is `applications` but this tool surfaces it as `cloud_applications` for consistency with other ZIA rule families.",
            },
            {
                "func": zia_update_cloud_app_control_rule,
                "name": "zia_update_cloud_app_control_rule",
                "description": "Update an existing ZIA Cloud App Control (CAC) rule (write operation). Both rule_type AND rule_id are required (the CAC API is category-scoped). Update is a PUT under the hood — `name` is silently backfilled from the existing rule when not supplied so partial updates work safely. Friendly cloud-application names are auto-resolved to canonical enums.",
            },
            {
                "func": zia_delete_cloud_app_control_rule,
                "name": "zia_delete_cloud_app_control_rule",
                "description": "Delete a ZIA Cloud App Control (CAC) rule by rule_type and rule_id (destructive operation). Both arguments are required because the CAC API is category-scoped. Requires HMAC confirmation token.",
            },
            # File Type Control Rules
            {
                "func": zia_create_file_type_control_rule,
                "name": "zia_create_file_type_control_rule",
                "description": "Create a new ZIA File Type Control rule (write operation). Friendly cloud-application names are auto-resolved to canonical enums.",
            },
            {
                "func": zia_update_file_type_control_rule,
                "name": "zia_update_file_type_control_rule",
                "description": "Update an existing ZIA File Type Control rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied. Friendly cloud-application names are auto-resolved.",
            },
            {
                "func": zia_delete_file_type_control_rule,
                "name": "zia_delete_file_type_control_rule",
                "description": "Delete a ZIA File Type Control rule (destructive operation)",
            },
            # Sandbox Rules
            {
                "func": zia_create_sandbox_rule,
                "name": "zia_create_sandbox_rule",
                "description": "Create a new ZIA Sandbox rule (write operation)",
            },
            {
                "func": zia_update_sandbox_rule,
                "name": "zia_update_sandbox_rule",
                "description": "Update an existing ZIA Sandbox rule (write operation). Update is a PUT — name/order are silently backfilled from the existing rule when not supplied.",
            },
            {
                "func": zia_delete_sandbox_rule,
                "name": "zia_delete_sandbox_rule",
                "description": "Delete a ZIA Sandbox rule (destructive operation)",
            },
            # Time Intervals
            {
                "func": zia_create_time_interval,
                "name": "zia_create_time_interval",
                "description": "Create a new ZIA Time Interval (reusable schedule referenced by policy rules via the time_windows field). start_time/end_time are minutes from midnight (0-1439). days_of_week accepts EVERYDAY, SUN, MON, TUE, WED, THU, FRI, SAT.",
            },
            {
                "func": zia_update_time_interval,
                "name": "zia_update_time_interval",
                "description": "Update an existing ZIA Time Interval (write operation). Update is a PUT — name, start_time, end_time, and days_of_week are silently backfilled from the existing record when not supplied.",
            },
            {
                "func": zia_delete_time_interval,
                "name": "zia_delete_time_interval",
                "description": "Delete a ZIA Time Interval (destructive operation). Will fail if the Time Interval is currently referenced by any policy rule.",
            },
        ]

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register ZIA tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(f"ZIA Service: Registered {read_count} read tools, {write_count} write tools")


class ZTWService(BaseService):
    """Zscaler Cloud & Branch Connector (ZTW) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import verb-based ZTW tools
        from .tools.ztw.account_details import ztw_list_public_account_details
        from .tools.ztw.discovery_service import ztw_get_discovery_settings
        from .tools.ztw.ip_destination_groups import (
            ztw_create_ip_destination_group,
            ztw_delete_ip_destination_group,
            ztw_list_ip_destination_groups,
            ztw_list_ip_destination_groups_lite,
        )
        from .tools.ztw.ip_groups import (
            ztw_create_ip_group,
            ztw_delete_ip_group,
            ztw_list_ip_groups,
            ztw_list_ip_groups_lite,
        )
        from .tools.ztw.ip_source_groups import (
            ztw_create_ip_source_group,
            ztw_delete_ip_source_group,
            ztw_list_ip_source_groups,
            ztw_list_ip_source_groups_lite,
        )
        from .tools.ztw.list_admins import ztw_list_admins
        from .tools.ztw.list_roles import ztw_list_roles
        from .tools.ztw.network_service_groups import ztw_list_network_service_groups
        from .tools.ztw.network_services import ztw_list_network_services
        from .tools.ztw.public_cloud_info import ztw_list_public_cloud_info

        # Read-only tools
        self.read_tools = [
            {
                "func": ztw_list_ip_destination_groups,
                "name": "ztw_list_ip_destination_groups",
                "description": "List ZTW IP destination groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_ip_destination_groups_lite,
                "name": "ztw_list_ip_destination_groups_lite",
                "description": "List ZTW IP destination groups in lite format (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_ip_groups,
                "name": "ztw_list_ip_groups",
                "description": "List ZTW IP groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_ip_groups_lite,
                "name": "ztw_list_ip_groups_lite",
                "description": "List ZTW IP groups in lite format (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_ip_source_groups,
                "name": "ztw_list_ip_source_groups",
                "description": "List ZTW IP source groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_ip_source_groups_lite,
                "name": "ztw_list_ip_source_groups_lite",
                "description": "List ZTW IP source groups in lite format (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_network_service_groups,
                "name": "ztw_list_network_service_groups",
                "description": "List ZTW network service groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_roles,
                "name": "ztw_list_roles",
                "description": "List all existing admin roles in ZTW (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_admins,
                "name": "ztw_list_admins",
                "description": "List all existing admin users in ZTW (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_public_cloud_info,
                "name": "ztw_list_public_cloud_info",
                "description": "List ZTW public cloud accounts with metadata (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_network_services,
                "name": "ztw_list_network_services",
                "description": "List ZTW network services (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_list_public_account_details,
                "name": "ztw_list_public_account_details",
                "description": "List detailed ZTW public cloud account information (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": ztw_get_discovery_settings,
                "name": "ztw_get_discovery_settings",
                "description": "Get ZTW workload discovery service settings (read-only)",
            },
        ]

        # Write tools
        self.write_tools = [
            {
                "func": ztw_create_ip_destination_group,
                "name": "ztw_create_ip_destination_group",
                "description": "Create a new ZTW IP destination group (write operation)",
            },
            {
                "func": ztw_delete_ip_destination_group,
                "name": "ztw_delete_ip_destination_group",
                "description": "Delete a ZTW IP destination group (destructive operation)",
            },
            {
                "func": ztw_create_ip_group,
                "name": "ztw_create_ip_group",
                "description": "Create a new ZTW IP group (write operation)",
            },
            {
                "func": ztw_delete_ip_group,
                "name": "ztw_delete_ip_group",
                "description": "Delete a ZTW IP group (destructive operation)",
            },
            {
                "func": ztw_create_ip_source_group,
                "name": "ztw_create_ip_source_group",
                "description": "Create a new ZTW IP source group (write operation)",
            },
            {
                "func": ztw_delete_ip_source_group,
                "name": "ztw_delete_ip_source_group",
                "description": "Delete a ZTW IP source group (destructive operation)",
            },
        ]

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register ZTW tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(f"ZTW Service: Registered {read_count} read tools, {write_count} write tools")


class ZIDService(BaseService):
    """Zscaler ZIdentity service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import verb-based ZIdentity tools
        from .tools.zid.groups import (
            zid_get_group,
            zid_get_group_users,
            zid_get_group_users_by_name,
            zid_list_groups,
            zid_search_groups,
        )
        from .tools.zid.users import (
            zid_get_user,
            zid_get_user_groups,
            zid_get_user_groups_by_name,
            zid_list_users,
            zid_search_users,
        )

        # All ZIdentity tools are read-only
        self.read_tools = [
            {
                "func": zid_list_groups,
                "name": "zid_list_groups",
                "description": "List ZIdentity groups (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zid_get_group,
                "name": "zid_get_group",
                "description": "Get a specific ZIdentity group by ID (read-only)",
            },
            {
                "func": zid_search_groups,
                "name": "zid_search_groups",
                "description": "Search ZIdentity groups (read-only)",
            },
            {
                "func": zid_get_group_users,
                "name": "zid_get_group_users",
                "description": "Get users in a ZIdentity group (read-only)",
            },
            {
                "func": zid_get_group_users_by_name,
                "name": "zid_get_group_users_by_name",
                "description": "Get users in a ZIdentity group by group name (read-only)",
            },
            {
                "func": zid_list_users,
                "name": "zid_list_users",
                "description": "List ZIdentity users (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zid_get_user,
                "name": "zid_get_user",
                "description": "Get a specific ZIdentity user by ID (read-only)",
            },
            {
                "func": zid_search_users,
                "name": "zid_search_users",
                "description": "Search ZIdentity users (read-only)",
            },
            {
                "func": zid_get_user_groups,
                "name": "zid_get_user_groups",
                "description": "Get groups for a ZIdentity user (read-only)",
            },
            {
                "func": zid_get_user_groups_by_name,
                "name": "zid_get_user_groups_by_name",
                "description": "Get groups for a ZIdentity user by username (read-only)",
            },
        ]

        self.write_tools = []  # ZIdentity has no write operations

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register ZIdentity tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations (all read-only)
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(
            f"ZIdentity Service: Registered {read_count} read tools, {write_count} write tools"
        )


class ZEASMService(BaseService):
    """Zscaler External Attack Surface Management (EASM) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import EASM tools
        from .tools.easm.findings import (
            zeasm_get_finding_details,
            zeasm_get_finding_evidence,
            zeasm_get_finding_scan_output,
            zeasm_list_findings,
        )
        from .tools.easm.lookalike_domains import (
            zeasm_get_lookalike_domain,
            zeasm_list_lookalike_domains,
        )
        from .tools.easm.organizations import zeasm_list_organizations

        # All EASM tools are read-only
        self.read_tools = [
            # Organizations
            {
                "func": zeasm_list_organizations,
                "name": "zeasm_list_organizations",
                "description": "List all EASM organizations configured for the tenant (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            # Findings
            {
                "func": zeasm_list_findings,
                "name": "zeasm_list_findings",
                "description": "List all EASM findings for an organization (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zeasm_get_finding_details,
                "name": "zeasm_get_finding_details",
                "description": "Get details for a specific EASM finding (read-only)",
            },
            {
                "func": zeasm_get_finding_evidence,
                "name": "zeasm_get_finding_evidence",
                "description": "Get scan evidence for a specific EASM finding (read-only)",
            },
            {
                "func": zeasm_get_finding_scan_output,
                "name": "zeasm_get_finding_scan_output",
                "description": "Get complete scan output for a specific EASM finding (read-only)",
            },
            # Lookalike Domains
            {
                "func": zeasm_list_lookalike_domains,
                "name": "zeasm_list_lookalike_domains",
                "description": "List all lookalike domains detected for an organization (read-only) Supports JMESPath client-side filtering via the query parameter.",
            },
            {
                "func": zeasm_get_lookalike_domain,
                "name": "zeasm_get_lookalike_domain",
                "description": "Get details for a specific lookalike domain (read-only)",
            },
        ]

        self.write_tools = []  # EASM has no write operations

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register EASM tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register read-only tools
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(f"EASM Service: Registered {read_count} read tools, {write_count} write tools")


class ZINSService(BaseService):
    """Zscaler Z-Insights Analytics service.

    Provides analytics and reporting capabilities through the Z-Insights GraphQL API.
    All tools in this service are read-only operations.

    Available domains in Z-Insights API:
    - WEB_TRAFFIC: Web traffic analytics and threat data
    - CYBER_SECURITY: Cybersecurity incidents and threat analysis
    - ZERO_TRUST_FIREWALL: Firewall activity and rule analytics
    - SAAS_SECURITY: Cloud Access Security Broker (CASB) data
    - SHADOW_IT: Unsanctioned application discovery
    - IOT: IoT device visibility and statistics
    """

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import Z-Insights Web Traffic tools
        # Import Z-Insights Cyber Security tools
        from .tools.zins.cyber_security import (
            zins_get_cyber_incidents,
            zins_get_cyber_incidents_by_location,
            zins_get_cyber_incidents_by_threat_and_app,
            zins_get_cyber_incidents_daily,
        )

        # Import Z-Insights Firewall tools
        from .tools.zins.firewall import (
            zins_get_firewall_by_action,
            zins_get_firewall_by_location,
            zins_get_firewall_network_services,
        )

        # Import Z-Insights IoT tools
        from .tools.zins.iot import (
            zins_get_iot_device_stats,
        )

        # Import Z-Insights SaaS Security / CASB tools
        from .tools.zins.saas_security import (
            zins_get_casb_app_report,
        )

        # Import Z-Insights Shadow IT tools
        from .tools.zins.shadow_it import (
            zins_get_shadow_it_apps,
            zins_get_shadow_it_summary,
        )
        from .tools.zins.web_traffic import (
            zins_get_threat_class,
            zins_get_threat_super_categories,
            zins_get_web_protocols,
            zins_get_web_traffic_by_location,
            zins_get_web_traffic_no_grouping,
        )

        # All Z-Insights tools are read-only (analytics)
        # NOTE: Tool descriptions are critical for AI tool selection - be explicit about use cases
        self.read_tools = [
            # Web Traffic Analytics
            {
                "func": zins_get_web_traffic_by_location,
                "name": "zins_get_web_traffic_by_location",
                "description": (
                    "Provides web traffic analytics grouped by location, including traffic volume, "
                    "bandwidth usage, and office traffic comparisons."
                ),
            },
            {
                "func": zins_get_web_traffic_no_grouping,
                "name": "zins_get_web_traffic_no_grouping",
                "description": (
                    "Provides total web traffic volume metrics without grouping, including "
                    "aggregate bandwidth and overall web usage statistics."
                ),
            },
            {
                "func": zins_get_web_protocols,
                "name": "zins_get_web_protocols",
                "description": (
                    "Provides web protocol distribution analytics (HTTP, HTTPS, SSL), "
                    "including protocol usage and HTTPS adoption metrics."
                ),
            },
            {
                "func": zins_get_threat_super_categories,
                "name": "zins_get_threat_super_categories",
                "description": (
                    "Provides threat super-category analytics including malware, phishing, spyware, "
                    "and other threat types detected across the tenant."
                ),
            },
            {
                "func": zins_get_threat_class,
                "name": "zins_get_threat_class",
                "description": (
                    "Provides detailed threat classification analytics including virus, trojan, "
                    "ransomware, and other malware type breakdowns."
                ),
            },
            # Cyber Security Analytics
            {
                "func": zins_get_cyber_incidents,
                "name": "zins_get_cyber_incidents",
                "description": (
                    "Provides cybersecurity incidents grouped by category, including "
                    "security events, cyber attacks, and incident breakdowns."
                ),
            },
            {
                "func": zins_get_cyber_incidents_by_location,
                "name": "zins_get_cyber_incidents_by_location",
                "description": (
                    "Provides cybersecurity incidents grouped by location, showing "
                    "incident distribution across offices and sites."
                ),
            },
            {
                "func": zins_get_cyber_incidents_daily,
                "name": "zins_get_cyber_incidents_daily",
                "description": (
                    "Provides daily cybersecurity incident trends, showing "
                    "incident patterns and security statistics over time."
                ),
            },
            {
                "func": zins_get_cyber_incidents_by_threat_and_app,
                "name": "zins_get_cyber_incidents_by_threat_and_app",
                "description": (
                    "Provides cybersecurity incidents correlated by threat type and application, "
                    "showing which apps are targeted and threat-application relationships."
                ),
            },
            # Firewall Analytics
            {
                "func": zins_get_firewall_by_action,
                "name": "zins_get_firewall_by_action",
                "description": (
                    "Provides Zero Trust Firewall traffic analytics by action (allow/block), "
                    "including blocked traffic volume and firewall policy effectiveness."
                ),
            },
            {
                "func": zins_get_firewall_by_location,
                "name": "zins_get_firewall_by_location",
                "description": (
                    "Provides Zero Trust Firewall traffic analytics grouped by location, "
                    "including firewall activity by office and branch."
                ),
            },
            {
                "func": zins_get_firewall_network_services,
                "name": "zins_get_firewall_network_services",
                "description": (
                    "Provides firewall network service usage analytics, including "
                    "port usage, protocol activity, and service breakdowns."
                ),
            },
            # SaaS Security / CASB Analytics
            {
                "func": zins_get_casb_app_report,
                "name": "zins_get_casb_app_report",
                "description": (
                    "Provides CASB SaaS application usage analytics, including "
                    "cloud app usage and cloud service adoption metrics."
                ),
            },
            # Shadow IT Analytics
            {
                "func": zins_get_shadow_it_apps,
                "name": "zins_get_shadow_it_apps",
                "description": (
                    "Provides discovered shadow IT applications with risk scores, "
                    "including unsanctioned and unauthorized application detection."
                ),
            },
            {
                "func": zins_get_shadow_it_summary,
                "name": "zins_get_shadow_it_summary",
                "description": (
                    "Provides shadow IT summary statistics, including total shadow apps, "
                    "app categories, and risk distribution overview."
                ),
            },
            # IoT Analytics
            {
                "func": zins_get_iot_device_stats,
                "name": "zins_get_iot_device_stats",
                "description": (
                    "Provides IoT device statistics and classifications, including "
                    "device inventory, connected device types, and unmanaged devices."
                ),
            },
        ]

        # Z-Insights is analytics-only - no write operations
        self.write_tools = []

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register Z-Insights tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register read-only tools
        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(
            f"Z-Insights Service: Registered {read_count} read tools, {write_count} write tools"
        )


class ZMSService(BaseService):
    """Zscaler Microsegmentation (ZMS) service.

    Provides read-only tools for managing and inspecting microsegmentation
    deployments through the ZMS GraphQL API.

    Available domains in the ZMS API:
    - AGENTS: Agent inventory, connection status, and version statistics
    - AGENT_GROUPS: Agent group management and TOTP secrets
    - RESOURCES: Workload inventory and protection status
    - RESOURCE_GROUPS: Resource group membership and protection status
    - POLICY_RULES: Microsegmentation policy rules and defaults
    - APP_ZONES: Application zone definitions
    - APP_CATALOG: Discovered application catalog
    - NONCES: Provisioning key management
    - TAGS: Tag namespace, key, and value hierarchy
    """

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)

        from .tools.zms.agent_groups import (
            zms_get_agent_group_totp_secrets,
            zms_list_agent_groups,
        )
        from .tools.zms.agents import (
            zms_get_agent_connection_status_statistics,
            zms_get_agent_version_statistics,
            zms_list_agents,
        )
        from .tools.zms.app_catalog import zms_list_app_catalog
        from .tools.zms.app_zones import zms_list_app_zones
        from .tools.zms.nonces import (
            zms_get_nonce,
            zms_list_nonces,
        )
        from .tools.zms.policy_rules import (
            zms_list_default_policy_rules,
            zms_list_policy_rules,
        )
        from .tools.zms.resource_groups import (
            zms_get_resource_group_members,
            zms_get_resource_group_protection_status,
            zms_list_resource_groups,
        )
        from .tools.zms.resources import (
            zms_get_metadata,
            zms_get_resource_protection_status,
            zms_list_resources,
        )
        from .tools.zms.tags import (
            zms_list_tag_keys,
            zms_list_tag_namespaces,
            zms_list_tag_values,
        )

        self.read_tools = [
            # Agents
            {
                "func": zms_list_agents,
                "name": "zms_list_agents",
                "description": (
                    "List Zscaler Microsegmentation agents with pagination and search. "
                    "Returns agent name, connection status, OS, version, IPs, and group membership. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_get_agent_connection_status_statistics,
                "name": "zms_get_agent_connection_status_statistics",
                "description": (
                    "Get aggregated connection status statistics for ZMS agents. "
                    "Returns connected/disconnected counts and percentages."
                ),
            },
            {
                "func": zms_get_agent_version_statistics,
                "name": "zms_get_agent_version_statistics",
                "description": (
                    "Get aggregated version statistics for ZMS agents. "
                    "Returns software version distribution across the agent fleet."
                ),
            },
            # Agent Groups
            {
                "func": zms_list_agent_groups,
                "name": "zms_list_agent_groups",
                "description": (
                    "List ZMS agent groups with pagination and search. "
                    "Returns group name, type, agent count, policy status, and upgrade settings. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_get_agent_group_totp_secrets,
                "name": "zms_get_agent_group_totp_secrets",
                "description": (
                    "Get TOTP secrets for a specific ZMS agent group. "
                    "Returns TOTP secret, QR code, and generation timestamp for agent enrollment."
                ),
            },
            # Resources
            {
                "func": zms_list_resources,
                "name": "zms_list_resources",
                "description": (
                    "List ZMS resources (workloads) with pagination and filtering. "
                    "Filter by name, status, resource_type, cloud_provider, cloud_region, or platform_os. "
                    "Returns resource type, status, cloud provider, region, hostname, OS, IPs, and app zones. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_get_resource_protection_status,
                "name": "zms_get_resource_protection_status",
                "description": (
                    "Get protection status summary for ZMS resources. "
                    "Returns protected/unprotected counts and protection coverage percentage."
                ),
            },
            {
                "func": zms_get_metadata,
                "name": "zms_get_metadata",
                "description": (
                    "Get event metadata for ZMS resources. "
                    "Returns metadata about available resource events."
                ),
            },
            # Resource Groups
            {
                "func": zms_list_resource_groups,
                "name": "zms_list_resource_groups",
                "description": (
                    "List ZMS resource groups with pagination and filtering. "
                    "Filter by name or resource_hostname. "
                    "Returns managed and unmanaged groups with member counts, CIDRs, and FQDNs. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_get_resource_group_members,
                "name": "zms_get_resource_group_members",
                "description": (
                    "Get members of a specific ZMS resource group. "
                    "Returns workloads in the group with resource type, status, cloud info, and OS."
                ),
            },
            {
                "func": zms_get_resource_group_protection_status,
                "name": "zms_get_resource_group_protection_status",
                "description": (
                    "Get protection status summary for ZMS resource groups. "
                    "Returns protected/unprotected group counts and coverage percentage."
                ),
            },
            # Policy Rules
            {
                "func": zms_list_policy_rules,
                "name": "zms_list_policy_rules",
                "description": (
                    "List ZMS microsegmentation policy rules with pagination and filtering. "
                    "Filter by name or action (ALLOW/BLOCK). "
                    "Returns rule name, action, priority, source/destination targets, and port/protocol specs. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_list_default_policy_rules,
                "name": "zms_list_default_policy_rules",
                "description": (
                    "List default microsegmentation policy rules. "
                    "Returns system-defined baseline rules with action, direction, and scope type. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            # App Zones
            {
                "func": zms_list_app_zones,
                "name": "zms_list_app_zones",
                "description": (
                    "List ZMS app zones with pagination and filtering. "
                    "Filter by name and sort by zone name. "
                    "Returns zone name, description, member count, and VPC/subnet settings. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            # App Catalog
            {
                "func": zms_list_app_catalog,
                "name": "zms_list_app_catalog",
                "description": (
                    "List ZMS application catalog entries with pagination and filtering. "
                    "Filter by name or category. Sort by name, category, creation_time, or modified_time. "
                    "Returns discovered apps with name, category, port/protocol specs, and processes. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            # Nonces (Provisioning Keys)
            {
                "func": zms_list_nonces,
                "name": "zms_list_nonces",
                "description": (
                    "List ZMS nonces (provisioning keys) with pagination and search. "
                    "Returns key name, value, max usage, current usage, and agent group association. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_get_nonce,
                "name": "zms_get_nonce",
                "description": (
                    "Get a specific ZMS nonce (provisioning key) by eyez ID. "
                    "Returns detailed key information including usage counts."
                ),
            },
            # Tags
            {
                "func": zms_list_tag_namespaces,
                "name": "zms_list_tag_namespaces",
                "description": (
                    "List ZMS tag namespaces with pagination and filtering. "
                    "Filter by name or origin (CUSTOM, EXTERNAL, ML, UNKNOWN). "
                    "Returns namespace name, description, and origin. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_list_tag_keys,
                "name": "zms_list_tag_keys",
                "description": (
                    "List tag keys within a ZMS tag namespace with filtering. "
                    "Filter by key_name. Returns tag key name and description. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
            {
                "func": zms_list_tag_values,
                "name": "zms_list_tag_values",
                "description": (
                    "List tag values for a specific ZMS tag key with filtering. "
                    "Filter by value name. Returns available values for filtering resources. "
                    "Supports JMESPath client-side filtering via the query parameter."
                ),
            },
        ]

        # ZMS tools are read-only (query-only GraphQL API)
        self.write_tools = []

    def register_tools(
        self, server, enabled_tools=None, enable_write_tools=False, write_tools=None, disabled_tools=None,
        selected_toolsets=None,
    ):
        """Register ZMS tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        read_count = register_read_tools(server, self.read_tools, enabled_tools, disabled_tools=disabled_tools, selected_toolsets=selected_toolsets)
        write_count = register_write_tools(
            server, self.write_tools, enabled_tools, enable_write_tools, write_tools,
            disabled_tools=disabled_tools, selected_toolsets=selected_toolsets,
        )

        logger.info(
            f"ZMS Service: Registered {read_count} read tools, {write_count} write tools"
        )


# Service registry
_AVAILABLE_SERVICES = {
    "zcc": ZCCService,
    "zdx": ZDXService,
    "zpa": ZPAService,
    "zia": ZIAService,
    "ztw": ZTWService,
    "zid": ZIDService,
    "zeasm": ZEASMService,
    "zins": ZINSService,
    "zms": ZMSService,
}


def get_service_names():
    """Get the names of all available services.

    Returns:
        List[str]: List of available service names
    """
    return list(_AVAILABLE_SERVICES.keys())


def get_available_services():
    """Get all available services.

    Returns:
        Dict[str, Type]: Dictionary mapping service names to service classes
    """
    return _AVAILABLE_SERVICES.copy()
