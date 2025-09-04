from typing import Annotated, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zcc_list_trusted_networks(
    page: Annotated[
        Optional[int], Field(description="Specifies the page offset.")
    ] = None,
    page_size: Annotated[
        Optional[int], Field(description="Specifies the page size.")
    ] = None,
    search: Annotated[
        Optional[str], Field(description="The search string used to partially match.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zcc",
) -> Union[List[dict], str]:
    """
    Returns the list of Trusted Networks By Company ID in the Client Connector Portal.

    Args:
        page (int, optional): Specifies the page offset.
        page_size (int, optional): Specifies the page size.
        search (str, optional): The search string used to partially match.
        use_legacy (bool): Whether to use the legacy API. Defaults to False.
        service (str): The service to use. Defaults to "zcc".

    Returns:
        Union[List[dict], str]: A list containing Trusted Networks By Company ID in the Client Connector Portal.

    Examples:
        List all Trusted Networks:

        >>> networks = zcc_list_trusted_networks()
        >>> print(f"Total trusted networks found: {len(networks)}")
        >>> for network in networks:
        ...     print(network)

        List trusted networks with pagination:

        >>> networks = zcc_list_trusted_networks(page=1, page_size=10)
        >>> print(f"Found {len(networks)} networks on page 1")

        Search for specific trusted networks:

        >>> networks = zcc_list_trusted_networks(search="office")
        >>> print(f"Found {len(networks)} networks matching 'office'")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size
    if search:
        query_params["search"] = search

    networks, _, err = client.zcc.trusted_networks.list_by_company(query_params=query_params)
    if err:
        raise Exception(f"Error listing ZCC trusted networks: {err}")
    return [n.as_dict() for n in networks]
