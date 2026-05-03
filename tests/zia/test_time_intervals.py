"""
Unit tests for ZIA Time Intervals tools.

This module tests the verb-based time interval operations:
- zia_list_time_intervals (read-only)
- zia_get_time_interval (read-only)
- zia_create_time_interval (write)
- zia_update_time_interval (write)
- zia_delete_time_interval (write)
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from zscaler_mcp.tools.zia.time_intervals import (
    _normalize_days_of_week,
    zia_create_time_interval,
    zia_delete_time_interval,
    zia_get_time_interval,
    zia_list_time_intervals,
    zia_update_time_interval,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Create a mock Zscaler client with ZIA time_intervals API."""
    client = MagicMock()
    client.zia.time_intervals = MagicMock()
    return client


@pytest.fixture
def mock_interval():
    """Create a mock time-interval object."""
    interval = MagicMock()
    interval.as_dict.return_value = {
        "id": 73459,
        "name": "Business Hours",
        "start_time": 480,
        "end_time": 1020,
        "days_of_week": ["MON", "TUE", "WED", "THU", "FRI"],
    }
    return interval


@pytest.fixture
def mock_interval_list():
    """Create a list of mock time intervals."""
    intervals = []
    for i in range(3):
        interval = MagicMock()
        interval.as_dict.return_value = {
            "id": 10000 + i,
            "name": f"Interval {i}",
            "start_time": 0,
            "end_time": 1439,
            "days_of_week": ["EVERYDAY"],
        }
        intervals.append(interval)
    return intervals


# =============================================================================
# days_of_week normalization
# =============================================================================


class TestNormalizeDaysOfWeek:
    """Validation rules for days_of_week input."""

    def test_none_passes_through(self):
        assert _normalize_days_of_week(None) is None

    def test_uppercases_lowercase_input(self):
        assert _normalize_days_of_week(["mon", "tue"]) == ["MON", "TUE"]

    def test_strips_whitespace(self):
        assert _normalize_days_of_week([" MON ", "  TUE"]) == ["MON", "TUE"]

    def test_accepts_json_string(self):
        assert _normalize_days_of_week('["MON", "FRI"]') == ["MON", "FRI"]

    def test_accepts_everyday(self):
        assert _normalize_days_of_week(["EVERYDAY"]) == ["EVERYDAY"]

    def test_rejects_invalid_day(self):
        with pytest.raises(ValueError) as exc_info:
            _normalize_days_of_week(["MON", "FUNDAY"])
        assert "FUNDAY" in str(exc_info.value)


# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


