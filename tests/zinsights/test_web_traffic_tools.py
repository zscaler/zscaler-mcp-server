"""
Tests for Z-Insights Web Traffic Tools

These tests validate the tool parameter validation and basic functionality.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestWebTrafficTools:
    """Tests for Z-Insights Web Traffic tools."""

    # ========================================================================
    # Parameter Validation Tests
    # ========================================================================

    def test_invalid_traffic_unit_raises_error(self):
        """Test that invalid traffic_unit raises ValueError."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_by_location,
        )

        with pytest.raises(ValueError) as exc_info:
            zinsights_get_web_traffic_by_location(
                start_time=1702600000000,
                end_time=1702686400000,
                traffic_unit="INVALID",
            )
        assert "Invalid traffic_unit" in str(exc_info.value)

    def test_invalid_time_range_raises_error(self):
        """Test that start_time >= end_time raises ValueError."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_by_location,
        )

        with pytest.raises(ValueError) as exc_info:
            zinsights_get_web_traffic_by_location(
                start_time=1702686400000,  # end before start
                end_time=1702600000000,
                traffic_unit="TRANSACTIONS",
            )
        assert "start_time must be less than end_time" in str(exc_info.value)

    def test_invalid_limit_raises_error(self):
        """Test that limit outside 1-1000 raises ValueError."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_by_location,
        )

        with pytest.raises(ValueError) as exc_info:
            zinsights_get_web_traffic_by_location(
                start_time=1702600000000,
                end_time=1702686400000,
                traffic_unit="TRANSACTIONS",
                limit=0,
            )
        assert "limit must be between 1 and 1000" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            zinsights_get_web_traffic_by_location(
                start_time=1702600000000,
                end_time=1702686400000,
                traffic_unit="TRANSACTIONS",
                limit=1001,
            )
        assert "limit must be between 1 and 1000" in str(exc_info.value)

    def test_invalid_trend_interval_raises_error(self):
        """Test that invalid trend_interval raises ValueError."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_by_location,
        )

        with pytest.raises(ValueError) as exc_info:
            zinsights_get_web_traffic_by_location(
                start_time=1702600000000,
                end_time=1702686400000,
                traffic_unit="TRANSACTIONS",
                trend_interval="INVALID",
            )
        assert "Invalid trend_interval" in str(exc_info.value)

    def test_invalid_dlp_engine_filter_raises_error(self):
        """Test that invalid dlp_engine_filter raises ValueError."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_no_grouping,
        )

        with pytest.raises(ValueError) as exc_info:
            zinsights_get_web_traffic_no_grouping(
                start_time=1702600000000,
                end_time=1702686400000,
                traffic_unit="TRANSACTIONS",
                dlp_engine_filter="INVALID",
            )
        assert "Invalid dlp_engine_filter" in str(exc_info.value)

    def test_invalid_action_filter_raises_error(self):
        """Test that invalid action_filter raises ValueError."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_no_grouping,
        )

        with pytest.raises(ValueError) as exc_info:
            zinsights_get_web_traffic_no_grouping(
                start_time=1702600000000,
                end_time=1702686400000,
                traffic_unit="TRANSACTIONS",
                action_filter="INVALID",
            )
        assert "Invalid action_filter" in str(exc_info.value)

    # ========================================================================
    # Mock API Call Tests
    # ========================================================================

    @patch("zscaler_mcp.tools.zinsights.web_traffic.get_zscaler_client")
    def test_get_web_traffic_by_location_success(self, mock_get_client):
        """Test successful web traffic by location query."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_by_location,
        )

        # Create mock response
        mock_entry = MagicMock()
        mock_entry.as_dict.return_value = {"name": "HQ", "total": 12345}

        mock_client = MagicMock()
        mock_client.zinsights.web_traffic.get_traffic_by_location.return_value = (
            [mock_entry],
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        # Execute
        result = zinsights_get_web_traffic_by_location(
            start_time=1702600000000,
            end_time=1702686400000,
            traffic_unit="TRANSACTIONS",
            limit=10,
        )

        # Verify
        assert len(result) == 1
        assert result[0]["name"] == "HQ"
        assert result[0]["total"] == 12345

    @patch("zscaler_mcp.tools.zinsights.web_traffic.get_zscaler_client")
    def test_get_web_traffic_by_location_empty_result(self, mock_get_client):
        """Test web traffic by location with no data."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_by_location,
        )

        mock_client = MagicMock()
        mock_client.zinsights.web_traffic.get_traffic_by_location.return_value = (
            [],
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        result = zinsights_get_web_traffic_by_location(
            start_time=1702600000000,
            end_time=1702686400000,
            traffic_unit="TRANSACTIONS",
        )

        assert result == []

    @patch("zscaler_mcp.tools.zinsights.web_traffic.get_zscaler_client")
    def test_get_web_traffic_by_location_api_error(self, mock_get_client):
        """Test web traffic by location with API error."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_by_location,
        )

        mock_client = MagicMock()
        mock_client.zinsights.web_traffic.get_traffic_by_location.return_value = (
            None,
            None,
            Exception("API Error"),
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception) as exc_info:
            zinsights_get_web_traffic_by_location(
                start_time=1702600000000,
                end_time=1702686400000,
                traffic_unit="TRANSACTIONS",
            )
        assert "Failed to get web traffic by location" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zinsights.web_traffic.get_zscaler_client")
    def test_get_web_protocols_success(self, mock_get_client):
        """Test successful web protocols query."""
        from zscaler_mcp.tools.zinsights.web_traffic import zinsights_get_web_protocols

        mock_entry1 = MagicMock()
        mock_entry1.as_dict.return_value = {"name": "HTTPS", "total": 50000}
        mock_entry2 = MagicMock()
        mock_entry2.as_dict.return_value = {"name": "HTTP", "total": 10000}

        mock_client = MagicMock()
        mock_client.zinsights.web_traffic.get_protocols.return_value = (
            [mock_entry1, mock_entry2],
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        result = zinsights_get_web_protocols(
            start_time=1702600000000,
            end_time=1702686400000,
            traffic_unit="TRANSACTIONS",
        )

        assert len(result) == 2
        assert result[0]["name"] == "HTTPS"
        assert result[1]["name"] == "HTTP"

    @patch("zscaler_mcp.tools.zinsights.web_traffic.get_zscaler_client")
    def test_get_threat_super_categories_success(self, mock_get_client):
        """Test successful threat super categories query."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_threat_super_categories,
        )

        mock_entry = MagicMock()
        mock_entry.as_dict.return_value = {"name": "Malware", "total": 500}

        mock_client = MagicMock()
        mock_client.zinsights.web_traffic.get_threat_super_categories.return_value = (
            [mock_entry],
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        result = zinsights_get_threat_super_categories(
            start_time=1702600000000,
            end_time=1702686400000,
            traffic_unit="TRANSACTIONS",
        )

        assert len(result) == 1
        assert result[0]["name"] == "Malware"

    @patch("zscaler_mcp.tools.zinsights.web_traffic.get_zscaler_client")
    def test_get_threat_class_success(self, mock_get_client):
        """Test successful threat class query."""
        from zscaler_mcp.tools.zinsights.web_traffic import zinsights_get_threat_class

        mock_entry = MagicMock()
        mock_entry.as_dict.return_value = {"name": "Advanced", "total": 100}

        mock_client = MagicMock()
        mock_client.zinsights.web_traffic.get_threat_class.return_value = (
            [mock_entry],
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        result = zinsights_get_threat_class(
            start_time=1702600000000,
            end_time=1702686400000,
            traffic_unit="TRANSACTIONS",
        )

        assert len(result) == 1
        assert result[0]["name"] == "Advanced"

    @patch("zscaler_mcp.tools.zinsights.web_traffic.get_zscaler_client")
    def test_get_web_traffic_no_grouping_with_filters(self, mock_get_client):
        """Test web traffic no grouping with DLP and action filters."""
        from zscaler_mcp.tools.zinsights.web_traffic import (
            zinsights_get_web_traffic_no_grouping,
        )

        mock_entry = MagicMock()
        mock_entry.as_dict.return_value = {"name": "Total", "total": 1000}

        mock_client = MagicMock()
        mock_client.zinsights.web_traffic.get_no_grouping.return_value = (
            [mock_entry],
            None,
            None,
        )
        mock_get_client.return_value = mock_client

        result = zinsights_get_web_traffic_no_grouping(
            start_time=1702600000000,
            end_time=1702686400000,
            traffic_unit="TRANSACTIONS",
            dlp_engine_filter="HIPAA",
            action_filter="BLOCK",
        )

        assert len(result) == 1

        # Verify the SDK was called with the correct parameters
        mock_client.zinsights.web_traffic.get_no_grouping.assert_called_once()
        call_kwargs = mock_client.zinsights.web_traffic.get_no_grouping.call_args[1]
        assert call_kwargs["dlp_engine_filter"] == "HIPAA"
        assert call_kwargs["action_filter"] == "BLOCK"


class TestZInsightsServiceRegistration:
    """Tests for Z-Insights service registration."""

    def test_zinsights_service_exists_in_registry(self):
        """Test that zinsights service is registered."""
        from zscaler_mcp.services import get_service_names, get_available_services

        service_names = get_service_names()
        assert "zinsights" in service_names

        services = get_available_services()
        assert "zinsights" in services

    def test_zinsights_service_has_read_tools_only(self):
        """Test that Z-Insights service only has read tools."""
        from zscaler_mcp.services import ZInsightsService

        service = ZInsightsService(None)
        assert len(service.read_tools) == 5
        assert len(service.write_tools) == 0

    def test_zinsights_service_tool_names(self):
        """Test that Z-Insights service has correct tool names."""
        from zscaler_mcp.services import ZInsightsService

        service = ZInsightsService(None)
        tool_names = [tool["name"] for tool in service.read_tools]

        expected_names = [
            "zinsights_get_web_traffic_by_location",
            "zinsights_get_web_traffic_no_grouping",
            "zinsights_get_web_protocols",
            "zinsights_get_threat_super_categories",
            "zinsights_get_threat_class",
        ]

        for name in expected_names:
            assert name in tool_names

