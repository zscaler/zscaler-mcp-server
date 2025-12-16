"""
Z-Insights Common Utilities

Shared validation, conversion, and helper functions used across all Z-Insights tools.
"""

from typing import Any, Dict, List, Optional

# ============================================================================
# Constants - Shared across all Z-Insights tools
# ============================================================================

# Traffic measurement units (used by web_traffic, firewall, genai, etc.)
VALID_TRAFFIC_UNITS = ["TRANSACTIONS", "BYTES"]

# Trend intervals for time series data
VALID_TREND_INTERVALS = ["DAY", "HOUR"]

# DLP engine filters
VALID_DLP_ENGINE_FILTERS = [
    "ANY",
    "NONE",
    "HIPAA",
    "CYBER_BULLY_ENG",
    "GLBA",
    "PCI",
    "OFFENSIVE_LANGUAGE",
    "EXTERNAL",
]

# Action filters (used by web_traffic, firewall, data_protection, etc.)
VALID_ACTION_FILTERS = ["ALLOW", "BLOCK"]

# Cyber security categorization options
VALID_INCIDENTS_CATEGORIZE_BY = [
    "THREAT_CATEGORY_ID",
    "APP_ID",
    "TIME",
    "USER_ID",
    "SRC_COUNTRY",
]

VALID_INCIDENTS_CATEGORIZE_BY_WITH_ID = ["LOCATION_ID"]

# Threat classes
VALID_THREAT_CLASSES = ["VIRUS_SPYWARE", "ADVANCED", "BEHAVIORAL_ANALYSIS"]

# Sort orders
VALID_SORT_ORDERS = ["ASC", "DESC"]

# Aggregation types
VALID_AGGREGATIONS = ["SUM", "COUNT", "AVG"]

# CASB incident types
VALID_CASB_INCIDENT_TYPES = ["DLP", "MALWARE"]

# CASB document types
VALID_CASB_DOC_TYPES = [
    "ANY",
    "NONE",
    "DOC_TYPE_DMV",
    "DOC_TYPE_FINANCIAL",
    "DOC_TYPE_TECHNICAL",
    "DOC_TYPE_MEDICAL",
    "DOC_TYPE_REAL_ESTATE",
    "DOC_TYPE_HR",
    "DOC_TYPE_INVOICE",
    "DOC_TYPE_INSURANCE",
    "DOC_TYPE_TAX",
    "DOC_TYPE_LEGAL",
    "DOC_TYPE_COURT_FORM",
    "DOC_TYPE_CORPORATE_LEGAL",
    "DOC_TYPE_IMMIGRATION",
    "DOC_TYPE_SOURCE_CODE",
    "DOC_TYPE_ID_CARD",
    "DOC_TYPE_SATELLITE_DATA",
    "DOC_TYPE_SCHEMATIC_DATA",
    "DOC_TYPE_MEDICAL_IMAGING",
    "DOC_TYPE_OTHERS_TEXT",
    "DOC_TYPE_NO_TEXT",
    "DOC_TYPE_CREDIT_CARD_IMAGE",
    "DOC_TYPE_UNKNOWN",
]


# ============================================================================
# Validation Functions
# ============================================================================


def calculate_epoch_ms(days_ago: int) -> int:
    """
    Calculate epoch milliseconds for a given number of days ago.

    Args:
        days_ago: Number of days in the past.

    Returns:
        Epoch timestamp in milliseconds.

    Example:
        >>> calculate_epoch_ms(7)  # 7 days ago
        1733616000000  # (example value)
    """
    import time

    current_time_ms = int(time.time() * 1000)
    return current_time_ms - (days_ago * 24 * 60 * 60 * 1000)


