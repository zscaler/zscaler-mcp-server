from typing import Annotated, Any, Dict

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zdx_start_deeptrace(
    device_id: Annotated[str, Field(description="The unique ID for the ZDX device.")],
    session_name: Annotated[str, Field(description="The name of the deeptrace session.")],
    app_id: Annotated[
        int,
        Field(
            description="REQUIRED. The application ID as an INTEGER (e.g. 3, not '3'). Get from zdx_list_applications."
        ),
    ],
    web_probe_id: Annotated[
        int,
        Field(
            description="REQUIRED. The Web probe ID as an INTEGER (e.g. 266957). Get from zdx_get_web_probes(device_id, app_id)."
        ),
    ],
    cloudpath_probe_id: Annotated[
        int,
        Field(
            description="REQUIRED. The Cloudpath probe ID as an INTEGER (e.g. 266958). Get from zdx_list_cloudpath_probes(device_id, app_id)."
        ),
    ],
    session_length_minutes: Annotated[
        int,
        Field(
            description="Duration of the deeptrace session in minutes. Supported values: 5, 15, 30, 60."
        ),
    ] = 5,
    probe_device: Annotated[
        bool,
        Field(
            description="Whether to probe the device for CPU, memory, disk, and network metrics."
        ),
    ] = True,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Dict[str, Any]:
    """
    Start a deep trace for a specific ZDX device.

    ⚠️  WRITE OPERATION - Requires --enable-write-tools flag.

    Initiates a deep trace session on the specified device for troubleshooting
    connectivity and performance issues. The trace captures detailed network
    path data, web probe metrics, health metrics, and system events.

    REQUIRED WORKFLOW - Before calling this tool, you MUST:
    1. Call zdx_list_applications to get the app_id (integer)
    2. Call zdx_get_web_probes(device_id, app_id) to get the web_probe_id (integer)
    3. Call zdx_list_cloudpath_probes(device_id, app_id) to get the cloudpath_probe_id (integer)
    4. Then call this tool with all IDs as integers

    Args:
        device_id: The unique ID for the ZDX device (required, string).
        session_name: The name of the deeptrace session (required).
        app_id: The application ID (integer, e.g. 3 not "3").
        web_probe_id: The Web probe ID (integer, e.g. 266957). Get from zdx_get_web_probes.
        cloudpath_probe_id: The Cloudpath probe ID (integer, e.g. 266958). Get from zdx_list_cloudpath_probes.
        session_length_minutes: Duration in minutes (default 5). Supported: 5, 15, 30, 60.
        probe_device: Whether to probe the device (default True).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing the started trace details.

    Raises:
        Exception: If starting the deep trace fails due to API errors.

    Examples:
        Full workflow to start a deep trace:
        1. probes = zdx_get_web_probes(device_id="155462842", app_id="3")
           # Returns [{"id": 266957, ...}]
        2. cp_probes = zdx_list_cloudpath_probes(device_id="155462842", app_id="3")
           # Returns [{"id": 266958, ...}]
        3. trace = zdx_start_deeptrace(
               device_id="155462842",
               session_name="ServiceNow-Trace",
               app_id=3,
               web_probe_id=266957,
               cloudpath_probe_id=266958,
               session_length_minutes=5,
               probe_device=True
           )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    sdk_kwargs = {
        "session_name": session_name,
        "app_id": int(app_id),
        "web_probe_id": int(web_probe_id),
        "cloudpath_probe_id": int(cloudpath_probe_id),
        "session_length_minutes": session_length_minutes,
        "probe_device": probe_device,
    }

    result, _, err = client.zdx.troubleshooting.start_deeptrace(device_id, **sdk_kwargs)
    if err:
        raise Exception(f"Failed to start deep trace: {err}")

    if result and hasattr(result, "as_dict"):
        return result.as_dict()
    return {"status": "Deep trace started successfully"}


def zdx_delete_deeptrace(
    device_id: Annotated[str, Field(description="The unique ID for the ZDX device.")],
    trace_id: Annotated[str, Field(description="The unique ID for the deeptrace to delete.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
    kwargs: str = "{}",
) -> str:
    """
    Delete a deep trace session and associated data for a specific ZDX device.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Args:
        device_id: The unique ID for the ZDX device (required).
        trace_id: The unique ID for the deeptrace to delete (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Success message string or confirmation message.

    Examples:
        >>> result = zdx_delete_deeptrace(
        ...     device_id="device123",
        ...     trace_id="trace456"
        ... )
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation(
        "zdx_delete_deeptrace",
        confirmed,
        {"device_id": device_id, "trace_id": trace_id},
    )
    if confirmation_check:
        return confirmation_check

    if not device_id:
        raise ValueError("device_id is required for delete")
    if not trace_id:
        raise ValueError("trace_id is required for delete")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    _, _, err = client.zdx.troubleshooting.delete_deeptrace(device_id, trace_id)
    if err:
        raise Exception(f"Failed to delete deep trace {trace_id}: {err}")

    return f"Successfully deleted deep trace {trace_id} for device {device_id}"
