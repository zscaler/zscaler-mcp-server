"""
Z-Insights SaaS Security (CASB) Analytics Tools

Provides analytics for Cloud Access Security Broker (CASB) data
including SaaS application usage and security.

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


def zinsights_get_casb_app_report(
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
    Get CASB (Cloud Access Security Broker) application report.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    CASB provides data and threat protection for data at rest in cloud services.

    Use this tool to:
    - See which SaaS applications are being accessed
    - Monitor cloud application usage across the organization
    - Identify SaaS application activity
    - Track cloud service adoption

    Args:
        start_days_ago: RECOMMENDED - Number of days ago for start.
        end_days_ago: RECOMMENDED - Number of days ago for end (minimum 2).
        start_time: Alternative - Epoch milliseconds.
        end_time: Alternative - Epoch milliseconds.
        limit: Maximum number of results (default: 50).

    Returns:
        List of application entries with name and total usage count.

    Examples:
        Get CASB app report for the past week:
        >>> apps = zinsights_get_casb_app_report(
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

    entries, response, err = client.zinsights.saas_security.get_casb_app_report(
        start_time=resolved_start,
        end_time=resolved_end,
        limit=limit,
    )

    query_type = "CASB SaaS application usage"

    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    error_info = check_graphql_errors(response, "get_casb_app_report")
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

