from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def ztw_list_public_account_details(
    page: Annotated[Optional[int], Field(description="Page offset for paginated results.")] = None,
    page_size: Annotated[
        Optional[int],
        Field(description="Number of results per page. Default 250; maximum 1000."),
    ] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """List public cloud account details from Zscaler Cloud & Branch Connector (ZTW).

    Args:
        page: Optional page offset for paginated results.
        page_size: Optional page size (default 250, maximum 1000).
        use_legacy: Whether to use the legacy API (default: False).
        service: The service to use (default: "ztw").

    Returns:
        List[Dict]: A list of public cloud account detail records.

    Raises:
        Exception: If the SDK reports an error.
    """

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.ztw.account_details

    query_params: Dict[str, object] = {}
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size

    details, _, err = api.list_public_account_details(query_params=query_params)
    if err:
        raise Exception(f"Failed to list ZTW public account details: {err}")

    return details
