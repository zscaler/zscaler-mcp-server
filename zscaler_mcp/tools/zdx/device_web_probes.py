from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_get_web_probes(
    device_id: Annotated[str, Field(description="The unique ID for the ZDX device.")],
    app_id: Annotated[str, Field(description="The unique ID for the application.")],
    since: Annotated[
        Optional[int], Field(description="Number of hours to look back (default 2h).")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Get web probes for a specific application on a device.
    This is a read-only operation.

    Returns web probe IDs and details for the specified device and application.
    The web_probe_id returned by this tool is required when starting a deep trace
    session with zdx_start_deeptrace.

    IMPORTANT: Call this tool BEFORE zdx_start_deeptrace to obtain the
    web_probe_id needed for the deep trace payload.

    Args:
        device_id: The unique ID for the ZDX device (required).
        app_id: The unique ID for the application (required).
        since: Number of hours to look back (default 2 hours).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing web probe information including probe IDs.

    Raises:
        Exception: If the web probe retrieval fails due to API errors.

    Examples:
        Get web probes for an app on a device:
        >>> probes = zdx_get_web_probes(device_id="155462842", app_id="3")
    """
    client = get_zscaler_client(service=service)

    query_params = {}
    if since:
        query_params["since"] = since

    result, _, err = client.zdx.devices.get_web_probes(device_id, app_id, query_params=query_params)
    if err:
        raise Exception(f"Web probe retrieval failed: {err}")

    if result and len(result) > 0:
        return [item.as_dict() if hasattr(item, "as_dict") else item for item in result]
    return []
