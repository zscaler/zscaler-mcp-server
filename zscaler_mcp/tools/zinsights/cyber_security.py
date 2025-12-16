"""
Z-Insights Cyber Security Analytics Tools

Provides analytics for cybersecurity incidents, threats, and security efficacy
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
    validate_limit,
    validate_time_range,
)

# Valid categorization options for cyber security incidents
VALID_CATEGORIZE_BY = [
    "THREAT_CATEGORY_ID",
    "APP_ID",
    "USER_ID",
    "TIME",
    "SRC_COUNTRY",
]

VALID_CATEGORIZE_BY_WITH_ID = [
    "LOCATION_ID",
    "APP_ID",
    "USER_ID",
    "DEPARTMENT_ID",
]


def validate_categorize_by(categorize_by: List[str]) -> None:
    """Validate categorize_by parameter."""
    for cat in categorize_by:
        if cat not in VALID_CATEGORIZE_BY:
            raise ValueError(
                f"Invalid categorize_by value: '{cat}'. "
                f"Must be one of: {VALID_CATEGORIZE_BY}"
            )


def validate_categorize_by_with_id(categorize_by: str) -> None:
    """Validate categorize_by_with_id parameter."""
    if categorize_by not in VALID_CATEGORIZE_BY_WITH_ID:
        raise ValueError(
            f"Invalid categorize_by value: '{categorize_by}'. "
            f"Must be one of: {VALID_CATEGORIZE_BY_WITH_ID}"
        )


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zinsights_get_cyber_incidents(
    start_days_ago: Annotated[
        int,
        Field(
            description="Days ago for start. API requires EXACTLY 7 or 14 day intervals. "
            "Default: 16 (with end_days_ago=2 gives 14-day interval). "
            "For 7-day: use 9. For 14-day: use 16."
        ),
    ] = 16,
    end_days_ago: Annotated[
        int,
        Field(
            description="Days ago for end. Default: 2 (data has 24-48hr delay). "
            "Interval = start_days_ago - end_days_ago must be 7 or 14."
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
    categorize_by: Annotated[
        Optional[List[str]],
        Field(
            description="Categories to group incidents by. "
            "Values: THREAT_CATEGORY_ID, APP_ID, USER_ID, TIME, SRC_COUNTRY. "
            "Default: ['THREAT_CATEGORY_ID']"
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of incident entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get cybersecurity incidents grouped by category.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    IMPORTANT: Z-Insights only supports HISTORICAL data queries. Data has a 24-48 hour
    processing delay, so end_days_ago should be at least 2.

    Use this tool to:
    - View security incidents by threat category (malware, phishing, etc.)
    - Analyze incidents by application or user
    - Track security incidents by source country
    - Understand the distribution of security threats

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start (e.g., 14 for two weeks).
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2 for data availability).
        start_time: Alternative - Epoch milliseconds (only if you have specific timestamp).
        end_time: Alternative - Epoch milliseconds (only if you have specific timestamp).
        categorize_by: List of categories to group by. Default: THREAT_CATEGORY_ID.
        limit: Maximum number of results to return (default: 50).

    Returns:
        List of incident entries grouped by the specified categories.
        Each entry contains: name, total, and potentially nested entries.

    Examples:
        Get incidents by threat category for the past 2 weeks:
        >>> incidents = zinsights_get_cyber_incidents(
        ...     start_days_ago=14,
        ...     end_days_ago=2,
        ...     categorize_by=["THREAT_CATEGORY_ID"],
        ...     limit=20
        ... )
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Use default categorization if not specified
    if categorize_by is None:
        categorize_by = ["THREAT_CATEGORY_ID"]

    # Validate inputs
    validate_categorize_by(categorize_by)
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.cyber_security.get_incidents(
        start_time=resolved_start,
        end_time=resolved_end,
        categorize_by=categorize_by,
        limit=limit,
    )

    query_type = "cybersecurity incidents by category"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_incidents")
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
            "This means no security incidents were detected - this is good news!"
        )]
    return [create_success_response(results, query_type)]


def zinsights_get_cyber_incidents_by_location(
    start_days_ago: Annotated[
        int,
        Field(
            description="Days ago for start. Default: 16 (14-day interval with end=2). "
            "API requires intervals of exactly 7 or 14 days."
        ),
    ] = 16,
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
    categorize_by: Annotated[
        str,
        Field(
            description="Category to group incidents by. "
            "Values: LOCATION_ID (default), APP_ID, USER_ID, DEPARTMENT_ID"
        ),
    ] = "LOCATION_ID",
    limit: Annotated[
        int,
        Field(description="Maximum number of entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get cybersecurity incidents grouped by location or other dimension.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - Identify which locations have the most security incidents
    - Compare security posture across office locations
    - Find incidents by user, application, or department
    - Prioritize security efforts by location

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        categorize_by: Dimension to group by. Default: LOCATION_ID.
        limit: Maximum number of results (default: 50).

    Returns:
        List of entries with id, name, and total incident count.

    Examples:
        Get incidents by location:
        >>> incidents = zinsights_get_cyber_incidents_by_location(
        ...     start_days_ago=14,
        ...     end_days_ago=2,
        ...     categorize_by="LOCATION_ID",
        ...     limit=20
        ... )
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_categorize_by_with_id(categorize_by)
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    entries, response, err = client.zinsights.cyber_security.get_incidents_by_location(
        start_time=resolved_start,
        end_time=resolved_end,
        categorize_by=categorize_by,
        limit=limit,
    )

    query_type = f"cybersecurity incidents by {categorize_by.lower().replace('_id', '')}"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_incidents_by_location")
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
            "This means no security incidents were detected at any location - this is positive!"
        )]
    return [create_success_response(results, query_type)]


def zinsights_get_cyber_incidents_daily(
    start_days_ago: Annotated[
        int,
        Field(
            description="Days ago for start. Default: 16 (14-day interval). "
            "API requires intervals of exactly 7 or 14 days."
        ),
    ] = 16,
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
    limit: Annotated[
        int,
        Field(description="Maximum number of daily entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get daily cybersecurity incidents over time.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - Track security incident trends over time
    - Identify days with unusual incident spikes
    - Monitor daily security posture
    - Create time-based security reports

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start (e.g., 30 for a month).
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        limit: Maximum number of daily entries (default: 50).

    Returns:
        List of daily incident counts with timestamps.

    Examples:
        Get daily incidents for the past month:
        >>> daily = zinsights_get_cyber_incidents_daily(
        ...     start_days_ago=30,
        ...     end_days_ago=2,
        ...     limit=30
        ... )
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    # Use TIME categorization to get daily data
    entries, response, err = client.zinsights.cyber_security.get_incidents(
        start_time=resolved_start,
        end_time=resolved_end,
        categorize_by=["TIME"],
        limit=limit,
    )

    query_type = "daily cybersecurity incident trends"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_incidents_daily")
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
            "This means no security incidents were detected during this period."
        )]
    return [create_success_response(results, query_type)]


def zinsights_get_cyber_incidents_by_threat_and_app(
    start_days_ago: Annotated[
        int,
        Field(
            description="Days ago for start. Default: 16 (14-day interval). "
            "API requires intervals of exactly 7 or 14 days."
        ),
    ] = 16,
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
    limit: Annotated[
        int,
        Field(description="Maximum number of entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get cybersecurity incidents grouped by both threat category and application.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Use this tool to:
    - Understand which applications are most targeted by threats
    - Correlate threat types with specific applications
    - Identify high-risk application/threat combinations
    - Prioritize application security improvements

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        limit: Maximum number of results (default: 50).

    Returns:
        List of nested entries showing threats by category with app breakdown.

    Examples:
        Get threats correlated with applications:
        >>> incidents = zinsights_get_cyber_incidents_by_threat_and_app(
        ...     start_days_ago=14,
        ...     end_days_ago=2,
        ...     limit=20
        ... )
    """
    # Resolve time parameters
    resolved_start, resolved_end = resolve_time_params(
        start_time, end_time, start_days_ago, end_days_ago
    )

    # Validate inputs
    validate_time_range(resolved_start, resolved_end)
    validate_limit(limit)

    # Get client - Z-Insights only supports OneAPI (not legacy)
    client = get_zscaler_client(use_legacy=False, service="zinsights")

    # Use both THREAT_CATEGORY_ID and APP_ID for correlation
    entries, response, err = client.zinsights.cyber_security.get_incidents(
        start_time=resolved_start,
        end_time=resolved_end,
        categorize_by=["THREAT_CATEGORY_ID", "APP_ID"],
        limit=limit,
    )

    query_type = "cybersecurity incidents by threat category and application"

    # Check for SDK-level errors
    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    # Check for GraphQL errors in response
    error_info = check_graphql_errors(response, "get_incidents_by_threat_and_app")
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
            "This means no security incidents were detected for any application."
        )]
    return [create_success_response(results, query_type)]

