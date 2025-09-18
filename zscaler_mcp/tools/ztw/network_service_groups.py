from typing import Annotated, List, Literal, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def ztw_network_service_group_manager(
    action: Annotated[
        Literal["read"],
        Field(description="Action to perform: list network service groups."),
    ] = "read",
    search: Annotated[
        Optional[str],
        Field(description="Optional search string for filtering results by group name or description."),
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "ztw",
) -> List[dict]:
    """
    Lists network service groups in your ZTW organization with optional search filtering.
    
    This tool provides read-only access to network service groups. Network service groups
    are collections of network services that can be used for policy configuration and
    traffic management in Zscaler Trusted Web.
    
    Args:
        action (str): Currently only supports "list" operation.
        search (str, optional): Search string to filter results by group name or description.
                               The search is case-insensitive and supports partial matching.
        use_legacy (bool): Whether to use the legacy API (default: False).
        service (str): The service to use (default: "ztw").
    
    Returns:
        List[dict]: List of network service group objects with their properties.
    
    Examples:
        List all network service groups:
        >>> groups = ztw_network_service_group_manager(action="read")
        
        Search for groups containing "web":
        >>> groups = ztw_network_service_group_manager(action="read", search="web")
        
        Search for groups containing "database":
        >>> groups = ztw_network_service_group_manager(action="read", search="database")
    
    Note:
        - This is a read-only operation. Network service groups cannot be created,
          updated, or deleted through this tool.
        - Each group object contains: id, name, description, creatorContext, and services.
        - The services field contains a list of network services within each group.
        - Search functionality supports partial matching on group names and descriptions.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    ztw = client.ztw.nw_service_groups

    if action == "read":
        query_params = {"search": search} if search else {}
        groups, _, err = ztw.list_network_svc_groups(query_params=query_params)
        if err:
            raise Exception(f"Error listing network service groups: {err}")
        return [g.as_dict() for g in groups]

    else:
        raise ValueError(f"Unsupported action: {action}")
