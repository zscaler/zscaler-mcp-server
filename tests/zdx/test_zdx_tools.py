"""
Unit tests for ZDX (Zscaler Digital Experience) tools.

This module tests all 18 ZDX read-only tools across 10 files:
- active_devices: zdx_list_devices, zdx_get_device  
- administration: zdx_list_departments, zdx_list_locations
- list_applications: zdx_list_applications
- get_application_score: zdx_get_application, zdx_get_application_score_trend
- get_application_user: zdx_list_application_users, zdx_get_application_user
- get_application_metric: zdx_get_application_metric
- list_alerts: zdx_list_alerts, zdx_get_alert, zdx_list_alert_affected_devices
- list_deep_traces: zdx_list_device_deep_traces, zdx_get_device_deep_trace
- list_software_inventory: zdx_list_software, zdx_get_software_details
- list_historical_alerts: zdx_list_historical_alerts
"""

from unittest.mock import MagicMock, patch

import pytest

# Import all ZDX tools
from zscaler_mcp.tools.zdx.active_devices import zdx_get_device, zdx_list_devices
from zscaler_mcp.tools.zdx.administration import zdx_list_departments, zdx_list_locations
from zscaler_mcp.tools.zdx.get_application_metric import zdx_get_application_metric
from zscaler_mcp.tools.zdx.get_application_score import (
    zdx_get_application,
    zdx_get_application_score_trend,
)
from zscaler_mcp.tools.zdx.get_application_user import (
    zdx_get_application_user,
    zdx_list_application_users,
)
from zscaler_mcp.tools.zdx.list_alerts import (
    zdx_get_alert,
    zdx_list_alert_affected_devices,
    zdx_list_alerts,
)
from zscaler_mcp.tools.zdx.list_applications import zdx_list_applications
from zscaler_mcp.tools.zdx.list_deep_traces import (
    zdx_get_device_deep_trace,
    zdx_list_device_deep_traces,
)
from zscaler_mcp.tools.zdx.list_historical_alerts import zdx_list_historical_alerts
from zscaler_mcp.tools.zdx.list_software_inventory import (
    zdx_get_software_details,
    zdx_list_software,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_client():
    """Create a mock Zscaler client with ZDX API."""
    client = MagicMock()
    client.zdx.devices = MagicMock()
    client.zdx.admin = MagicMock()
    client.zdx.apps = MagicMock()
    client.zdx.alerts = MagicMock()
    client.zdx.troubleshooting = MagicMock()
    client.zdx.inventory = MagicMock()
    return client


@pytest.fixture
def mock_devices_response():
    """Create a mock devices response with wrapped structure."""
    devices_wrapper = MagicMock()
    device1 = MagicMock()
    device1.as_dict.return_value = {"id": "dev1", "name": "Device 1", "email": "user1@example.com"}
    device2 = MagicMock()
    device2.as_dict.return_value = {"id": "dev2", "name": "Device 2", "email": "user2@example.com"}
    devices_wrapper.devices = [device1, device2]
    return [devices_wrapper]


@pytest.fixture
def mock_device_response():
    """Create a mock single device response."""
    device = MagicMock()
    device.as_dict.return_value = {"id": "dev123", "name": "Test Device", "email": "test@example.com"}
    return [device]


# =============================================================================
# ACTIVE DEVICES TESTS
# =============================================================================

class TestZdxActiveDevices:
    """Test cases for ZDX active devices functions."""

    @patch("zscaler_mcp.tools.zdx.active_devices.get_zscaler_client")
    def test_list_devices_success(self, mock_get_client, mock_client, mock_devices_response):
        """Test successful listing of ZDX devices."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.devices.list_devices.return_value = (mock_devices_response, None, None)

        # Execute
        result = zdx_list_devices()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zdx")
        mock_client.zdx.devices.list_devices.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["id"] == "dev1"
        assert result[1]["email"] == "user2@example.com"

    @patch("zscaler_mcp.tools.zdx.active_devices.get_zscaler_client")
    def test_list_devices_with_filters(self, mock_get_client, mock_client, mock_devices_response):
        """Test listing devices with multiple filters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.devices.list_devices.return_value = (mock_devices_response, None, None)

        # Execute
        result = zdx_list_devices(
            emails=["test@example.com"],
            location_id=["loc123"],
            since=24
        )

        # Verify
        mock_client.zdx.devices.list_devices.assert_called_once_with(
            query_params={
                "emails": ["test@example.com"],
                "location_id": ["loc123"],
                "since": 24
            }
        )
        assert len(result) == 2

    @patch("zscaler_mcp.tools.zdx.active_devices.get_zscaler_client")
    def test_list_devices_with_error(self, mock_get_client, mock_client):
        """Test listing devices with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.devices.list_devices.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_devices()
        assert "Device listing failed: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zdx.active_devices.get_zscaler_client")
    def test_get_device_success(self, mock_get_client, mock_client, mock_device_response):
        """Test successful retrieval of a specific device."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.devices.get_device.return_value = (mock_device_response, None, None)

        # Execute
        result = zdx_get_device(device_id="dev123")

        # Verify
        mock_client.zdx.devices.get_device.assert_called_once_with("dev123", query_params={})
        assert result["id"] == "dev123"
        assert result["name"] == "Test Device"

    @patch("zscaler_mcp.tools.zdx.active_devices.get_zscaler_client")
    def test_get_device_with_filters(self, mock_get_client, mock_client, mock_device_response):
        """Test getting device with filters."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.devices.get_device.return_value = (mock_device_response, None, None)

        # Execute
        result = zdx_get_device(device_id="dev123", location_id=["loc123"], since=48)

        # Verify
        mock_client.zdx.devices.get_device.assert_called_once_with(
            "dev123",
            query_params={"location_id": ["loc123"], "since": 48}
        )
        assert result["id"] == "dev123"

    @patch("zscaler_mcp.tools.zdx.active_devices.get_zscaler_client")
    def test_get_device_with_error(self, mock_get_client, mock_client):
        """Test getting device with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.devices.get_device.return_value = (None, None, "Not Found")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_get_device(device_id="dev123")
        assert "Device lookup failed: Not Found" in str(exc_info.value)


# =============================================================================
# ADMINISTRATION TESTS
# =============================================================================

class TestZdxAdministration:
    """Test cases for ZDX administration functions."""

    @patch("zscaler_mcp.tools.zdx.administration.get_zscaler_client")
    def test_list_departments_success(self, mock_get_client, mock_client):
        """Test successful listing of departments."""
        # Setup
        mock_get_client.return_value = mock_client
        dept1 = MagicMock()
        dept1.as_dict.return_value = {"id": "dept1", "name": "Engineering"}
        dept2 = MagicMock()
        dept2.as_dict.return_value = {"id": "dept2", "name": "Finance"}
        mock_client.zdx.admin.list_departments.return_value = ([dept1, dept2], None, None)

        # Execute
        result = zdx_list_departments()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zdx")
        mock_client.zdx.admin.list_departments.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["name"] == "Engineering"
        assert result[1]["name"] == "Finance"

    @patch("zscaler_mcp.tools.zdx.administration.get_zscaler_client")
    def test_list_departments_with_search(self, mock_get_client, mock_client):
        """Test listing departments with search filter."""
        # Setup
        mock_get_client.return_value = mock_client
        dept = MagicMock()
        dept.as_dict.return_value = {"id": "dept1", "name": "Engineering"}
        mock_client.zdx.admin.list_departments.return_value = ([dept], None, None)

        # Execute
        result = zdx_list_departments(search="Eng", since=10)

        # Verify
        mock_client.zdx.admin.list_departments.assert_called_once_with(
            query_params={"search": "Eng", "since": 10}
        )
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zdx.administration.get_zscaler_client")
    def test_list_departments_with_error(self, mock_get_client, mock_client):
        """Test listing departments with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.admin.list_departments.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_departments()
        assert "Error retrieving departments: API Error" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zdx.administration.get_zscaler_client")
    def test_list_locations_success(self, mock_get_client, mock_client):
        """Test successful listing of locations."""
        # Setup
        mock_get_client.return_value = mock_client
        loc1 = MagicMock()
        loc1.as_dict.return_value = {"id": "loc1", "name": "San Francisco"}
        loc2 = MagicMock()
        loc2.as_dict.return_value = {"id": "loc2", "name": "London"}
        mock_client.zdx.admin.list_locations.return_value = ([loc1, loc2], None, None)

        # Execute
        result = zdx_list_locations()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zdx")
        mock_client.zdx.admin.list_locations.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["name"] == "San Francisco"

    @patch("zscaler_mcp.tools.zdx.administration.get_zscaler_client")
    def test_list_locations_with_search(self, mock_get_client, mock_client):
        """Test listing locations with search filter."""
        # Setup
        mock_get_client.return_value = mock_client
        loc = MagicMock()
        loc.as_dict.return_value = {"id": "loc1", "name": "San Francisco"}
        mock_client.zdx.admin.list_locations.return_value = ([loc], None, None)

        # Execute
        result = zdx_list_locations(search="San", since=24)

        # Verify
        mock_client.zdx.admin.list_locations.assert_called_once_with(
            query_params={"search": "San", "since": 24}
        )
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zdx.administration.get_zscaler_client")
    def test_list_locations_with_error(self, mock_get_client, mock_client):
        """Test listing locations with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.admin.list_locations.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_locations()
        assert "Error retrieving locations: API Error" in str(exc_info.value)


# =============================================================================
# APPLICATIONS TESTS
# =============================================================================

class TestZdxApplications:
    """Test cases for ZDX applications functions."""

    @patch("zscaler_mcp.tools.zdx.list_applications.get_zscaler_client")
    def test_list_applications_success(self, mock_get_client, mock_client):
        """Test successful listing of applications."""
        # Setup
        mock_get_client.return_value = mock_client
        app1 = MagicMock()
        app1.as_dict.return_value = {"id": "app1", "name": "Salesforce"}
        app2 = MagicMock()
        app2.as_dict.return_value = {"id": "app2", "name": "Office 365"}
        mock_client.zdx.apps.list_apps.return_value = ([app1, app2], None, None)

        # Execute
        result = zdx_list_applications()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zdx")
        mock_client.zdx.apps.list_apps.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["name"] == "Salesforce"

    @patch("zscaler_mcp.tools.zdx.list_applications.get_zscaler_client")
    def test_list_applications_with_filters(self, mock_get_client, mock_client):
        """Test listing applications with filters."""
        # Setup
        mock_get_client.return_value = mock_client
        app = MagicMock()
        app.as_dict.return_value = {"id": "app1", "name": "Salesforce"}
        mock_client.zdx.apps.list_apps.return_value = ([app], None, None)

        # Execute
        result = zdx_list_applications(location_id=["loc1"], since=12)

        # Verify
        mock_client.zdx.apps.list_apps.assert_called_once_with(
            query_params={"location_id": ["loc1"], "since": 12}
        )
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zdx.list_applications.get_zscaler_client")
    def test_list_applications_with_error(self, mock_get_client, mock_client):
        """Test listing applications with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.apps.list_apps.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_applications()
        assert "Application listing failed: API Error" in str(exc_info.value)


# =============================================================================
# APPLICATION SCORE TESTS
# =============================================================================

class TestZdxApplicationScore:
    """Test cases for ZDX application score functions."""

    @patch("zscaler_mcp.tools.zdx.get_application_score.get_zscaler_client")
    def test_get_application_success(self, mock_get_client, mock_client):
        """Test successful retrieval of application score."""
        # Setup
        mock_get_client.return_value = mock_client
        score = MagicMock()
        score.as_dict.return_value = {"id": "app1", "score": 85, "status": "good"}
        mock_client.zdx.apps.get_app.return_value = ([score], None, None)

        # Execute
        result = zdx_get_application(app_id="app1")

        # Verify
        mock_client.zdx.apps.get_app.assert_called_once_with("app1", query_params={})
        assert result["id"] == "app1"
        assert result["score"] == 85

    @patch("zscaler_mcp.tools.zdx.get_application_score.get_zscaler_client")
    def test_get_application_score_trend_success(self, mock_get_client, mock_client):
        """Test successful retrieval of application score trend."""
        # Setup
        mock_get_client.return_value = mock_client
        trend = MagicMock()
        trend.as_dict.return_value = {"id": "app1", "trend": [80, 85, 90]}
        mock_client.zdx.apps.get_app_score.return_value = ([trend], None, None)

        # Execute
        result = zdx_get_application_score_trend(app_id="app1")

        # Verify
        mock_client.zdx.apps.get_app_score.assert_called_once_with("app1", query_params={})
        assert result["id"] == "app1"
        assert len(result["trend"]) == 3

    @patch("zscaler_mcp.tools.zdx.get_application_score.get_zscaler_client")
    def test_get_application_with_filters(self, mock_get_client, mock_client):
        """Test getting application with filters."""
        # Setup
        mock_get_client.return_value = mock_client
        score = MagicMock()
        score.as_dict.return_value = {"id": "app1", "score": 85}
        mock_client.zdx.apps.get_app.return_value = ([score], None, None)

        # Execute
        result = zdx_get_application(app_id="app1", location_id=["loc1"], since=24)

        # Verify
        mock_client.zdx.apps.get_app.assert_called_once_with(
            "app1",
            query_params={"location_id": ["loc1"], "since": 24}
        )
        assert result["id"] == "app1"

    @patch("zscaler_mcp.tools.zdx.get_application_score.get_zscaler_client")
    def test_get_application_with_error(self, mock_get_client, mock_client):
        """Test getting application with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.apps.get_app.return_value = (None, None, "Not Found")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_get_application(app_id="app1")
        assert "Application score lookup failed: Not Found" in str(exc_info.value)


# =============================================================================
# APPLICATION USER TESTS
# =============================================================================

class TestZdxApplicationUser:
    """Test cases for ZDX application user functions."""

    @patch("zscaler_mcp.tools.zdx.get_application_user.get_zscaler_client")
    def test_list_application_users_success(self, mock_get_client, mock_client):
        """Test successful listing of application users."""
        # Setup
        mock_get_client.return_value = mock_client
        users_wrapper = MagicMock()
        user1 = MagicMock()
        user1.as_dict.return_value = {"id": "user1", "email": "user1@example.com"}
        user2 = MagicMock()
        user2.as_dict.return_value = {"id": "user2", "email": "user2@example.com"}
        users_wrapper.users = [user1, user2]
        mock_client.zdx.apps.list_users.return_value = ([users_wrapper], None, None)

        # Execute
        result = zdx_list_application_users(app_id="app1")

        # Verify
        mock_client.zdx.apps.list_users.assert_called_once_with("app1", query_params={})
        assert len(result) == 2
        assert result[0]["email"] == "user1@example.com"

    @patch("zscaler_mcp.tools.zdx.get_application_user.get_zscaler_client")
    def test_list_application_users_with_score_bucket(self, mock_get_client, mock_client):
        """Test listing application users with score bucket filter."""
        # Setup
        mock_get_client.return_value = mock_client
        users_wrapper = MagicMock()
        users_wrapper.users = []
        mock_client.zdx.apps.list_users.return_value = ([users_wrapper], None, None)

        # Execute
        _result = zdx_list_application_users(app_id="app1", score_bucket="poor")

        # Verify
        mock_client.zdx.apps.list_users.assert_called_once_with(
            "app1",
            query_params={"score_bucket": "poor"}
        )

    @patch("zscaler_mcp.tools.zdx.get_application_user.get_zscaler_client")
    def test_get_application_user_success(self, mock_get_client, mock_client):
        """Test successful retrieval of a specific application user."""
        # Setup
        mock_get_client.return_value = mock_client
        user = MagicMock()
        user.as_dict.return_value = {"id": "user1", "email": "user1@example.com", "score": 75}
        mock_client.zdx.apps.get_user.return_value = (user, None, None)  # Returns single object, not list

        # Execute
        result = zdx_get_application_user(app_id="app1", user_id="user1")

        # Verify
        mock_client.zdx.apps.get_user.assert_called_once_with("app1", "user1", query_params={})
        assert result["id"] == "user1"
        assert result["score"] == 75

    @patch("zscaler_mcp.tools.zdx.get_application_user.get_zscaler_client")
    def test_list_application_users_with_error(self, mock_get_client, mock_client):
        """Test listing application users with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.apps.list_users.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_application_users(app_id="app1")
        assert "Application user listing failed: API Error" in str(exc_info.value)


# =============================================================================
# APPLICATION METRIC TESTS
# =============================================================================

class TestZdxApplicationMetric:
    """Test cases for ZDX application metric function."""

    @patch("zscaler_mcp.tools.zdx.get_application_metric.get_zscaler_client")
    def test_get_application_metric_success(self, mock_get_client, mock_client):
        """Test successful retrieval of application metrics."""
        # Setup
        mock_get_client.return_value = mock_client
        metric1 = MagicMock()
        metric1.as_dict.return_value = {"name": "pft", "value": 150}
        metric2 = MagicMock()
        metric2.as_dict.return_value = {"name": "dns", "value": 50}
        mock_client.zdx.apps.get_app_metrics.return_value = ([metric1, metric2], None, None)

        # Execute
        result = zdx_get_application_metric(app_id="app1")

        # Verify
        mock_client.zdx.apps.get_app_metrics.assert_called_once_with("app1", query_params={})
        assert len(result) == 2
        assert result[0]["name"] == "pft"
        assert result[1]["value"] == 50

    @patch("zscaler_mcp.tools.zdx.get_application_metric.get_zscaler_client")
    def test_get_application_metric_with_filters(self, mock_get_client, mock_client):
        """Test getting application metric with filters."""
        # Setup
        mock_get_client.return_value = mock_client
        metric = MagicMock()
        metric.as_dict.return_value = {"name": "dns", "value": 50}
        mock_client.zdx.apps.get_app_metrics.return_value = ([metric], None, None)

        # Execute
        result = zdx_get_application_metric(
            app_id="app1",
            metric_name="dns",
            location_id=["loc1"],
            since=24
        )

        # Verify
        mock_client.zdx.apps.get_app_metrics.assert_called_once_with(
            "app1",
            query_params={"metric_name": "dns", "location_id": ["loc1"], "since": 24}
        )
        assert len(result) == 1

    @patch("zscaler_mcp.tools.zdx.get_application_metric.get_zscaler_client")
    def test_get_application_metric_with_error(self, mock_get_client, mock_client):
        """Test getting application metric with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.apps.get_app_metrics.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_get_application_metric(app_id="app1")
        assert "Application metrics retrieval failed: API Error" in str(exc_info.value)


# =============================================================================
# ALERTS TESTS
# =============================================================================

class TestZdxAlerts:
    """Test cases for ZDX alerts functions."""

    @patch("zscaler_mcp.tools.zdx.list_alerts.get_zscaler_client")
    def test_list_alerts_success(self, mock_get_client, mock_client):
        """Test successful listing of alerts."""
        # Setup
        mock_get_client.return_value = mock_client
        alerts_wrapper = MagicMock()
        alert1 = MagicMock()
        alert1.as_dict.return_value = {"id": "alert1", "severity": "high"}
        alert2 = MagicMock()
        alert2.as_dict.return_value = {"id": "alert2", "severity": "medium"}
        alerts_wrapper.alerts = [alert1, alert2]
        mock_client.zdx.alerts.read.return_value = ([alerts_wrapper], None, None)

        # Execute
        result = zdx_list_alerts()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zdx")
        mock_client.zdx.alerts.read.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["severity"] == "high"

    @patch("zscaler_mcp.tools.zdx.list_alerts.get_zscaler_client")
    def test_list_alerts_with_filters(self, mock_get_client, mock_client):
        """Test listing alerts with filters."""
        # Setup
        mock_get_client.return_value = mock_client
        alerts_wrapper = MagicMock()
        alerts_wrapper.alerts = []
        mock_client.zdx.alerts.read.return_value = ([alerts_wrapper], None, None)

        # Execute
        zdx_list_alerts(location_id=["loc1"], since=24, limit=50)

        # Verify
        mock_client.zdx.alerts.read.assert_called_once_with(
            query_params={"location_id": ["loc1"], "since": 24, "limit": 50}
        )

    @patch("zscaler_mcp.tools.zdx.list_alerts.get_zscaler_client")
    def test_get_alert_success(self, mock_get_client, mock_client):
        """Test successful retrieval of a specific alert."""
        # Setup
        mock_get_client.return_value = mock_client
        alert = MagicMock()
        alert.as_dict.return_value = {"id": "alert1", "severity": "high", "status": "active"}
        mock_client.zdx.alerts.get_alert.return_value = (alert, None, None)  # Returns single object, not list

        # Execute
        result = zdx_get_alert(alert_id="alert1")

        # Verify
        mock_client.zdx.alerts.get_alert.assert_called_once_with("alert1")
        assert result["id"] == "alert1"
        assert result["status"] == "active"

    @patch("zscaler_mcp.tools.zdx.list_alerts.get_zscaler_client")
    def test_list_alert_affected_devices_success(self, mock_get_client, mock_client):
        """Test successful listing of affected devices for an alert."""
        # Setup
        mock_get_client.return_value = mock_client
        devices_wrapper = MagicMock()
        device1 = MagicMock()
        device1.as_dict.return_value = {"id": "dev1", "name": "Device 1"}
        devices_wrapper.devices = [device1]
        mock_client.zdx.alerts.read_affected_devices.return_value = ([devices_wrapper], None, None)

        # Execute
        result = zdx_list_alert_affected_devices(alert_id="alert1")

        # Verify
        mock_client.zdx.alerts.read_affected_devices.assert_called_once_with("alert1", query_params={})
        assert len(result) == 1
        assert result[0]["name"] == "Device 1"

    @patch("zscaler_mcp.tools.zdx.list_alerts.get_zscaler_client")
    def test_list_alerts_with_error(self, mock_get_client, mock_client):
        """Test listing alerts with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.alerts.read.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_alerts()
        assert "Ongoing alerts listing failed: API Error" in str(exc_info.value)


# =============================================================================
# DEEP TRACES TESTS
# =============================================================================

class TestZdxDeepTraces:
    """Test cases for ZDX deep traces functions."""

    @patch("zscaler_mcp.tools.zdx.list_deep_traces.get_zscaler_client")
    def test_list_device_deep_traces_success(self, mock_get_client, mock_client):
        """Test successful listing of device deep traces."""
        # Setup
        mock_get_client.return_value = mock_client
        traces_wrapper = MagicMock()
        trace1 = MagicMock()
        trace1.as_dict.return_value = {"id": "trace1", "status": "completed"}
        trace2 = MagicMock()
        trace2.as_dict.return_value = {"id": "trace2", "status": "pending"}
        traces_wrapper.traces = [trace1, trace2]
        mock_client.zdx.troubleshooting.list_deeptraces.return_value = ([traces_wrapper], None, None)

        # Execute
        result = zdx_list_device_deep_traces(device_id="dev123")

        # Verify
        mock_client.zdx.troubleshooting.list_deeptraces.assert_called_once_with("dev123")
        assert len(result) == 2
        assert result[0]["status"] == "completed"

    @patch("zscaler_mcp.tools.zdx.list_deep_traces.get_zscaler_client")
    def test_get_device_deep_trace_success(self, mock_get_client, mock_client):
        """Test successful retrieval of a specific deep trace."""
        # Setup
        mock_get_client.return_value = mock_client
        trace = MagicMock()
        trace.as_dict.return_value = {"id": "trace1", "status": "completed", "hops": 10}
        mock_client.zdx.troubleshooting.get_deeptrace.return_value = (trace, None, None)  # Returns single object, not list

        # Execute
        result = zdx_get_device_deep_trace(device_id="dev123", trace_id="trace1")

        # Verify
        mock_client.zdx.troubleshooting.get_deeptrace.assert_called_once_with("dev123", "trace1")
        assert result["id"] == "trace1"
        assert result["hops"] == 10

    @patch("zscaler_mcp.tools.zdx.list_deep_traces.get_zscaler_client")
    def test_list_device_deep_traces_with_error(self, mock_get_client, mock_client):
        """Test listing device deep traces with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.troubleshooting.list_deeptraces.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_device_deep_traces(device_id="dev123")
        assert "Deep trace listing failed: API Error" in str(exc_info.value)


# =============================================================================
# SOFTWARE INVENTORY TESTS
# =============================================================================

class TestZdxSoftwareInventory:
    """Test cases for ZDX software inventory functions."""

    @patch("zscaler_mcp.tools.zdx.list_software_inventory.get_zscaler_client")
    def test_list_software_success(self, mock_get_client, mock_client):
        """Test successful listing of software inventory."""
        # Setup
        mock_get_client.return_value = mock_client
        inventory_wrapper = MagicMock()
        sw1 = MagicMock()
        sw1.as_dict.return_value = {"key": "sw1", "name": "Chrome", "version": "120.0"}
        sw2 = MagicMock()
        sw2.as_dict.return_value = {"key": "sw2", "name": "Firefox", "version": "121.0"}
        inventory_wrapper.software = [sw1, sw2]
        mock_client.zdx.inventory.list_software.return_value = ([inventory_wrapper], None, None)

        # Execute
        result = zdx_list_software()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zdx")
        mock_client.zdx.inventory.list_software.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["name"] == "Chrome"

    @patch("zscaler_mcp.tools.zdx.list_software_inventory.get_zscaler_client")
    def test_list_software_with_filters(self, mock_get_client, mock_client):
        """Test listing software with filters."""
        # Setup
        mock_get_client.return_value = mock_client
        inventory_wrapper = MagicMock()
        inventory_wrapper.software = []
        mock_client.zdx.inventory.list_software.return_value = ([inventory_wrapper], None, None)

        # Execute
        zdx_list_software(user_ids=["user1"], device_ids=["dev1"])

        # Verify
        mock_client.zdx.inventory.list_software.assert_called_once_with(
            query_params={"user_ids": ["user1"], "device_ids": ["dev1"]}
        )

    @patch("zscaler_mcp.tools.zdx.list_software_inventory.get_zscaler_client")
    def test_get_software_details_success(self, mock_get_client, mock_client):
        """Test successful retrieval of software details."""
        # Setup
        mock_get_client.return_value = mock_client
        software_wrapper = MagicMock()
        device = MagicMock()
        device.as_dict.return_value = {"device_id": "dev1", "user": "user1@example.com"}
        software_wrapper.devices = [device]
        mock_client.zdx.inventory.get_software.return_value = ([software_wrapper], None, None)

        # Execute
        result = zdx_get_software_details(software_key="Chrome-120.0")

        # Verify
        mock_client.zdx.inventory.get_software.assert_called_once_with("Chrome-120.0", query_params={})
        assert len(result) == 1  # Returns list of devices
        assert result[0]["device_id"] == "dev1"

    @patch("zscaler_mcp.tools.zdx.list_software_inventory.get_zscaler_client")
    def test_list_software_with_error(self, mock_get_client, mock_client):
        """Test listing software with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.inventory.list_software.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_software()
        assert "Software inventory listing failed: API Error" in str(exc_info.value)


# =============================================================================
# HISTORICAL ALERTS TESTS
# =============================================================================

class TestZdxHistoricalAlerts:
    """Test cases for ZDX historical alerts function."""

    @patch("zscaler_mcp.tools.zdx.list_historical_alerts.get_zscaler_client")
    def test_list_historical_alerts_success(self, mock_get_client, mock_client):
        """Test successful listing of historical alerts."""
        # Setup
        mock_get_client.return_value = mock_client
        alerts_wrapper = MagicMock()
        alert1 = MagicMock()
        alert1.as_dict.return_value = {"id": "alert1", "ended_on": "2024-01-01"}
        alert2 = MagicMock()
        alert2.as_dict.return_value = {"id": "alert2", "ended_on": "2024-01-02"}
        alerts_wrapper.alerts = [alert1, alert2]
        mock_client.zdx.alerts.list_historical.return_value = ([alerts_wrapper], None, None)

        # Execute
        result = zdx_list_historical_alerts()

        # Verify
        mock_get_client.assert_called_once_with(use_legacy=False, service="zdx")
        mock_client.zdx.alerts.list_historical.assert_called_once_with(query_params={})
        assert len(result) == 2
        assert result[0]["ended_on"] == "2024-01-01"

    @patch("zscaler_mcp.tools.zdx.list_historical_alerts.get_zscaler_client")
    def test_list_historical_alerts_with_filters(self, mock_get_client, mock_client):
        """Test listing historical alerts with filters."""
        # Setup
        mock_get_client.return_value = mock_client
        alerts_wrapper = MagicMock()
        alerts_wrapper.alerts = []
        mock_client.zdx.alerts.list_historical.return_value = ([alerts_wrapper], None, None)

        # Execute
        zdx_list_historical_alerts(
            location_id=["loc1"],
            since=336,  # 14 days
            limit=100
        )

        # Verify
        mock_client.zdx.alerts.list_historical.assert_called_once_with(
            query_params={"location_id": ["loc1"], "since": 336, "limit": 100}
        )

    @patch("zscaler_mcp.tools.zdx.list_historical_alerts.get_zscaler_client")
    def test_list_historical_alerts_with_error(self, mock_get_client, mock_client):
        """Test listing historical alerts with API error."""
        # Setup
        mock_get_client.return_value = mock_client
        mock_client.zdx.alerts.list_historical.return_value = (None, None, "API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            zdx_list_historical_alerts()
        assert "Historical alerts listing failed: API Error" in str(exc_info.value)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestZdxWorkflows:
    """Test cases for complete ZDX workflows."""

    @patch("zscaler_mcp.tools.zdx.active_devices.get_zscaler_client")
    @patch("zscaler_mcp.tools.zdx.list_applications.get_zscaler_client")
    @patch("zscaler_mcp.tools.zdx.get_application_score.get_zscaler_client")
    def test_device_to_application_workflow(self, mock_app_client, mock_list_client, mock_dev_client):
        """Test workflow from device discovery to application monitoring."""
        # Setup clients
        dev_client = MagicMock()
        list_client = MagicMock()
        app_client = MagicMock()
        
        mock_dev_client.return_value = dev_client
        mock_list_client.return_value = list_client
        mock_app_client.return_value = app_client

        # Setup device response
        devices_wrapper = MagicMock()
        device = MagicMock()
        device.as_dict.return_value = {"id": "dev1", "email": "user@example.com"}
        devices_wrapper.devices = [device]
        dev_client.zdx.devices.list_devices.return_value = ([devices_wrapper], None, None)

        # Setup applications response
        app = MagicMock()
        app.as_dict.return_value = {"id": "app1", "name": "Salesforce"}
        list_client.zdx.apps.list_apps.return_value = ([app], None, None)

        # Setup application score response
        score = MagicMock()
        score.as_dict.return_value = {"id": "app1", "score": 85}
        app_client.zdx.apps.get_app.return_value = ([score], None, None)

        # Execute workflow
        devices = zdx_list_devices()
        apps = zdx_list_applications()
        app_score = zdx_get_application(app_id="app1")

        # Verify
        assert len(devices) == 1
        assert len(apps) == 1
        assert app_score["score"] == 85

