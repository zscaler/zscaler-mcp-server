"""
Unit tests for ZIA Rule Labels tools.

This module tests the verb-based rule label operations:
- zia_list_rule_labels (read-only)
- zia_get_rule_label (read-only)
- zia_create_rule_label (write)
- zia_update_rule_label (write)
- zia_delete_rule_label (write)
"""

import pytest
from unittest.mock import MagicMock, patch
from zscaler_mcp.tools.zia.rule_labels import (
    zia_list_rule_labels,
    zia_get_rule_label,
    zia_create_rule_label,
    zia_update_rule_label,
    zia_delete_rule_label,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_client():
    """Create a mock Zscaler client with ZIA rule_labels API."""
    client = MagicMock()
    client.zia.rule_labels = MagicMock()
    return client


@pytest.fixture
def mock_label():
    """Create a mock rule label object."""
    label = MagicMock()
    label.as_dict.return_value = {
        "id": 12345,
        "name": "Test Label",
        "description": "Test Description"
    }
    return label


@pytest.fixture
def mock_label_list():
    """Create a list of mock rule labels."""
    labels = []
    for i in range(3):
        label = MagicMock()
        label.as_dict.return_value = {
            "id": 10000 + i,
            "name": f"Label {i}",
            "description": f"Description {i}"
        }
        labels.append(label)
    return labels


# =============================================================================
# READ-ONLY OPERATIONS TESTS
# =============================================================================

class TestZiaListRuleLabels:
    """Test cases for zia_list_rule_labels function."""

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_list_labels_success(self, mock_get_client, mock_client, mock_label_list):
        """Test successful listing of rule labels."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.list_labels.return_value = (mock_label_list, None, None)

        # Execute
        result = zia_list_rule_labels()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zia")
        mock_client.zia.rule_labels.list_labels.assert_called_once_with(query_params={})
        assert len(result) == 3
        assert result[0]["name"] == "Label 0"
        assert result[1]["name"] == "Label 1"
        assert result[2]["name"] == "Label 2"

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_list_labels_with_query_params(self, mock_get_client, mock_client, mock_label_list):
        """Test listing labels with query parameters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.list_labels.return_value = (mock_label_list, None, None)
        query_params = {"search": "Test", "page": 1}

        # Execute
        result = zia_list_rule_labels(query_params=query_params)

        # Verify
        mock_client.zia.rule_labels.list_labels.assert_called_once_with(query_params=query_params)
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_list_labels_with_error(self, mock_get_client, mock_client):
        """Test listing labels with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.list_labels.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zia_list_rule_labels()
        assert "List failed: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_list_labels_legacy_mode(self, mock_get_client, mock_client, mock_label_list):
        """Test listing labels using legacy API."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.list_labels.return_value = (mock_label_list, None, None)

        # Execute
        result = zia_list_rule_labels(use_legacy=True)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="zia")
        assert len(result) == 3


class TestZiaGetRuleLabel:
    """Test cases for zia_get_rule_label function."""

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_get_label_success(self, mock_get_client, mock_client, mock_label):
        """Test successful retrieval of a single rule label."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.get_label.return_value = (mock_label, None, None)

        # Execute
        result = zia_get_rule_label(label_id=12345)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zia")
        mock_client.zia.rule_labels.get_label.assert_called_once_with(label_id=12345)
        assert result["id"] == 12345
        assert result["name"] == "Test Label"
        assert result["description"] == "Test Description"

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_get_label_with_error(self, mock_get_client, mock_client):
        """Test getting label with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.get_label.return_value = (None, None, "Not Found")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zia_get_rule_label(label_id=99999)
        assert "Read failed: Not Found" in str(exc_info.value)

    def test_get_label_missing_id(self):
        """Test getting label without providing label_id."""
        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            zia_get_rule_label(label_id=None)
        assert "label_id is required" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_get_label_legacy_mode(self, mock_get_client, mock_client, mock_label):
        """Test getting label using legacy API."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.get_label.return_value = (mock_label, None, None)

        # Execute
        result = zia_get_rule_label(label_id=12345, use_legacy=True)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="zia")
        assert result["id"] == 12345


# =============================================================================
# WRITE OPERATIONS TESTS
# =============================================================================

class TestZiaCreateRuleLabel:
    """Test cases for zia_create_rule_label function."""

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_create_label_success(self, mock_get_client, mock_client, mock_label):
        """Test successful creation of a rule label."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.add_label.return_value = (mock_label, None, None)

        # Execute
        result = zia_create_rule_label(name="Test Label", description="Test Description")

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zia")
        mock_client.zia.rule_labels.add_label.assert_called_once_with(
            name="Test Label",
            description="Test Description"
        )
        assert result["id"] == 12345
        assert result["name"] == "Test Label"

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_create_label_without_description(self, mock_get_client, mock_client, mock_label):
        """Test creating label without optional description."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.add_label.return_value = (mock_label, None, None)

        # Execute
        result = zia_create_rule_label(name="Test Label")

        # Verify
        mock_client.zia.rule_labels.add_label.assert_called_once_with(name="Test Label")
        assert result["id"] == 12345

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_create_label_with_error(self, mock_get_client, mock_client):
        """Test creating label with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.add_label.return_value = (None, None, "Creation Failed")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zia_create_rule_label(name="Test Label")
        assert "Create failed: Creation Failed" in str(exc_info.value)

    def test_create_label_missing_name(self):
        """Test creating label without required name."""
        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            zia_create_rule_label(name="")
        assert "Label name is required for creation" in str(exc_info.value)


