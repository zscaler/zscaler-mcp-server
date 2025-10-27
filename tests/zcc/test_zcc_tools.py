"""
Unit tests for ZCC (Zscaler Client Connector) tools.

This module tests all ZCC tools:
- zcc_list_devices (read-only)
- zcc_devices_csv_exporter (read-only)
- zcc_list_forwarding_profiles (read-only)
- zcc_list_trusted_networks (read-only)
"""

from unittest.mock import MagicMock, patch

import pytest

from zscaler_mcp.tools.zcc.download_devices import zcc_devices_csv_exporter
from zscaler_mcp.tools.zcc.list_devices import zcc_list_devices
from zscaler_mcp.tools.zcc.list_forwarding_profiles import zcc_list_forwarding_profiles
from zscaler_mcp.tools.zcc.list_trusted_networks import zcc_list_trusted_networks

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_client():
    """Create a mock Zscaler client with ZCC API."""
    client = MagicMock()
    client.zcc.devices = MagicMock()
    client.zcc.forwarding_profile = MagicMock()
    client.zcc.trusted_networks = MagicMock()
    return client


@pytest.fixture
def mock_device():
    """Create a mock ZCC device object."""
    device = MagicMock()
    device.as_dict.return_value = {
        "device_id": "dev123",
        "username": "jdoe@example.com",
        "os_type": "windows",
        "device_name": "JDOE-LAPTOP"
    }
    return device


@pytest.fixture
def mock_device_list(mock_device):
    """Create a list of mock ZCC devices."""
    devices = []
    for i in range(3):
        device = MagicMock()
        device.as_dict.return_value = {
            "device_id": f"dev{i}",
            "username": f"user{i}@example.com",
            "os_type": "windows",
            "device_name": f"DEVICE-{i}"
        }
        devices.append(device)
    return devices


@pytest.fixture
def mock_profile():
    """Create a mock forwarding profile object."""
    profile = MagicMock()
    profile.as_dict.return_value = {
        "id": "prof123",
        "name": "Test Profile",
        "description": "Test forwarding profile"
    }
    return profile


@pytest.fixture
def mock_profile_list():
    """Create a list of mock forwarding profiles."""
    profiles = []
    for i in range(3):
        profile = MagicMock()
        profile.as_dict.return_value = {
            "id": f"prof{i}",
            "name": f"Profile {i}",
            "description": f"Description {i}"
        }
        profiles.append(profile)
    return profiles


@pytest.fixture
def mock_network():
    """Create a mock trusted network object."""
    network = MagicMock()
    network.as_dict.return_value = {
        "id": "net123",
        "name": "Corporate Network",
        "network_range": "192.168.1.0/24"
    }
    return network


@pytest.fixture
def mock_network_list():
    """Create a list of mock trusted networks."""
    networks = []
    for i in range(3):
        network = MagicMock()
        network.as_dict.return_value = {
            "id": f"net{i}",
            "name": f"Network {i}",
            "network_range": f"10.{i}.0.0/16"
        }
        networks.append(network)
    return networks


# =============================================================================
# ZCC LIST DEVICES TESTS
# =============================================================================

