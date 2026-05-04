from typing import Annotated, Any, Dict, List

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_get_deeptrace_cloudpath(
    device_id: Annotated[str, Field(description="The unique ID for the ZDX device.")],
    trace_id: Annotated[str, Field(description="The unique ID for the deeptrace session.")],
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Get the list of cloud paths from a ZDX deep trace session.
    This is a read-only operation.

    Returns the full cloud path topology captured during the deep trace session,
    showing each hop between the device and the destination. Useful for
    identifying specific network segments causing latency or packet loss.

    Args:
        device_id: The unique ID for the ZDX device (required).
        trace_id: The unique ID for the deeptrace session (required).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing cloud path information.

    Raises:
        Exception: If the cloud path retrieval fails due to API errors.

    Examples:
        Get cloud paths from a deep trace:
        >>> paths = zdx_get_deeptrace_cloudpath(
        ...     device_id="device123",
        ...     trace_id="trace456"
        ... )
    """
    client = get_zscaler_client(service=service)

    result, _, err = client.zdx.troubleshooting.get_deeptrace_cloudpath(device_id, trace_id)
    if err:
        raise Exception(f"Cloud path retrieval failed: {err}")

    if result and len(result) > 0:
        return [item.as_dict() if hasattr(item, "as_dict") else item for item in result]
    return []
