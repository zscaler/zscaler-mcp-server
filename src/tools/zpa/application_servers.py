from src.sdk.zscaler_client import get_zscaler_client
from typing import Union

def application_server_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    server_id: str = None,
    name: str = None,
    description: str = None,
    address: str = None,
    enabled: bool = True,
    app_server_group_ids: list[str] = None,
    config_space: str = None,
    microtenant_id: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> Union[dict, list[dict], str]:
    """
    Tool for managing ZPA Application Servers.

    Supported actions:
    - create: Requires name, address, app_server_group_ids.
    - read: List all servers or one by server_id.
    - update: Requires server_id.
    - delete: Requires server_id.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
        use_legacy=use_legacy,
        service=service,
    )

    api = client.zpa.servers

    if action == "create":
        if not all([name, address, app_server_group_ids]):
            raise ValueError("name, address, and app_server_group_ids are required for creation")

        payload = {
            "name": name,
            "description": description,
            "address": address,
            "enabled": enabled,
            "app_server_group_ids": app_server_group_ids,
            "config_space": config_space,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        created, _, err = api.add_server(**payload)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if server_id:
            result, _, err = api.get_server(server_id, query_params={"microtenant_id": microtenant_id})
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            qp = query_params or {}
            if microtenant_id:
                qp["microtenant_id"] = microtenant_id
            servers, _, err = api.list_servers(query_params=qp)
            if err:
                raise Exception(f"List failed: {err}")
            return [s.as_dict() for s in servers]

    elif action == "update":
        if not server_id:
            raise ValueError("server_id is required for update")

        payload = {
            "name": name,
            "description": description,
            "address": address,
            "enabled": enabled,
            "app_server_group_ids": app_server_group_ids,
            "config_space": config_space,
        }
        if microtenant_id:
            payload["microtenant_id"] = microtenant_id

        updated, _, err = api.update_server(server_id, **payload)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not server_id:
            raise ValueError("server_id is required for deletion")

        _, _, err = api.delete_server(server_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted application server {server_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