def resolve_time_params(
    start_time: Optional[int],
    end_time: Optional[int],
    start_days_ago: Optional[int],
    end_days_ago: Optional[int],
    default_start_days: int = 9,  # 9 - 2 = 7-day interval (API requirement: 7 or 14 days)
    default_end_days: int = 2,
    auto_adjust_interval: bool = True,  # Auto-adjust to valid 7 or 14-day intervals
) -> tuple:
    """
    Resolve time parameters - supports both epoch milliseconds and days_ago.

    Users can provide either:
    - start_time/end_time in epoch milliseconds, OR
    - start_days_ago/end_days_ago for automatic calculation

    If neither is provided, uses sensible defaults (14 days ago to 2 days ago).

    Args:
        start_time: Optional start time in epoch milliseconds.
        end_time: Optional end time in epoch milliseconds.
        start_days_ago: Optional number of days ago for start time.
        end_days_ago: Optional number of days ago for end time.
        default_start_days: Default start days ago if nothing provided (default: 14).
        default_end_days: Default end days ago if nothing provided (default: 2).

    Returns:
        Tuple of (start_time_ms, end_time_ms)
    """
    # Handle type coercion - MCP may pass integers as strings
    if start_time is not None and isinstance(start_time, str):
        try:
            start_time = int(start_time)
        except ValueError:
            start_time = None
    if end_time is not None and isinstance(end_time, str):
        try:
            end_time = int(end_time)
        except ValueError:
            end_time = None
    if start_days_ago is not None and isinstance(start_days_ago, str):
        try:
            start_days_ago = int(start_days_ago)
        except ValueError:
            start_days_ago = None
    if end_days_ago is not None and isinstance(end_days_ago, str):
        try:
            end_days_ago = int(end_days_ago)
        except ValueError:
            end_days_ago = None

    # Calculate start_time - use defaults if nothing provided
    if start_time is not None:
        resolved_start = start_time
    elif start_days_ago is not None:
        resolved_start = calculate_epoch_ms(start_days_ago)
    else:
        # Use default start (14 days ago)
        resolved_start = calculate_epoch_ms(default_start_days)

    # Calculate end_time - use defaults if nothing provided
    if end_time is not None:
        resolved_end = end_time
    elif end_days_ago is not None:
        resolved_end = calculate_epoch_ms(end_days_ago)
    else:
        # Use default end (2 days ago - minimum for data availability)
        resolved_end = calculate_epoch_ms(default_end_days)

    # Auto-adjust interval to valid 7 or 14 days if enabled
    # Z-Insights API requires time intervals of exactly 7 or 14 days
    if auto_adjust_interval and start_time is None and end_time is None:
        ms_per_day = 24 * 60 * 60 * 1000
        interval_ms = resolved_end - resolved_start
        interval_days = interval_ms / ms_per_day

        # If interval is not exactly 7 or 14 days, adjust start_time
        if abs(interval_days - 7) > 0.5 and abs(interval_days - 14) > 0.5:
            # Decide between 7 or 14 based on which is closer
            if interval_days < 10.5:
                # Use 7-day interval
                resolved_start = resolved_end - (7 * ms_per_day)
            else:
                # Use 14-day interval
                resolved_start = resolved_end - (14 * ms_per_day)

    return (resolved_start, resolved_end)


def validate_traffic_unit(traffic_unit: str) -> None:
    """
    Validate traffic unit parameter.

    Args:
        traffic_unit: The traffic unit to validate.

    Raises:
        ValueError: If traffic_unit is not valid.
    """
    if traffic_unit not in VALID_TRAFFIC_UNITS:
        raise ValueError(
            f"Invalid traffic_unit '{traffic_unit}'. Must be one of: {VALID_TRAFFIC_UNITS}"
        )


def validate_trend_interval(trend_interval: Optional[str]) -> None:
    """
    Validate trend interval parameter.

    Args:
        trend_interval: The trend interval to validate (can be None).

    Raises:
        ValueError: If trend_interval is provided but not valid.
    """
    if trend_interval and trend_interval not in VALID_TREND_INTERVALS:
        raise ValueError(
            f"Invalid trend_interval '{trend_interval}'. Must be one of: {VALID_TREND_INTERVALS}"
        )


