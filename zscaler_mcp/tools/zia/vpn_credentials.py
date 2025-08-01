from zscaler_mcp.client import get_zscaler_client
from typing import Annotated, Union, List
from pydantic import Field


def vpn_credential_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', or 'delete'."
        ),
    ],
    credential_id: Annotated[
        int, Field(description="Credential ID for read, update, or delete operations.")
    ] = None,
    credential_type: Annotated[
        str, Field(description="Type of credential: 'IP' or 'UFQDN'.")
    ] = None,
    pre_shared_key: Annotated[
        str, Field(description="Pre-shared key (required for create and update).")
    ] = None,
    ip_address: Annotated[
        str, Field(description="IP address (required for type 'IP').")
    ] = None,
    fqdn: Annotated[str, Field(description="FQDN (required for type 'UFQDN').")] = None,
    comments: Annotated[
        str, Field(description="Optional comments for the credential.")
    ] = None,
    query_params: Annotated[
        dict, Field(description="Optional query parameters for filtering results.")
    ] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Union[dict, List[dict], str]:
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
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

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