class TestZccListDevices:
    """Test cases for zcc_list_devices function."""

    @patch("zscaler_mcp.tools.zcc.list_devices.get_zscaler_client")
    def test_list_devices_success(self, mock_get_client, mock_client, mock_device_list):
        """Test successful listing of ZCC devices."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.list_devices.return_value = (mock_device_list, None, None)

        # Execute
        result = zcc_list_devices()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zcc")
        mock_client.zcc.devices.list_devices.assert_called_once_with(query_params={})
        assert len(result) == 3
        assert result[0]["device_id"] == "dev0"
        assert result[1]["username"] == "user1@example.com"

    @patch("zscaler_mcp.tools.zcc.list_devices.get_zscaler_client")
    def test_list_devices_with_username_filter(self, mock_get_client, mock_client, mock_device_list):
        """Test listing devices with username filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.list_devices.return_value = (mock_device_list, None, None)

        # Execute
        result = zcc_list_devices(username="jdoe@example.com")

        # Verify
        mock_client.zcc.devices.list_devices.assert_called_once_with(
            query_params={"username": "jdoe@example.com"}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_devices.get_zscaler_client")
    def test_list_devices_with_os_type_filter(self, mock_get_client, mock_client, mock_device_list):
        """Test listing devices with OS type filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.list_devices.return_value = (mock_device_list, None, None)

        # Execute
        result = zcc_list_devices(os_type="windows")

        # Verify
        mock_client.zcc.devices.list_devices.assert_called_once_with(
            query_params={"os_type": "windows"}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_devices.get_zscaler_client")
    def test_list_devices_with_pagination(self, mock_get_client, mock_client, mock_device_list):
        """Test listing devices with pagination."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.list_devices.return_value = (mock_device_list, None, None)

        # Execute
        result = zcc_list_devices(page=1, page_size=50)

        # Verify
        mock_client.zcc.devices.list_devices.assert_called_once_with(
            query_params={"page": 1, "page_size": 50}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_devices.get_zscaler_client")
    def test_list_devices_with_all_params(self, mock_get_client, mock_client, mock_device_list):
        """Test listing devices with all parameters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.list_devices.return_value = (mock_device_list, None, None)

        # Execute
        result = zcc_list_devices(
            username="jdoe@example.com",
            os_type="windows",
            page=1,
            page_size=100
        )

        # Verify
        mock_client.zcc.devices.list_devices.assert_called_once_with(
            query_params={
                "username": "jdoe@example.com",
                "os_type": "windows",
                "page": 1,
                "page_size": 100
            }
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_devices.get_zscaler_client")
    def test_list_devices_with_error(self, mock_get_client, mock_client):
        """Test listing devices with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.list_devices.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zcc_list_devices()
        assert "Error listing ZCC devices: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zcc.list_devices.get_zscaler_client")
    def test_list_devices_legacy_mode(self, mock_get_client, mock_client, mock_device_list):
        """Test listing devices using legacy API."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.list_devices.return_value = (mock_device_list, None, None)

        # Execute
        result = zcc_list_devices(use_legacy=True)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="zcc")
        assert len(result) == 3


# =============================================================================
# ZCC DEVICES CSV EXPORTER TESTS
# =============================================================================

class TestZccDevicesCsvExporter:
    """Test cases for zcc_devices_csv_exporter function."""

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_devices_csv_default(self, mock_get_client, mock_client):
        """Test successful CSV export with default dataset (devices)."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.download_devices.return_value = "devices.csv"

        # Execute
        result = zcc_devices_csv_exporter()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zcc")
        mock_client.zcc.devices.download_devices.assert_called_once()
        call_args = mock_client.zcc.devices.download_devices.call_args
        assert call_args[1]["query_params"] == {}
        assert "zcc-devices-" in call_args[1]["filename"]
        assert result == "devices.csv"

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_service_status_csv(self, mock_get_client, mock_client):
        """Test CSV export for service_status dataset."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.download_service_status.return_value = "service_status.csv"

        # Execute
        result = zcc_devices_csv_exporter(dataset="service_status")

        # Verify
        mock_client.zcc.devices.download_service_status.assert_called_once()
        call_args = mock_client.zcc.devices.download_service_status.call_args
        assert "zcc-service-status-" in call_args[1]["filename"]
        assert result == "service_status.csv"

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_with_os_type_filter(self, mock_get_client, mock_client):
        """Test CSV export with OS type filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.download_devices.return_value = "devices.csv"

        # Execute
        result = zcc_devices_csv_exporter(os_type="windows")

        # Verify
        call_args = mock_client.zcc.devices.download_devices.call_args
        assert call_args[1]["query_params"] == {"os_types": ["windows"]}
        assert result == "devices.csv"

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_with_registration_type_filter(self, mock_get_client, mock_client):
        """Test CSV export with registration type filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.download_devices.return_value = "devices.csv"

        # Execute
        result = zcc_devices_csv_exporter(registration_type="registered")

        # Verify
        call_args = mock_client.zcc.devices.download_devices.call_args
        assert call_args[1]["query_params"] == {"registration_types": ["registered"]}
        assert result == "devices.csv"

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_with_custom_filename(self, mock_get_client, mock_client):
        """Test CSV export with custom filename."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.download_devices.return_value = "custom.csv"

        # Execute
        result = zcc_devices_csv_exporter(filename="custom.csv")

        # Verify
        call_args = mock_client.zcc.devices.download_devices.call_args
        assert call_args[1]["filename"] == "custom.csv"
        assert result == "custom.csv"

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_with_all_params(self, mock_get_client, mock_client):
        """Test CSV export with all parameters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.download_devices.return_value = "all_params.csv"

        # Execute
        result = zcc_devices_csv_exporter(
            dataset="devices",
            os_type="macos",
            registration_type="unregistered",
            filename="all_params.csv"
        )

        # Verify
        call_args = mock_client.zcc.devices.download_devices.call_args
        assert call_args[1]["query_params"] == {
            "os_types": ["macos"],
            "registration_types": ["unregistered"]
        }
        assert call_args[1]["filename"] == "all_params.csv"
        assert result == "all_params.csv"

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_invalid_dataset(self, mock_get_client, mock_client):
        """Test CSV export with invalid dataset type."""
        # Setup
        mock_get_client.return_value = mock_client

        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            zcc_devices_csv_exporter(dataset="invalid_dataset")
        assert "Invalid dataset type" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zcc.download_devices.get_zscaler_client")
    def test_export_legacy_mode(self, mock_get_client, mock_client):
        """Test CSV export using legacy API."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.devices.download_devices.return_value = "devices.csv"

        # Execute
        result = zcc_devices_csv_exporter(use_legacy=True)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="zcc")
        assert result == "devices.csv"


