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
            zscaler_client: The Zscaler client instance (can be None in legacy mode)
        """
        self.zscaler_client = zscaler_client
        self.tools = []  # Kept for backward compatibility during migration
        self.read_tools = []  # NEW: Read-only tools (with annotations)
        self.write_tools = []  # NEW: Write tools (with annotations)
        self.resources = []

    @abstractmethod
    def register_tools(self, server, enabled_tools=None, enable_write_tools=False, write_tools=None):
        """Register tools with the MCP server.

        Args:
            server: The MCP server instance
            enabled_tools: Set of enabled tool names (if None, all tools are enabled)
            enable_write_tools: Whether to enable write tools (default: False)
            write_tools: Explicit allowlist of write tools (supports wildcards). Requires enable_write_tools=True.
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
        from .tools.zcc.download_devices import zcc_devices_csv_exporter
        from .tools.zcc.list_devices import zcc_list_devices
        from .tools.zcc.list_forwarding_profiles import zcc_list_forwarding_profiles
        from .tools.zcc.list_trusted_networks import zcc_list_trusted_networks

        # All ZCC tools are read-only
        self.read_tools = [
            {"func": zcc_list_devices, "name": "zcc_list_devices", "description": "Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal (read-only)"},
            {"func": zcc_devices_csv_exporter, "name": "zcc_devices_csv_exporter", "description": "Downloads ZCC device information or service status as a CSV file (read-only)"},
            {"func": zcc_list_trusted_networks, "name": "zcc_list_trusted_networks", "description": "Returns the list of Trusted Networks By Company ID in the Client Connector Portal (read-only)"},
            {"func": zcc_list_forwarding_profiles, "name": "zcc_list_forwarding_profiles", "description": "Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal (read-only)"},
        ]

        self.write_tools = []  # ZCC has no write operations

    def register_tools(self, server, enabled_tools=None, enable_write_tools=False, write_tools=None):
        """Register ZCC tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations (all read-only)
        read_count = register_read_tools(server, self.read_tools, enabled_tools)
        write_count = register_write_tools(server, self.write_tools, enabled_tools, enable_write_tools, write_tools)

        logger.info(f"ZCC Service: Registered {read_count} read tools, {write_count} write tools")


class ZDXService(BaseService):
    """Zscaler Digital Experience (ZDX) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import verb-based ZDX tools (all read-only)
        from .tools.zdx.active_devices import zdx_get_device, zdx_list_devices
        from .tools.zdx.administration import zdx_list_departments, zdx_list_locations
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

        # All ZDX tools are read-only
        self.read_tools = [
            {"func": zdx_list_devices, "name": "zdx_list_devices", "description": "List ZDX devices with optional filtering (read-only)"},
            {"func": zdx_get_device, "name": "zdx_get_device", "description": "Get a specific ZDX device by ID (read-only)"},
            {"func": zdx_list_departments, "name": "zdx_list_departments", "description": "List ZDX departments (read-only)"},
            {"func": zdx_list_locations, "name": "zdx_list_locations", "description": "List ZDX locations (read-only)"},
            {"func": zdx_get_application_metric, "name": "zdx_get_application_metric", "description": "Get ZDX metrics for a specified application (read-only)"},
            {"func": zdx_get_application, "name": "zdx_get_application", "description": "Get ZDX application details (read-only)"},
            {"func": zdx_get_application_score_trend, "name": "zdx_get_application_score_trend", "description": "Get ZDX application score trend (read-only)"},
            {"func": zdx_list_application_users, "name": "zdx_list_application_users", "description": "List users for a ZDX application (read-only)"},
            {"func": zdx_get_application_user, "name": "zdx_get_application_user", "description": "Get a specific ZDX application user (read-only)"},
            {"func": zdx_list_alerts, "name": "zdx_list_alerts", "description": "List ZDX alerts (read-only)"},
            {"func": zdx_get_alert, "name": "zdx_get_alert", "description": "Get a specific ZDX alert by ID (read-only)"},
            {"func": zdx_list_alert_affected_devices, "name": "zdx_list_alert_affected_devices", "description": "List devices affected by a ZDX alert (read-only)"},
            {"func": zdx_list_applications, "name": "zdx_list_applications", "description": "List ZDX applications (read-only)"},
            {"func": zdx_list_device_deep_traces, "name": "zdx_list_device_deep_traces", "description": "List ZDX deep traces for a device (read-only)"},
            {"func": zdx_get_device_deep_trace, "name": "zdx_get_device_deep_trace", "description": "Get a specific ZDX deep trace by ID (read-only)"},
            {"func": zdx_list_historical_alerts, "name": "zdx_list_historical_alerts", "description": "List ZDX historical alerts (read-only)"},
            {"func": zdx_list_software, "name": "zdx_list_software", "description": "List ZDX software inventory (read-only)"},
            {"func": zdx_get_software_details, "name": "zdx_get_software_details", "description": "Get details for specific ZDX software (read-only)"},
        ]

        self.write_tools = []  # ZDX has no write operations

    def register_tools(self, server, enabled_tools=None, enable_write_tools=False, write_tools=None):
        """Register ZDX tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations (all read-only)
        read_count = register_read_tools(server, self.read_tools, enabled_tools)
        write_count = register_write_tools(server, self.write_tools, enabled_tools, enable_write_tools, write_tools)

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
            {"func": zpa_list_application_segments, "name": "zpa_list_application_segments", "description": "List ZPA application segments with optional filtering (read-only)"},
            {"func": zpa_get_application_segment, "name": "zpa_get_application_segment", "description": "Get a specific ZPA application segment by ID (read-only)"},
            {"func": zpa_list_app_connector_groups, "name": "zpa_list_app_connector_groups", "description": "List ZPA app connector groups (read-only)"},
            {"func": zpa_get_app_connector_group, "name": "zpa_get_app_connector_group", "description": "Get a specific ZPA app connector group by ID (read-only)"},
            {"func": zpa_list_server_groups, "name": "zpa_list_server_groups", "description": "List ZPA server groups (read-only)"},
            {"func": zpa_get_server_group, "name": "zpa_get_server_group", "description": "Get a specific ZPA server group by ID (read-only)"},
            {"func": zpa_list_segment_groups, "name": "zpa_list_segment_groups", "description": "List ZPA segment groups (read-only)"},
            {"func": zpa_get_segment_group, "name": "zpa_get_segment_group", "description": "Get a specific ZPA segment group by ID (read-only)"},
            {"func": zpa_list_application_servers, "name": "zpa_list_application_servers", "description": "List ZPA application servers (read-only)"},
            {"func": zpa_get_application_server, "name": "zpa_get_application_server", "description": "Get a specific ZPA application server by ID (read-only)"},
            {"func": zpa_list_service_edge_groups, "name": "zpa_list_service_edge_groups", "description": "List ZPA service edge groups (read-only)"},
            {"func": zpa_get_service_edge_group, "name": "zpa_get_service_edge_group", "description": "Get a specific ZPA service edge group by ID (read-only)"},
            {"func": zpa_list_ba_certificates, "name": "zpa_list_ba_certificates", "description": "List ZPA browser access certificates (read-only)"},
            {"func": zpa_get_ba_certificate, "name": "zpa_get_ba_certificate", "description": "Get a specific ZPA browser access certificate by ID (read-only)"},
            {"func": zpa_list_access_policy_rules, "name": "zpa_list_access_policy_rules", "description": "List ZPA access policy rules (read-only)"},
            {"func": zpa_get_access_policy_rule, "name": "zpa_get_access_policy_rule", "description": "Get a specific ZPA access policy rule by ID (read-only)"},
            {"func": zpa_list_forwarding_policy_rules, "name": "zpa_list_forwarding_policy_rules", "description": "List ZPA forwarding policy rules (read-only)"},
            {"func": zpa_get_forwarding_policy_rule, "name": "zpa_get_forwarding_policy_rule", "description": "Get a specific ZPA forwarding policy rule by ID (read-only)"},
            {"func": zpa_list_timeout_policy_rules, "name": "zpa_list_timeout_policy_rules", "description": "List ZPA timeout policy rules (read-only)"},
            {"func": zpa_get_timeout_policy_rule, "name": "zpa_get_timeout_policy_rule", "description": "Get a specific ZPA timeout policy rule by ID (read-only)"},
            {"func": zpa_list_isolation_policy_rules, "name": "zpa_list_isolation_policy_rules", "description": "List ZPA isolation policy rules (read-only)"},
            {"func": zpa_get_isolation_policy_rule, "name": "zpa_get_isolation_policy_rule", "description": "Get a specific ZPA isolation policy rule by ID (read-only)"},
            {"func": zpa_list_app_protection_rules, "name": "zpa_list_app_protection_rules", "description": "List ZPA app protection rules (read-only)"},
            {"func": zpa_get_app_protection_rule, "name": "zpa_get_app_protection_rule", "description": "Get a specific ZPA app protection rule by ID (read-only)"},
            {"func": zpa_list_provisioning_keys, "name": "zpa_list_provisioning_keys", "description": "List ZPA provisioning keys (read-only)"},
            {"func": zpa_get_provisioning_key, "name": "zpa_get_provisioning_key", "description": "Get a specific ZPA provisioning key by ID (read-only)"},
            {"func": zpa_list_pra_portals, "name": "zpa_list_pra_portals", "description": "List ZPA PRA portals (read-only)"},
            {"func": zpa_get_pra_portal, "name": "zpa_get_pra_portal", "description": "Get a specific ZPA PRA portal by ID (read-only)"},
            {"func": zpa_list_pra_credentials, "name": "zpa_list_pra_credentials", "description": "List ZPA PRA credentials (read-only)"},
            {"func": zpa_get_pra_credential, "name": "zpa_get_pra_credential", "description": "Get a specific ZPA PRA credential by ID (read-only)"},
            # Profile and Certificate Management
            {"func": app_protection_profile_manager, "name": "get_zpa_app_protection_profile", "description": "Manage ZPA App Protection Profiles (Inspection Profiles) (read-only)"},
            {"func": enrollment_certificate_manager, "name": "get_zpa_enrollment_certificate", "description": "Manage ZPA Enrollment Certificates (read-only)"},
            {"func": isolation_profile_manager, "name": "get_zpa_isolation_profile", "description": "Manage ZPA Cloud Browser Isolation (CBI) profiles (read-only)"},
            {"func": posture_profile_manager, "name": "get_zpa_posture_profile", "description": "Manage ZPA Posture Profiles (read-only)"},
            # Identity and Access Management
            {"func": saml_attribute_manager, "name": "get_zpa_saml_attribute", "description": "Manage ZPA SAML Attributes (read-only)"},
            {"func": scim_attribute_manager, "name": "get_zpa_scim_attribute", "description": "Manage ZPA SCIM Attributes (read-only)"},
            {"func": scim_group_manager, "name": "get_zpa_scim_group", "description": "Manage ZPA SCIM Groups (read-only)"},
            # Network and Segment Management
            {"func": app_segments_by_type_manager, "name": "get_zpa_app_segments_by_type", "description": "Manage ZPA application segments by type (read-only)"},
            {"func": trusted_network_manager, "name": "get_zpa_trusted_network", "description": "Manage ZPA Trusted Networks (read-only)"},
        ]

        # Define write tools
        self.write_tools = [
            {"func": zpa_create_application_segment, "name": "zpa_create_application_segment", "description": "Create a new ZPA application segment (write operation)"},
            {"func": zpa_update_application_segment, "name": "zpa_update_application_segment", "description": "Update an existing ZPA application segment (write operation)"},
            {"func": zpa_delete_application_segment, "name": "zpa_delete_application_segment", "description": "Delete a ZPA application segment (destructive operation)"},
            {"func": zpa_create_app_connector_group, "name": "zpa_create_app_connector_group", "description": "Create a new ZPA app connector group (write operation)"},
            {"func": zpa_update_app_connector_group, "name": "zpa_update_app_connector_group", "description": "Update an existing ZPA app connector group (write operation)"},
            {"func": zpa_delete_app_connector_group, "name": "zpa_delete_app_connector_group", "description": "Delete a ZPA app connector group (destructive operation)"},
            {"func": zpa_create_server_group, "name": "zpa_create_server_group", "description": "Create a new ZPA server group (write operation)"},
            {"func": zpa_update_server_group, "name": "zpa_update_server_group", "description": "Update an existing ZPA server group (write operation)"},
            {"func": zpa_delete_server_group, "name": "zpa_delete_server_group", "description": "Delete a ZPA server group (destructive operation)"},
            {"func": zpa_create_segment_group, "name": "zpa_create_segment_group", "description": "Create a new ZPA segment group (write operation)"},
            {"func": zpa_update_segment_group, "name": "zpa_update_segment_group", "description": "Update an existing ZPA segment group (write operation)"},
            {"func": zpa_delete_segment_group, "name": "zpa_delete_segment_group", "description": "Delete a ZPA segment group (destructive operation)"},
            {"func": zpa_create_application_server, "name": "zpa_create_application_server", "description": "Create a new ZPA application server (write operation)"},
            {"func": zpa_update_application_server, "name": "zpa_update_application_server", "description": "Update an existing ZPA application server (write operation)"},
            {"func": zpa_delete_application_server, "name": "zpa_delete_application_server", "description": "Delete a ZPA application server (destructive operation)"},
            {"func": zpa_create_service_edge_group, "name": "zpa_create_service_edge_group", "description": "Create a new ZPA service edge group (write operation)"},
            {"func": zpa_update_service_edge_group, "name": "zpa_update_service_edge_group", "description": "Update an existing ZPA service edge group (write operation)"},
            {"func": zpa_delete_service_edge_group, "name": "zpa_delete_service_edge_group", "description": "Delete a ZPA service edge group (destructive operation)"},
            {"func": zpa_create_ba_certificate, "name": "zpa_create_ba_certificate", "description": "Create a new ZPA browser access certificate (write operation)"},
            {"func": zpa_delete_ba_certificate, "name": "zpa_delete_ba_certificate", "description": "Delete a ZPA browser access certificate (destructive operation)"},
            {"func": zpa_create_access_policy_rule, "name": "zpa_create_access_policy_rule", "description": "Create a new ZPA access policy rule (write operation)"},
            {"func": zpa_update_access_policy_rule, "name": "zpa_update_access_policy_rule", "description": "Update an existing ZPA access policy rule (write operation)"},
            {"func": zpa_delete_access_policy_rule, "name": "zpa_delete_access_policy_rule", "description": "Delete a ZPA access policy rule (destructive operation)"},
            {"func": zpa_create_forwarding_policy_rule, "name": "zpa_create_forwarding_policy_rule", "description": "Create a new ZPA forwarding policy rule (write operation)"},
            {"func": zpa_update_forwarding_policy_rule, "name": "zpa_update_forwarding_policy_rule", "description": "Update an existing ZPA forwarding policy rule (write operation)"},
            {"func": zpa_delete_forwarding_policy_rule, "name": "zpa_delete_forwarding_policy_rule", "description": "Delete a ZPA forwarding policy rule (destructive operation)"},
            {"func": zpa_create_timeout_policy_rule, "name": "zpa_create_timeout_policy_rule", "description": "Create a new ZPA timeout policy rule (write operation)"},
            {"func": zpa_update_timeout_policy_rule, "name": "zpa_update_timeout_policy_rule", "description": "Update an existing ZPA timeout policy rule (write operation)"},
            {"func": zpa_delete_timeout_policy_rule, "name": "zpa_delete_timeout_policy_rule", "description": "Delete a ZPA timeout policy rule (destructive operation)"},
            {"func": zpa_create_isolation_policy_rule, "name": "zpa_create_isolation_policy_rule", "description": "Create a new ZPA isolation policy rule (write operation)"},
            {"func": zpa_update_isolation_policy_rule, "name": "zpa_update_isolation_policy_rule", "description": "Update an existing ZPA isolation policy rule (write operation)"},
            {"func": zpa_delete_isolation_policy_rule, "name": "zpa_delete_isolation_policy_rule", "description": "Delete a ZPA isolation policy rule (destructive operation)"},
            {"func": zpa_create_app_protection_rule, "name": "zpa_create_app_protection_rule", "description": "Create a new ZPA app protection rule (write operation)"},
            {"func": zpa_update_app_protection_rule, "name": "zpa_update_app_protection_rule", "description": "Update an existing ZPA app protection rule (write operation)"},
            {"func": zpa_delete_app_protection_rule, "name": "zpa_delete_app_protection_rule", "description": "Delete a ZPA app protection rule (destructive operation)"},
            {"func": zpa_create_provisioning_key, "name": "zpa_create_provisioning_key", "description": "Create a new ZPA provisioning key (write operation)"},
            {"func": zpa_update_provisioning_key, "name": "zpa_update_provisioning_key", "description": "Update an existing ZPA provisioning key (write operation)"},
            {"func": zpa_delete_provisioning_key, "name": "zpa_delete_provisioning_key", "description": "Delete a ZPA provisioning key (destructive operation)"},
            {"func": zpa_create_pra_portal, "name": "zpa_create_pra_portal", "description": "Create a new ZPA PRA portal (write operation)"},
            {"func": zpa_update_pra_portal, "name": "zpa_update_pra_portal", "description": "Update an existing ZPA PRA portal (write operation)"},
            {"func": zpa_delete_pra_portal, "name": "zpa_delete_pra_portal", "description": "Delete a ZPA PRA portal (destructive operation)"},
            {"func": zpa_create_pra_credential, "name": "zpa_create_pra_credential", "description": "Create a new ZPA PRA credential (write operation)"},
            {"func": zpa_update_pra_credential, "name": "zpa_update_pra_credential", "description": "Update an existing ZPA PRA credential (write operation)"},
            {"func": zpa_delete_pra_credential, "name": "zpa_delete_pra_credential", "description": "Delete a ZPA PRA credential (destructive operation)"},
        ]

    def register_tools(self, server, enabled_tools=None, enable_write_tools=False, write_tools=None):
        """Register ZPA tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations
        read_count = register_read_tools(server, self.read_tools, enabled_tools)
        write_count = register_write_tools(server, self.write_tools, enabled_tools, enable_write_tools, write_tools)

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
        from .tools.zia.cloud_applications import (
            zia_bulk_update_cloud_applications,
            zia_list_cloud_application_custom_tags,
            zia_list_cloud_applications,
        )
        from .tools.zia.cloud_firewall_rules import (
            zia_create_cloud_firewall_rule,
            zia_delete_cloud_firewall_rule,
            zia_get_cloud_firewall_rule,
            zia_list_cloud_firewall_rules,
            zia_update_cloud_firewall_rule,
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
        from .tools.zia.rule_labels import (
            zia_create_rule_label,
            zia_delete_rule_label,
            zia_get_rule_label,
            zia_list_rule_labels,
            zia_update_rule_label,
        )
        from .tools.zia.static_ips import (
            zia_create_static_ip,
            zia_delete_static_ip,
            zia_get_static_ip,
            zia_list_static_ips,
            zia_update_static_ip,
        )
        from .tools.zia.url_categories import (
            zia_add_urls_to_category,
            zia_create_url_category,
            zia_delete_url_category,
            zia_get_url_category,
            zia_list_url_categories,
            zia_remove_urls_from_category,
            zia_update_url_category,
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

        # Read-only tools
        self.read_tools = [
            # Cloud Firewall Rules
            {"func": zia_list_cloud_firewall_rules, "name": "zia_list_cloud_firewall_rules", "description": "List ZIA cloud firewall rules with optional filtering (read-only)"},
            {"func": zia_get_cloud_firewall_rule, "name": "zia_get_cloud_firewall_rule", "description": "Get a specific ZIA cloud firewall rule by ID (read-only)"},
            # URL Filtering Rules
            {"func": zia_list_url_filtering_rules, "name": "zia_list_url_filtering_rules", "description": "List ZIA URL filtering rules (read-only)"},
            {"func": zia_get_url_filtering_rule, "name": "zia_get_url_filtering_rule", "description": "Get a specific ZIA URL filtering rule by ID (read-only)"},
            # Web DLP Rules
            {"func": zia_list_web_dlp_rules, "name": "zia_list_web_dlp_rules", "description": "List ZIA web DLP rules (read-only)"},
            {"func": zia_list_web_dlp_rules_lite, "name": "zia_list_web_dlp_rules_lite", "description": "List ZIA web DLP rules in lite format (read-only)"},
            {"func": zia_get_web_dlp_rule, "name": "zia_get_web_dlp_rule", "description": "Get a specific ZIA web DLP rule by ID (read-only)"},
            # DLP Dictionaries
            {"func": zia_dlp_dictionary_manager, "name": "get_zia_dlp_dictionaries", "description": "Manage ZIA DLP dictionaries for data loss prevention pattern and phrase matching (read-only)"},
            # DLP Engines
            {"func": zia_dlp_engine_manager, "name": "get_zia_dlp_engines", "description": "Manage ZIA DLP engines for data loss prevention rule processing (read-only)"},
            # User Management
            {"func": zia_user_department_manager, "name": "get_zia_user_departments", "description": "Manage ZIA user departments for organizational structure (read-only)"},
            {"func": zia_user_group_manager, "name": "get_zia_user_groups", "description": "Manage ZIA user groups for access control and policy assignment (read-only)"},
            {"func": zia_users_manager, "name": "get_zia_users", "description": "Manage ZIA users for authentication and access control (read-only)"},
            # IP Source Groups
            {"func": zia_list_ip_source_groups, "name": "zia_list_ip_source_groups", "description": "List ZIA IP source groups (read-only)"},
            {"func": zia_get_ip_source_group, "name": "zia_get_ip_source_group", "description": "Get a specific ZIA IP source group by ID (read-only)"},
            # IP Destination Groups
            {"func": zia_list_ip_destination_groups, "name": "zia_list_ip_destination_groups", "description": "List ZIA IP destination groups (read-only)"},
            {"func": zia_get_ip_destination_group, "name": "zia_get_ip_destination_group", "description": "Get a specific ZIA IP destination group by ID (read-only)"},
            # Network App Groups
            {"func": zia_list_network_app_groups, "name": "zia_list_network_app_groups", "description": "List ZIA network application groups (read-only)"},
            {"func": zia_get_network_app_group, "name": "zia_get_network_app_group", "description": "Get a specific ZIA network application group by ID (read-only)"},
            # URL Categories
            {"func": zia_list_url_categories, "name": "zia_list_url_categories", "description": "List ZIA URL categories (read-only)"},
            {"func": zia_get_url_category, "name": "zia_get_url_category", "description": "Get a specific ZIA URL category by ID (read-only)"},
            # Rule Labels
            {"func": zia_list_rule_labels, "name": "zia_list_rule_labels", "description": "List ZIA rule labels (read-only)"},
            {"func": zia_get_rule_label, "name": "zia_get_rule_label", "description": "Get a specific ZIA rule label by ID (read-only)"},
            # Locations
            {"func": zia_list_locations, "name": "zia_list_locations", "description": "List ZIA locations (read-only)"},
            {"func": zia_get_location, "name": "zia_get_location", "description": "Get a specific ZIA location by ID (read-only)"},
            # VPN Credentials
            {"func": zia_list_vpn_credentials, "name": "zia_list_vpn_credentials", "description": "List ZIA VPN credentials (read-only)"},
            {"func": zia_get_vpn_credential, "name": "zia_get_vpn_credential", "description": "Get a specific ZIA VPN credential by ID (read-only)"},
            # Static IPs
            {"func": zia_list_static_ips, "name": "zia_list_static_ips", "description": "List ZIA static IPs (read-only)"},
            {"func": zia_get_static_ip, "name": "zia_get_static_ip", "description": "Get a specific ZIA static IP by ID (read-only)"},
            # GRE Tunnels
            {"func": zia_list_gre_tunnels, "name": "zia_list_gre_tunnels", "description": "List ZIA GRE tunnels (read-only)"},
            {"func": zia_get_gre_tunnel, "name": "zia_get_gre_tunnel", "description": "Get a specific ZIA GRE tunnel by ID (read-only)"},
            {"func": zia_list_gre_ranges, "name": "zia_list_gre_ranges", "description": "List available ZIA GRE IP ranges (read-only)"},
            # Activation
            {"func": zia_get_activation_status, "name": "zia_get_activation_status", "description": "Get ZIA configuration activation status (read-only)"},
            # ATP Malicious URLs
            {"func": zia_list_atp_malicious_urls, "name": "zia_list_atp_malicious_urls", "description": "List ZIA ATP malicious URLs (read-only)"},
            # Auth Exempt URLs
            {"func": zia_list_auth_exempt_urls, "name": "zia_list_auth_exempt_urls", "description": "List ZIA authentication exempt URLs (read-only)"},
            # Cloud Applications
            {"func": zia_list_cloud_applications, "name": "zia_list_cloud_applications", "description": "List ZIA cloud applications (read-only)"},
            {"func": zia_list_cloud_application_custom_tags, "name": "zia_list_cloud_application_custom_tags", "description": "List ZIA cloud application custom tags (read-only)"},
        ]

        # Write tools
        self.write_tools = [
            # Cloud Firewall Rules
            {"func": zia_create_cloud_firewall_rule, "name": "zia_create_cloud_firewall_rule", "description": "Create a new ZIA cloud firewall rule (write operation)"},
            {"func": zia_update_cloud_firewall_rule, "name": "zia_update_cloud_firewall_rule", "description": "Update an existing ZIA cloud firewall rule (write operation)"},
            {"func": zia_delete_cloud_firewall_rule, "name": "zia_delete_cloud_firewall_rule", "description": "Delete a ZIA cloud firewall rule (destructive operation)"},
            # URL Filtering Rules
            {"func": zia_create_url_filtering_rule, "name": "zia_create_url_filtering_rule", "description": "Create a new ZIA URL filtering rule (write operation)"},
            {"func": zia_update_url_filtering_rule, "name": "zia_update_url_filtering_rule", "description": "Update an existing ZIA URL filtering rule (write operation)"},
            {"func": zia_delete_url_filtering_rule, "name": "zia_delete_url_filtering_rule", "description": "Delete a ZIA URL filtering rule (destructive operation)"},
            # Web DLP Rules
            {"func": zia_create_web_dlp_rule, "name": "zia_create_web_dlp_rule", "description": "Create a new ZIA web DLP rule (write operation)"},
            {"func": zia_update_web_dlp_rule, "name": "zia_update_web_dlp_rule", "description": "Update an existing ZIA web DLP rule (write operation)"},
            {"func": zia_delete_web_dlp_rule, "name": "zia_delete_web_dlp_rule", "description": "Delete a ZIA web DLP rule (destructive operation)"},
            # IP Source Groups
            {"func": zia_create_ip_source_group, "name": "zia_create_ip_source_group", "description": "Create a new ZIA IP source group (write operation)"},
            {"func": zia_update_ip_source_group, "name": "zia_update_ip_source_group", "description": "Update an existing ZIA IP source group (write operation)"},
            {"func": zia_delete_ip_source_group, "name": "zia_delete_ip_source_group", "description": "Delete a ZIA IP source group (destructive operation)"},
            # IP Destination Groups
            {"func": zia_create_ip_destination_group, "name": "zia_create_ip_destination_group", "description": "Create a new ZIA IP destination group (write operation)"},
            {"func": zia_update_ip_destination_group, "name": "zia_update_ip_destination_group", "description": "Update an existing ZIA IP destination group (write operation)"},
            {"func": zia_delete_ip_destination_group, "name": "zia_delete_ip_destination_group", "description": "Delete a ZIA IP destination group (destructive operation)"},
            # Network App Groups
            {"func": zia_create_network_app_group, "name": "zia_create_network_app_group", "description": "Create a new ZIA network application group (write operation)"},
            {"func": zia_update_network_app_group, "name": "zia_update_network_app_group", "description": "Update an existing ZIA network application group (write operation)"},
            {"func": zia_delete_network_app_group, "name": "zia_delete_network_app_group", "description": "Delete a ZIA network application group (destructive operation)"},
            # URL Categories
            {"func": zia_create_url_category, "name": "zia_create_url_category", "description": "Create a new ZIA URL category (write operation)"},
            {"func": zia_update_url_category, "name": "zia_update_url_category", "description": "Update an existing ZIA URL category (write operation)"},
            {"func": zia_delete_url_category, "name": "zia_delete_url_category", "description": "Delete a ZIA URL category (destructive operation)"},
            {"func": zia_add_urls_to_category, "name": "zia_add_urls_to_category", "description": "Add URLs to a ZIA URL category (write operation)"},
            {"func": zia_remove_urls_from_category, "name": "zia_remove_urls_from_category", "description": "Remove URLs from a ZIA URL category (write operation)"},
            # Rule Labels
            {"func": zia_create_rule_label, "name": "zia_create_rule_label", "description": "Create a new ZIA rule label (write operation)"},
            {"func": zia_update_rule_label, "name": "zia_update_rule_label", "description": "Update an existing ZIA rule label (write operation)"},
            {"func": zia_delete_rule_label, "name": "zia_delete_rule_label", "description": "Delete a ZIA rule label (destructive operation)"},
            # Locations
            {"func": zia_create_location, "name": "zia_create_location", "description": "Create a new ZIA location (write operation)"},
            {"func": zia_update_location, "name": "zia_update_location", "description": "Update an existing ZIA location (write operation)"},
            {"func": zia_delete_location, "name": "zia_delete_location", "description": "Delete a ZIA location (destructive operation)"},
            # VPN Credentials
            {"func": zia_create_vpn_credential, "name": "zia_create_vpn_credential", "description": "Create a new ZIA VPN credential (write operation)"},
            {"func": zia_update_vpn_credential, "name": "zia_update_vpn_credential", "description": "Update an existing ZIA VPN credential (write operation)"},
            {"func": zia_delete_vpn_credential, "name": "zia_delete_vpn_credential", "description": "Delete a ZIA VPN credential (destructive operation)"},
            # Static IPs
            {"func": zia_create_static_ip, "name": "zia_create_static_ip", "description": "Create a new ZIA static IP (write operation)"},
            {"func": zia_update_static_ip, "name": "zia_update_static_ip", "description": "Update an existing ZIA static IP (write operation)"},
            {"func": zia_delete_static_ip, "name": "zia_delete_static_ip", "description": "Delete a ZIA static IP (destructive operation)"},
            # GRE Tunnels
            {"func": zia_create_gre_tunnel, "name": "zia_create_gre_tunnel", "description": "Create a new ZIA GRE tunnel (write operation)"},
            {"func": zia_delete_gre_tunnel, "name": "zia_delete_gre_tunnel", "description": "Delete a ZIA GRE tunnel (destructive operation)"},
            # Activation
            {"func": zia_activate_configuration, "name": "zia_activate_configuration", "description": "Activate ZIA configuration changes (write operation)"},
            # ATP Malicious URLs
            {"func": zia_add_atp_malicious_urls, "name": "zia_add_atp_malicious_urls", "description": "Add URLs to ZIA ATP malicious URL list (write operation)"},
            {"func": zia_delete_atp_malicious_urls, "name": "zia_delete_atp_malicious_urls", "description": "Delete URLs from ZIA ATP malicious URL list (destructive operation)"},
            # Auth Exempt URLs
            {"func": zia_add_auth_exempt_urls, "name": "zia_add_auth_exempt_urls", "description": "Add URLs to ZIA authentication exempt list (write operation)"},
            {"func": zia_delete_auth_exempt_urls, "name": "zia_delete_auth_exempt_urls", "description": "Delete URLs from ZIA authentication exempt list (destructive operation)"},
            # Cloud Applications
            {"func": zia_bulk_update_cloud_applications, "name": "zia_bulk_update_cloud_applications", "description": "Bulk update ZIA cloud applications (write operation)"},
        ]

    def register_tools(self, server, enabled_tools=None, enable_write_tools=False, write_tools=None):
        """Register ZIA tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations
        read_count = register_read_tools(server, self.read_tools, enabled_tools)
        write_count = register_write_tools(server, self.write_tools, enabled_tools, enable_write_tools, write_tools)

        logger.info(f"ZIA Service: Registered {read_count} read tools, {write_count} write tools")


class ZTWService(BaseService):
    """Zscaler Cloud & Branch Connector (ZTW) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import verb-based ZTW tools
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

        # Read-only tools
        self.read_tools = [
            {"func": ztw_list_ip_destination_groups, "name": "ztw_list_ip_destination_groups", "description": "List ZTW IP destination groups (read-only)"},
            {"func": ztw_list_ip_destination_groups_lite, "name": "ztw_list_ip_destination_groups_lite", "description": "List ZTW IP destination groups in lite format (read-only)"},
            {"func": ztw_list_ip_groups, "name": "ztw_list_ip_groups", "description": "List ZTW IP groups (read-only)"},
            {"func": ztw_list_ip_groups_lite, "name": "ztw_list_ip_groups_lite", "description": "List ZTW IP groups in lite format (read-only)"},
            {"func": ztw_list_ip_source_groups, "name": "ztw_list_ip_source_groups", "description": "List ZTW IP source groups (read-only)"},
            {"func": ztw_list_ip_source_groups_lite, "name": "ztw_list_ip_source_groups_lite", "description": "List ZTW IP source groups in lite format (read-only)"},
            {"func": ztw_list_network_service_groups, "name": "ztw_list_network_service_groups", "description": "List ZTW network service groups (read-only)"},
            {"func": ztw_list_roles, "name": "ztw_list_roles", "description": "List all existing admin roles in ZTW (read-only)"},
            {"func": ztw_list_admins, "name": "ztw_list_admins", "description": "List all existing admin users in ZTW (read-only)"},
        ]

        # Write tools
        self.write_tools = [
            {"func": ztw_create_ip_destination_group, "name": "ztw_create_ip_destination_group", "description": "Create a new ZTW IP destination group (write operation)"},
            {"func": ztw_delete_ip_destination_group, "name": "ztw_delete_ip_destination_group", "description": "Delete a ZTW IP destination group (destructive operation)"},
            {"func": ztw_create_ip_group, "name": "ztw_create_ip_group", "description": "Create a new ZTW IP group (write operation)"},
            {"func": ztw_delete_ip_group, "name": "ztw_delete_ip_group", "description": "Delete a ZTW IP group (destructive operation)"},
            {"func": ztw_create_ip_source_group, "name": "ztw_create_ip_source_group", "description": "Create a new ZTW IP source group (write operation)"},
            {"func": ztw_delete_ip_source_group, "name": "ztw_delete_ip_source_group", "description": "Delete a ZTW IP source group (destructive operation)"},
        ]

    def register_tools(self, server, enabled_tools=None, enable_write_tools=False, write_tools=None):
        """Register ZTW tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations
        read_count = register_read_tools(server, self.read_tools, enabled_tools)
        write_count = register_write_tools(server, self.write_tools, enabled_tools, enable_write_tools, write_tools)

        logger.info(f"ZTW Service: Registered {read_count} read tools, {write_count} write tools")


class ZIdentityService(BaseService):
    """Zscaler ZIdentity service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import verb-based ZIdentity tools
        from .tools.zidentity.groups import (
            zidentity_get_group,
            zidentity_get_group_users,
            zidentity_get_group_users_by_name,
            zidentity_list_groups,
            zidentity_search_groups,
        )
        from .tools.zidentity.users import (
            zidentity_get_user,
            zidentity_get_user_groups,
            zidentity_get_user_groups_by_name,
            zidentity_list_users,
            zidentity_search_users,
        )

        # All ZIdentity tools are read-only
        self.read_tools = [
            {"func": zidentity_list_groups, "name": "zidentity_list_groups", "description": "List ZIdentity groups (read-only)"},
            {"func": zidentity_get_group, "name": "zidentity_get_group", "description": "Get a specific ZIdentity group by ID (read-only)"},
            {"func": zidentity_search_groups, "name": "zidentity_search_groups", "description": "Search ZIdentity groups (read-only)"},
            {"func": zidentity_get_group_users, "name": "zidentity_get_group_users", "description": "Get users in a ZIdentity group (read-only)"},
            {"func": zidentity_get_group_users_by_name, "name": "zidentity_get_group_users_by_name", "description": "Get users in a ZIdentity group by group name (read-only)"},
            {"func": zidentity_list_users, "name": "zidentity_list_users", "description": "List ZIdentity users (read-only)"},
            {"func": zidentity_get_user, "name": "zidentity_get_user", "description": "Get a specific ZIdentity user by ID (read-only)"},
            {"func": zidentity_search_users, "name": "zidentity_search_users", "description": "Search ZIdentity users (read-only)"},
            {"func": zidentity_get_user_groups, "name": "zidentity_get_user_groups", "description": "Get groups for a ZIdentity user (read-only)"},
            {"func": zidentity_get_user_groups_by_name, "name": "zidentity_get_user_groups_by_name", "description": "Get groups for a ZIdentity user by username (read-only)"},
        ]

        self.write_tools = []  # ZIdentity has no write operations

    def register_tools(self, server, enabled_tools=None, enable_write_tools=False, write_tools=None):
        """Register ZIdentity tools with the server."""
        from zscaler_mcp.common.tool_helpers import register_read_tools, register_write_tools

        # Register verb-based tools with proper annotations (all read-only)
        read_count = register_read_tools(server, self.read_tools, enabled_tools)
        write_count = register_write_tools(server, self.write_tools, enabled_tools, enable_write_tools, write_tools)

        logger.info(f"ZIdentity Service: Registered {read_count} read tools, {write_count} write tools")


# Service registry
_AVAILABLE_SERVICES = {
    "zcc": ZCCService,
    "zdx": ZDXService,
    "zpa": ZPAService,
    "zia": ZIAService,
    "ztw": ZTWService,
    "zidentity": ZIdentityService,
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