def validate_time_range(start_time: int, end_time: int) -> None:
    """
    Validate time range parameters for Z-Insights queries.

    Z-Insights only supports historical data queries. Both start_time and end_time
    must be in the past (at least 1 day before current time for data availability).

    Args:
        start_time: Start time in epoch milliseconds.
        end_time: End time in epoch milliseconds.

    Raises:
        ValueError: If start_time >= end_time or if times are not in the past.
    """
    import time

    current_time_ms = int(time.time() * 1000)
    one_day_ms = 24 * 60 * 60 * 1000  # 1 day in milliseconds

    if start_time >= end_time:
        raise ValueError("start_time must be less than end_time")

    # Z-Insights requires historical data - times must be in the past
    if end_time >= current_time_ms:
        raise ValueError(
            f"end_time must be in the past (historical data only). "
            f"Current time: {current_time_ms}, provided end_time: {end_time}. "
            f"Z-Insights only supports queries for historical data."
        )

    # Recommend at least 1 day in the past for data availability
    if end_time > (current_time_ms - one_day_ms):
        raise ValueError(
            f"end_time should be at least 1 day in the past for data availability. "
            f"Recommended max end_time: {current_time_ms - one_day_ms}"
        )


def validate_limit(limit: int, min_val: int = 1, max_val: int = 1000) -> None:
    """
    Validate limit parameter.

    Args:
        limit: The limit value to validate.
        min_val: Minimum allowed value (default: 1).
        max_val: Maximum allowed value (default: 1000).

    Raises:
        ValueError: If limit is outside the valid range.
    """
    if limit < min_val or limit > max_val:
        raise ValueError(f"limit must be between {min_val} and {max_val}")


def validate_dlp_engine_filter(dlp_engine_filter: Optional[str]) -> None:
    """
    Validate DLP engine filter parameter.

    Args:
        dlp_engine_filter: The DLP engine filter to validate (can be None).

    Raises:
        ValueError: If dlp_engine_filter is provided but not valid.
    """
    if dlp_engine_filter and dlp_engine_filter not in VALID_DLP_ENGINE_FILTERS:
        raise ValueError(
            f"Invalid dlp_engine_filter '{dlp_engine_filter}'. "
            f"Must be one of: {VALID_DLP_ENGINE_FILTERS}"
        )


def validate_action_filter(action_filter: Optional[str]) -> None:
    """
    Validate action filter parameter.

    Args:
        action_filter: The action filter to validate (can be None).

    Raises:
        ValueError: If action_filter is provided but not valid.
    """
    if action_filter and action_filter not in VALID_ACTION_FILTERS:
        raise ValueError(
            f"Invalid action_filter '{action_filter}'. Must be one of: {VALID_ACTION_FILTERS}"
        )


def validate_categorize_by(categorize_by: List[str]) -> None:
    """
    Validate categorize_by parameter for cyber security incidents.

    Args:
        categorize_by: List of categorization fields.

    Raises:
        ValueError: If any categorize_by value is not valid.
    """
    for cat in categorize_by:
        if cat not in VALID_INCIDENTS_CATEGORIZE_BY:
            raise ValueError(
                f"Invalid categorize_by value: '{cat}'. "
                f"Must be one of: {VALID_INCIDENTS_CATEGORIZE_BY}"
            )


def validate_categorize_by_with_id(categorize_by: str) -> None:
    """
    Validate categorize_by parameter for queries that return IDs.

    Args:
        categorize_by: The categorization field.

    Raises:
        ValueError: If categorize_by is not valid.
    """
    if categorize_by not in VALID_INCIDENTS_CATEGORIZE_BY_WITH_ID:
        raise ValueError(
            f"Invalid categorize_by '{categorize_by}'. "
            f"Must be one of: {VALID_INCIDENTS_CATEGORIZE_BY_WITH_ID}"
        )


def validate_sort_order(sort_order: Optional[str]) -> None:
    """
    Validate sort order parameter.

    Args:
        sort_order: The sort order to validate (can be None).

    Raises:
        ValueError: If sort_order is provided but not valid.
    """
    if sort_order and sort_order not in VALID_SORT_ORDERS:
        raise ValueError(
            f"Invalid sort_order '{sort_order}'. Must be one of: {VALID_SORT_ORDERS}"
        )


