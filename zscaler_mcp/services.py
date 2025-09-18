"""
Zscaler MCP Server Services

This module provides the service classes for the Zscaler MCP server.
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
        self.tools = []
        self.resources = []

    @abstractmethod
    def register_tools(self, server, enabled_tools=None):
        """Register tools with the MCP server.

        Args:
            server: The MCP server instance
            enabled_tools: Set of enabled tool names (if None, all tools are enabled)
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
        # Import tools here to avoid circular imports
        from .tools.zcc.download_devices import zcc_devices_csv_exporter
        from .tools.zcc.list_devices import zcc_devices_v1_manager
        from .tools.zcc.list_forwarding_profiles import zcc_list_forwarding_profiles
        from .tools.zcc.list_trusted_networks import zcc_list_trusted_networks

        self.tools = [
            zcc_devices_v1_manager,
            zcc_devices_csv_exporter,
            zcc_list_trusted_networks,
            zcc_list_forwarding_profiles,
        ]

    def register_tools(self, server, enabled_tools=None):
        """Register ZCC tools with the server."""
        # Define tool metadata for registration
        tool_metadata = {
            "zcc_devices_v1_manager": {
                "name": "zcc_list_devices",
                "description": "Retrieves ZCC device enrollment information from the Zscaler Client Connector Portal.",
            },
            "zcc_devices_csv_exporter": {
                "name": "zcc_devices_csv_exporter",
                "description": "Downloads ZCC device information or service status as a CSV file.",
            },
            "zcc_list_trusted_networks": {
                "name": "zcc_list_trusted_networks",
                "description": "Returns the list of Trusted Networks By Company ID in the Client Connector Portal.",
            },
            "zcc_list_forwarding_profiles": {
                "name": "zcc_list_forwarding_profiles",
                "description": "Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal.",
            },
        }

        for tool in self.tools:
            # Get the function name to look up metadata
            tool_name = tool.__name__

            if tool_name in tool_metadata:
                metadata = tool_metadata[tool_name]
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and metadata["name"] not in enabled_tools:
                    continue
                server.add_tool(
                    tool, name=metadata["name"], description=metadata["description"]
                )
            else:
                # Fallback: use function name and docstring
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and tool_name not in enabled_tools:
                    continue
                server.add_tool(tool)


