from typing import Annotated, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def ztw_list_roles(
    include_auditor_role: Annotated[
        Optional[bool], Field(description="Include or exclude auditor user information in the list.")
    ] = None,
    include_partner_role: Annotated[
        Optional[bool], Field(description="Include or exclude admin user information in the list. Default is True.")
    ] = None,
    include_api_roles: Annotated[
        Optional[bool], Field(description="Include or exclude API role information in the list. Default is True.")
    ] = None,
    role_ids: Annotated[
        Optional[List[str]], Field(description="Include or exclude role ID information in the list.")
    ] = None,
    search: Annotated[
        Optional[str], Field(description="Search string to filter roles by name.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> Union[List[dict], str]:
    """
    List all existing admin roles in Zscaler Cloud & Branch Connector (ZTW).

    Args:
        include_auditor_role (bool, optional): Include or exclude auditor user information in the list.
        include_partner_role (bool, optional): Include or exclude admin user information in the list. Default is True.
        include_api_roles (bool, optional): Include or exclude API role information in the list. Default is True.
        role_ids (List[str], optional): Include or exclude role ID information in the list.
        search (str, optional): Search string to filter roles by name.
        use_legacy (bool): Whether to use the legacy API. Defaults to False.
        service (str): The service to use. Defaults to "ztw".

    Returns:
        Union[List[dict], str]: A list containing all existing admin roles in ZTW.

    Examples:
        List all roles:

        >>> roles = ztw_list_roles()
        >>> print(f"Total roles found: {len(roles)}")
        >>> for role in roles:
        ...     print(role)

        List roles with specific filters:

        >>> roles = ztw_list_roles(
        ...     include_auditor_role=True,
        ...     include_partner_role=True,
        ...     include_api_roles=True
        ... )
        >>> print(f"Found {len(roles)} roles with specified filters")

        Search for roles by name:

        >>> roles = ztw_list_roles(search="admin")
        >>> print(f"Found {len(roles)} roles matching 'admin'")

        List specific roles by ID:

        >>> roles = ztw_list_roles(role_ids=["123456789", "987654321"])
        >>> print(f"Found {len(roles)} specific roles")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    query_params = {}
    if include_auditor_role is not None:
        query_params["include_auditor_role"] = include_auditor_role
    if include_partner_role is not None:
        query_params["include_partner_role"] = include_partner_role
    if include_api_roles is not None:
        query_params["include_api_roles"] = include_api_roles
    if role_ids:
        query_params["id"] = role_ids
    if search:
        query_params["search"] = search

    roles, _, err = client.ztw.admin_roles.list_roles(query_params=query_params)
    if err:
        raise Exception(f"Error listing ZTW admin roles: {err}")
    return [r.as_dict() for r in roles]
