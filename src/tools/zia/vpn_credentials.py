from src.sdk.zscaler_client import get_zscaler_client

def vpn_credential_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    credential_id: int = None,
    credential_type: str = None,  # "IP" or "UFQDN"
    pre_shared_key: str = None,
    ip_address: str = None,
    fqdn: str = None,
    comments: str = None,
    query_params: dict = None,
) -> dict | list[dict] | str:
    """
    Tool for managing ZIA VPN Credentials.

    Supported actions:
    - create: Requires pre_shared_key and type ("IP" or "UFQDN").
        - If type is "IP", ip_address is required.
        - If type is "UFQDN", fqdn is required.
    - read: List or get credential(s).
    - update: Requires credential_id. fqdn/ip_address cannot be changed.
    - delete: Deletes a single VPN credential using credential_id.

    Returns:
        dict | list[dict] | str
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )
    api = client.zia.traffic_vpn_credentials

    if action == "create":
        if credential_type not in ["IP", "UFQDN"]:
            raise ValueError("credential_type must be 'IP' or 'UFQDN'")
        if not pre_shared_key:
            raise ValueError("pre_shared_key is required for VPN credential creation")

        body = {
            "type": credential_type,
            "pre_shared_key": pre_shared_key,
            "comments": comments,
        }
        if credential_type == "IP":
            if not ip_address:
                raise ValueError("ip_address is required for type 'IP'")
            body["ip_address"] = ip_address
        else:
            if not fqdn:
                raise ValueError("fqdn is required for type 'UFQDN'")
            body["fqdn"] = fqdn

        created, _, err = api.add_vpn_credential(**body)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if credential_id:
            result, _, err = api.get_vpn_credential(credential_id)
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            credentials, _, err = api.list_vpn_credentials(query_params=query_params)
            if err:
                raise Exception(f"List failed: {err}")
            return [c.as_dict() for c in credentials]

    elif action == "update":
        if not credential_id:
            raise ValueError("credential_id is required for update")

        update_fields = {
            "pre_shared_key": pre_shared_key,
            "comments": comments,
        }
        updated, _, err = api.update_vpn_credential(credential_id, **update_fields)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not credential_id:
            raise ValueError("credential_id is required for deletion")
        _, _, err = api.delete_vpn_credential(credential_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted VPN credential {credential_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
