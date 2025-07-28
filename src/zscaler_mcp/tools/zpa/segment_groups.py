from zscaler_mcp.sdk.zscaler_client import get_zscaler_client
from zscaler_mcp import app
from typing import Union, List
from typing import Annotated
from pydantic import Field


@app.tool(
    name="zpa_segment_groups",
    description="Tool for managing Segment Groups.",
)
def segment_group_v6_manager(
    action: Annotated[
        str,
        Field(description="Operation to perform: 'create', 'read', 'update', or 'delete'.")
    ],
    group_id: Annotated[
        str,
        Field(description="ID of the segment group (required for read/update/delete).")
    ] = None,
    name: Annotated[
        str,
        Field(description="Name of the segment group (required for create/update).")
    ] = None,
    description: Annotated[
        str,
        Field(description="Description of the segment group.")
    ] = None,
    enabled: Annotated[
        bool,
        Field(description="Whether the group is enabled.")
    ] = True,
    microtenant_id: Annotated[
        str,
        Field(description="Microtenant ID for scoping operations.")
    ] = None,
    search: Annotated[
        str,
        Field(description="Search term for listing groups.")
    ] = None,
    page: Annotated[
        str,
        Field(description="Page number for pagination.")
    ] = None,
    page_size: Annotated[
        str,
        Field(description="Items per page for pagination.")
    ] = None,
    use_legacy: Annotated[
        bool,
        Field(description="Whether to use the legacy API.")
    ] = False,
    service: Annotated[
        str,
        Field(description="The service to use.")
    ] = "zpa",
) -> Union[dict, List[dict], str]:
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