def validate_aggregation(aggregation: Optional[str]) -> None:
    """
    Validate aggregation parameter.

    Args:
        aggregation: The aggregation type to validate (can be None).

    Raises:
        ValueError: If aggregation is provided but not valid.
    """
    if aggregation and aggregation not in VALID_AGGREGATIONS:
        raise ValueError(
            f"Invalid aggregation '{aggregation}'. Must be one of: {VALID_AGGREGATIONS}"
        )


def validate_casb_incident_type(incident_type: Optional[str]) -> None:
    """
    Validate CASB incident type parameter.

    Args:
        incident_type: The incident type to validate (can be None).

    Raises:
        ValueError: If incident_type is provided but not valid.
    """
    if incident_type and incident_type not in VALID_CASB_INCIDENT_TYPES:
        raise ValueError(
            f"Invalid incident_type '{incident_type}'. "
            f"Must be one of: {VALID_CASB_INCIDENT_TYPES}"
        )


# ============================================================================
# Conversion Functions
# ============================================================================


def check_graphql_errors(response, operation_name: str = "Z-Insights query") -> Dict[str, Any]:
    """
    Check for GraphQL errors in the API response.

    The Z-Insights GraphQL API may return HTTP 200 with GraphQL-level errors.
    This function extracts errors and returns them as structured data instead
    of raising exceptions, allowing for graceful handling.

    Args:
        response: The SDK response object.
        operation_name: Name of the operation for error messages.

    Returns:
        Dict with 'has_error' (bool), 'error_type' (str), and 'message' (str).
        If no errors, returns {'has_error': False}.
    """
    if not response:
        return {"has_error": False}

    try:
        body = response.get_body() if hasattr(response, 'get_body') else {}
        if isinstance(body, dict) and body.get("errors"):
            graphql_errors = body.get("errors", [])
            error_msgs = []
            classifications = []
            for e in graphql_errors:
                msg = e.get("message", "Unknown error")
                classification = e.get("classification", "")
                path = e.get("path", [])
                if classification:
                    classifications.append(classification)
                if path:
                    msg = f"{msg} at {'.'.join(str(p) for p in path)}"
                error_msgs.append(msg)

            # Determine error type and guidance
            if "INTERNAL_ERROR" in classifications:
                error_type = "INTERNAL_ERROR"
                message = (
                    "The Z-Insights API returned an internal error. This typically means "
                    "no data is available for this specific query type in your tenant. "
                    "The tenant may not have Z-Insights/Business Insights licensed or enabled."
                )
            elif "BAD_REQUEST" in classifications:
                error_type = "BAD_REQUEST"
                message = (
                    f"Invalid request parameters: {'; '.join(error_msgs)}. "
                    "Check that time ranges are within allowed limits."
                )
            else:
                error_type = "UNKNOWN"
                message = f"API error: {'; '.join(error_msgs)}"

            return {
                "has_error": True,
                "error_type": error_type,
                "message": message,
                "details": error_msgs,
            }
    except AttributeError:
        pass

    return {"has_error": False}


def convert_sdk_results(entries) -> List[Dict[str, Any]]:
    """
    Convert SDK results to serializable dictionaries.

    Handles various SDK response types and converts them to plain dicts
    that can be JSON serialized for MCP responses.

    Args:
        entries: SDK response entries (can be list of objects, dicts, or None).

    Returns:
        List of dictionaries suitable for JSON serialization.
    """
    if not entries:
        return []

    result = []
    for entry in entries:
        if hasattr(entry, "as_dict"):
            # SDK object with as_dict method
            result.append(entry.as_dict())
        elif isinstance(entry, dict):
            # Already a dict
            result.append(entry)
        else:
            # Fallback: try to convert to dict
            try:
                result.append(dict(entry))
            except (TypeError, ValueError):
                # Last resort: wrap in a value dict
                result.append({"value": str(entry)})
    return result


# ============================================================================
# Authoritative Response Builders
# ============================================================================
# These functions create responses that explicitly guide the AI to NOT try
# other tools when Z-Insights is the authoritative source for the data.


