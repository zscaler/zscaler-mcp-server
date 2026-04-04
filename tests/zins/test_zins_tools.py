"""
Unit tests for Z-Insights tools and common utilities.

Covers: common.py validation/conversion functions, cyber_security, shadow_it,
firewall, iot, saas_security tools.
"""

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# COMMON UTILITIES
# ============================================================================


class TestZinsCommonValidation:

    def test_validate_traffic_unit_valid(self):
        from zscaler_mcp.tools.zins.common import validate_traffic_unit

        validate_traffic_unit("TRANSACTIONS")
        validate_traffic_unit("BYTES")

    def test_validate_traffic_unit_invalid(self):
        from zscaler_mcp.tools.zins.common import validate_traffic_unit

        with pytest.raises(ValueError, match="Invalid traffic_unit"):
            validate_traffic_unit("INVALID")

    def test_validate_trend_interval_valid(self):
        from zscaler_mcp.tools.zins.common import validate_trend_interval

        validate_trend_interval("DAY")
        validate_trend_interval("HOUR")
        validate_trend_interval(None)

    def test_validate_trend_interval_invalid(self):
        from zscaler_mcp.tools.zins.common import validate_trend_interval

        with pytest.raises(ValueError, match="Invalid trend_interval"):
            validate_trend_interval("WEEKLY")

    def test_validate_limit_valid(self):
        from zscaler_mcp.tools.zins.common import validate_limit

        validate_limit(1)
        validate_limit(500)
        validate_limit(1000)

    def test_validate_limit_too_low(self):
        from zscaler_mcp.tools.zins.common import validate_limit

        with pytest.raises(ValueError, match="limit must be between"):
            validate_limit(0)

    def test_validate_limit_too_high(self):
        from zscaler_mcp.tools.zins.common import validate_limit

        with pytest.raises(ValueError, match="limit must be between"):
            validate_limit(1001)

    def test_validate_dlp_engine_filter_valid(self):
        from zscaler_mcp.tools.zins.common import validate_dlp_engine_filter

        validate_dlp_engine_filter("HIPAA")
        validate_dlp_engine_filter("PCI")
        validate_dlp_engine_filter(None)

    def test_validate_dlp_engine_filter_invalid(self):
        from zscaler_mcp.tools.zins.common import validate_dlp_engine_filter

        with pytest.raises(ValueError, match="Invalid dlp_engine_filter"):
            validate_dlp_engine_filter("INVALID_FILTER")

    def test_validate_action_filter_valid(self):
        from zscaler_mcp.tools.zins.common import validate_action_filter

        validate_action_filter("ALLOW")
        validate_action_filter("BLOCK")
        validate_action_filter(None)

    def test_validate_action_filter_invalid(self):
        from zscaler_mcp.tools.zins.common import validate_action_filter

        with pytest.raises(ValueError, match="Invalid action_filter"):
            validate_action_filter("DROP")

    def test_validate_sort_order_valid(self):
        from zscaler_mcp.tools.zins.common import validate_sort_order

        validate_sort_order("ASC")
        validate_sort_order("DESC")
        validate_sort_order(None)

    def test_validate_sort_order_invalid(self):
        from zscaler_mcp.tools.zins.common import validate_sort_order

        with pytest.raises(ValueError, match="Invalid sort_order"):
            validate_sort_order("RANDOM")

    def test_validate_aggregation_valid(self):
        from zscaler_mcp.tools.zins.common import validate_aggregation

        validate_aggregation("SUM")
        validate_aggregation("COUNT")
        validate_aggregation("AVG")
        validate_aggregation(None)

    def test_validate_aggregation_invalid(self):
        from zscaler_mcp.tools.zins.common import validate_aggregation

        with pytest.raises(ValueError, match="Invalid aggregation"):
            validate_aggregation("MAX")

    def test_validate_casb_incident_type_valid(self):
        from zscaler_mcp.tools.zins.common import validate_casb_incident_type

        validate_casb_incident_type("DLP")
        validate_casb_incident_type("MALWARE")
        validate_casb_incident_type(None)

    def test_validate_casb_incident_type_invalid(self):
        from zscaler_mcp.tools.zins.common import validate_casb_incident_type

        with pytest.raises(ValueError, match="Invalid incident_type"):
            validate_casb_incident_type("PHISHING")

    def test_validate_time_range_valid(self):
        from zscaler_mcp.tools.zins.common import validate_time_range

        import time
        now_ms = int(time.time() * 1000)
        two_days_ms = 2 * 24 * 60 * 60 * 1000
        validate_time_range(
            now_ms - (9 * 24 * 60 * 60 * 1000),
            now_ms - two_days_ms,
        )

    def test_validate_time_range_start_after_end(self):
        from zscaler_mcp.tools.zins.common import validate_time_range

        with pytest.raises(ValueError, match="start_time must be less than end_time"):
            validate_time_range(2000, 1000)


