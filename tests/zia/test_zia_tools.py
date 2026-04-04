"""
Unit tests for ZIA (Zscaler Internet Access) tools.

Covers: url_categories, url_filtering_rules, cloud_firewall_rules,
ip_destination_groups, ip_source_groups, network_services,
location_management, list_dlp_dictionaries, web_dlp_rules,
list_users, list_user_groups, list_user_departments,
static_ips, vpn_credentials, gre_tunnels, get_sandbox_info.
"""

from unittest.mock import MagicMock, patch

import pytest


def _mock_obj(data: dict):
    obj = MagicMock()
    obj.as_dict.return_value = data
    return obj


# ============================================================================
# URL CATEGORIES
# ============================================================================


class TestZiaUrlCategories:

    @patch("zscaler_mcp.tools.zia.url_categories.get_zscaler_client")
    def test_list_url_categories(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_categories import zia_list_url_categories

        mock_client = MagicMock()
        cats = [_mock_obj({"id": "c1", "configuredName": "Blocked"})]
        mock_client.zia.url_categories.list_categories.return_value = (cats, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_url_categories()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.url_categories.get_zscaler_client")
    def test_get_url_category(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_categories import zia_get_url_category

        mock_client = MagicMock()
        cat = _mock_obj({"id": "c1", "configuredName": "Blocked"})
        mock_client.zia.url_categories.get_category.return_value = (cat, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_url_category(category_id="c1")
        assert result["configuredName"] == "Blocked"

    @patch("zscaler_mcp.tools.zia.url_categories.get_zscaler_client")
    def test_url_lookup(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_categories import zia_url_lookup

        mock_client = MagicMock()
        lookup_result = [_mock_obj({"url": "example.com", "urlClassifications": ["NEWS"]})]
        mock_client.zia.url_categories.lookup.return_value = (lookup_result, None)
        mock_get_client.return_value = mock_client

        result = zia_url_lookup(urls=["example.com"])
        assert len(result) >= 1

    @patch("zscaler_mcp.tools.zia.url_categories.get_zscaler_client")
    def test_create_url_category(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_categories import zia_create_url_category

        mock_client = MagicMock()
        created = _mock_obj({"id": "c2", "configuredName": "Custom"})
        mock_client.zia.url_categories.add_url_category.return_value = (created, None, None)
        mock_get_client.return_value = mock_client

        result = zia_create_url_category(
            configured_name="Custom", super_category="USER_DEFINED", urls=["test.com"]
        )
        assert result["configuredName"] == "Custom"

    @patch("zscaler_mcp.tools.zia.url_categories.get_zscaler_client")
    def test_list_url_categories_error(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_categories import zia_list_url_categories

        mock_client = MagicMock()
        mock_client.zia.url_categories.list_categories.return_value = (None, None, "API Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zia_list_url_categories()


# ============================================================================
# URL FILTERING RULES
# ============================================================================


class TestZiaUrlFilteringRules:

    @patch("zscaler_mcp.tools.zia.url_filtering_rules.get_zscaler_client")
    def test_list_url_filtering_rules(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_filtering_rules import zia_list_url_filtering_rules

        mock_client = MagicMock()
        rules = [_mock_obj({"id": "r1", "name": "Block Social"})]
        mock_client.zia.url_filtering.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_url_filtering_rules()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.url_filtering_rules.get_zscaler_client")
    def test_get_url_filtering_rule(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_filtering_rules import zia_get_url_filtering_rule

        mock_client = MagicMock()
        rule = _mock_obj({"id": "r1", "name": "Block Social"})
        mock_client.zia.url_filtering.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_url_filtering_rule(rule_id="r1")
        assert result["name"] == "Block Social"

    @patch("zscaler_mcp.tools.zia.url_filtering_rules.get_zscaler_client")
    def test_list_url_filtering_rules_error(self, mock_get_client):
        from zscaler_mcp.tools.zia.url_filtering_rules import zia_list_url_filtering_rules

        mock_client = MagicMock()
        mock_client.zia.url_filtering.list_rules.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zia_list_url_filtering_rules()


# ============================================================================
# CLOUD FIREWALL RULES
# ============================================================================


class TestZiaCloudFirewallRules:

    @patch("zscaler_mcp.tools.zia.cloud_firewall_rules.get_zscaler_client")
    def test_list_cloud_firewall_rules(self, mock_get_client):
        from zscaler_mcp.tools.zia.cloud_firewall_rules import zia_list_cloud_firewall_rules

        mock_client = MagicMock()
        rules = [_mock_obj({"id": "fw1", "name": "Allow DNS"})]
        mock_client.zia.cloud_firewall_rules.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_cloud_firewall_rules()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.cloud_firewall_rules.get_zscaler_client")
    def test_get_cloud_firewall_rule(self, mock_get_client):
        from zscaler_mcp.tools.zia.cloud_firewall_rules import zia_get_cloud_firewall_rule

        mock_client = MagicMock()
        rule = _mock_obj({"id": "fw1", "name": "Allow DNS"})
        mock_client.zia.cloud_firewall_rules.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_cloud_firewall_rule(rule_id="fw1")
        assert result["name"] == "Allow DNS"

    @patch("zscaler_mcp.tools.zia.cloud_firewall_rules.get_zscaler_client")
    def test_list_cloud_firewall_rules_error(self, mock_get_client):
        from zscaler_mcp.tools.zia.cloud_firewall_rules import zia_list_cloud_firewall_rules

        mock_client = MagicMock()
        mock_client.zia.cloud_firewall_rules.list_rules.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zia_list_cloud_firewall_rules()


# ============================================================================
# IP DESTINATION GROUPS
# ============================================================================


class TestZiaIpDestinationGroups:

    @patch("zscaler_mcp.tools.zia.ip_destination_groups.get_zscaler_client")
    def test_list_ip_destination_groups(self, mock_get_client):
        from zscaler_mcp.tools.zia.ip_destination_groups import zia_list_ip_destination_groups

        mock_client = MagicMock()
        groups = [_mock_obj({"id": "dg1", "name": "Blocked IPs"})]
        mock_client.zia.cloud_firewall.list_ip_destination_groups.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_ip_destination_groups()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.ip_destination_groups.get_zscaler_client")
    def test_get_ip_destination_group(self, mock_get_client):
        from zscaler_mcp.tools.zia.ip_destination_groups import zia_get_ip_destination_group

        mock_client = MagicMock()
        group = _mock_obj({"id": "dg1", "name": "Blocked IPs"})
        mock_client.zia.cloud_firewall.get_ip_destination_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_ip_destination_group(group_id="dg1")
        assert result["name"] == "Blocked IPs"


# ============================================================================
# IP SOURCE GROUPS
# ============================================================================


class TestZiaIpSourceGroups:

    @patch("zscaler_mcp.tools.zia.ip_source_groups.get_zscaler_client")
    def test_list_ip_source_groups(self, mock_get_client):
        from zscaler_mcp.tools.zia.ip_source_groups import zia_list_ip_source_groups

        mock_client = MagicMock()
        groups = [_mock_obj({"id": "sg1", "name": "Office IPs"})]
        mock_client.zia.cloud_firewall.list_ip_source_groups.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_ip_source_groups()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.ip_source_groups.get_zscaler_client")
    def test_get_ip_source_group(self, mock_get_client):
        from zscaler_mcp.tools.zia.ip_source_groups import zia_get_ip_source_group

        mock_client = MagicMock()
        group = _mock_obj({"id": "sg1", "name": "Office IPs"})
        mock_client.zia.cloud_firewall.get_ip_source_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_ip_source_group(group_id="sg1")
        assert result["name"] == "Office IPs"


# ============================================================================
# NETWORK SERVICES
# ============================================================================


class TestZiaNetworkServices:

    @patch("zscaler_mcp.tools.zia.network_services.get_zscaler_client")
    def test_list_network_services(self, mock_get_client):
        from zscaler_mcp.tools.zia.network_services import zia_list_network_services

        mock_client = MagicMock()
        services = [_mock_obj({"id": "ns1", "name": "DNS"})]
        mock_client.zia.cloud_firewall.list_network_services.return_value = (services, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_network_services()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.network_services.get_zscaler_client")
    def test_get_network_service(self, mock_get_client):
        from zscaler_mcp.tools.zia.network_services import zia_get_network_service

        mock_client = MagicMock()
        svc = _mock_obj({"id": "ns1", "name": "DNS"})
        mock_client.zia.cloud_firewall.get_network_service.return_value = (svc, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_network_service(service_id="ns1")
        assert result["name"] == "DNS"


# ============================================================================
# LOCATION MANAGEMENT
# ============================================================================


class TestZiaLocationManagement:

    @patch("zscaler_mcp.tools.zia.location_management.get_zscaler_client")
    def test_list_locations(self, mock_get_client):
        from zscaler_mcp.tools.zia.location_management import zia_list_locations

        mock_client = MagicMock()
        locations = [_mock_obj({"id": "l1", "name": "HQ"}), _mock_obj({"id": "l2", "name": "Branch"})]
        mock_client.zia.locations.list_locations.return_value = (locations, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_locations()
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zia.location_management.get_zscaler_client")
    def test_get_location(self, mock_get_client):
        from zscaler_mcp.tools.zia.location_management import zia_get_location

        mock_client = MagicMock()
        loc = _mock_obj({"id": "l1", "name": "HQ"})
        mock_client.zia.locations.get_location.return_value = (loc, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_location(location_id="l1")
        assert result["name"] == "HQ"

    @patch("zscaler_mcp.tools.zia.location_management.get_zscaler_client")
    def test_list_locations_error(self, mock_get_client):
        from zscaler_mcp.tools.zia.location_management import zia_list_locations

        mock_client = MagicMock()
        mock_client.zia.locations.list_locations.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zia_list_locations()


# ============================================================================
# DLP DICTIONARIES
# ============================================================================


class TestZiaDlpDictionaries:

    @patch("zscaler_mcp.tools.zia.list_dlp_dictionaries.get_zscaler_client")
    def test_list_dlp_dictionaries(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_dlp_dictionaries import zia_dlp_dictionary_manager

        mock_client = MagicMock()
        dicts = [_mock_obj({"id": "d1", "name": "SSN"}), _mock_obj({"id": "d2", "name": "CCN"})]
        mock_client.zia.dlp_dictionary.list_dicts.return_value = (dicts, None, None)
        mock_get_client.return_value = mock_client

        result = zia_dlp_dictionary_manager(action="read")
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zia.list_dlp_dictionaries.get_zscaler_client")
    def test_get_dlp_dictionary_by_id(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_dlp_dictionaries import zia_dlp_dictionary_manager

        mock_client = MagicMock()
        d = _mock_obj({"id": "d1", "name": "SSN"})
        mock_client.zia.dlp_dictionary.get_dict.return_value = (d, None, None)
        mock_get_client.return_value = mock_client

        result = zia_dlp_dictionary_manager(action="read", dict_id="d1")
        assert result["name"] == "SSN"

    @patch("zscaler_mcp.tools.zia.list_dlp_dictionaries.get_zscaler_client")
    def test_list_dlp_dictionaries_lite(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_dlp_dictionaries import zia_dlp_dictionary_manager

        mock_client = MagicMock()
        dicts = [_mock_obj({"id": "d1", "name": "SSN Lite"})]
        mock_client.zia.dlp_dictionary.list_dicts_lite.return_value = (dicts, None, None)
        mock_get_client.return_value = mock_client

        result = zia_dlp_dictionary_manager(action="read_lite")
        assert len(result) == 1


# ============================================================================
# WEB DLP RULES
# ============================================================================


class TestZiaWebDlpRules:

    @patch("zscaler_mcp.tools.zia.web_dlp_rules.get_zscaler_client")
    def test_list_web_dlp_rules(self, mock_get_client):
        from zscaler_mcp.tools.zia.web_dlp_rules import zia_list_web_dlp_rules

        mock_client = MagicMock()
        rules = [_mock_obj({"id": "r1", "name": "Block SSN Upload"})]
        mock_client.zia.dlp_web_rules.list_rules.return_value = (rules, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_web_dlp_rules()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.web_dlp_rules.get_zscaler_client")
    def test_get_web_dlp_rule(self, mock_get_client):
        from zscaler_mcp.tools.zia.web_dlp_rules import zia_get_web_dlp_rule

        mock_client = MagicMock()
        rule = _mock_obj({"id": "r1", "name": "Block SSN Upload"})
        mock_client.zia.dlp_web_rules.get_rule.return_value = (rule, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_web_dlp_rule(rule_id="r1")
        assert result["name"] == "Block SSN Upload"

    @patch("zscaler_mcp.tools.zia.web_dlp_rules.get_zscaler_client")
    def test_list_web_dlp_rules_error(self, mock_get_client):
        from zscaler_mcp.tools.zia.web_dlp_rules import zia_list_web_dlp_rules

        mock_client = MagicMock()
        mock_client.zia.dlp_web_rules.list_rules.return_value = (None, None, "Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zia_list_web_dlp_rules()


# ============================================================================
# USER MANAGEMENT
# ============================================================================


class TestZiaUserManagement:

    @patch("zscaler_mcp.tools.zia.list_users.get_zscaler_client")
    def test_list_users(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_users import zia_users_manager

        mock_client = MagicMock()
        users = [_mock_obj({"id": "u1", "name": "Alice"})]
        mock_client.zia.user_management.list_users.return_value = (users, None, None)
        mock_get_client.return_value = mock_client

        result = zia_users_manager(action="read")
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.list_users.get_zscaler_client")
    def test_get_user_by_id(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_users import zia_users_manager

        mock_client = MagicMock()
        user = _mock_obj({"id": "u1", "name": "Alice"})
        mock_client.zia.user_management.get_user.return_value = (user, None, None)
        mock_get_client.return_value = mock_client

        result = zia_users_manager(action="read", user_id="u1")
        assert result["name"] == "Alice"


class TestZiaUserGroups:

    @patch("zscaler_mcp.tools.zia.list_user_groups.get_zscaler_client")
    def test_list_user_groups(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_user_groups import zia_user_group_manager

        mock_client = MagicMock()
        groups = [_mock_obj({"id": "g1", "name": "Engineering"})]
        mock_client.zia.user_management.list_groups.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zia_user_group_manager(action="read")
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.list_user_groups.get_zscaler_client")
    def test_get_user_group_by_id(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_user_groups import zia_user_group_manager

        mock_client = MagicMock()
        group = _mock_obj({"id": "g1", "name": "Engineering"})
        mock_client.zia.user_management.get_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zia_user_group_manager(action="read", group_id="g1")
        assert result["name"] == "Engineering"


class TestZiaUserDepartments:

    @patch("zscaler_mcp.tools.zia.list_user_departments.get_zscaler_client")
    def test_list_user_departments(self, mock_get_client):
        from zscaler_mcp.tools.zia.list_user_departments import zia_user_department_manager

        mock_client = MagicMock()
        depts = [_mock_obj({"id": "d1", "name": "IT"})]
        mock_client.zia.user_management.list_departments.return_value = (depts, None, None)
        mock_get_client.return_value = mock_client

        result = zia_user_department_manager(action="read")
        assert len(result) == 1


# ============================================================================
# TRAFFIC FORWARDING
# ============================================================================


class TestZiaStaticIps:

    @patch("zscaler_mcp.tools.zia.static_ips.get_zscaler_client")
    def test_list_static_ips(self, mock_get_client):
        from zscaler_mcp.tools.zia.static_ips import zia_list_static_ips

        mock_client = MagicMock()
        ips = [_mock_obj({"id": "ip1", "ipAddress": "1.2.3.4"})]
        mock_client.zia.traffic_static_ip.list_static_ips.return_value = (ips, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_static_ips()
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zia.static_ips.get_zscaler_client")
    def test_get_static_ip(self, mock_get_client):
        from zscaler_mcp.tools.zia.static_ips import zia_get_static_ip

        mock_client = MagicMock()
        ip = _mock_obj({"id": "ip1", "ipAddress": "1.2.3.4"})
        mock_client.zia.traffic_static_ip.get_static_ip.return_value = (ip, None, None)
        mock_get_client.return_value = mock_client

        result = zia_get_static_ip(static_ip_id="ip1")
        assert result["ipAddress"] == "1.2.3.4"


class TestZiaVpnCredentials:

    @patch("zscaler_mcp.tools.zia.vpn_credentials.get_zscaler_client")
    def test_list_vpn_credentials(self, mock_get_client):
        from zscaler_mcp.tools.zia.vpn_credentials import zia_list_vpn_credentials

        mock_client = MagicMock()
        creds = [_mock_obj({"id": "vc1", "type": "UFQDN"})]
        mock_client.zia.traffic_vpn_credentials.list_vpn_credentials.return_value = (creds, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_vpn_credentials()
        assert len(result) == 1


class TestZiaGreTunnels:

    @patch("zscaler_mcp.tools.zia.gre_tunnels.get_zscaler_client")
    def test_list_gre_tunnels(self, mock_get_client):
        from zscaler_mcp.tools.zia.gre_tunnels import zia_list_gre_tunnels

        mock_client = MagicMock()
        tunnels = [_mock_obj({"id": "t1", "sourceIp": "5.6.7.8"})]
        mock_client.zia.gre_tunnel.list_gre_tunnels.return_value = (tunnels, None, None)
        mock_get_client.return_value = mock_client

        result = zia_list_gre_tunnels()
        assert len(result) == 1


# ============================================================================
# SANDBOX
# ============================================================================


class TestZiaSandbox:

    @patch("zscaler_mcp.tools.zia.get_sandbox_info.get_zscaler_client")
    def test_get_sandbox_quota(self, mock_get_client):
        from zscaler_mcp.tools.zia.get_sandbox_info import zia_get_sandbox_quota

        mock_client = MagicMock()
        mock_client.zia.sandbox.get_quota.return_value = (
            {"allowed": 5000, "used": 100, "unused": 4900}, None, None
        )
        mock_get_client.return_value = mock_client

        result = zia_get_sandbox_quota()
        assert result["allowed"] == 5000

    @patch("zscaler_mcp.tools.zia.get_sandbox_info.get_zscaler_client")
    def test_sandbox_manager_invalid_action(self, mock_get_client):
        from zscaler_mcp.tools.zia.get_sandbox_info import sandbox_manager

        mock_get_client.return_value = MagicMock()
        with pytest.raises(ValueError):
            sandbox_manager(action="invalid_action")


# ============================================================================
# SERVICE REGISTRATION
# ============================================================================


class TestZIAServiceRegistration:

    def test_zia_service_exists_in_registry(self):
        from zscaler_mcp.services import get_available_services, get_service_names

        assert "zia" in get_service_names()
        assert "zia" in get_available_services()

    def test_zia_service_has_both_tool_types(self):
        from zscaler_mcp.services import ZIAService

        service = ZIAService(None)
        assert len(service.read_tools) > 0
        assert len(service.write_tools) > 0

    def test_all_zia_tools_have_naming_convention(self):
        from zscaler_mcp.services import ZIAService

        service = ZIAService(None)
        for tool in service.read_tools:
            name = tool["name"]
            assert "zia" in name.lower(), f"Tool {name} missing zia in name"
        for tool in service.write_tools:
            name = tool["name"]
            assert "zia" in name.lower(), f"Tool {name} missing zia in name"
