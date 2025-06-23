from src.sdk.zscaler_client import get_zscaler_client
from typing import Union

def application_server_v2_manager(
    action: str,
    server_id: str = None,
    name: str = None,
    description: str = None,
    address: str = None,
    enabled: bool = True,
    app_server_group_ids: list[str] = None,
    microtenant_id: str = None,
    query_params: dict = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> Union[dict, list[dict], str]:
    """
    Tool for managing ZPA Application Servers.

    Note: Authentication credentials are automatically loaded from environment variables.
    Do NOT pass credentials as arguments.

    Args:

        action: Operation to perform ('create', 'read', 'update', 'delete')
        name: Name of the segment group (required for create/update)
        description: Description of the segment group
        enabled: Whether the group is enabled
        address: The domain or IP address of the server.
        app_server_group_ids: (Optional) The ID of the server group if required
        microtenant_id: Microtenant ID for scoping
        use_legacy: Whether to use legacy API
        service: Service type (defaults to 'zpa')
        create: Requires name, address.
        read: List all servers or one by server_id.
        update: Requires server_id.
        delete: Requires server_id.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    api = client.zpa.servers

    if action == "create":
        if not all([name, address]):
            raise ValueError("Both 'name' and 'address' are required for creation.")

        payload = {
            "name": name,
            "description": description,
            "address": address,
            "enabled": enabled,
            "app_server_group_ids": app_server_group_ids,
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