class TestZinsCommonConversion:

    def test_convert_sdk_results_empty(self):
        from zscaler_mcp.tools.zins.common import convert_sdk_results

        assert convert_sdk_results(None) == []
        assert convert_sdk_results([]) == []

    def test_convert_sdk_results_with_as_dict(self):
        from zscaler_mcp.tools.zins.common import convert_sdk_results

        obj = MagicMock()
        obj.as_dict.return_value = {"key": "value"}

        result = convert_sdk_results([obj])
        assert result == [{"key": "value"}]

    def test_convert_sdk_results_with_dict(self):
        from zscaler_mcp.tools.zins.common import convert_sdk_results

        result = convert_sdk_results([{"key": "value"}])
        assert result == [{"key": "value"}]

    def test_convert_sdk_results_fallback(self):
        from zscaler_mcp.tools.zins.common import convert_sdk_results

        result = convert_sdk_results(["simple_string"])
        assert len(result) == 1
        assert "value" in result[0]


class TestZinsCommonResponseBuilders:

    def test_create_no_data_response(self):
        from zscaler_mcp.tools.zins.common import create_no_data_response

        resp = create_no_data_response("threat categories")
        assert resp["status"] == "no_data"
        assert resp["authoritative"] is True
        assert resp["data"] == []

    def test_create_error_response(self):
        from zscaler_mcp.tools.zins.common import create_error_response

        resp = create_error_response("INTERNAL_ERROR", "Server error", "threats")
        assert resp["status"] == "error"
        assert resp["error_type"] == "INTERNAL_ERROR"

    def test_create_success_response(self):
        from zscaler_mcp.tools.zins.common import create_success_response

        data = [{"id": 1}, {"id": 2}]
        resp = create_success_response(data, "traffic")
        assert resp["status"] == "success"
        assert resp["record_count"] == 2
        assert len(resp["data"]) == 2

    def test_build_query_kwargs_minimal(self):
        from zscaler_mcp.tools.zins.common import build_query_kwargs

        kwargs = build_query_kwargs(start_time=1000, end_time=2000, limit=50)
        assert kwargs["start_time"] == 1000
        assert kwargs["end_time"] == 2000
        assert kwargs["limit"] == 50
        assert "traffic_unit" not in kwargs

    def test_build_query_kwargs_full(self):
        from zscaler_mcp.tools.zins.common import build_query_kwargs

        kwargs = build_query_kwargs(
            start_time=1000, end_time=2000, limit=50,
            traffic_unit="BYTES", include_trend=True, trend_interval="DAY",
            action_filter="ALLOW",
        )
        assert kwargs["traffic_unit"] == "BYTES"
        assert kwargs["include_trend"] is True
        assert kwargs["trend_interval"] == "DAY"
        assert kwargs["action_filter"] == "ALLOW"


class TestZinsCommonTimeResolution:

    def test_resolve_time_params_with_epoch(self):
        from zscaler_mcp.tools.zins.common import resolve_time_params

        start, end = resolve_time_params(start_time=1000, end_time=2000, start_days_ago=None, end_days_ago=None)
        assert start == 1000
        assert end == 2000

    def test_resolve_time_params_with_days_ago(self):
        from zscaler_mcp.tools.zins.common import resolve_time_params

        start, end = resolve_time_params(start_time=None, end_time=None, start_days_ago=14, end_days_ago=7)
        assert start < end

    def test_resolve_time_params_defaults(self):
        from zscaler_mcp.tools.zins.common import resolve_time_params

        start, end = resolve_time_params(start_time=None, end_time=None, start_days_ago=None, end_days_ago=None)
        assert start < end

    def test_resolve_time_params_string_coercion(self):
        from zscaler_mcp.tools.zins.common import resolve_time_params

        start, end = resolve_time_params(start_time="1000", end_time="2000", start_days_ago=None, end_days_ago=None)
        assert start == 1000
        assert end == 2000

    def test_resolve_time_params_invalid_string(self):
        from zscaler_mcp.tools.zins.common import resolve_time_params

        start, end = resolve_time_params(start_time="not_a_number", end_time=None, start_days_ago=None, end_days_ago=None)
        assert start < end

    def test_calculate_epoch_ms(self):
        from zscaler_mcp.tools.zins.common import calculate_epoch_ms

        import time
        now_ms = int(time.time() * 1000)
        result = calculate_epoch_ms(7)
        expected = now_ms - (7 * 24 * 60 * 60 * 1000)
        assert abs(result - expected) < 1000


