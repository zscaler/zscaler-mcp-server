from src.sdk.zscaler_client import get_zscaler_client
from typing import Union


def scim_group_manager(
    action: str,
    scim_group_id: str = None,
    idp_name: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> Union[dict, list[dict], str]:
    """
    Tool for retrieving ZPA SCIM groups under a given Identity Provider (IdP).

    Supported actions:
    - read: Fetch all SCIM groups for a given IdP name, or one SCIM group by ID.

    Args:
        scim_group_id (str): If provided, fetch a specific SCIM group.
        idp_name (str): Required for listing SCIM groups.
        query_params (dict): Optional filters like search, page, page_size, etc.

    Returns:
        Union[dict, list[dict], str]: SCIM group(s) data.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    idp_api = client.zpa.idp
    scim_api = client.zpa.scim_groups

    if action == "read":
        query_params = query_params or {}

        # Fetch a specific SCIM group
        if scim_group_id:
            result, _, err = scim_api.get_scim_group(scim_group_id, query_params=query_params)
            if err:
                raise Exception(f"Failed to fetch SCIM group {scim_group_id}: {err}")
            return result.as_dict()

        # List SCIM groups under a resolved IdP
        if not idp_name:
            raise ValueError("idp_name is required to list SCIM groups")

        idps, _, err = idp_api.list_idps(query_params={"search": idp_name})
        if err:
            raise Exception(f"Failed to look up IdP by name: {err}")

        idp_match = next((idp for idp in idps if idp.name == idp_name), None)
        if not idp_match:
            raise Exception(f"No matching IdP found with name '{idp_name}'")

        scim_groups, _, err = scim_api.list_scim_groups(idp_id=idp_match.id, query_params=query_params)
        if err:
            raise Exception(f"Failed to list SCIM groups for IdP '{idp_name}': {err}")

        return [group.as_dict() for group in scim_groups]

    raise ValueError(f"Unsupported action: {action}")
