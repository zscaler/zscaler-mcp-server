from src.sdk.zscaler_client import get_zscaler_client
from typing import Union


def scim_attribute_manager(
    action: str,
    idp_name: str = None,
    attribute_id: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> Union[list[dict], dict, str]:
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
        attr, _, err = scim_api.get_scim_attribute(idp_id=idp_id, attribute_id=attribute_id, query_params=query_params)
        if err:
            raise Exception(f"Failed to fetch SCIM attribute by ID: {err}")
        return attr.as_dict()
    else:
        attributes, _, err = scim_api.list_scim_attributes(idp_id=idp_id, query_params=query_params)
        if err:
            raise Exception(f"Failed to list SCIM attributes for IdP {idp_name}: {err}")
        return [a.as_dict() for a in attributes]
