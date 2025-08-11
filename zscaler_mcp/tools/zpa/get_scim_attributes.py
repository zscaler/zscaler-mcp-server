from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def scim_attribute_manager(
    action: Annotated[str, Field(description="Must be 'read'.")],
    idp_name: Annotated[
        str, Field(description="Required to resolve the IdP and fetch SCIM attributes.")
    ] = None,
    attribute_id: Annotated[
        str, Field(description="ID of a specific SCIM attribute.")
    ] = None,
    query_params: Annotated[
        dict, Field(description="Pagination or search filters.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[List[dict], dict, str]:
    """
    Tool for managing ZPA SCIM Attributes.

    Supported actions:
    - read: Requires idp_name to resolve IdP ID.
        - If attribute_id is provided, fetches a specific attribute.
        - Otherwise returns all SCIM attributes for the IdP.

    Args:
        action (str): Must be 'read'.
        idp_name (str): Required to resolve the IdP and fetch SCIM attributes.
        attribute_id (str, optional): ID of a specific SCIM attribute.
        query_params (dict, optional): Pagination or search filters.

    Returns:
        list[dict] or dict or str
    """
    if action != "read":
        raise ValueError("Only 'read' action is supported.")

    if not idp_name:
        raise ValueError("idp_name is required for SCIM attribute discovery.")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    idp_api = client.zpa.idp
    scim_api = client.zpa.scim_attributes
    query_params = query_params or {}

    # Step 1: Resolve IdP by name
    idps, _, err = idp_api.list_idps(query_params={"search": idp_name})
    if err:
        raise Exception(f"Failed to search IdPs: {err}")
    idp_match = next((i for i in idps if i.name.lower() == idp_name.lower()), None)
    if not idp_match:
        raise Exception(f"No IdP found with name: {idp_name}")
    idp_id = idp_match.id

    # Step 2: Fetch either all attributes or one by ID
    if attribute_id:
        attr, _, err = scim_api.get_scim_attribute(
            idp_id=idp_id, attribute_id=attribute_id, query_params=query_params
        )
        if err:
            raise Exception(f"Failed to fetch SCIM attribute by ID: {err}")
        return attr.as_dict()
    else:
        attributes, _, err = scim_api.list_scim_attributes(
            idp_id=idp_id, query_params=query_params
        )
        if err:
            raise Exception(f"Failed to list SCIM attributes for IdP {idp_name}: {err}")
        return [a.as_dict() for a in attributes]
