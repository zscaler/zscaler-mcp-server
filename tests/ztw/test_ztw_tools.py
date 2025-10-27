"""
Unit tests for ZTW (Zscaler Tenant Workload) tools.

This module tests all 15 ZTW tools:
Read-only operations (9):
- ztw_list_ip_destination_groups, ztw_list_ip_destination_groups_lite
- ztw_list_ip_groups, ztw_list_ip_groups_lite  
- ztw_list_ip_source_groups, ztw_list_ip_source_groups_lite
- ztw_list_network_service_groups
- ztw_list_admins (with action parameter)
- ztw_list_roles

Write operations (6):
- ztw_create_ip_destination_group, ztw_delete_ip_destination_group
- ztw_create_ip_group, ztw_delete_ip_group
- ztw_create_ip_source_group, ztw_delete_ip_source_group
"""

import pytest
from unittest.mock import MagicMock, patch
from zscaler_mcp.tools.ztw.ip_destination_groups import (
    ztw_list_ip_destination_groups,
    ztw_list_ip_destination_groups_lite,
    ztw_create_ip_destination_group,
    ztw_delete_ip_destination_group,
)
from zscaler_mcp.tools.ztw.ip_groups import (
    ztw_list_ip_groups,
    ztw_list_ip_groups_lite,
    ztw_create_ip_group,
    ztw_delete_ip_group,
)
from zscaler_mcp.tools.ztw.ip_source_groups import (
    ztw_list_ip_source_groups,
    ztw_list_ip_source_groups_lite,
    ztw_create_ip_source_group,
    ztw_delete_ip_source_group,
)
from zscaler_mcp.tools.ztw.list_admins import ztw_list_admins
from zscaler_mcp.tools.ztw.list_roles import ztw_list_roles
from zscaler_mcp.tools.ztw.network_service_groups import ztw_list_network_service_groups


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_client():
    """Create a mock Zscaler client with ZTW API."""
    client = MagicMock()
    client.ztw.ip_destination_groups = MagicMock()
    client.ztw.ip_groups = MagicMock()
    client.ztw.ip_source_groups = MagicMock()
    client.ztw.admin_users = MagicMock()
    client.ztw.admin_roles = MagicMock()
    client.ztw.nw_service_groups = MagicMock()
    return client


@pytest.fixture
def mock_group_list():
    """Create a list of mock groups."""
    groups = []
    for i in range(3):
        group = MagicMock()
        group.as_dict.return_value = {
            "id": f"group{i}",
            "name": f"Test Group {i}",
            "description": f"Description {i}"
        }
        groups.append(group)
    return groups


@pytest.fixture
def mock_group():
    """Create a single mock group."""
    group = MagicMock()
    group.as_dict.return_value = {
        "id": "group123",
        "name": "Test Group",
        "description": "Test Description",
        "addresses": ["192.168.1.1", "192.168.1.2"]
    }
    return group


# =============================================================================
# IP DESTINATION GROUPS TESTS
# =============================================================================