class ZDXService(BaseService):
    """Zscaler Digital Experience (ZDX) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import tools here to avoid circular imports
        from .tools.zdx.active_devices import zdx_device_discovery_tool
        from .tools.zdx.administration import zdx_admin_discovery_tool
        from .tools.zdx.get_application_metric import zdx_get_application_metric
        from .tools.zdx.get_application_score import zdx_get_application_score
        from .tools.zdx.get_application_user import zdx_get_application_user
        from .tools.zdx.list_alerts import zdx_list_alerts
        from .tools.zdx.list_applications import zdx_list_applications
        from .tools.zdx.list_deep_traces import zdx_list_deep_traces
        from .tools.zdx.list_historical_alerts import zdx_list_historical_alerts
        from .tools.zdx.list_software_inventory import zdx_list_software_inventory

        self.tools = [
            zdx_admin_discovery_tool,
            zdx_device_discovery_tool,
            zdx_list_applications,
            zdx_get_application_score,
            zdx_get_application_metric,
            zdx_get_application_user,
            zdx_list_software_inventory,
            zdx_list_alerts,
            zdx_list_historical_alerts,
            zdx_list_deep_traces,
        ]

    def register_tools(self, server, enabled_tools=None):
        """Register ZDX tools with the server."""
        # Define tool metadata for registration
        tool_metadata = {
            "zdx_admin_discovery_tool": {
                "name": "zdx_administration",
                "description": "Tool for discovering ZDX departments or locations.",
            },
            "zdx_device_discovery_tool": {
                "name": "zdx_active_devices",
                "description": "Tool for discovering ZDX devices using various filters.",
            },
            "zdx_list_applications": {
                "name": "zdx_list_applications",
                "description": "Tool for listing ZDX applications and getting application details.",
            },
            "zdx_get_application_score": {
                "name": "zdx_get_application_score",
                "description": "Tool for retrieving ZDX application scores and trends.",
            },
            "zdx_get_application_metric": {
                "name": "zdx_get_application_metric",
                "description": "Tool for retrieving ZDX metrics for a specified application",
            },
            "zdx_get_application_user": {
                "name": "zdx_get_application_user",
                "description": "Tool for retrieving ZDX application user information and device details",
            },
            "zdx_list_software_inventory": {
                "name": "zdx_list_software_inventory",
                "description": "Tool for retrieving ZDX software inventory information.",
            },
            "zdx_list_alerts": {
                "name": "zdx_list_alerts",
                "description": "Tool for listing ZDX alerts and retrieving alert details.",
            },
            "zdx_list_historical_alerts": {
                "name": "zdx_list_historical_alerts",
                "description": "Tool for retrieving ZDX historical alert information.",
            },
            "zdx_list_deep_traces": {
                "name": "zdx_list_deep_traces",
                "description": "Tool for retrieving ZDX deep trace information for troubleshooting device connectivity issues.",
            },
        }

        for tool in self.tools:
            # Get the function name to look up metadata
            tool_name = tool.__name__

            if tool_name in tool_metadata:
                metadata = tool_metadata[tool_name]
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and metadata["name"] not in enabled_tools:
                    continue
                server.add_tool(
                    tool, name=metadata["name"], description=metadata["description"]
                )
            else:
                # Fallback: use function name and docstring
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and tool_name not in enabled_tools:
                    continue
                server.add_tool(tool)


class ZPAService(BaseService):
    """Zscaler Private Access (ZPA) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import tools here to avoid circular imports
        from .tools.zpa.access_app_protection_rules import app_protection_policy_manager
        from .tools.zpa.access_forwarding_rules import forwarding_policy_manager
        from .tools.zpa.access_isolation_rules import isolation_policy_manager
        from .tools.zpa.access_policy_rules import access_policy_manager
        from .tools.zpa.access_timeout_rules import timeout_policy_manager
        from .tools.zpa.app_connector_groups import connector_group_manager
        from .tools.zpa.app_segments import app_segment_manager
        from .tools.zpa.application_servers import application_server_v2_manager
        from .tools.zpa.ba_certificate import ba_certificate_manager
        from .tools.zpa.get_app_protection_profile import app_protection_profile_manager
        from .tools.zpa.get_enrollment_certificate import enrollment_certificate_manager
        from .tools.zpa.get_isolation_profile import isolation_profile_manager
        from .tools.zpa.get_posture_profiles import posture_profile_manager
        from .tools.zpa.get_saml_attributes import saml_attribute_manager
        from .tools.zpa.get_scim_attributes import scim_attribute_manager
        from .tools.zpa.get_scim_groups import scim_group_manager
        from .tools.zpa.get_segments_by_type import app_segments_by_type_manager
        from .tools.zpa.get_trusted_networks import trusted_network_manager
        from .tools.zpa.pra_credential import pra_credential_manager
        from .tools.zpa.pra_portal import pra_portal_manager
        from .tools.zpa.provisioning_key import provisioning_key_manager
        from .tools.zpa.segment_groups import segment_group_v6_manager
        from .tools.zpa.server_groups import server_group_manager
        from .tools.zpa.service_edge_groups import service_edge_group_manager

        self.tools = [
            app_segment_manager,
            app_segments_by_type_manager,
            application_server_v2_manager,
            ba_certificate_manager,
            segment_group_v6_manager,
            server_group_manager,
            connector_group_manager,
            service_edge_group_manager,
            access_policy_manager,
            forwarding_policy_manager,
            timeout_policy_manager,
            isolation_policy_manager,
            isolation_profile_manager,
            app_protection_profile_manager,
            app_protection_policy_manager,
            enrollment_certificate_manager,
            provisioning_key_manager,
            pra_portal_manager,
            pra_credential_manager,
            scim_group_manager,
            scim_attribute_manager,
            saml_attribute_manager,
            trusted_network_manager,
            posture_profile_manager,
        ]

    def register_tools(self, server, enabled_tools=None):
        """Register ZPA tools with the server."""
        # Define tool metadata for registration
        tool_metadata = {
            "app_segment_manager": {
                "name": "zpa_application_segments",
                "description": "CRUD handler for ZPA Application Segments via the Python SDK.",
            },
            "app_segments_by_type_manager": {
                "name": "zpa_app_segments_by_type",
                "description": "Tool to retrieve ZPA application segments by type.",
            },
            "application_server_v2_manager": {
                "name": "zpa_application_servers",
                "description": "Tool for managing ZPA Application Servers.",
            },
            "ba_certificate_manager": {
                "name": "zpa_ba_certificates",
                "description": "Tool for managing ZPA Browser Access (BA) Certificates.",
            },
            "segment_group_v6_manager": {
                "name": "zpa_segment_groups",
                "description": "Tool for managing Segment Groups.",
            },
            "server_group_manager": {
                "name": "zpa_server_groups",
                "description": "CRUD handler for ZPA Server Groups via the Python SDK.",
            },
            "connector_group_manager": {
                "name": "zpa_app_connector_groups",
                "description": "CRUD handler for ZPA App Connector Groups via the Python SDK.",
            },
            "service_edge_group_manager": {
                "name": "zpa_service_edge_groups",
                "description": "CRUD handler for ZPA Service Edge Groups via the Python SDK.",
            },
            "access_policy_manager": {
                "name": "zpa_access_policy",
                "description": "CRUD handler for ZPA Access Policy Rules via the Python SDK.",
            },
            "forwarding_policy_manager": {
                "name": "zpa_forwarding_policy",
                "description": "CRUD handler for ZPA Client Forwarding Policy Rules via the Python SDK.",
            },
            "timeout_policy_manager": {
                "name": "zpa_timeout_policy",
                "description": "CRUD handler for ZPA Timeout Policy Rules via the Python SDK.",
            },
            "isolation_policy_manager": {
                "name": "zpa_isolation_policy",
                "description": "CRUD handler for ZPA Isolation Policy Rules via the Python SDK.",
            },
            "isolation_profile_manager": {
                "name": "zpa_isolation_profile",
                "description": "Tool for retrieving ZPA Cloud Browser Isolation (CBI) profiles.",
            },
            "app_protection_profile_manager": {
                "name": "zpa_app_protection_profiles",
                "description": "Tool for listing and searching ZPA App Protection Profiles (Inspection Profiles).",
            },
            "enrollment_certificate_manager": {
                "name": "zpa_enrollment_certificates",
                "description": "Get-only tool for retrieving ZPA Enrollment Certificates.",
            },
            "provisioning_key_manager": {
                "name": "zpa_provisioning_key",
                "description": "Tool for managing ZPA Provisioning Keys.",
            },
            "pra_portal_manager": {
                "name": "zpa_pra_portals",
                "description": "Tool for managing ZPA Privileged Remote Access (PRA) Portals.",
            },
            "pra_credential_manager": {
                "name": "zpa_pra_credentials",
                "description": "Tool for managing ZPA Privileged Remote Access (PRA) Credentials.",
            },
            "scim_group_manager": {
                "name": "zpa_scim_groups",
                "description": "Tool for retrieving ZPA SCIM groups under a given Identity Provider (IdP).",
            },
            "scim_attribute_manager": {
                "name": "zpa_scim_attributes",
                "description": "Tool for managing ZPA SCIM Attributes.",
            },
            "saml_attribute_manager": {
                "name": "zpa_saml_attributes",
                "description": "Tool for querying ZPA SAML Attributes.",
            },
            "trusted_network_manager": {
                "name": "zpa_trusted_networks",
                "description": "Tool for retrieving ZPA Trusted Networks.",
            },
            "posture_profile_manager": {
                "name": "zpa_posture_profiles",
                "description": "Tool for retrieving ZPA Posture Profiles.",
            },
            "app_protection_policy_manager": {
                "name": "zpa_app_protection_policy",
                "description": "CRUD handler for ZPA Inspection Policy Rules via the Python SDK.",
            },
        }

        for tool in self.tools:
            # Get the function name to look up metadata
            tool_name = tool.__name__

            if tool_name in tool_metadata:
                metadata = tool_metadata[tool_name]
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and metadata["name"] not in enabled_tools:
                    continue
                server.add_tool(
                    tool, name=metadata["name"], description=metadata["description"]
                )
            else:
                # Fallback: use function name and docstring
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and tool_name not in enabled_tools:
                    continue
                logger.debug(f"Tool metadata not found for {tool_name}")
                server.add_tool(tool)


