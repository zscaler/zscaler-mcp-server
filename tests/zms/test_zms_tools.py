"""
Tests for ZMS (Zscaler Microsegmentation) Tools

These tests validate tool behavior with mocked SDK responses.
"""

import os
from unittest.mock import MagicMock, patch


class TestZMSServiceRegistration:
    """Tests for ZMS service registration."""

    def test_zms_service_exists_in_registry(self):
        """Test that zms service is registered."""
        from zscaler_mcp.services import get_available_services, get_service_names

        service_names = get_service_names()
        assert "zms" in service_names

        available = get_available_services()
        assert "zms" in available

    def test_zms_service_has_read_tools_only(self):
        """Test that ZMS service only has read tools."""
        from zscaler_mcp.services import ZMSService

        service = ZMSService(None)
        assert len(service.read_tools) == 20
        assert len(service.write_tools) == 0

    def test_zms_service_tool_names(self):
        """Test that ZMS service has correct tool names."""
        from zscaler_mcp.services import ZMSService

        service = ZMSService(None)
        tool_names = [tool["name"] for tool in service.read_tools]

        expected_names = [
            "zms_list_agents",
            "zms_get_agent_connection_status_statistics",
            "zms_get_agent_version_statistics",
            "zms_list_agent_groups",
            "zms_get_agent_group_totp_secrets",
            "zms_list_resources",
            "zms_get_resource_protection_status",
            "zms_get_metadata",
            "zms_list_resource_groups",
            "zms_get_resource_group_members",
            "zms_get_resource_group_protection_status",
            "zms_list_policy_rules",
            "zms_list_default_policy_rules",
            "zms_list_app_zones",
            "zms_list_app_catalog",
            "zms_list_nonces",
            "zms_get_nonce",
            "zms_list_tag_namespaces",
            "zms_list_tag_keys",
            "zms_list_tag_values",
        ]

        for name in expected_names:
            assert name in tool_names, f"Missing tool: {name}"

    def test_all_zms_tools_have_zms_prefix(self):
        """Test that all ZMS tools follow naming convention."""
        from zscaler_mcp.services import ZMSService

        service = ZMSService(None)
        for tool in service.read_tools:
            assert tool["name"].startswith("zms_"), f"Tool {tool['name']} missing zms_ prefix"


