"""
Z-Insights IoT Analytics Tools

Provides analytics for IoT device visibility including device
detection, classification, and statistics.

All tools in this module are read-only operations.
"""

from typing import Annotated, Any, Dict, List

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zinsights.common import (
    check_graphql_errors,
    create_error_response,
    create_no_data_response,
    create_success_response,
    validate_limit,
)


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zinsights_get_iot_device_stats(
    limit: Annotated[
        int,
        Field(description="Maximum number of device classification entries to return (1-1000)."),
    ] = 50,
) -> List[Dict[str, Any]]:
    """
    Get IoT device statistics and classifications.
    This is a read-only operation using Z-Insights GraphQL API (OneAPI only).

    Zscaler IoT Device Visibility uses AI/ML to automatically detect,
    identify, and classify IoT devices across your network.

    Use this tool to:
    - Get total counts of IoT devices on your network
    - See device classifications (cameras, printers, etc.)
    - Identify unmanaged user devices
    - Find unclassified devices
    - Understand IoT device distribution

    Note: IoT device stats don't require a time range - they show current state.

    Args:
        limit: Maximum number of classification entries (default: 50).

    Returns:
        Statistics containing:
        - devices_count: Total devices
        - iot_devices_count: IoT devices
        - user_devices_count: Unmanaged user devices
        - server_devices_count: Server devices
        - un_classified_devices_count: Unclassified devices
        - entries: List of device classifications with counts

    Examples:
        Get IoT device statistics:
        >>> stats = zinsights_get_iot_device_stats(limit=20)
    """
    validate_limit(limit)

    client = get_zscaler_client(use_legacy=False, service="zinsights")

    stats, response, err = client.zinsights.iot.get_device_stats(limit=limit)

    query_type = "IoT device statistics and classifications"

    if err:
        return [create_error_response("SDK_ERROR", f"SDK error: {err}", query_type)]

    error_info = check_graphql_errors(response, "get_device_stats")
    if error_info.get("has_error"):
        return [create_error_response(
            error_info.get("error_type", "UNKNOWN"),
            error_info.get("message", "API error occurred"),
            query_type
        )]

    if not stats:
        return [create_no_data_response(
            query_type,
            "your network",
            "This means no IoT devices have been detected or IoT visibility is not enabled."
        )]

    # Stats is a dict with counts and entries, wrap it in success response
    return [create_success_response([stats], query_type, record_count=1)]

