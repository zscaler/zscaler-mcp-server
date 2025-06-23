from src.sdk.zscaler_client import get_zscaler_client

def segment_group_v6_manager(
    action: str,
    group_id: str = None,
    name: str = None,
    description: str = None,
    enabled: bool = True,
    microtenant_id: str = None,
    search: str = None,
    page: str = None,
    page_size: str = None,
    use_legacy: bool = False,
    service: str = "zpa",
) -> dict | list[dict] | str:
    """
    Tool for managing Segment Groups.

    Note: Authentication credentials are automatically loaded from environment variables.
    Do NOT pass credentials as arguments.

    Args:
        action: Operation to perform ('create', 'read', 'update', 'delete')
        group_id: ID of the segment group (required for read/update/delete)
        name: Name of the segment group (required for create/update)
        description: Description of the segment group
        enabled: Whether the group is enabled
        microtenant_id: Microtenant ID for scoping
        search: Search term for listing groups
        page: Page number for pagination
        page_size: Items per page
        use_legacy: Whether to use legacy API
        service: Service type (defaults to 'zpa')
    """

    # Block any credential passthrough attempts
    # import inspect
    # frame = inspect.currentframe()
    # args, _, _, values = inspect.getargvalues(frame)
    # credential_keys = ['client_id', 'client_secret', 'customer_id', 'vanity_domain']
    # if any(k in values for k in credential_keys):
    #     raise ValueError("Credentials must be set via environment variables, not function arguments")

    client = get_zscaler_client(use_legacy=use_legacy, service=service)

    sg = client.zpa.segment_groups

    if action == "create":
        body = {
            "name": name,
            "description": description,
            "enabled": enabled,
        }
        if microtenant_id:
            body["microtenant_id"] = microtenant_id

        result, _, err = sg.add_group(**body)
        if err:
            raise Exception(f"Create failed: {err}")
        return result.as_dict()

    elif action == "read":
        if group_id:
            result, _, err = sg.get_group(group_id, query_params={"microtenant_id": microtenant_id})
            if err:
                raise Exception(f"Read failed: {err}")
            return result.as_dict()
        else:
            qp = {"microtenant_id": microtenant_id}
            if search:
                qp["search"] = search
            if page:
                qp["page"] = page
            if page_size:
                qp["page_size"] = page_size

            groups, _, err = sg.list_groups(query_params=qp)
            if err:
                raise Exception(f"List failed: {err}")
            return [g.as_dict() for g in (groups or [])]

    elif action == "update":
        if not group_id:
            raise ValueError("group_id is required for update")

        update_data = {
            "name": name,
            "description": description,
            "enabled": enabled,
        }
        if microtenant_id:
            update_data["microtenant_id"] = microtenant_id

        result, _, err = sg.update_group_v2(group_id, **update_data)
        if err:
            raise Exception(f"Update failed: {err}")
        return result.as_dict()

    elif action == "delete":
        if not group_id:
            raise ValueError("group_id is required for delete")

        _, _, err = sg.delete_group(group_id, microtenant_id=microtenant_id)
        if err:
            raise Exception(f"Delete failed: {err}")
        return f"Deleted segment group {group_id}"

    else:
        raise ValueError(f"Unsupported action: {action}")