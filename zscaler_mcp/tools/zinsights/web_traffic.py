"""
Z-Insights Web Traffic Analytics Tools

Provides analytics for web traffic across locations, protocols, and threats
using the Z-Insights GraphQL API.

All tools in this module are read-only operations.
"""

from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zinsights.common import (
    check_graphql_errors,
    convert_sdk_results,
    create_error_response,
    create_no_data_response,
    create_success_response,
    resolve_time_params,
    validate_action_filter,
    validate_dlp_engine_filter,
    validate_limit,
    validate_time_range,
    validate_traffic_unit,
    validate_trend_interval,
)

# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zinsights_get_web_traffic_by_location(
    start_days_ago: Annotated[
        int,
        Field(
            description="Days ago for start. Default: 9 (7-day interval with end=2). "
            "API requires intervals of exactly 7 or 14 days. For 14-day use 16."
        ),
    ] = 9,
    end_days_ago: Annotated[
        int,
        Field(
            description="Days ago for end. Default: 2. "
            "Interval = start - end must be 7 or 14."
        ),
    ] = 2,
    start_time: Annotated[
        Optional[int],
        Field(
            description="ALTERNATIVE: Start time as Unix epoch in MILLISECONDS. "
            "Only use if you need a specific timestamp. Overrides start_days_ago."
        ),
    ] = None,
    end_time: Annotated[
        Optional[int],
        Field(
            description="ALTERNATIVE: End time as Unix epoch in MILLISECONDS. "
            "Only use if you need a specific timestamp. Overrides end_days_ago."
        ),
    ] = None,
    traffic_unit: Annotated[
        str,
        Field(description="Traffic measurement unit. Values: TRANSACTIONS, BYTES"),
    ] = "TRANSACTIONS",
    include_trend: Annotated[
        bool,
        Field(description="Include trend data showing traffic patterns over time."),
    ] = False,
    trend_interval: Annotated[
        Optional[str],
        Field(
            description="Trend interval for time series data. Values: DAY, HOUR. "
            "Only applicable when include_trend=True."
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of location entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get web traffic analytics grouped by location.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    IMPORTANT: Z-Insights only supports HISTORICAL data queries. Data has a 24-48 hour
    processing delay, so end_days_ago should be at least 2.

    Use this tool to:
    - Identify high-traffic locations in your organization
    - Monitor traffic distribution across offices and branches
    - Analyze traffic trends over time for capacity planning
    - Compare traffic volumes between different locations

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start (e.g., 7 for last week).
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2 for data availability).
        start_time: Alternative - Epoch milliseconds (only if you have specific timestamp).
        end_time: Alternative - Epoch milliseconds (only if you have specific timestamp).
        traffic_unit: Measurement unit - TRANSACTIONS for request counts, BYTES for data volume.
        include_trend: If True, includes time series trend data in the response.
        trend_interval: Granularity for trend data - DAY for daily, HOUR for hourly.
        limit: Maximum number of location results to return (default: 50).

    Returns:
        List of location traffic entries, each containing:
        - name: Location name
        - total: Total transactions or bytes
        - trend: (if include_trend=True) Time series data

    Examples:
        Get top 10 locations for the past week (RECOMMENDED approach):
        >>> locations = zinsights_get_web_traffic_by_location(
        ...     start_days_ago=7,  # 7 days ago
        ...     end_days_ago=2,    # 2 days ago (data delay)
        ...     limit=10
        ... )
    """
    # Resolve time parameters (supports both days_ago and epoch ms)
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_traffic_unit(traffic_unit)
    validate_trend_interval(trend_interval)
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    # Build kwargs for the SDK call (use resolved timestamps)
    kwargs = {
        "start_time": resolved_start,
        "end_time": resolved_end,
        "traffic_unit": traffic_unit,
        "limit": limit,
    }

    if include_trend:
        kwargs["include_trend"] = include_trend
    if trend_interval:
        kwargs["trend_interval"] = trend_interval

    entries, response, err = client.zinsights.web_traffic.get_traffic_by_location(**kwargs)

    query_type = "web traffic by location"

    # Check for SDK-level errors (network issues, auth failures, etc.)
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_traffic_by_location")
    if error_info.get("has_error"):
        return [create_error_response(
            error_info.get("error_type", "UNKNOWN"),
            error_info.get("message", "API error occurred"),
            query_type
        )]

    # Return actual data with authoritative response
    results = convert_sdk_results(entries)
    if not results:
        return [create_no_data_response(query_type, "the specified time range")]
    return [create_success_response(results, query_type)]


def zinsights_get_web_traffic_no_grouping(
    start_days_ago: Annotated[
        int,
        Field(
            description="Days ago for start. Default: 9 (7-day interval). "
            "API requires intervals of exactly 7 or 14 days."
        ),
    ] = 9,
    end_days_ago: Annotated[
        int,
        Field(
            description="Days ago for end. Default: 2. "
            "Interval = start - end must be 7 or 14."
        ),
    ] = 2,
    start_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: Start time as Unix epoch in MILLISECONDS."),
    ] = None,
    end_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: End time as Unix epoch in MILLISECONDS."),
    ] = None,
    traffic_unit: Annotated[
        str,
        Field(description="Traffic measurement unit. Values: TRANSACTIONS, BYTES"),
    ] = "TRANSACTIONS",
    dlp_engine_filter: Annotated[
        Optional[str],
        Field(
            description="Filter by DLP engine. Values: ANY, NONE, HIPAA, CYBER_BULLY_ENG, "
            "GLBA, PCI, OFFENSIVE_LANGUAGE, EXTERNAL"
        ),
    ] = None,
    action_filter: Annotated[
        Optional[str],
        Field(description="Filter by action taken. Values: ALLOW, BLOCK"),
    ] = None,
    include_trend: Annotated[
        bool,
        Field(description="Include trend data showing traffic patterns over time."),
    ] = False,
    trend_interval: Annotated[
        Optional[str],
        Field(
            description="Trend interval for time series data. Values: DAY, HOUR. "
            "Only applicable when include_trend=True."
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get overall web traffic analytics without grouping.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - Get overall organization traffic volume
    - Filter traffic by DLP policy violations
    - Analyze allowed vs blocked traffic

    Examples:
        >>> traffic = zinsights_get_web_traffic_no_grouping(
        ...     start_days_ago=7, end_days_ago=2, action_filter="BLOCK"
        ... )
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_traffic_unit(traffic_unit)
    validate_trend_interval(trend_interval)
    validate_time_range(resolved_start, resolved_end)
    validate_dlp_engine_filter(dlp_engine_filter)
    validate_action_filter(action_filter)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    # Build kwargs for the SDK call
    kwargs = {
        "start_time": resolved_start,
        "end_time": resolved_end,
        "traffic_unit": traffic_unit,
        "limit": limit,
    }

    if dlp_engine_filter:
        kwargs["dlp_engine_filter"] = dlp_engine_filter
    if action_filter:
        kwargs["action_filter"] = action_filter
    if include_trend:
        kwargs["include_trend"] = include_trend
    if trend_interval:
        kwargs["trend_interval"] = trend_interval

    entries, response, err = client.zinsights.web_traffic.get_no_grouping(**kwargs)

    query_type = "total web traffic volume"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_no_grouping")
    if error_info.get("has_error"):
        return [create_error_response(
            error_info.get("error_type", "UNKNOWN"),
            error_info.get("message", "API error occurred"),
            query_type
        )]

    results = convert_sdk_results(entries)
    if not results:
        return [create_no_data_response(query_type, "the specified time range")]
    return [create_success_response(results, query_type)]


def zinsights_get_web_protocols(
    start_days_ago: Annotated[
        int,
        Field(description="Days ago for start. Default: 9 (7-day interval). API needs 7 or 14 day intervals."),
    ] = 9,
    end_days_ago: Annotated[
        int,
        Field(description="Days ago for end. Default: 2. Interval = start - end must be 7 or 14."),
    ] = 2,
    start_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: Start time as Unix epoch in MILLISECONDS."),
    ] = None,
    end_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: End time as Unix epoch in MILLISECONDS."),
    ] = None,
    traffic_unit: Annotated[
        str,
        Field(description="Traffic measurement unit. Values: TRANSACTIONS, BYTES"),
    ] = "TRANSACTIONS",
    limit: Annotated[
        int,
        Field(description="Maximum number of protocol entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get web traffic analytics by protocol (HTTP, HTTPS, SSL, etc.).
    This is a read-only operation using Z-Insights GraphQL API.

    Use this tool to:
    - Analyze HTTP vs HTTPS traffic distribution
    - Monitor SSL/TLS adoption
    - Detect unusual protocol activity

    Examples:
        >>> protocols = zinsights_get_web_protocols(start_days_ago=7, end_days_ago=2)
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_traffic_unit(traffic_unit)
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.web_traffic.get_protocols(
        start_time=resolved_start,
        end_time=resolved_end,
        traffic_unit=traffic_unit,
        limit=limit,
    )

    query_type = "web protocol distribution"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_protocols")
    if error_info.get("has_error"):
        return [create_error_response(
            error_info.get("error_type", "UNKNOWN"),
            error_info.get("message", "API error occurred"),
            query_type
        )]

    results = convert_sdk_results(entries)
    if not results:
        return [create_no_data_response(query_type, "the specified time range")]
    return [create_success_response(results, query_type)]


def zinsights_get_threat_super_categories(
    start_days_ago: Annotated[
        int,
        Field(description="Days ago for start. Default: 9 (7-day interval). API needs 7 or 14 day intervals."),
    ] = 9,
    end_days_ago: Annotated[
        int,
        Field(description="Days ago for end. Default: 2. Interval = start - end must be 7 or 14."),
    ] = 2,
    start_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: Start time as Unix epoch in MILLISECONDS."),
    ] = None,
    end_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: End time as Unix epoch in MILLISECONDS."),
    ] = None,
    traffic_unit: Annotated[
        str,
        Field(description="Traffic measurement unit. Values: TRANSACTIONS, BYTES"),
    ] = "TRANSACTIONS",
    limit: Annotated[
        int,
        Field(description="Maximum number of threat category entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get threat super category analytics from web traffic.
    This is a read-only operation using Z-Insights GraphQL API.

    Use this tool to:
    - Identify top threat categories in your traffic
    - Monitor virus and spyware detection trends
    - Assess security posture based on blocked threats

    Examples:
        >>> threats = zinsights_get_threat_super_categories(start_days_ago=7, end_days_ago=2)
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_traffic_unit(traffic_unit)
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.web_traffic.get_threat_super_categories(
        start_time=resolved_start,
        end_time=resolved_end,
        traffic_unit=traffic_unit,
        limit=limit,
    )

    query_type = "threat categories (malware, phishing, spyware, etc.)"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_threat_super_categories")
    if error_info.get("has_error"):
        return [create_error_response(
            error_info.get("error_type", "UNKNOWN"),
            error_info.get("message", "API error occurred"),
            query_type
        )]

    results = convert_sdk_results(entries)
    if not results:
        return [create_no_data_response(
            query_type,
            "the specified time range",
            "This means no threats were detected during this period - this is good news!"
        )]
    return [create_success_response(results, query_type)]


def zinsights_get_threat_class(
    start_days_ago: Annotated[
        int,
        Field(description="Days ago for start. Default: 9 (7-day interval). API needs 7 or 14 day intervals."),
    ] = 9,
    end_days_ago: Annotated[
        int,
        Field(description="Days ago for end. Default: 2. Interval = start - end must be 7 or 14."),
    ] = 2,
    start_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: Start time as Unix epoch in MILLISECONDS."),
    ] = None,
    end_time: Annotated[
        Optional[int],
        Field(description="ALTERNATIVE: End time as Unix epoch in MILLISECONDS."),
    ] = None,
    traffic_unit: Annotated[
        str,
        Field(description="Traffic measurement unit. Values: TRANSACTIONS, BYTES"),
    ] = "TRANSACTIONS",
    limit: Annotated[
        int,
        Field(description="Maximum number of threat class entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get threat class analytics from web traffic (Virus/Spyware, Advanced, Behavioral).
    This is a read-only operation using Z-Insights GraphQL API.

    Use this tool to:
    - Understand the distribution of threat types
    - Monitor advanced threat detection effectiveness
    - Compare signature-based vs behavioral detection

    Examples:
        >>> threat_classes = zinsights_get_threat_class(start_days_ago=7, end_days_ago=2)
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_traffic_unit(traffic_unit)
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.web_traffic.get_threat_class(
        start_time=resolved_start,
        end_time=resolved_end,
        traffic_unit=traffic_unit,
        limit=limit,
    )

    query_type = "threat class distribution (virus, trojan, ransomware, etc.)"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_threat_class")
    if error_info.get("has_error"):
        return [create_error_response(
            error_info.get("error_type", "UNKNOWN"),
            error_info.get("message", "API error occurred"),
            query_type
        )]

    results = convert_sdk_results(entries)
    if not results:
        return [create_no_data_response(
            query_type,
            "the specified time range",
            "This means no threats of this classification were detected - this is positive!"
        )]
    return [create_success_response(results, query_type)]