class ZIAService(BaseService):
    """Zscaler Internet Access (ZIA) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import tools here to avoid circular imports
        from .tools.zia.activation import zia_activation_manager
        from .tools.zia.atp_malicious_urls import zia_atp_malicious_urls_manager
        from .tools.zia.auth_exempt_urls import zia_auth_exempt_urls_manager
        from .tools.zia.cloud_applications import cloud_applications_manager
        from .tools.zia.cloud_firewall_rules import zia_firewall_rule_manager
        from .tools.zia.geo_search import zia_geo_search_tool
        from .tools.zia.get_sandbox_info import sandbox_manager
        from .tools.zia.gre_ranges import gre_range_discovery_manager
        from .tools.zia.gre_tunnels import gre_tunnel_manager
        from .tools.zia.ip_destination_groups import zia_ip_destination_group_manager
        from .tools.zia.ip_source_groups import zia_ip_source_group_manager
        from .tools.zia.list_dlp_dictionaries import zia_dlp_dictionary_manager
        from .tools.zia.list_dlp_engines import zia_dlp_engine_manager
        from .tools.zia.list_user_departments import zia_user_department_manager
        from .tools.zia.list_user_groups import zia_user_group_manager
        from .tools.zia.list_users import zia_users_manager
        from .tools.zia.location_management import zia_locations_manager
        from .tools.zia.network_app_groups import zia_network_app_group_manager
        from .tools.zia.rule_labels import rule_label_manager
        from .tools.zia.static_ips import static_ip_manager
        from .tools.zia.url_categories import url_category_manager
        from .tools.zia.vpn_credentials import vpn_credential_manager

        self.tools = [
            zia_activation_manager,
            cloud_applications_manager,
            zia_atp_malicious_urls_manager,
            zia_auth_exempt_urls_manager,
            rule_label_manager,
            url_category_manager,
            zia_firewall_rule_manager,
            zia_ip_source_group_manager,
            zia_ip_destination_group_manager,
            zia_user_group_manager,
            zia_user_department_manager,
            zia_users_manager,
            zia_network_app_group_manager,
            zia_locations_manager,
            vpn_credential_manager,
            static_ip_manager,
            gre_tunnel_manager,
            gre_range_discovery_manager,
            zia_geo_search_tool,
            sandbox_manager,
            zia_dlp_dictionary_manager,
            zia_dlp_engine_manager,
        ]

    def register_tools(self, server, enabled_tools=None):
        """Register ZIA tools with the server."""
        # Define tool metadata for registration
        tool_metadata = {
            "zia_activation_manager": {
                "name": "zia_activation",
                "description": "Tool to check or activate ZIA configuration changes.",
            },
            "cloud_applications_manager": {
                "name": "zia_cloud_applications",
                "description": "Tool for managing ZIA Shadow IT Cloud Applications.",
            },
            "zia_atp_malicious_urls_manager": {
                "name": "zia_atp_malicious_urls",
                "description": "Manages the malicious URL denylist in the ZIA Advanced Threat Protection (ATP) policy.",
            },
            "zia_auth_exempt_urls_manager": {
                "name": "zia_auth_exempt_urls",
                "description": "Manages the list of cookie authentication exempt URLs in ZIA.",
            },
            "rule_label_manager": {
                "name": "zia_rule_labels",
                "description": "Tool for managing ZIA Rule Labels via the Python SDK.",
            },
            "url_category_manager": {
                "name": "zia_url_categories",
                "description": "Tool for managing ZIA URL Categories via the Python SDK.",
            },
            "zia_firewall_rule_manager": {
                "name": "zia_cloud_firewall_rule",
                "description": "Manages ZIA Cloud Firewall Rules.",
            },
            "zia_ip_source_group_manager": {
                "name": "zia_ip_source_group",
                "description": "Performs CRUD operations on ZIA IP Source Groups.",
            },
            "zia_ip_destination_group_manager": {
                "name": "zia_ip_destination_groups",
                "description": "Manages ZIA IP Destination Groups.",
            },
            "zia_user_group_manager": {
                "name": "zia_user_groups",
                "description": "Lists and retrieves ZIA User Groups with pagination, filtering and sorting via the Python SDK.",
            },
            "zia_user_department_manager": {
                "name": "zia_user_departments",
                "description": "Lists and retrieves ZIA User Departments with pagination, filtering and sorting via the Python SDK.",
            },
            "zia_users_manager": {
                "name": "zia_users",
                "description": "Lists and retrieves ZIA Users with filtering and pagination via the Python SDK.",
            },
            "zia_network_app_group_manager": {
                "name": "zia_network_app_group",
                "description": "Manages ZIA Network Application Groups.",
            },
            "zia_locations_manager": {
                "name": "zia_location_management",
                "description": "FastMCP tool to manage ZIA Locations.",
            },
            "vpn_credential_manager": {
                "name": "zia_vpn_credentials",
                "description": "Tool for managing ZIA VPN Credentials.",
            },
            "static_ip_manager": {
                "name": "zia_static_ips",
                "description": "Tool for managing ZIA Static IP addresses.",
            },
            "gre_tunnel_manager": {
                "name": "zia_gre_tunnels",
                "description": "Tool for managing ZIA GRE Tunnels and associated static IPs.",
            },
            "gre_range_discovery_manager": {
                "name": "zia_gre_range",
                "description": "Tool for discovering available GRE internal IP ranges in ZIA.",
            },
            "zia_geo_search_tool": {
                "name": "zia_geo_search",
                "description": "Performs geographical lookup actions using the ZIA Locations API.",
            },
            "sandbox_manager": {
                "name": "zia_sandbox_info",
                "description": "Tool for retrieving ZIA Sandbox information.",
            },
            "zia_dlp_dictionary_manager": {
                "name": "zia_dlp_dictionaries",
                "description": "Tool for managing ZIA DLP Dictionaries.",
            },
            "zia_dlp_engine_manager": {
                "name": "zia_dlp_engines",
                "description": "Tool for managing ZIA DLP Engines.",
            },
        }

        for tool in self.tools:
            # Get the function name to look up metadata
            tool_name = tool.__name__

            if tool_name in tool_metadata:
                metadata = tool_metadata[tool_name]
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and metadata["name"] not in enabled_tools:
                    continue
                server.add_tool(
                    tool, name=metadata["name"], description=metadata["description"]
                )
            else:
                # Fallback: use function name and docstring
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and tool_name not in enabled_tools:
                    continue
                server.add_tool(tool)


class ZTWService(BaseService):
    """Zscaler Cloud & Branch Connector (ZTW) service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import tools here to avoid circular imports
        from .tools.ztw.ip_destination_groups import ztw_ip_destination_group_manager
        from .tools.ztw.ip_groups import ztw_ip_group_manager
        from .tools.ztw.ip_source_groups import ztw_ip_source_group_manager
        from .tools.ztw.list_admins import ztw_list_admins
        from .tools.ztw.list_roles import ztw_list_roles
        from .tools.ztw.network_service_groups import ztw_network_service_group_manager

        self.tools = [
            ztw_ip_destination_group_manager,
            ztw_ip_group_manager,
            ztw_ip_source_group_manager,
            ztw_network_service_group_manager,
            ztw_list_roles,
            ztw_list_admins,
        ]

    def register_tools(self, server, enabled_tools=None):
        """Register ZTW tools with the server."""
        # Define tool metadata for registration
        tool_metadata = {
            "ztw_ip_destination_group_manager": {
                "name": "ztw_ip_destination_groups",
                "description": "Manages ZTW IP Destination Groups",
            },
            "ztw_ip_group_manager": {
                "name": "ztw_ip_group",
                "description": "Manages ZTW IP Groups",
            },
            "ztw_ip_source_group_manager": {
                "name": "ztw_ip_source_groups",
                "description": "Manages ZTW IP Source Groups",
            },
            "ztw_network_service_group_manager": {
                "name": "ztw_network_service_groups",
                "description": "Manages ZTW Network Service Groups",
            },
            "ztw_list_roles": {
                "name": "ztw_list_roles",
                "description": "List all existing admin roles in Zscaler Cloud & Branch Connector (ZTW).",
            },
            "ztw_list_admins": {
                "name": "ztw_list_admins",
                "description": "List all existing admin users or get details for a specific admin user in Zscaler Cloud & Branch Connector (ZTW).",
            },
        }

        for tool in self.tools:
            # Get the function name to look up metadata
            tool_name = tool.__name__

            if tool_name in tool_metadata:
                metadata = tool_metadata[tool_name]
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and metadata["name"] not in enabled_tools:
                    continue
                server.add_tool(
                    tool, name=metadata["name"], description=metadata["description"]
                )
            else:
                # Fallback: use function name and docstring
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and tool_name not in enabled_tools:
                    continue
                server.add_tool(tool)


