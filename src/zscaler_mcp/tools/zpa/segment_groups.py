from zscaler_mcp.sdk.zscaler_client import get_zscaler_client

def segment_group_manager(
    action: str,
    cloud: str,
    client_id: str,
    client_secret: str,
    customer_id: str,
    vanity_domain: str,
    group_id: str = None,
    name: str = None,
    description: str = None,
    enabled: bool = True,
    microtenant_id: str = None,
    search: str = None,
    page: str = None,
    page_size: str = None,
) -> dict | list[dict] | str:
    """
    CRUD handler for ZPA Segment Groups using the Zscaler Python SDK.
    """
    client = get_zscaler_client(
        cloud=cloud,
        client_id=client_id,
        client_secret=client_secret,
        customer_id=customer_id,
        vanity_domain=vanity_domain,
    )

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