# =============================================================================
# ZCC LIST FORWARDING PROFILES TESTS
# =============================================================================

class TestZccListForwardingProfiles:
    """Test cases for zcc_list_forwarding_profiles function."""

    @patch("zscaler_mcp.tools.zcc.list_forwarding_profiles.get_zscaler_client")
    def test_list_profiles_success(self, mock_get_client, mock_client, mock_profile_list):
        """Test successful listing of forwarding profiles."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.forwarding_profile.list_by_company.return_value = (mock_profile_list, None, None)

        # Execute
        result = zcc_list_forwarding_profiles()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zcc")
        mock_client.zcc.forwarding_profile.list_by_company.assert_called_once_with(query_params={})
        assert len(result) == 3
        assert result[0]["id"] == "prof0"
        assert result[1]["name"] == "Profile 1"

    @patch("zscaler_mcp.tools.zcc.list_forwarding_profiles.get_zscaler_client")
    def test_list_profiles_with_pagination(self, mock_get_client, mock_client, mock_profile_list):
        """Test listing profiles with pagination."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.forwarding_profile.list_by_company.return_value = (mock_profile_list, None, None)

        # Execute
        result = zcc_list_forwarding_profiles(page=1, page_size=10)

        # Verify
        mock_client.zcc.forwarding_profile.list_by_company.assert_called_once_with(
            query_params={"page": 1, "page_size": 10}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_forwarding_profiles.get_zscaler_client")
    def test_list_profiles_with_search(self, mock_get_client, mock_client, mock_profile_list):
        """Test listing profiles with search filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.forwarding_profile.list_by_company.return_value = (mock_profile_list, None, None)

        # Execute
        result = zcc_list_forwarding_profiles(search="production")

        # Verify
        mock_client.zcc.forwarding_profile.list_by_company.assert_called_once_with(
            query_params={"search": "production"}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_forwarding_profiles.get_zscaler_client")
    def test_list_profiles_with_all_params(self, mock_get_client, mock_client, mock_profile_list):
        """Test listing profiles with all parameters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.forwarding_profile.list_by_company.return_value = (mock_profile_list, None, None)

        # Execute
        result = zcc_list_forwarding_profiles(page=2, page_size=20, search="test")

        # Verify
        mock_client.zcc.forwarding_profile.list_by_company.assert_called_once_with(
            query_params={"page": 2, "page_size": 20, "search": "test"}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_forwarding_profiles.get_zscaler_client")
    def test_list_profiles_with_error(self, mock_get_client, mock_client):
        """Test listing profiles with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.forwarding_profile.list_by_company.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zcc_list_forwarding_profiles()
        assert "Error listing ZCC forwarding profiles: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zcc.list_forwarding_profiles.get_zscaler_client")
    def test_list_profiles_legacy_mode(self, mock_get_client, mock_client, mock_profile_list):
        """Test listing profiles using legacy API."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.forwarding_profile.list_by_company.return_value = (mock_profile_list, None, None)

        # Execute
        result = zcc_list_forwarding_profiles(use_legacy=True)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="zcc")
        assert len(result) == 3


# =============================================================================
# ZCC LIST TRUSTED NETWORKS TESTS
# =============================================================================

class TestZccListTrustedNetworks:
    """Test cases for zcc_list_trusted_networks function."""

    @patch("zscaler_mcp.tools.zcc.list_trusted_networks.get_zscaler_client")
    def test_list_networks_success(self, mock_get_client, mock_client, mock_network_list):
        """Test successful listing of trusted networks."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.trusted_networks.list_by_company.return_value = (mock_network_list, None, None)

        # Execute
        result = zcc_list_trusted_networks()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zcc")
        mock_client.zcc.trusted_networks.list_by_company.assert_called_once_with(query_params={})
        assert len(result) == 3
        assert result[0]["id"] == "net0"
        assert result[1]["name"] == "Network 1"

    @patch("zscaler_mcp.tools.zcc.list_trusted_networks.get_zscaler_client")
    def test_list_networks_with_pagination(self, mock_get_client, mock_client, mock_network_list):
        """Test listing networks with pagination."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.trusted_networks.list_by_company.return_value = (mock_network_list, None, None)

        # Execute
        result = zcc_list_trusted_networks(page=1, page_size=10)

        # Verify
        mock_client.zcc.trusted_networks.list_by_company.assert_called_once_with(
            query_params={"page": 1, "page_size": 10}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_trusted_networks.get_zscaler_client")
    def test_list_networks_with_search(self, mock_get_client, mock_client, mock_network_list):
        """Test listing networks with search filter."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.trusted_networks.list_by_company.return_value = (mock_network_list, None, None)

        # Execute
        result = zcc_list_trusted_networks(search="office")

        # Verify
        mock_client.zcc.trusted_networks.list_by_company.assert_called_once_with(
            query_params={"search": "office"}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_trusted_networks.get_zscaler_client")
    def test_list_networks_with_all_params(self, mock_get_client, mock_client, mock_network_list):
        """Test listing networks with all parameters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.trusted_networks.list_by_company.return_value = (mock_network_list, None, None)

        # Execute
        result = zcc_list_trusted_networks(page=3, page_size=25, search="corp")

        # Verify
        mock_client.zcc.trusted_networks.list_by_company.assert_called_once_with(
            query_params={"page": 3, "page_size": 25, "search": "corp"}
        )
        assert len(result) == 3

    @patch("zscaler_mcp.tools.zcc.list_trusted_networks.get_zscaler_client")
    def test_list_networks_with_error(self, mock_get_client, mock_client):
        """Test listing networks with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.trusted_networks.list_by_company.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zcc_list_trusted_networks()
        assert "Error listing ZCC trusted networks: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zcc.list_trusted_networks.get_zscaler_client")
    def test_list_networks_legacy_mode(self, mock_get_client, mock_client, mock_network_list):
        """Test listing networks using legacy API."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zcc.trusted_networks.list_by_company.return_value = (mock_network_list, None, None)

        # Execute
        result = zcc_list_trusted_networks(use_legacy=True)

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=True, service="zcc")
        assert len(result) == 3

