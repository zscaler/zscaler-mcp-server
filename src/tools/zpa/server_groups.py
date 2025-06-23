from src.sdk.zscaler_client import get_zscaler_client

def server_group_manager(
    action: str,
    group_id: str = None,
    microtenant_id: str = None,
    name: str = None,
    description: str = None,
    enabled: bool = True,
    app_connector_group_ids: list[str] = None,
    server_ids: list[str] = None,
    ip_anchored: bool = None,
    dynamic_discovery: bool = None,
    search: str = None,
    page: str = None,
    page_size: str = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> dict | list[dict] | str:
    """
    CRUD handler for ZPA Server Groups via the Python SDK.

    Required fields:
    - create: name, app_connector_group_ids
    - update: group_id, at least one mutable field
    - delete: group_id

    Arguments:
    - action (str): One of 'create', 'read', 'update', or 'delete'.
    - app_connector_group_ids (list[str]): Required when action is 'create'.
    - group_id (str): Required for 'read' (single), 'update', and 'delete'.
    - microtenant_id (str): Optional, passed through to API query or payload.
    """
    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    api = client.zpa.server_groups

    if action == "create":
        if not app_connector_group_ids:
            raise ValueError("app_connector_group_ids is required for creating a server group")

        body = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "app_connector_group_ids": app_connector_group_ids or [],
            "server_ids": server_ids or [],
            "ip_anchored": ip_anchored,
            "dynamic_discovery": dynamic_discovery,
        }
        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        created, _, err = api.add_group(**body)
        if err:
            raise Exception(f"Create failed: {err}")
        return created.as_dict()

    elif action == "read":
        if group_id:
            group, _, err = api.get_group(group_id, query_params={"microtenant_id": microtenant_id})
            if err:
                raise Exception(f"Read failed: {err}")
            return group.as_dict()
        else:
            qp = {"microtenant_id": microtenant_id}
            if search:
                qp["search"] = search
            if page:
                qp["page"] = page
            if page_size:
                qp["page_size"] = page_size

            groups, _, err = api.list_groups(query_params=qp)
            if err:
                raise Exception(f"List failed: {err}")
            return [g.as_dict() for g in (groups or [])]

    elif action == "update":
        if not group_id:
            raise ValueError("group_id is required for update")

        body = {
            "name": name,
            "description": description,
            "enabled": enabled,
            "app_connector_group_ids": app_connector_group_ids or [],
            "server_ids": server_ids or [],
            "ip_anchored": ip_anchored,
            "dynamic_discovery": dynamic_discovery,
        }

        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        updated, _, err = api.update_group(group_id, **body)
        if err:
            raise Exception(f"Update failed: {err}")
        return updated.as_dict()

    elif action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete")
        _, _, err = api.delete_group(group_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted server group {group_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")
