from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def ztw_list_public_cloud_info(
    page: Annotated[Optional[int], Field(description="Page offset for paginated results. The default is 0.")] = None,
    page_size: Annotated[Optional[int], Field(description="Number of results per page. Default is 100; maximum is 1000.")] = None,
    search: Annotated[Optional[str], Field(description="Optional search filter for account name or metadata.")] = None,
    cloud_type: Annotated[Optional[str], Field(description="Cloud provider filter (e.g., 'AWS', 'AZURE', 'GCP').")] = None,
    use_legacy: Annotated[bool, Field(description="Whether to use the legacy API.")] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[Dict]:
    """List Zscaler Public Cloud (ZTW) accounts with optional filtering.

    This tool queries the Zscaler Cloud & Branch Connector (ZTW) public cloud information
    endpoint and returns account metadata such as account IDs, regions, and integration details.

    Args:
        page: Page offset for paginated results.
        page_size: Number of results per page (default 100, maximum 1000).
        search: Optional search filter applied to account metadata.
        cloud_type: Optional cloud provider filter (AWS, AZURE, or GCP).
        use_legacy: Whether to use the legacy API (default: False).
        service: The service to use (default: "ztw").

    Returns:
        List[Dict]: A list of public cloud account records.

    Raises:
        Exception: If the Zscaler SDK reports an error.
    """

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    api = client.ztw.public_cloud_info

    query_params: Dict[str, object] = {}
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size
    if search:
        query_params["search"] = search
    if cloud_type:
        query_params["cloud_type"] = cloud_type

    accounts, _, err = api.list_public_cloud_info(query_params=query_params)
    if err:
        raise Exception(f"Failed to list ZTW public cloud info: {err}")

    return [account.as_dict() for account in accounts]
