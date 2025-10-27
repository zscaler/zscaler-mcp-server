from datetime import datetime
from typing import Annotated, Any, Dict, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# Helper Functions
# ============================================================================

def _convert_timestamps(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Convert Unix epoch timestamps to ISO format in the response data.
    
    Args:
        data: Dictionary or list of dictionaries containing trace data
        
    Returns:
        Data with timestamps converted to ISO format
    """
    def convert_single_item(item):
        if isinstance(item, dict):
            converted_item = {}
            for key, value in item.items():
                if isinstance(value, (int, str)) and key.lower() in ['created', 'started', 'ended', 'timestamp', 'time']:
                    try:
                        # Try to convert to int if it's a string
                        timestamp = int(value)
                        # Convert Unix epoch to ISO format
                        dt = datetime.fromtimestamp(timestamp)
                        converted_item[key] = dt.isoformat()
                        # Keep original timestamp as well for reference
                        converted_item[f"{key}_epoch"] = timestamp
                    except (ValueError, TypeError):
                        # If conversion fails, keep original value
                        converted_item[key] = value
                elif isinstance(value, dict):
                    converted_item[key] = convert_single_item(value)
                elif isinstance(value, list):
                    converted_item[key] = [convert_single_item(v) if isinstance(v, dict) else v for v in value]
                else:
                    converted_item[key] = value
            return converted_item
        return item
    
    if isinstance(data, list):
        return [convert_single_item(item) for item in data]
    else:
        return convert_single_item(data)


# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================

def zdx_list_device_deep_traces(
    device_id: Annotated[
        str, Field(description="The unique ID for the ZDX device.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Lists all deep traces for a specific ZDX device.
    This is a read-only operation.

    Returns a list of all deep traces for the specified device. Deep traces are used
    for troubleshooting device connectivity and performance issues. Timestamps are
    automatically converted from Unix epoch to ISO format for easier reading.

    Args:
        device_id: The unique ID for the ZDX device (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing deep trace information with converted timestamps.

    Raises:
        Exception: If the deep trace listing fails due to API errors.

    Examples:
        Get all deep traces for a device:
        >>> traces = zdx_list_device_deep_traces(device_id="device123")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    result, _, err = client.zdx.troubleshooting.list_deeptraces(device_id)
    if err:
        raise Exception(f"Deep trace listing failed: {err}")

    if result and len(result) > 0:
        traces_obj = result[0]
        traces_list = traces_obj.traces if hasattr(traces_obj, 'traces') else []
        traces_data = [trace.as_dict() for trace in traces_list]
        return _convert_timestamps(traces_data)
    else:
        return []


def zdx_get_device_deep_trace(
    device_id: Annotated[
        str, Field(description="The unique ID for the ZDX device.")
    ],
    trace_id: Annotated[
        str, Field(description="The unique ID for the deeptrace.")
    ],
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Dict[str, Any]:
    """
    Gets detailed information for a specific deep trace.
    This is a read-only operation.

    Returns detailed information on a single deeptrace for a specific device, including
    hop-by-hop network path analysis. Use this for in-depth analysis of connectivity
    issues. Timestamps are automatically converted from Unix epoch to ISO format.

    Args:
        device_id: The unique ID for the ZDX device (required).
        trace_id: The unique ID for the deeptrace (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing detailed deeptrace information with converted timestamps.

    Raises:
        Exception: If the deeptrace lookup fails due to API errors.

    Examples:
        Get specific deep trace details:
        >>> trace = zdx_get_device_deep_trace(
        ...     device_id="device123",
        ...     trace_id="trace456"
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    result, _, err = client.zdx.troubleshooting.get_deeptrace(device_id, trace_id)
    if err:
        raise Exception(f"Deeptrace lookup failed: {err}")

    if result:
        trace_data = result.as_dict()
        return _convert_timestamps(trace_data)
    else:
        return {}
