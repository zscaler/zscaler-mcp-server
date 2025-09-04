from typing import Annotated, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zcc_list_forwarding_profiles(
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
    Returns the list of Forwarding Profiles By Company ID in the Client Connector Portal.

    Args:
        page (int, optional): Specifies the page offset.
        page_size (int, optional): Specifies the page size.
        search (str, optional): The search string used to partially match.
        use_legacy (bool): Whether to use the legacy API. Defaults to False.
        service (str): The service to use. Defaults to "zcc".

    Returns:
        Union[List[dict], str]: A list containing Forwarding Profiles By Company ID in the Client Connector Portal.

    Examples:
        List all Forwarding Profiles:

        >>> profiles = zcc_list_forwarding_profiles()
        >>> print(f"Total forwarding profiles found: {len(profiles)}")
        >>> for profile in profiles:
        ...     print(profile)

        List forwarding profiles with pagination:

        >>> profiles = zcc_list_forwarding_profiles(page=1, page_size=10)
        >>> print(f"Found {len(profiles)} profiles on page 1")

        Search for specific forwarding profiles:

        >>> profiles = zcc_list_forwarding_profiles(search="production")
        >>> print(f"Found {len(profiles)} profiles matching 'production'")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size
    if search:
        query_params["search"] = search

    profiles, _, err = client.zcc.forwarding_profile.list_by_company(query_params=query_params)
    if err:
        raise Exception(f"Error listing ZCC forwarding profiles: {err}")
    return [p.as_dict() for p in profiles]
