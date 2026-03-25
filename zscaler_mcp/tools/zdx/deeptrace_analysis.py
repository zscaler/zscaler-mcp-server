from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# ============================================================================
# READ-ONLY OPERATIONS
# ============================================================================


def zdx_get_analysis(
    analysis_id: Annotated[str, Field(description="The unique ID for the analysis.")],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> List[Dict[str, Any]]:
    """
    Get the status of a ZDX score analysis.
    This is a read-only operation.

    Returns the current status, progress, or results of a previously started
    ZDX score analysis. Use this to check whether an analysis is still running
    or to retrieve completed results.

    Args:
        analysis_id: The unique ID for the analysis (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        List of dictionaries containing analysis status/results.

    Raises:
        Exception: If the analysis retrieval fails due to API errors.

    Examples:
        Get analysis status:
        >>> status = zdx_get_analysis(analysis_id="analysis123")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    result, _, err = client.zdx.troubleshooting.get_analysis(analysis_id)
    if err:
        raise Exception(f"Analysis retrieval failed: {err}")

    if result and len(result) > 0:
        return result
    return []


# ============================================================================
# WRITE OPERATIONS
# ============================================================================


def zdx_start_analysis(
    device_id: Annotated[str, Field(description="The unique ID for the ZDX device.")],
    app_id: Annotated[
        int,
        Field(
            description="The unique ID for the application (integer). Use zdx_list_applications to find app IDs."
        ),
    ],
    t0: Annotated[
        Optional[int],
        Field(description="Start time as Unix epoch timestamp."),
    ] = None,
    t1: Annotated[
        Optional[int],
        Field(description="End time as Unix epoch timestamp."),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
) -> Dict[str, Any]:
    """
    Start a ZDX score analysis on a device for a specific application.

    ⚠️  WRITE OPERATION - Requires --enable-write-tools flag.

    Initiates a ZDX score analysis for the specified device and application.
    The analysis evaluates connectivity and performance metrics over the given
    time range.

    Args:
        device_id: The unique ID for the ZDX device (required).
        app_id: The unique ID for the application (required).
        t0: Start time as Unix epoch timestamp.
        t1: End time as Unix epoch timestamp.
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Dictionary containing the started analysis details.

    Raises:
        Exception: If starting the analysis fails due to API errors.

    Examples:
        Start a score analysis:
        >>> analysis = zdx_start_analysis(
        ...     device_id="155462842",
        ...     app_id=1
        ... )
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    kwargs = {
        "device_id": device_id,
        "app_id": int(app_id),
    }
    if t0 is not None:
        kwargs["t0"] = t0
    if t1 is not None:
        kwargs["t1"] = t1

    result, _, err = client.zdx.troubleshooting.start_analysis(**kwargs)
    if err:
        raise Exception(f"Failed to start analysis: {err}")

    if result and hasattr(result, "as_dict"):
        return result.as_dict()
    return {"status": "Analysis started successfully"}


def zdx_delete_analysis(
    analysis_id: Annotated[
        str, Field(description="The unique ID for the analysis to stop/delete.")
    ],
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zdx",
    kwargs: str = "{}",
) -> str:
    """
    Stop a ZDX score analysis that is currently running.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    Args:
        analysis_id: The unique ID for the analysis to stop (required).
        use_legacy: Whether to use the legacy API (default False).
        service: The Zscaler service to use (default "zdx").

    Returns:
        Success message string or confirmation message.

    Examples:
        >>> result = zdx_delete_analysis(analysis_id="analysis123")
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation(
        "zdx_delete_analysis",
        confirmed,
        {"analysis_id": analysis_id},
    )
    if confirmation_check:
        return confirmation_check

    if not analysis_id:
        raise ValueError("analysis_id is required for delete")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    _, _, err = client.zdx.troubleshooting.delete_analysis(analysis_id)
    if err:
        raise Exception(f"Failed to delete analysis {analysis_id}: {err}")

    return f"Successfully stopped/deleted analysis {analysis_id}"
