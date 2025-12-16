"""
Z-Insights Firewall Analytics Tools

Provides analytics for Zero Trust Firewall traffic including
action breakdowns, location analysis, and network services.

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
    validate_limit,
    validate_time_range,
)


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zinsights_get_firewall_by_action(
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
    limit: Annotated[
        int,
        Field(description="Maximum number of action entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get Zero Trust Firewall traffic grouped by action (allow/block).
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - See how much traffic is being allowed vs blocked
    - Monitor firewall policy effectiveness
    - Track blocked traffic trends
    - Understand firewall action distribution

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        limit: Maximum number of results (default: 50).

    Returns:
        List of action entries with name (ALLOW/BLOCK) and total count.

    Examples:
        Get firewall actions for the past week:
        >>> actions = zinsights_get_firewall_by_action(
        ...     start_days_ago=7,
        ...     end_days_ago=2,
        ...     limit=10
        ... )
    """
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.firewall.get_traffic_by_action(
        start_time=resolved_start,
        end_time=resolved_end,
        limit=limit,
    )

    query_type = "firewall traffic by action (allow/block)"

    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    error_info = check_graphql_errors(response, "get_traffic_by_action")
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


def zinsights_get_firewall_by_location(
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
    limit: Annotated[
        int,
        Field(description="Maximum number of location entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get Zero Trust Firewall traffic grouped by location.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - Identify which locations generate most firewall traffic
    - Compare firewall activity across offices
    - Find locations with unusual firewall activity
    - Monitor branch office firewall usage

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        limit: Maximum number of results (default: 50).

    Returns:
        List of location entries with id, name, and total traffic count.

    Examples:
        Get firewall traffic by location:
        >>> locations = zinsights_get_firewall_by_location(
        ...     start_days_ago=7,
        ...     end_days_ago=2,
        ...     limit=20
        ... )
    """
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.firewall.get_traffic_by_location(
        start_time=resolved_start,
        end_time=resolved_end,
        limit=limit,
    )

    query_type = "firewall traffic by location"

    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    error_info = check_graphql_errors(response, "get_traffic_by_location")
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


def zinsights_get_firewall_network_services(
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
    limit: Annotated[
        int,
        Field(description="Maximum number of service entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get Zero Trust Firewall traffic by network service.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - See which network services are being used
    - Identify service usage patterns
    - Monitor specific protocol/port usage
    - Find unusual network service activity

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        limit: Maximum number of results (default: 50).

    Returns:
        List of network service entries with name and total count.

    Examples:
        Get firewall network services:
        >>> services = zinsights_get_firewall_network_services(
        ...     start_days_ago=7,
        ...     end_days_ago=2,
        ...     limit=30
        ... )
    """
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.firewall.get_network_services(
        start_time=resolved_start,
        end_time=resolved_end,
        limit=limit,
    )

    query_type = "firewall network services"

    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    error_info = check_graphql_errors(response, "get_network_services")
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