class TestZtwIpDestinationGroups:
    """Test cases for ZTW IP destination groups functions."""

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_list_ip_destination_groups_success(self, mock_get_client, mock_client, mock_group_list):
        """Test successful listing of IP destination groups."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_destination_groups.list_ip_destination_groups.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_destination_groups()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="ztw")
        mock_client.ztw.ip_destination_groups.list_ip_destination_groups.assert_called_once_with(query_params={})
        assert len(result) == 3
        assert result[0]["name"] == "Test Group 0"

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_list_ip_destination_groups_with_filter(self, mock_get_client, mock_client, mock_group_list):
        """Test listing IP destination groups with exclude_type filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_destination_groups.list_ip_destination_groups.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_destination_groups(exclude_type="DSTN_FQDN")

        # Verify
        mock_client.ztw.ip_destination_groups.list_ip_destination_groups.assert_called_once_with(
            query_params={"exclude_type": "DSTN_FQDN"}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_list_ip_destination_groups_with_error(self, mock_get_client, mock_client):
        """Test listing IP destination groups with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_destination_groups.list_ip_destination_groups.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            ztw_list_ip_destination_groups()
        assert "Failed to list IP destination groups: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_list_ip_destination_groups_lite_success(self, mock_get_client, mock_client, mock_group_list):
        """Test successful listing of IP destination groups (lite version)."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_destination_groups.list_ip_destination_groups_lite.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_destination_groups_lite()

        # Verify
        mock_client.ztw.ip_destination_groups.list_ip_destination_groups_lite.assert_called_once_with(query_params={})
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_create_ip_destination_group_success(self, mock_get_client, mock_client, mock_group):
        """Test successful creation of IP destination group."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_destination_groups.add_ip_destination_group.return_value = (mock_group, None, None)

        # Execute
        result = ztw_create_ip_destination_group(
            name="Test Group",
            type="DSTN_IP",
            addresses=["192.168.1.1", "192.168.1.2"]
        )

        # Verify
        mock_client.ztw.ip_destination_groups.add_ip_destination_group.assert_called_once()
        call_kwargs = mock_client.ztw.ip_destination_groups.add_ip_destination_group.call_args[1]
        assert call_kwargs["name"] == "Test Group"
        assert call_kwargs["type"] == "DSTN_IP"
        assert result["id"] == "group123"

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.validate_and_convert_country_codes")
    def test_create_ip_destination_group_with_countries(self, mock_validate, mock_get_client, mock_client, mock_group):
        """Test creating IP destination group with countries."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_validate.return_value = ["COUNTRY_CA", "COUNTRY_US"]
        mock_client.ztw.ip_destination_groups.add_ip_destination_group.return_value = (mock_group, None, None)

        # Execute
        ztw_create_ip_destination_group(
            name="Test Group",
            type="DSTN_OTHER",
            countries=["CA", "US"]
        )

        # Verify
        mock_validate.assert_called_once_with(["CA", "US"])
        call_kwargs = mock_client.ztw.ip_destination_groups.add_ip_destination_group.call_args[1]
        assert call_kwargs["countries"] == ["COUNTRY_CA", "COUNTRY_US"]

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_create_ip_destination_group_missing_required(self, mock_get_client, mock_client):
        """Test creating IP destination group without required fields."""
        # Setup
        mock_get_client.return_value = mock_client

        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            ztw_create_ip_destination_group(name="", type="DSTN_IP")
        assert "name and type are required" in str(exc_info.value)

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_create_ip_destination_group_invalid_country_type(self, mock_get_client, mock_client):
        """Test creating IP destination group with countries for wrong type."""
        # Setup
        mock_get_client.return_value = mock_client

        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            ztw_create_ip_destination_group(
                name="Test", 
                type="DSTN_IP",  # Not DSTN_OTHER
                countries=["US"]
            )
        assert "Countries are only supported when type is DSTN_OTHER" in str(exc_info.value)

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_delete_ip_destination_group_success(self, mock_get_client, mock_client):
        """Test successful deletion of IP destination group."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_destination_groups.delete_ip_destination_group.return_value = (None, None, None)

        # Execute with confirmation
        result = ztw_delete_ip_destination_group(group_id="123", kwargs='{"confirmed": true}')

        # Verify
        mock_client.ztw.ip_destination_groups.delete_ip_destination_group.assert_called_once_with("123")
        assert "Group 123 deleted successfully" in result

    @patch("zscaler_mcp.tools.ztw.ip_destination_groups.get_zscaler_client")
    def test_delete_ip_destination_group_missing_id(self, mock_get_client, mock_client):
        """Test deleting IP destination group without ID (confirmation still blocks)."""
        # Setup
        mock_get_client.return_value = mock_client

        # Execute without confirmation - returns confirmation message
        result = ztw_delete_ip_destination_group(group_id="")
        assert isinstance(result, str)  # Returns confirmation message


# =============================================================================
# IP GROUPS TESTS
# =============================================================================

class TestZtwIpGroups:
    """Test cases for ZTW IP groups functions."""

    @patch("zscaler_mcp.tools.ztw.ip_groups.get_zscaler_client")
    def test_list_ip_groups_success(self, mock_get_client, mock_client, mock_group_list):
        """Test successful listing of IP groups."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_groups.list_ip_groups.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_groups()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="ztw")
        mock_client.ztw.ip_groups.list_ip_groups.assert_called_once_with(query_params={})
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_groups.get_zscaler_client")
    def test_list_ip_groups_with_search(self, mock_get_client, mock_client, mock_group_list):
        """Test listing IP groups with search filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_groups.list_ip_groups.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_groups(search="test")

        # Verify
        mock_client.ztw.ip_groups.list_ip_groups.assert_called_once_with(query_params={"search": "test"})
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_groups.get_zscaler_client")
    def test_list_ip_groups_lite_success(self, mock_get_client, mock_client, mock_group_list):
        """Test successful listing of IP groups (lite version)."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_groups.list_ip_groups_lite.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_groups_lite(search="test")

        # Verify
        mock_client.ztw.ip_groups.list_ip_groups_lite.assert_called_once_with(query_params={"search": "test"})
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_groups.get_zscaler_client")
    def test_create_ip_group_success(self, mock_get_client, mock_client, mock_group):
        """Test successful creation of IP group."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_groups.add_ip_group.return_value = (mock_group, None, None)

        # Execute
        result = ztw_create_ip_group(
            name="Test Group",
            ip_addresses=["192.168.1.1", "192.168.1.2"]
        )

        # Verify
        mock_client.ztw.ip_groups.add_ip_group.assert_called_once()
        call_kwargs = mock_client.ztw.ip_groups.add_ip_group.call_args[1]
        assert call_kwargs["name"] == "Test Group"
        assert result["id"] == "group123"

    @patch("zscaler_mcp.tools.ztw.ip_groups.get_zscaler_client")
    def test_create_ip_group_with_json_string(self, mock_get_client, mock_client, mock_group):
        """Test creating IP group with JSON string for IP addresses."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_groups.add_ip_group.return_value = (mock_group, None, None)

        # Execute
        ztw_create_ip_group(
            name="Test Group",
            ip_addresses='["192.168.1.1", "192.168.1.2"]'
        )

        # Verify
        call_kwargs = mock_client.ztw.ip_groups.add_ip_group.call_args[1]
        assert call_kwargs["ip_addresses"] == ["192.168.1.1", "192.168.1.2"]

    @patch("zscaler_mcp.tools.ztw.ip_groups.get_zscaler_client")
    def test_create_ip_group_missing_required(self, mock_get_client, mock_client):
        """Test creating IP group without required fields."""
        # Setup
        mock_get_client.return_value = mock_client

        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            ztw_create_ip_group(name="", ip_addresses=[])
        assert "Both name and ip_addresses are required" in str(exc_info.value)

    @patch("zscaler_mcp.tools.ztw.ip_groups.get_zscaler_client")
    def test_delete_ip_group_success(self, mock_get_client, mock_client):
        """Test successful deletion of IP group."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_groups.delete_ip_group.return_value = (None, None, None)

        # Execute with confirmation
        result = ztw_delete_ip_group(group_id=123, kwargs='{"confirmed": true}')

        # Verify
        mock_client.ztw.ip_groups.delete_ip_group.assert_called_once_with(123)
        assert "Group 123 deleted successfully" in result


# =============================================================================
# IP SOURCE GROUPS TESTS
# =============================================================================

class TestZtwIpSourceGroups:
    """Test cases for ZTW IP source groups functions."""

    @patch("zscaler_mcp.tools.ztw.ip_source_groups.get_zscaler_client")
    def test_list_ip_source_groups_success(self, mock_get_client, mock_client, mock_group_list):
        """Test successful listing of IP source groups."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_source_groups.list_ip_source_groups.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_source_groups()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="ztw")
        mock_client.ztw.ip_source_groups.list_ip_source_groups.assert_called_once_with(query_params={})
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_source_groups.get_zscaler_client")
    def test_list_ip_source_groups_with_search(self, mock_get_client, mock_client, mock_group_list):
        """Test listing IP source groups with search filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_source_groups.list_ip_source_groups.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_source_groups(search="prod")

        # Verify
        mock_client.ztw.ip_source_groups.list_ip_source_groups.assert_called_once_with(query_params={"search": "prod"})
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_source_groups.get_zscaler_client")
    def test_list_ip_source_groups_lite_success(self, mock_get_client, mock_client, mock_group_list):
        """Test successful listing of IP source groups (lite version)."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_source_groups.list_ip_source_groups_lite.return_value = (mock_group_list, None, None)

        # Execute
        result = ztw_list_ip_source_groups_lite()

        # Verify
        mock_client.ztw.ip_source_groups.list_ip_source_groups_lite.assert_called_once_with(query_params={})
        assert len(result) == 3

    @patch("zscaler_mcp.tools.ztw.ip_source_groups.get_zscaler_client")
    def test_create_ip_source_group_success(self, mock_get_client, mock_client, mock_group):
        """Test successful creation of IP source group."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_source_groups.add_ip_source_group.return_value = (mock_group, None, None)

        # Execute
        result = ztw_create_ip_source_group(
            name="Source Group",
            ip_addresses=["10.0.0.1", "10.0.0.2"],
            description="Test source group"
        )

        # Verify
        mock_client.ztw.ip_source_groups.add_ip_source_group.assert_called_once()
        call_kwargs = mock_client.ztw.ip_source_groups.add_ip_source_group.call_args[1]
        assert call_kwargs["name"] == "Source Group"
        assert call_kwargs["description"] == "Test source group"
        assert result["id"] == "group123"

    @patch("zscaler_mcp.tools.ztw.ip_source_groups.get_zscaler_client")
    def test_delete_ip_source_group_success(self, mock_get_client, mock_client):
        """Test successful deletion of IP source group with confirmation."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.ip_source_groups.delete_ip_source_group.return_value = (None, None, None)

        # Execute with confirmation
        result = ztw_delete_ip_source_group(group_id="456", kwargs='{"confirmed": true}')

        # Verify
        mock_client.ztw.ip_source_groups.delete_ip_source_group.assert_called_once_with("456")
        assert "Group 456 deleted successfully" in result


# =============================================================================
# ADMIN USERS TESTS
# =============================================================================

class TestZtwAdmins:
    """Test cases for ZTW admin users functions."""

    @patch("zscaler_mcp.tools.ztw.list_admins.get_zscaler_client")
    def test_list_admins_success(self, mock_get_client, mock_client):
        """Test successful listing of admin users."""
        # Setup
        mock_get_client.return_value = mock_client
        admin1 = MagicMock()
        admin1.as_dict.return_value = {"id": "admin1", "username": "admin@example.com"}
        admin2 = MagicMock()
        admin2.as_dict.return_value = {"id": "admin2", "username": "user@example.com"}
        mock_client.ztw.admin_users.list_admins.return_value = ([admin1, admin2], None, None)

        # Execute
        result = ztw_list_admins()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="ztw")
        mock_client.ztw.admin_users.list_admins.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["username"] == "admin@example.com"

    @patch("zscaler_mcp.tools.ztw.list_admins.get_zscaler_client")
    def test_list_admins_with_filters(self, mock_get_client, mock_client):
        """Test listing admins with multiple filters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.admin_users.list_admins.return_value = ([], None, None)

        # Execute
        ztw_list_admins(
            action="list_admins",
            include_auditor_users=True,
            include_admin_users=True,
            include_api_roles=False,
            search="admin",
            page=1,
            page_size=10
        )

        # Verify
        call_kwargs = mock_client.ztw.admin_users.list_admins.call_args[1]["query_params"]
        assert call_kwargs["include_auditor_users"] is True
        assert call_kwargs["include_admin_users"] is True
        assert call_kwargs["include_api_roles"] is False
        assert call_kwargs["search"] == "admin"
        assert call_kwargs["page"] == 1
        assert call_kwargs["page_size"] == 10

    @patch("zscaler_mcp.tools.ztw.list_admins.get_zscaler_client")
    def test_get_admin_success(self, mock_get_client, mock_client):
        """Test successful retrieval of a specific admin."""
        # Setup
        mock_get_client.return_value = mock_client
        admin = MagicMock()
        admin.as_dict.return_value = {"id": "admin123", "username": "admin@example.com", "role": "Super Admin"}
        mock_client.ztw.admin_users.get_admin.return_value = (admin, None, None)

        # Execute
        result = ztw_list_admins(action="get_admin", admin_id="admin123")

        # Verify
        mock_client.ztw.admin_users.get_admin.assert_called_once_with("admin123")
        assert result["id"] == "admin123"
        assert result["role"] == "Super Admin"

    @patch("zscaler_mcp.tools.ztw.list_admins.get_zscaler_client")
    def test_get_admin_missing_id(self, mock_get_client, mock_client):
        """Test getting admin without providing admin_id."""
        # Setup
        mock_get_client.return_value = mock_client

        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            ztw_list_admins(action="get_admin")
        assert "admin_id is required when action is 'get_admin'" in str(exc_info.value)

    @patch("zscaler_mcp.tools.ztw.list_admins.get_zscaler_client")
    def test_list_admins_invalid_action(self, mock_get_client, mock_client):
        """Test listing admins with invalid action."""
        # Setup
        mock_get_client.return_value = mock_client

        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            ztw_list_admins(action="invalid_action")
        assert "Invalid action 'invalid_action'" in str(exc_info.value)

    @patch("zscaler_mcp.tools.ztw.list_admins.get_zscaler_client")
    def test_list_admins_with_version(self, mock_get_client, mock_client):
        """Test listing admins from backup version."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.admin_users.list_admins.return_value = ([], None, None)

        # Execute
        ztw_list_admins(version=1)

        # Verify
        call_kwargs = mock_client.ztw.admin_users.list_admins.call_args[1]["query_params"]
        assert call_kwargs["version"] == 1