class TestZMSAgentTools:
    """Tests for ZMS Agent tools."""

    @patch("zscaler_mcp.tools.zms.agents.get_zscaler_client")
    def test_list_agents_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.agents import zms_list_agents

        mock_client = MagicMock()
        mock_client.zms.agents.list_agents.return_value = (
            {
                "nodes": [
                    {"name": "agent-1", "connectionStatus": "CONNECTED", "hostOs": "Linux"},
                ],
                "pageInfo": {"pageNumber": 1, "pageSize": 20, "totalCount": 1, "totalPages": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_agents()

        assert len(result) == 1
        assert "nodes" in result[0]
        assert result[0]["nodes"][0]["name"] == "agent-1"

    @patch("zscaler_mcp.tools.zms.agents.get_zscaler_client")
    def test_list_agents_with_search(self, mock_get_client):
        from zscaler_mcp.tools.zms.agents import zms_list_agents

        mock_client = MagicMock()
        mock_client.zms.agents.list_agents.return_value = (
            {"nodes": [], "pageInfo": {"totalCount": 0}},
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            zms_list_agents(search="web-server", sort="name", sort_dir="ASC")

        call_kwargs = mock_client.zms.agents.list_agents.call_args[1]
        assert call_kwargs["search"] == "web-server"
        assert call_kwargs["sort"] == "name"
        assert call_kwargs["sort_dir"] == "ASC"

    def test_list_agents_missing_customer_id(self):
        from zscaler_mcp.tools.zms.agents import zms_list_agents

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ZSCALER_CUSTOMER_ID", None)
            result = zms_list_agents()

        assert len(result) == 1
        assert "error" in result[0]
        assert "ZSCALER_CUSTOMER_ID" in result[0]["error"]

    @patch("zscaler_mcp.tools.zms.agents.get_zscaler_client")
    def test_list_agents_sdk_error(self, mock_get_client):
        from zscaler_mcp.tools.zms.agents import zms_list_agents

        mock_client = MagicMock()
        mock_client.zms.agents.list_agents.return_value = (
            None,
            None,
            Exception("Connection error"),
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_agents()

        assert len(result) == 1
        assert "error" in result[0]
        assert "SDK error" in result[0]["error"]

    @patch("zscaler_mcp.tools.zms.agents.get_zscaler_client")
    def test_get_agent_connection_status_statistics_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.agents import zms_get_agent_connection_status_statistics

        mock_client = MagicMock()
        mock_client.zms.agents.get_agent_connection_status_statistics.return_value = (
            {"totalCount": 10, "totalPercentage": 100.0, "agentStatuses": []},
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_get_agent_connection_status_statistics()

        assert len(result) == 1
        assert result[0]["totalCount"] == 10

    @patch("zscaler_mcp.tools.zms.agents.get_zscaler_client")
    def test_get_agent_version_statistics_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.agents import zms_get_agent_version_statistics

        mock_client = MagicMock()
        mock_client.zms.agents.get_agent_version_statistics.return_value = (
            {"totalCount": 5, "agentVersions": [{"version": "2.0.1", "count": 3}]},
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_get_agent_version_statistics()

        assert len(result) == 1
        assert result[0]["totalCount"] == 5


class TestZMSAgentGroupTools:
    """Tests for ZMS Agent Group tools."""

    @patch("zscaler_mcp.tools.zms.agent_groups.get_zscaler_client")
    def test_list_agent_groups_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.agent_groups import zms_list_agent_groups

        mock_client = MagicMock()
        mock_client.zms.agent_groups.list_agent_groups.return_value = (
            {
                "nodes": [{"name": "web-servers", "agentCount": 5}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_agent_groups()

        assert len(result) == 1
        assert result[0]["nodes"][0]["name"] == "web-servers"

    @patch("zscaler_mcp.tools.zms.agent_groups.get_zscaler_client")
    def test_get_agent_group_totp_secrets_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.agent_groups import zms_get_agent_group_totp_secrets

        mock_client = MagicMock()
        mock_client.zms.agent_groups.get_agent_group_totp_secrets.return_value = (
            {"eyezId": "abc-123", "totpSecret": "JBSWY3DPEHPK3PXP"},
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_get_agent_group_totp_secrets(eyez_id="abc-123")

        assert len(result) == 1
        assert result[0]["totpSecret"] == "JBSWY3DPEHPK3PXP"


class TestZMSResourceTools:
    """Tests for ZMS Resource tools."""

    @patch("zscaler_mcp.tools.zms.resources.get_zscaler_client")
    def test_list_resources_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.resources import zms_list_resources

        mock_client = MagicMock()
        mock_client.zms.resources.list_resources.return_value = (
            {
                "nodes": [{"name": "web-01", "resourceType": "VM", "status": "ACTIVE"}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_resources()

        assert len(result) == 1
        assert result[0]["nodes"][0]["name"] == "web-01"

    @patch("zscaler_mcp.tools.zms.resources.get_zscaler_client")
    def test_get_resource_protection_status_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.resources import zms_get_resource_protection_status

        mock_client = MagicMock()
        mock_client.zms.resources.get_resource_protection_status.return_value = (
            {
                "nodes": [{"protectedPercentage": 85.5, "totalResources": 100}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_get_resource_protection_status()

        assert len(result) == 1
        assert result[0]["nodes"][0]["protectedPercentage"] == 85.5

    @patch("zscaler_mcp.tools.zms.resources.get_zscaler_client")
    def test_get_metadata_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.resources import zms_get_metadata

        mock_client = MagicMock()
        mock_client.zms.resources.get_metadata.return_value = (
            {"eventTypes": ["NETWORK", "PROCESS"]},
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_get_metadata()

        assert len(result) == 1
        assert "eventTypes" in result[0]


class TestZMSResourceGroupTools:
    """Tests for ZMS Resource Group tools."""

    @patch("zscaler_mcp.tools.zms.resource_groups.get_zscaler_client")
    def test_list_resource_groups_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.resource_groups import zms_list_resource_groups

        mock_client = MagicMock()
        mock_client.zms.resource_groups.list_resource_groups.return_value = (
            {
                "nodes": [{"name": "db-servers", "type": "ManagedResourceGroup", "resourceMemberCount": 3}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_resource_groups()

        assert len(result) == 1
        assert result[0]["nodes"][0]["name"] == "db-servers"

    @patch("zscaler_mcp.tools.zms.resource_groups.get_zscaler_client")
    def test_get_resource_group_members_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.resource_groups import zms_get_resource_group_members

        mock_client = MagicMock()
        mock_client.zms.resource_groups.get_resource_group_members.return_value = (
            {
                "nodes": [{"name": "db-01", "resourceType": "VM"}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_get_resource_group_members(group_id="rg-abc-123")

        assert len(result) == 1
        assert result[0]["nodes"][0]["name"] == "db-01"


class TestZMSPolicyRuleTools:
    """Tests for ZMS Policy Rule tools."""

    @patch("zscaler_mcp.tools.zms.policy_rules.get_zscaler_client")
    def test_list_policy_rules_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.policy_rules import zms_list_policy_rules

        mock_client = MagicMock()
        mock_client.zms.policy_rules.list_policy_rules.return_value = (
            {
                "nodes": [{"name": "allow-web-to-db", "action": "ALLOW", "priority": 1}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_policy_rules()

        assert len(result) == 1
        assert result[0]["nodes"][0]["action"] == "ALLOW"

    @patch("zscaler_mcp.tools.zms.policy_rules.get_zscaler_client")
    def test_list_default_policy_rules_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.policy_rules import zms_list_default_policy_rules

        mock_client = MagicMock()
        mock_client.zms.policy_rules.list_default_policy_rules.return_value = (
            {
                "nodes": [{"name": "default-deny", "action": "DENY", "direction": "INBOUND"}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_default_policy_rules()

        assert len(result) == 1
        assert result[0]["nodes"][0]["direction"] == "INBOUND"


class TestZMSAppZoneTools:
    """Tests for ZMS App Zone tools."""

    @patch("zscaler_mcp.tools.zms.app_zones.get_zscaler_client")
    def test_list_app_zones_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.app_zones import zms_list_app_zones

        mock_client = MagicMock()
        mock_client.zms.app_zones.list_app_zones.return_value = (
            {
                "nodes": [{"appZoneName": "production", "memberCount": 25}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_app_zones()

        assert len(result) == 1
        assert result[0]["nodes"][0]["appZoneName"] == "production"


class TestZMSAppCatalogTools:
    """Tests for ZMS App Catalog tools."""

    @patch("zscaler_mcp.tools.zms.app_catalog.get_zscaler_client")
    def test_list_app_catalog_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.app_catalog import zms_list_app_catalog

        mock_client = MagicMock()
        mock_client.zms.app_catalog.list_app_catalog.return_value = (
            {
                "nodes": [{"name": "nginx", "category": "WEB_SERVER"}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_app_catalog()

        assert len(result) == 1
        assert result[0]["nodes"][0]["name"] == "nginx"


class TestZMSNonceTools:
    """Tests for ZMS Nonce (Provisioning Key) tools."""

    @patch("zscaler_mcp.tools.zms.nonces.get_zscaler_client")
    def test_list_nonces_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.nonces import zms_list_nonces

        mock_client = MagicMock()
        mock_client.zms.nonces.list_nonces.return_value = (
            {
                "nodes": [{"name": "prod-key-1", "maxUsage": 10, "usageCount": 3}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_nonces()

        assert len(result) == 1
        assert result[0]["nodes"][0]["maxUsage"] == 10

    @patch("zscaler_mcp.tools.zms.nonces.get_zscaler_client")
    def test_get_nonce_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.nonces import zms_get_nonce

        mock_client = MagicMock()
        mock_client.zms.nonces.get_nonce.return_value = (
            {"nonce": {"name": "prod-key-1", "key": "abc-xyz-123"}},
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_get_nonce(eyez_id="nonce-abc-123")

        assert len(result) == 1
        assert result[0]["nonce"]["name"] == "prod-key-1"


class TestZMSTagTools:
    """Tests for ZMS Tag tools."""

    @patch("zscaler_mcp.tools.zms.tags.get_zscaler_client")
    def test_list_tag_namespaces_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.tags import zms_list_tag_namespaces

        mock_client = MagicMock()
        mock_client.zms.tags.list_tag_namespaces.return_value = (
            {
                "nodes": [{"name": "aws-tags", "origin": "EXTERNAL"}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_tag_namespaces()

        assert len(result) == 1
        assert result[0]["nodes"][0]["origin"] == "EXTERNAL"

    @patch("zscaler_mcp.tools.zms.tags.get_zscaler_client")
    def test_list_tag_keys_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.tags import zms_list_tag_keys

        mock_client = MagicMock()
        mock_client.zms.tags.list_tag_keys.return_value = (
            {
                "nodes": [{"name": "environment", "id": "key-123"}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_tag_keys(namespace_id="ns-abc-123")

        assert len(result) == 1
        assert result[0]["nodes"][0]["name"] == "environment"

    @patch("zscaler_mcp.tools.zms.tags.get_zscaler_client")
    def test_list_tag_values_success(self, mock_get_client):
        from zscaler_mcp.tools.zms.tags import zms_list_tag_values

        mock_client = MagicMock()
        mock_client.zms.tags.list_tag_values.return_value = (
            {
                "nodes": [{"name": "production", "id": "val-123"}],
                "pageInfo": {"totalCount": 1},
            },
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_tag_values(tag_id="key-123", namespace_origin="CUSTOM")

        assert len(result) == 1
        assert result[0]["nodes"][0]["name"] == "production"

    @patch("zscaler_mcp.tools.zms.tags.get_zscaler_client")
    def test_list_tag_values_empty_result(self, mock_get_client):
        from zscaler_mcp.tools.zms.tags import zms_list_tag_values

        mock_client = MagicMock()
        mock_client.zms.tags.list_tag_values.return_value = (
            None,
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"ZSCALER_CUSTOMER_ID": "test-customer-123"}):
            result = zms_list_tag_values(tag_id="key-123", namespace_origin="ML")

        assert len(result) == 1
        assert result[0]["status"] == "no_data"