class TestZinsCommonGraphQLErrors:

    def test_check_graphql_errors_no_response(self):
        from zscaler_mcp.tools.zins.common import check_graphql_errors

        result = check_graphql_errors(None)
        assert result["has_error"] is False

    def test_check_graphql_errors_no_errors(self):
        from zscaler_mcp.tools.zins.common import check_graphql_errors

        resp = MagicMock()
        resp.get_body.return_value = {"data": {"result": []}}
        result = check_graphql_errors(resp)
        assert result["has_error"] is False

    def test_check_graphql_errors_internal_error(self):
        from zscaler_mcp.tools.zins.common import check_graphql_errors

        resp = MagicMock()
        resp.get_body.return_value = {
            "errors": [{"message": "internal", "classification": "INTERNAL_ERROR"}]
        }
        result = check_graphql_errors(resp)
        assert result["has_error"] is True
        assert result["error_type"] == "INTERNAL_ERROR"

    def test_check_graphql_errors_bad_request(self):
        from zscaler_mcp.tools.zins.common import check_graphql_errors

        resp = MagicMock()
        resp.get_body.return_value = {
            "errors": [{"message": "invalid param", "classification": "BAD_REQUEST", "path": ["query"]}]
        }
        result = check_graphql_errors(resp)
        assert result["has_error"] is True
        assert result["error_type"] == "BAD_REQUEST"


# ============================================================================
# CYBER SECURITY TOOLS
# ============================================================================


class TestZinsCyberSecurity:

    def test_validate_categorize_by_valid(self):
        from zscaler_mcp.tools.zins.cyber_security import validate_categorize_by

        validate_categorize_by(["THREAT_CATEGORY_ID", "APP_ID"])

    def test_validate_categorize_by_invalid(self):
        from zscaler_mcp.tools.zins.cyber_security import validate_categorize_by

        with pytest.raises(ValueError, match="Invalid categorize_by"):
            validate_categorize_by(["INVALID_CAT"])

    def test_validate_categorize_by_with_id_valid(self):
        from zscaler_mcp.tools.zins.cyber_security import validate_categorize_by_with_id

        validate_categorize_by_with_id("LOCATION_ID")

    def test_validate_categorize_by_with_id_invalid(self):
        from zscaler_mcp.tools.zins.cyber_security import validate_categorize_by_with_id

        with pytest.raises(ValueError, match="Invalid categorize_by"):
            validate_categorize_by_with_id("BAD_FIELD")


# ============================================================================
# SHADOW IT TOOLS
# ============================================================================


class TestZinsShadowIt:

    @patch("zscaler_mcp.tools.zins.shadow_it.get_zscaler_client")
    def test_get_shadow_it_apps_success(self, mock_get_client):
        from zscaler_mcp.tools.zins.shadow_it import zins_get_shadow_it_apps

        mock_client = MagicMock()

        entry = MagicMock()
        entry.as_dict.return_value = {"application": "Dropbox", "risk_index": 8}
        mock_client.zins.shadow_it.get_apps.return_value = ([entry], MagicMock(), None)
        mock_get_client.return_value = mock_client

        result = zins_get_shadow_it_apps()
        assert isinstance(result, list)
        assert result[0]["status"] == "success"
        assert result[0]["record_count"] == 1


# ============================================================================
# SERVICE REGISTRATION
# ============================================================================


class TestZInsightsServiceRegistration:

    def test_zins_service_exists_in_registry(self):
        from zscaler_mcp.services import get_available_services, get_service_names

        assert "zins" in get_service_names()
        assert "zins" in get_available_services()

    def test_zins_service_has_read_tools_only(self):
        from zscaler_mcp.services import ZINSService

        service = ZINSService(None)
        assert len(service.read_tools) > 0
        assert len(service.write_tools) == 0

    def test_all_zins_tools_have_prefix(self):
        from zscaler_mcp.services import ZINSService

        service = ZINSService(None)
        for tool in service.read_tools:
            assert tool["name"].startswith("zins_"), f"Tool {tool['name']} missing zins_ prefix"
