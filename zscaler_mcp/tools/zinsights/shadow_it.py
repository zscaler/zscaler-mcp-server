"""
Z-Insights Shadow IT Analytics Tools

Provides analytics for discovering and managing shadow IT applications
used by your organization's users, departments, or locations.

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


def zinsights_get_shadow_it_apps(
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
        Field(description="Maximum number of application entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get discovered Shadow IT applications with details.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - Discover unsanctioned applications being used
    - View application risk scores
    - Identify data being uploaded/downloaded to shadow apps
    - Track sanctioned vs unsanctioned app usage
    - Find high-risk applications

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        limit: Maximum number of results (default: 50).

    Returns:
        List of shadow IT applications with details including:
        - application: Application name
        - application_category: Category
        - risk_index: Risk score
        - sanctioned_state: Sanctioned/unsanctioned status
        - data_consumed: Total data transferred
        - authenticated_users: Number of users

    Examples:
        Get shadow IT apps for the past week:
        >>> apps = zinsights_get_shadow_it_apps(
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

    entries, response, err = client.zinsights.shadow_it.get_apps(
        start_time=resolved_start,
        end_time=resolved_end,
        limit=limit,
    )

    query_type = "shadow IT discovered applications"

    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    error_info = check_graphql_errors(response, "get_apps")
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
            "This means no shadow IT applications were detected - your organization may have good app governance!"
        )]
    return [create_success_response(results, query_type)]


def zinsights_get_shadow_it_summary(
    start_days_ago: Annotated[
        int,
        Field(description="Days ago for start. Default: 16 (14-day interval). API needs 7 or 14 day intervals."),
    ] = 16,
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
) -> List[Dict[str, Any]]:
    """
    Get comprehensive Shadow IT summary with statistics and groupings.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - Get a dashboard overview of shadow IT activity
    - View total apps, bytes transferred, and user counts
    - See apps grouped by category, risk index, and status
    - Understand overall shadow IT exposure

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.

    Returns:
        Summary containing:
        - total_apps: Total number of shadow apps
        - total_bytes: Total data transferred
        - total_upload_bytes: Total uploaded
        - total_download_bytes: Total downloaded
        - group_by_app_cat_for_app: Apps by category
        - group_by_risk_index_for_app: Apps by risk level

    Examples:
        Get shadow IT summary:
        >>> summary = zinsights_get_shadow_it_summary(
        ...     start_days_ago=14,
        ...     end_days_ago=2
        ... )
    """
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    validate_time_range(resolved_start, resolved_end)

    client = get_zscaler_client(use_legacy=False, service="zinsights")

    summary, response, err = client.zinsights.shadow_it.get_shadow_it_summary(
        start_time=resolved_start,
        end_time=resolved_end,
    )

    query_type = "shadow IT summary statistics"

    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    error_info = check_graphql_errors(response, "get_shadow_it_summary")
    if error_info.get("has_error"):
        return [create_error_response(
            error_info.get("error_type", "UNKNOWN"),
            error_info.get("message", "API error occurred"),
            query_type
        )]

    if not summary:
        return [create_no_data_response(query_type, "the specified time range")]

    # Summary is a dict, not a list, so wrap it
    return [create_success_response([summary], query_type, record_count=1)]

