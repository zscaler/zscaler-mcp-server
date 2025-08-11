from typing import Annotated, List, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def server_group_manager(
    action: Annotated[
        str,
        Field(
            description="Action to perform: 'create', 'read', 'update', or 'delete'."
        ),
    ],
    group_id: Annotated[
        str, Field(description="Group ID for read, update, or delete operations.")
    ] = None,
    microtenant_id: Annotated[
        str, Field(description="Microtenant ID for scoping operations.")
    ] = None,
    name: Annotated[str, Field(description="Name of the server group.")] = None,
    description: Annotated[
        str, Field(description="Description of the server group.")
    ] = None,
    enabled: Annotated[bool, Field(description="Whether the group is enabled.")] = True,
    app_connector_group_ids: Annotated[
        List[str],
        Field(description="List of app connector group IDs (required for create)."),
    ] = None,
    server_ids: Annotated[List[str], Field(description="List of server IDs.")] = None,
    ip_anchored: Annotated[
        bool, Field(description="Whether the group is IP anchored.")
    ] = None,
    dynamic_discovery: Annotated[
        bool, Field(description="Whether dynamic discovery is enabled.")
    ] = None,
    search: Annotated[
        str, Field(description="Search term for filtering results.")
    ] = None,
    page: Annotated[str, Field(description="Page number for pagination.")] = None,
    page_size: Annotated[str, Field(description="Number of items per page.")] = None,
    use_legacy: Annotated[
        bool, Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Union[dict, List[dict], str]:
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
            raise ValueError(
                "app_connector_group_ids is required for creating a server group"
            )

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
            group, _, err = api.get_group(
                group_id, query_params={"microtenant_id": microtenant_id}
            )
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