class TestZiaListTimeIntervals:
    """Test cases for zia_list_time_intervals."""

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_list_success(self, mock_get_client, mock_client, mock_interval_list):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.list_time_intervals.return_value = (
            mock_interval_list,
            None,
            None,
        )

        result = zia_list_time_intervals()

        mock_get_client.assert_called_once_with(service="zia")
        mock_client.zia.time_intervals.list_time_intervals.assert_called_once_with(query_params={})
        assert len(result) == 3
        assert result[0]["name"] == "Interval 0"

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_list_with_search_and_pagination(
        self, mock_get_client, mock_client, mock_interval_list
    ):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.list_time_intervals.return_value = (
            mock_interval_list,
            None,
            None,
        )

        zia_list_time_intervals(search="Off-Work", page=2, page_size=50)

        mock_client.zia.time_intervals.list_time_intervals.assert_called_once_with(
            query_params={"search": "Off-Work", "page": 2, "page_size": 50}
        )

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_list_jmespath_count(self, mock_get_client, mock_client, mock_interval_list):
        """JMESPath ``length(@)`` produces a scalar that must not be rejected."""
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.list_time_intervals.return_value = (
            mock_interval_list,
            None,
            None,
        )

        result = zia_list_time_intervals(query="length(@)")
        assert result == [3]

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_list_with_error(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.list_time_intervals.return_value = (
            None,
            None,
            "List Failed",
        )

        with pytest.raises(Exception) as exc_info:
            zia_list_time_intervals()
        assert "Failed to list Time Intervals" in str(exc_info.value)


class TestZiaGetTimeInterval:
    """Test cases for zia_get_time_interval."""

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_get_success(self, mock_get_client, mock_client, mock_interval):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.get_time_intervals.return_value = (
            mock_interval,
            None,
            None,
        )

        result = zia_get_time_interval(interval_id=73459)

        mock_client.zia.time_intervals.get_time_intervals.assert_called_once_with(73459)
        assert result["id"] == 73459
        assert result["name"] == "Business Hours"

    def test_get_missing_id(self):
        with pytest.raises(ValueError) as exc_info:
            zia_get_time_interval(interval_id=None)
        assert "interval_id is required" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_get_with_error(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.get_time_intervals.return_value = (
            None,
            None,
            "Not Found",
        )

        with pytest.raises(Exception) as exc_info:
            zia_get_time_interval(interval_id=99999)
        assert "Failed to retrieve Time Interval 99999" in str(exc_info.value)


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


class TestZiaCreateTimeInterval:
    """Test cases for zia_create_time_interval."""

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_create_success(self, mock_get_client, mock_client, mock_interval):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.add_time_intervals.return_value = (
            mock_interval,
            None,
            None,
        )

        result = zia_create_time_interval(
            name="Business Hours",
            start_time=480,
            end_time=1020,
            days_of_week=["MON", "TUE", "WED", "THU", "FRI"],
        )

        mock_client.zia.time_intervals.add_time_intervals.assert_called_once_with(
            name="Business Hours",
            start_time=480,
            end_time=1020,
            days_of_week=["MON", "TUE", "WED", "THU", "FRI"],
        )
        assert result["id"] == 73459

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_create_normalizes_lowercase_days(
        self, mock_get_client, mock_client, mock_interval
    ):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.add_time_intervals.return_value = (
            mock_interval,
            None,
            None,
        )

        zia_create_time_interval(
            name="All Week",
            start_time=0,
            end_time=1439,
            days_of_week=["everyday"],
        )

        _, kwargs = mock_client.zia.time_intervals.add_time_intervals.call_args
        assert kwargs["days_of_week"] == ["EVERYDAY"]

    def test_create_rejects_invalid_day(self):
        with pytest.raises(ValueError):
            zia_create_time_interval(
                name="Bogus",
                start_time=0,
                end_time=100,
                days_of_week=["FUNDAY"],
            )

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_create_with_error(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.add_time_intervals.return_value = (
            None,
            None,
            "Creation Failed",
        )

        with pytest.raises(Exception) as exc_info:
            zia_create_time_interval(
                name="Business Hours",
                start_time=480,
                end_time=1020,
                days_of_week=["MON"],
            )
        assert "Failed to create Time Interval" in str(exc_info.value)


class TestZiaUpdateTimeInterval:
    """Test cases for zia_update_time_interval."""

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_full_update_does_not_backfill(
        self, mock_get_client, mock_client, mock_interval
    ):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.update_time_intervals.return_value = (
            mock_interval,
            None,
            None,
        )

        result = zia_update_time_interval(
            interval_id=73459,
            name="Business Hours",
            start_time=480,
            end_time=1020,
            days_of_week=["MON", "TUE"],
        )

        mock_client.zia.time_intervals.get_time_intervals.assert_not_called()
        mock_client.zia.time_intervals.update_time_intervals.assert_called_once_with(
            73459,
            name="Business Hours",
            start_time=480,
            end_time=1020,
            days_of_week=["MON", "TUE"],
        )
        assert result["id"] == 73459

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_partial_update_backfills_missing_fields(
        self, mock_get_client, mock_client, mock_interval
    ):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.get_time_intervals.return_value = (
            mock_interval,
            None,
            None,
        )
        mock_client.zia.time_intervals.update_time_intervals.return_value = (
            mock_interval,
            None,
            None,
        )

        zia_update_time_interval(interval_id=73459, end_time=1080)

        mock_client.zia.time_intervals.get_time_intervals.assert_called_once_with(73459)
        _, kwargs = mock_client.zia.time_intervals.update_time_intervals.call_args
        assert kwargs == {
            "end_time": 1080,
            "name": "Business Hours",
            "start_time": 480,
            "days_of_week": ["MON", "TUE", "WED", "THU", "FRI"],
        }

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_update_backfill_fetch_failure_raises(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.get_time_intervals.return_value = (
            None,
            None,
            "Not Found",
        )

        with pytest.raises(Exception) as exc_info:
            zia_update_time_interval(interval_id=73459, end_time=1080)
        assert "Failed to fetch Time Interval 73459" in str(exc_info.value)

    def test_update_missing_id(self):
        with pytest.raises(ValueError) as exc_info:
            zia_update_time_interval(interval_id=None, name="X")
        assert "interval_id is required for update" in str(exc_info.value)

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_update_with_api_error(self, mock_get_client, mock_client, mock_interval):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.update_time_intervals.return_value = (
            None,
            None,
            "Update Failed",
        )

        with pytest.raises(Exception) as exc_info:
            zia_update_time_interval(
                interval_id=73459,
                name="X",
                start_time=0,
                end_time=100,
                days_of_week=["MON"],
            )
        assert "Failed to update Time Interval 73459" in str(exc_info.value)


class TestZiaDeleteTimeInterval:
    """Test cases for zia_delete_time_interval."""

    def test_delete_requires_confirmation(self):
        result = zia_delete_time_interval(interval_id=73459)
        assert isinstance(result, str)
        assert "DESTRUCTIVE OPERATION" in result
        assert "CONFIRMATION REQUIRED" in result

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_delete_success(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.delete_time_intervals.return_value = (None, None, None)

        with patch.dict(os.environ, {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "true"}):
            result = zia_delete_time_interval(interval_id=73459)

        mock_client.zia.time_intervals.delete_time_intervals.assert_called_once_with(73459)
        assert result == "Time Interval 73459 deleted successfully."

    @patch("zscaler_mcp.tools.zia.time_intervals.get_zscaler_client")
    def test_delete_with_api_error(self, mock_get_client, mock_client):
        mock_get_client.return_value = mock_client
        mock_client.zia.time_intervals.delete_time_intervals.return_value = (
            None,
            None,
            "Resource In Use",
        )

        with patch.dict(os.environ, {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "true"}):
            with pytest.raises(Exception) as exc_info:
                zia_delete_time_interval(interval_id=73459)
        assert "Failed to delete Time Interval 73459" in str(exc_info.value)