class TestZiaUpdateRuleLabel:
    """Test cases for zia_update_rule_label function."""

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_update_label_name_only(self, mock_get_client, mock_client, mock_label):
        """Test updating label name only."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.update_label.return_value = (mock_label, None, None)

        # Execute
        result = zia_update_rule_label(label_id=12345, name="Updated Name")

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zia")
        mock_client.zia.rule_labels.update_label.assert_called_once_with(
            label_id=12345,
            name="Updated Name"
        )
        assert result["id"] == 12345

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_update_label_description_only(self, mock_get_client, mock_client, mock_label):
        """Test updating label description only."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.update_label.return_value = (mock_label, None, None)

        # Execute
        result = zia_update_rule_label(label_id=12345, description="Updated Description")

        # Verify
        mock_client.zia.rule_labels.update_label.assert_called_once_with(
            label_id=12345,
            description="Updated Description"
        )
        assert result["id"] == 12345

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_update_label_both_fields(self, mock_get_client, mock_client, mock_label):
        """Test updating both name and description."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.update_label.return_value = (mock_label, None, None)

        # Execute
        result = zia_update_rule_label(
            label_id=12345,
            name="Updated Name",
            description="Updated Description"
        )

        # Verify
        mock_client.zia.rule_labels.update_label.assert_called_once_with(
            label_id=12345,
            name="Updated Name",
            description="Updated Description"
        )
        assert result["id"] == 12345

    def test_update_label_missing_id(self):
        """Test updating label without label_id."""
        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            zia_update_rule_label(label_id=None, name="Test")
        assert "label_id is required for update" in str(exc_info.value)

    def test_update_label_no_fields(self):
        """Test updating label without any fields to update."""
        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            zia_update_rule_label(label_id=12345)
        assert "At least one field (name or description) must be provided for update" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_update_label_with_error(self, mock_get_client, mock_client):
        """Test updating label with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.update_label.return_value = (None, None, "Update Failed")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zia_update_rule_label(label_id=12345, name="Updated Name")
        assert "Update failed: Update Failed" in str(exc_info.value)


class TestZiaDeleteRuleLabel:
    """Test cases for zia_delete_rule_label function."""

    def test_delete_label_without_confirmation(self):
        """Test that delete requires confirmation."""
        # Execute without confirmation
        result = zia_delete_rule_label(label_id=12345)
        
        # Verify confirmation is required
        assert isinstance(result, str)
        assert "DESTRUCTIVE OPERATION" in result
        assert "CONFIRMATION REQUIRED" in result

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_delete_label_success(self, mock_get_client, mock_client):
        """Test successful deletion of a rule label with confirmation."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.delete_label.return_value = (None, None, None)

        # Execute with confirmation
        result = zia_delete_rule_label(label_id=12345, kwargs='{"confirmed": true}')

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zia")
        mock_client.zia.rule_labels.delete_label.assert_called_once_with(label_id=12345)
        assert result == "Deleted rule label 12345"

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_delete_label_with_error(self, mock_get_client, mock_client):
        """Test deleting label with API error (with confirmation)."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.delete_label.return_value = (None, None, "Delete Failed")

        # Execute & Verify (with confirmation)
        with pytest.raises(Exception) as exc_info:
            zia_delete_rule_label(label_id=12345, kwargs='{"confirmed": true}')
        assert "Delete failed: Delete Failed" in str(exc_info.value)

    def test_delete_label_missing_id(self):
        """Test deleting label without label_id (confirmation will check ID too)."""
        # Execute without confirmation - should return confirmation message
        result = zia_delete_rule_label(label_id=None)
        
        # Even without ID, confirmation message should be shown first
        assert isinstance(result, str)

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_delete_label_legacy_mode(self, mock_get_client, mock_client):
        """Test deleting label using legacy API with confirmation."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zia.rule_labels.delete_label.return_value = (None, None, None)

        # Execute with confirmation
        result = zia_delete_rule_label(label_id=12345, use_legacy=True, kwargs='{"confirmed": true}')

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="zia")
        assert result == "Deleted rule label 12345"


# =============================================================================
# INTEGRATION TESTS (Multiple Operations)
# =============================================================================

class TestRuleLabelWorkflow:
    """Test cases for complete CRUD workflow."""

    @patch("zscaler_mcp.tools.zia.rule_labels.get_zscaler_client")
    def test_full_crud_workflow(self, mock_get_client, mock_client):
        """Test complete create-read-update-delete workflow."""
        # Setup mock client
        mock_get_client.return_value = mock_client

        # 1. Create
        created_label = MagicMock()
        created_label.as_dict.return_value = {"id": 12345, "name": "New Label", "description": "New Description"}
        mock_client.zia.rule_labels.add_label.return_value = (created_label, None, None)

        result = zia_create_rule_label(name="New Label", description="New Description")
        assert result["id"] == 12345
        assert result["name"] == "New Label"

        # 2. Read
        read_label = MagicMock()
        read_label.as_dict.return_value = {"id": 12345, "name": "New Label", "description": "New Description"}
        mock_client.zia.rule_labels.get_label.return_value = (read_label, None, None)

        result = zia_get_rule_label(label_id=12345)
        assert result["id"] == 12345

        # 3. Update
        updated_label = MagicMock()
        updated_label.as_dict.return_value = {"id": 12345, "name": "Updated Label", "description": "Updated Description"}
        mock_client.zia.rule_labels.update_label.return_value = (updated_label, None, None)

        result = zia_update_rule_label(label_id=12345, name="Updated Label")
        assert result["name"] == "Updated Label"

        # 4. Delete (with confirmation)
        mock_client.zia.rule_labels.delete_label.return_value = (None, None, None)
        result = zia_delete_rule_label(label_id=12345, kwargs='{"confirmed": true}')
        assert "Deleted" in result

