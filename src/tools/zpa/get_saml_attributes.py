from src.sdk.zscaler_client import get_zscaler_client
from typing import Union


def saml_attribute_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    idp_name: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> Union[list[dict], str]:
    """
    Tool for querying ZPA SAML Attributes.

    Supported actions:
    - read: Lists all SAML attributes or filters by IdP name (resolved internally).

    Args:
        action (str): Must be 'read'.
        idp_name (str, optional): The name of the IdP to filter attributes by.
        query_params (dict, optional): Optional filters like search, page, page_size.

    Returns:
        List[dict] or str: A list of SAML attribute dictionaries.
    """
    if action != "read":
        raise ValueError("Only 'read' action is supported")

    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        use_legacy=use_legacy,
        service=service,
    )

    saml_api = client.zpa.saml_attributes
    idp_api = client.zpa.idp
    query_params = query_params or {}

    if idp_name:
        # Resolve IdP ID from name
        idps, _, err = idp_api.list_idps(query_params={"search": idp_name})
        if err:
            raise Exception(f"Failed to search IdP: {err}")
        idp_match = next((i for i in idps if i.name.lower() == idp_name.lower()), None)
        if not idp_match:
            raise Exception(f"No IdP found with name: {idp_name}")
        idp_id = idp_match.id

        # Fetch SAML attributes for the resolved IdP
        attributes, _, err = saml_api.list_saml_attributes_by_idp(idp_id=idp_id, query_params=query_params)
        if err:
            raise Exception(f"Failed to list SAML attributes for IdP {idp_name}: {err}")
        return [a.as_dict() for a in attributes]

    else:
        # Fetch all SAML attributes
        attributes, _, err = saml_api.list_saml_attributes(query_params=query_params)
        if err:
            raise Exception(f"Failed to list SAML attributes: {err}")
        return [a.as_dict() for a in attributes]
