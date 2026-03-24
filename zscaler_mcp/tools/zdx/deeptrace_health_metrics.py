from typing import Annotated, Any, Dict, List

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_get_deeptrace_health_metrics(
    device_id: Annotated[str, Field(description="The unique ID for the ZDX device.")],
    trace_id: Annotated[str, Field(description="The unique ID for the deeptrace session.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Get health metrics from a ZDX deep trace session.
    This is a read-only operation.

    Returns health metrics captured during the deep trace session, including
    CPU usage, memory usage, disk I/O, and network utilization. Useful for
    correlating device health with connectivity or performance issues.

    Args:
        device_id: The unique ID for the ZDX device (required).
        trace_id: The unique ID for the deeptrace session (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing health metrics.

    Raises:
        Exception: If the health metrics retrieval fails due to API errors.

    Examples:
        Get health metrics from a deep trace:
        >>> metrics = zdx_get_deeptrace_health_metrics(
        ...     device_id="device123",
        ...     trace_id="trace456"
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    result, _, err = client.zdx.troubleshooting.get_deeptrace_health_metrics(device_id, trace_id)
    if err:
        raise Exception(f"Health metrics retrieval failed: {err}")

    if result and len(result) > 0:
        return [item.as_dict() if hasattr(item, "as_dict") else item for item in result]
    return []
