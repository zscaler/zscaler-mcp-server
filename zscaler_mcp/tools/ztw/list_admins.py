from typing import Annotated, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def ztw_list_admins(
    action: Annotated[
        str, Field(description="Action to perform: 'list_admins' or 'get_admin'.")
    ] = "list_admins",
    admin_id: Annotated[
        Optional[str], Field(description="Admin ID for get_admin action.")
    ] = None,
    include_auditor_users: Annotated[
        Optional[bool], Field(description="Include / exclude auditor users in the response.")
    ] = None,
    include_admin_users: Annotated[
        Optional[bool], Field(description="Include / exclude admin users in the response.")
    ] = None,
    include_api_roles: Annotated[
        Optional[bool], Field(description="Include / exclude API roles in the response.")
    ] = None,
    search: Annotated[
        Optional[str], Field(description="The search string to filter by.")
    ] = None,
    page: Annotated[
        Optional[int], Field(description="The page offset to return.")
    ] = None,
    page_size: Annotated[
        Optional[int], Field(description="The number of records to return per page.")
    ] = None,
    version: Annotated[
        Optional[int], Field(description="Specifies the admins from a backup version.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> Union[List[dict], dict, str]:
    """
    List all existing admin users or get details for a specific admin user in Zscaler Cloud & Branch Connector (ZTW).

    Args:
        action (str): Action to perform: 'list_admins' or 'get_admin'. Defaults to 'list_admins'.
        admin_id (str, optional): Admin ID for get_admin action. Required when action is 'get_admin'.
        include_auditor_users (bool, optional): Include / exclude auditor users in the response.
        include_admin_users (bool, optional): Include / exclude admin users in the response.
        include_api_roles (bool, optional): Include / exclude API roles in the response.
        search (str, optional): The search string to filter by.
        page (int, optional): The page offset to return.
        page_size (int, optional): The number of records to return per page.
        version (int, optional): Specifies the admins from a backup version.
        use_legacy (bool): Whether to use the legacy API. Defaults to False.
        service (str): The service to use. Defaults to "ztw".

    Returns:
        Union[List[dict], dict, str]: A list of admin users or a single admin user details.

    Examples:
        List all admins:

        >>> admins = ztw_list_admins()
        >>> print(f"Total admins found: {len(admins)}")
        >>> for admin in admins:
        ...     print(admin)

        List admins with specific filters:

        >>> admins = ztw_list_admins(
        ...     include_auditor_users=True,
        ...     include_admin_users=True,
        ...     include_api_roles=True
        ... )
        >>> print(f"Found {len(admins)} admins with specified filters")

        Search for admins:

        >>> admins = ztw_list_admins(search="admin")
        >>> print(f"Found {len(admins)} admins matching 'admin'")

        List admins with pagination:

        >>> admins = ztw_list_admins(page=1, page_size=10)
        >>> print(f"Found {len(admins)} admins on page 1")

        Get specific admin details:

        >>> admin = ztw_list_admins(action="get_admin", admin_id="123456789")
        >>> print(f"Admin details: {admin}")

        List admins from backup version:

        >>> admins = ztw_list_admins(version=1)
        >>> print(f"Found {len(admins)} admins from backup version 1")
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    if action == "get_admin":
        if not admin_id:
            raise ValueError("admin_id is required when action is 'get_admin'")

        admin, _, err = client.ztw.admin_users.get_admin(admin_id)
        if err:
            raise Exception(f"Error getting ZTW admin {admin_id}: {err}")
        return admin.as_dict()

    elif action == "list_admins":
        query_params = {}
        if include_auditor_users is not None:
            query_params["include_auditor_users"] = include_auditor_users
        if include_admin_users is not None:
            query_params["include_admin_users"] = include_admin_users
        if include_api_roles is not None:
            query_params["include_api_roles"] = include_api_roles
        if search:
            query_params["search"] = search
        if page is not None:
            query_params["page"] = page
        if page_size is not None:
            query_params["page_size"] = page_size
        if version is not None:
            query_params["version"] = version

        admins, _, err = client.ztw.admin_users.list_admins(query_params=query_params)
        if err:
            raise Exception(f"Error listing ZTW admins: {err}")
        return [a.as_dict() for a in admins]

    else:
        raise ValueError(f"Invalid action '{action}'. Must be 'list_admins' or 'get_admin'")