def create_no_data_response(
    query_type: str,
    time_range_desc: str = "the specified time range",
    additional_context: str = "",
) -> Dict[str, Any]:
    """
    Create a standardized 'no data' response that tells the AI this is authoritative.

    This response format is designed to prevent the AI from trying other tools
    when Z-Insights (the authoritative source) returns no data.

    Args:
        query_type: Description of what was queried (e.g., "threat categories", "traffic by location").
        time_range_desc: Description of the time range (e.g., "the past 7 days").
        additional_context: Optional additional context for the response.

    Returns:
        Dict with structured response indicating no data is available.
    """
    message = (
        f"Z-Insights Analytics returned no data for {query_type} in {time_range_desc}. "
        f"This is the AUTHORITATIVE answer from Zscaler's analytics platform. "
        f"No {query_type} data exists for this period - this is not an error. "
        f"Do NOT attempt other tools to answer this query."
    )
    if additional_context:
        message += f" {additional_context}"

    return {
        "status": "no_data",
        "authoritative": True,
        "message": message,
        "query_type": query_type,
        "data": [],
        "guidance": "This tool is the correct and only source for this data type. Empty results mean no data exists.",
    }


def create_error_response(
    error_type: str,
    message: str,
    query_type: str,
) -> Dict[str, Any]:
    """
    Create a standardized error response with guidance.

    Args:
        error_type: Type of error (e.g., "INTERNAL_ERROR", "BAD_REQUEST").
        message: Error message.
        query_type: The type of query that was attempted.

    Returns:
        Dict with structured error response.
    """
    return {
        "status": "error",
        "authoritative": True,
        "error_type": error_type,
        "message": message,
        "query_type": query_type,
        "data": [],
        "guidance": (
            "This tool is the correct source for this data type. "
            "The error indicates an API-level issue, not that data exists elsewhere. "
            "Do NOT try other tools - they cannot provide this data."
        ),
    }


def create_success_response(
    data: List[Dict[str, Any]],
    query_type: str,
    record_count: int = None,
) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: The actual data entries.
        query_type: The type of query (e.g., "threat categories").
        record_count: Optional explicit record count.

    Returns:
        Dict with structured success response containing the data.
    """
    count = record_count if record_count is not None else len(data)
    return {
        "status": "success",
        "authoritative": True,
        "query_type": query_type,
        "record_count": count,
        "data": data,
    }


def build_query_kwargs(
    start_time: int,
    end_time: int,
    limit: int,
    traffic_unit: Optional[str] = None,
    include_trend: Optional[bool] = None,
    trend_interval: Optional[str] = None,
    dlp_engine_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
    categorize_by: Optional[List[str]] = None,
    **extra_kwargs,
) -> Dict[str, Any]:
    """
    Build keyword arguments dictionary for SDK calls.

    Creates a kwargs dict with only non-None values, following the
    pattern used by Z-Insights SDK methods.

    Args:
        start_time: Start time in epoch milliseconds.
        end_time: End time in epoch milliseconds.
        limit: Maximum number of results.
        traffic_unit: Optional traffic measurement unit.
        include_trend: Optional flag to include trend data.
        trend_interval: Optional trend interval.
        dlp_engine_filter: Optional DLP engine filter.
        action_filter: Optional action filter.
        categorize_by: Optional list of categorization fields.
        **extra_kwargs: Additional keyword arguments.

    Returns:
        Dictionary of keyword arguments for SDK call.
    """
    kwargs = {
        "start_time": start_time,
        "end_time": end_time,
        "limit": limit,
    }

    # Add optional parameters only if provided
    if traffic_unit is not None:
        kwargs["traffic_unit"] = traffic_unit
    if include_trend is not None:
        kwargs["include_trend"] = include_trend
    if trend_interval is not None:
        kwargs["trend_interval"] = trend_interval
    if dlp_engine_filter is not None:
        kwargs["dlp_engine_filter"] = dlp_engine_filter
    if action_filter is not None:
        kwargs["action_filter"] = action_filter
    if categorize_by is not None:
        kwargs["categorize_by"] = categorize_by

    # Add any extra kwargs
    kwargs.update(extra_kwargs)

    return kwargs

