"""
Unit tests for ZID (ZIdentity) tools.

Covers: groups.py, users.py
"""

from unittest.mock import MagicMock, patch

import pytest


def _mock_obj(data: dict):
    obj = MagicMock()
    obj.as_dict.return_value = data
    return obj


def _mock_response(records):
    """Create a mock SDK response with .records attribute."""
    resp = MagicMock()
    resp.records = records
    return resp


# ============================================================================
# GROUPS
# ============================================================================


class TestZidGroups:

    @patch("zscaler_mcp.tools.zid.groups.get_zscaler_client")
    def test_list_groups(self, mock_get_client):
        from zscaler_mcp.tools.zid.groups import zid_list_groups

        mock_client = MagicMock()
        groups = [_mock_obj({"id": f"g{i}", "name": f"Group {i}"}) for i in range(3)]
        groups_response = _mock_response(groups)
        mock_client.zid.groups.list_groups.return_value = (groups_response, None, None)
        mock_get_client.return_value = mock_client

        result = zid_list_groups()
        assert len(result) == 3
        assert result[0]["name"] == "Group 0"

    @patch("zscaler_mcp.tools.zid.groups.get_zscaler_client")
    def test_list_groups_with_jmespath(self, mock_get_client):
        from zscaler_mcp.tools.zid.groups import zid_list_groups

        mock_client = MagicMock()
        groups = [
            _mock_obj({"id": "g1", "name": "Admins"}),
            _mock_obj({"id": "g2", "name": "Users"}),
        ]
        groups_response = _mock_response(groups)
        mock_client.zid.groups.list_groups.return_value = (groups_response, None, None)
        mock_get_client.return_value = mock_client

        result = zid_list_groups(query="[?name == 'Admins']")
        assert len(result) == 1
        assert result[0]["name"] == "Admins"

    @patch("zscaler_mcp.tools.zid.groups.get_zscaler_client")
    def test_list_groups_error(self, mock_get_client):
        from zscaler_mcp.tools.zid.groups import zid_list_groups

        mock_client = MagicMock()
        mock_client.zid.groups.list_groups.return_value = (None, None, "API Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zid_list_groups()

    @patch("zscaler_mcp.tools.zid.groups.get_zscaler_client")
    def test_get_group(self, mock_get_client):
        from zscaler_mcp.tools.zid.groups import zid_get_group

        mock_client = MagicMock()
        group = _mock_obj({"id": "g1", "name": "Engineering"})
        mock_client.zid.groups.get_group.return_value = (group, None, None)
        mock_get_client.return_value = mock_client

        result = zid_get_group(group_id="g1")
        assert result["name"] == "Engineering"

    def test_get_group_missing_id(self):
        from zscaler_mcp.tools.zid.groups import zid_get_group

        with pytest.raises(ValueError):
            zid_get_group(group_id="")

    @patch("zscaler_mcp.tools.zid.groups.get_zscaler_client")
    def test_search_groups(self, mock_get_client):
        from zscaler_mcp.tools.zid.groups import zid_search_groups

        mock_client = MagicMock()
        groups = [_mock_obj({"id": "g1", "name": "Engineering"})]
        groups_response = _mock_response(groups)
        mock_client.zid.groups.list_groups.return_value = (groups_response, None, None)
        mock_get_client.return_value = mock_client

        result = zid_search_groups(name="Engineer")
        assert len(result) == 1

    def test_search_groups_empty_name(self):
        from zscaler_mcp.tools.zid.groups import zid_search_groups

        with pytest.raises(ValueError):
            zid_search_groups(name="")

    @patch("zscaler_mcp.tools.zid.groups.get_zscaler_client")
    def test_get_group_users(self, mock_get_client):
        from zscaler_mcp.tools.zid.groups import zid_get_group_users

        mock_client = MagicMock()
        users = [_mock_obj({"id": "u1", "name": "Alice"}), _mock_obj({"id": "u2", "name": "Bob"})]
        users_response = _mock_response(users)
        mock_client.zid.groups.list_group_users_details.return_value = (users_response, None, None)
        mock_get_client.return_value = mock_client

        result = zid_get_group_users(group_id="g1")
        assert len(result) == 2

    def test_get_group_users_missing_id(self):
        from zscaler_mcp.tools.zid.groups import zid_get_group_users

        with pytest.raises(ValueError):
            zid_get_group_users(group_id="")


# ============================================================================
# USERS
# ============================================================================


class TestZidUsers:

    @patch("zscaler_mcp.tools.zid.users.get_zscaler_client")
    def test_list_users(self, mock_get_client):
        from zscaler_mcp.tools.zid.users import zid_list_users

        mock_client = MagicMock()
        users = [_mock_obj({"id": f"u{i}", "name": f"User {i}"}) for i in range(3)]
        users_response = _mock_response(users)
        mock_client.zid.users.list_users.return_value = (users_response, None, None)
        mock_get_client.return_value = mock_client

        result = zid_list_users()
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zid.users.get_zscaler_client")
    def test_list_users_with_jmespath(self, mock_get_client):
        from zscaler_mcp.tools.zid.users import zid_list_users

        mock_client = MagicMock()
        users = [
            _mock_obj({"id": "u1", "name": "Alice", "status": "active"}),
            _mock_obj({"id": "u2", "name": "Bob", "status": "inactive"}),
        ]
        users_response = _mock_response(users)
        mock_client.zid.users.list_users.return_value = (users_response, None, None)
        mock_get_client.return_value = mock_client

        result = zid_list_users(query="[?status == 'active']")
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zid.users.get_zscaler_client")
    def test_list_users_error(self, mock_get_client):
        from zscaler_mcp.tools.zid.users import zid_list_users

        mock_client = MagicMock()
        mock_client.zid.users.list_users.return_value = (None, None, "API Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            zid_list_users()

    @patch("zscaler_mcp.tools.zid.users.get_zscaler_client")
    def test_get_user(self, mock_get_client):
        from zscaler_mcp.tools.zid.users import zid_get_user

        mock_client = MagicMock()
        user = _mock_obj({"id": "u1", "name": "Alice", "email": "alice@example.com"})
        mock_client.zid.users.get_user.return_value = (user, None, None)
        mock_get_client.return_value = mock_client

        result = zid_get_user(user_id="u1")
        assert result["email"] == "alice@example.com"

    def test_get_user_missing_id(self):
        from zscaler_mcp.tools.zid.users import zid_get_user

        with pytest.raises(ValueError):
            zid_get_user(user_id="")

    @patch("zscaler_mcp.tools.zid.users.get_zscaler_client")
    def test_search_users_by_email(self, mock_get_client):
        from zscaler_mcp.tools.zid.users import zid_search_users

        mock_client = MagicMock()
        users = [_mock_obj({"id": "u1", "name": "Alice"})]
        users_response = _mock_response(users)
        mock_client.zid.users.list_users.return_value = (users_response, None, None)
        mock_get_client.return_value = mock_client

        result = zid_search_users(name="alice@example.com")
        assert len(result) == 1
        call_kwargs = mock_client.zid.users.list_users.call_args[1]
        assert "primary_email[like]" in call_kwargs.get("query_params", {})

    def test_search_users_empty_name(self):
        from zscaler_mcp.tools.zid.users import zid_search_users

        with pytest.raises(ValueError):
            zid_search_users(name="")

    @patch("zscaler_mcp.tools.zid.users.get_zscaler_client")
    def test_get_user_groups(self, mock_get_client):
        from zscaler_mcp.tools.zid.users import zid_get_user_groups

        mock_client = MagicMock()
        groups = [_mock_obj({"id": "g1", "name": "Admins"})]
        mock_client.zid.users.list_user_group_details.return_value = (groups, None, None)
        mock_get_client.return_value = mock_client

        result = zid_get_user_groups(user_id="u1")
        assert len(result) == 1

    def test_get_user_groups_missing_id(self):
        from zscaler_mcp.tools.zid.users import zid_get_user_groups

        with pytest.raises(ValueError):
            zid_get_user_groups(user_id="")


# ============================================================================
# SERVICE REGISTRATION
# ============================================================================


class TestZIDServiceRegistration:

    def test_zid_service_exists_in_registry(self):
        from zscaler_mcp.services import get_available_services, get_service_names

        assert "zid" in get_service_names()
        assert "zid" in get_available_services()

    def test_zid_service_has_read_tools(self):
        from zscaler_mcp.services import ZIDService

        service = ZIDService(None)
        assert len(service.read_tools) > 0

    def test_all_zid_tools_have_prefix(self):
        from zscaler_mcp.services import ZIDService

        service = ZIDService(None)
        for tool in service.read_tools:
            assert tool["name"].startswith("zid_"), f"Tool {tool['name']} missing zid_ prefix"