# =============================================================================
# ADMIN ROLES TESTS
# =============================================================================

class TestZtwRoles:
    """Test cases for ZTW admin roles functions."""

    @patch("zscaler_mcp.tools.ztw.list_roles.get_zscaler_client")
    def test_list_roles_success(self, mock_get_client, mock_client):
        """Test successful listing of admin roles."""
        # Setup
        mock_get_client.return_value = mock_client
        role1 = MagicMock()
        role1.as_dict.return_value = {"id": "role1", "name": "Super Admin"}
        role2 = MagicMock()
        role2.as_dict.return_value = {"id": "role2", "name": "Auditor"}
        mock_client.ztw.admin_roles.list_roles.return_value = ([role1, role2], None, None)

        # Execute
        result = ztw_list_roles()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="ztw")
        mock_client.ztw.admin_roles.list_roles.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["name"] == "Super Admin"

    @patch("zscaler_mcp.tools.ztw.list_roles.get_zscaler_client")
    def test_list_roles_with_filters(self, mock_get_client, mock_client):
        """Test listing roles with multiple filters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.admin_roles.list_roles.return_value = ([], None, None)

        # Execute
        ztw_list_roles(
            include_auditor_role=True,
            include_partner_role=False,
            include_api_roles=True,
            search="admin"
        )

        # Verify
        call_kwargs = mock_client.ztw.admin_roles.list_roles.call_args[1]["query_params"]
        assert call_kwargs["include_auditor_role"] is True
        assert call_kwargs["include_partner_role"] is False
        assert call_kwargs["include_api_roles"] is True
        assert call_kwargs["search"] == "admin"

    @patch("zscaler_mcp.tools.ztw.list_roles.get_zscaler_client")
    def test_list_roles_with_role_ids(self, mock_get_client, mock_client):
        """Test listing specific roles by ID."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.admin_roles.list_roles.return_value = ([], None, None)

        # Execute
        ztw_list_roles(role_ids=["123", "456"])

        # Verify
        call_kwargs = mock_client.ztw.admin_roles.list_roles.call_args[1]["query_params"]
        assert call_kwargs["id"] == ["123", "456"]

    @patch("zscaler_mcp.tools.ztw.list_roles.get_zscaler_client")
    def test_list_roles_with_error(self, mock_get_client, mock_client):
        """Test listing roles with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.admin_roles.list_roles.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            ztw_list_roles()
        assert "Error listing ZTW admin roles: API Error" in str(exc_info.value)


# =============================================================================
# NETWORK SERVICE GROUPS TESTS
# =============================================================================

class TestZtwNetworkServiceGroups:
    """Test cases for ZTW network service groups functions."""

    @patch("zscaler_mcp.tools.ztw.network_service_groups.get_zscaler_client")
    def test_list_network_service_groups_success(self, mock_get_client, mock_client):
        """Test successful listing of network service groups."""
        # Setup
        mock_get_client.return_value = mock_client
        group1 = MagicMock()
        group1.as_dict.return_value = {"id": "nsg1", "name": "HTTP Services"}
        group2 = MagicMock()
        group2.as_dict.return_value = {"id": "nsg2", "name": "HTTPS Services"}
        mock_client.ztw.nw_service_groups.list_network_svc_groups.return_value = ([group1, group2], None, None)

        # Execute
        result = ztw_list_network_service_groups()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="ztw")
        mock_client.ztw.nw_service_groups.list_network_svc_groups.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["name"] == "HTTP Services"

    @patch("zscaler_mcp.tools.ztw.network_service_groups.get_zscaler_client")
    def test_list_network_service_groups_with_search(self, mock_get_client, mock_client):
        """Test listing network service groups with search filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.nw_service_groups.list_network_svc_groups.return_value = ([], None, None)

        # Execute
        ztw_list_network_service_groups(search="HTTP")

        # Verify
        mock_client.ztw.nw_service_groups.list_network_svc_groups.assert_called_once_with(
            query_params={"search": "HTTP"}
        )

    @patch("zscaler_mcp.tools.ztw.network_service_groups.get_zscaler_client")
    def test_list_network_service_groups_with_error(self, mock_get_client, mock_client):
        """Test listing network service groups with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.nw_service_groups.list_network_svc_groups.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            ztw_list_network_service_groups()
        assert "Error listing network service groups: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.ztw.network_service_groups.get_zscaler_client")
    def test_list_network_service_groups_legacy_mode(self, mock_get_client, mock_client):
        """Test listing network service groups using legacy API."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.ztw.nw_service_groups.list_network_svc_groups.return_value = ([], None, None)

        # Execute
        ztw_list_network_service_groups(use_legacy=True)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="ztw")