class ZIdentityService(BaseService):
    """Zscaler ZIdentity service."""

    def __init__(self, zscaler_client):
        super().__init__(zscaler_client)
        # Import tools here to avoid circular imports
        from .tools.zidentity.groups import groups_manager
        from .tools.zidentity.users import users_manager

        self.tools = [
            groups_manager,
            users_manager,
        ]

    def register_tools(self, server, enabled_tools=None):
        """Register ZIdentity tools with the server."""
        # Define tool metadata for registration
        tool_metadata = {
            "groups_manager": {
                "name": "zidentity_groups",
                "description": "Retrieves Zidentity group information",
            },
            "users_manager": {
                "name": "zidentity_users",
                "description": "Retrieves Zidentity user information",
            },
        }

        for tool in self.tools:
            # Get the function name to look up metadata
            tool_name = tool.__name__

            if tool_name in tool_metadata:
                metadata = tool_metadata[tool_name]
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and metadata["name"] not in enabled_tools:
                    continue
                server.add_tool(
                    tool, name=metadata["name"], description=metadata["description"]
                )
            else:
                # Fallback: use function name and docstring
                # Skip if tool is not in enabled_tools (if enabled_tools is specified)
                if enabled_tools and tool_name not in enabled_tools:
                    continue
                server.add_tool(tool)


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
