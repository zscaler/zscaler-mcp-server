from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


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


def zdx_list_deep_traces(
    action: Annotated[
        Literal["list_deeptraces", "read_deeptrace"],
        Field(description="Must be one of 'list_deeptraces' or 'read_deeptrace'."),
    ],
    device_id: Annotated[
        str, Field(description="The unique ID for the ZDX device.")
    ],
    trace_id: Annotated[
        Optional[str], Field(description="Required if action is 'read_deeptrace'. The unique ID for the deeptrace.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Tool for retrieving ZDX deep trace information for troubleshooting device connectivity issues.
    
    Supports two actions:
    - list_deeptraces: Returns a list of all deep traces for a specific device (USE THIS FOR GENERAL TROUBLESHOOTING OVERVIEW).
    - read_deeptrace: Returns detailed information on a single deeptrace for a specific device (USE FOR SPECIFIC TRACE ANALYSIS).
    
    USAGE GUIDELINES:
    - Use action='list_deeptraces' by default to get an overview of all deep traces for a device
    - Use action='read_deeptrace' when you need detailed information about a specific trace
    - Deep traces are used for troubleshooting device connectivity and performance issues
    
    TIMESTAMP CONVERSION INSTRUCTIONS:
    - CONVERT all Unix epoch timestamps (created, started, ended, timestamp, time fields) to ISO 8601 format
    - PRESERVE original epoch timestamps with "_epoch" suffix for reference
    - ALWAYS convert: "created": 1754537141 → "created": "2025-01-07T10:32:21", "created_epoch": 1754537141
    - APPLY conversion to both list_deeptraces and read_deeptrace actions
    
    Args:
        action: The type of deep trace information to retrieve ('list_deeptraces' or 'read_deeptrace').
        device_id: The unique ID for the ZDX device.
        trace_id: Required if action is 'read_deeptrace'. The unique ID for the deeptrace.
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").
        
    Returns:
        For 'list_deeptraces': List of dictionaries containing deep trace information with CONVERTED timestamps to ISO format.
        For 'read_deeptrace': Dictionary containing detailed deep trace information with CONVERTED timestamps to ISO format.
        
    Raises:
        Exception: If the deep trace information retrieval fails due to API errors.
        
    Examples:
        DEFAULT USAGE - Get overview of all deep traces for a device:
        >>> traces = zdx_list_deep_traces(
        ...     action="list_deeptraces", 
        ...     device_id="132559212"
        ... )
        
        SPECIFIC TRACE QUERY - Get detailed information for a specific trace:
        >>> trace_details = zdx_list_deep_traces(
        ...     action="read_deeptrace", 
        ...     device_id="132559212", 
        ...     trace_id="342941739947287"
        ... )
        
        TROUBLESHOOTING WORKFLOW:
        1. First, list all deep traces for a device to identify problematic traces:
        >>> traces = zdx_list_deep_traces(
        ...     action="list_deeptraces", 
        ...     device_id="132559212"
        ... )
        
        2. Then, get detailed information for a specific trace that shows issues:
        >>> trace_details = zdx_list_deep_traces(
        ...     action="read_deeptrace", 
        ...     device_id="132559212", 
        ...     trace_id="342941739947287"
        ... )
        
        REQUIRED TIMESTAMP OUTPUT FORMAT:
        {
            "created": "2025-01-07T10:32:21",
            "created_epoch": 1754537141,
            "started": "2025-01-07T10:32:31", 
            "started_epoch": 1754537151,
            "ended": "2025-01-07T10:39:41",
            "ended_epoch": 1754537581
        }
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    if action == "read_deeptrace":
        """
        Returns information on a single deeptrace for a specific device.
        """
        if not trace_id:
            raise ValueError("trace_id is required for action=read_deeptrace")
        
        result, _, err = client.zdx.troubleshooting.get_deeptrace(device_id, trace_id)
        if err:
            raise Exception(f"Deep trace lookup failed: {err}")
        
        # The ZDX SDK returns a list of DeviceDeepTraces objects
        if result and len(result) > 0:
            trace_data = result[0].as_dict()
            return _convert_timestamps(trace_data)
        else:
            return {}

    elif action == "list_deeptraces":
        """
        Returns a list of all deep traces for a specific device.
        """
        result, _, err = client.zdx.troubleshooting.list_deeptraces(device_id)
        if err:
            raise Exception(f"Deep traces listing failed: {err}")
        
        # The ZDX SDK returns a list of DeviceDeepTraces objects
        if result:
            traces_data = [trace.as_dict() for trace in result]
            return _convert_timestamps(traces_data)
        else:
            return []

    else:
        raise ValueError("Invalid action. Must be one of: 'list_deeptraces', 'read_deeptrace'")