from typing import Annotated, Any, Dict, List

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_list_deeptrace_top_processes(
    device_id: Annotated[str, Field(description="The unique ID for the ZDX device.")],
    trace_id: Annotated[str, Field(description="The unique ID for the deeptrace session.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Get top processes from a ZDX deep trace session.
    This is a read-only operation.

    Returns the list of top processes captured during the deep trace session
    for the specified device. Useful for identifying resource-intensive processes
    that may be impacting device performance or connectivity.

    Args:
        device_id: The unique ID for the ZDX device (required).
        trace_id: The unique ID for the deeptrace session (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing top process information.

    Raises:
        Exception: If the top processes retrieval fails due to API errors.

    Examples:
        Get top processes from a deep trace:
        >>> processes = zdx_list_deeptrace_top_processes(
        ...     device_id="device123",
        ...     trace_id="trace456"
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    result, _, err = client.zdx.troubleshooting.list_top_processes(device_id, trace_id)
    if err:
        raise Exception(f"Top processes retrieval failed: {err}")

    if result and len(result) > 0:
        return [item.as_dict() if hasattr(item, "as_dict") else item for item in result]
    return []
