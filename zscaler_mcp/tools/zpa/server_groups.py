from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zpa_list_server_groups(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring match on the server group's `name` field. "
                "Returns the full set of matches in this tenant — no fuzzy matching, no "
                "synonym expansion. An empty list means no server group name contains this "
                "string; do not retry with split keywords or no filter."
            )
        ),
    ] = None,
    page: Annotated[Optional[str], Field(description="Page number for pagination.")] = None,
    page_size: Annotated[Optional[str], Field(description="Number of items per page.")] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List ZPA server groups with optional filtering and pagination.

    Supports JMESPath client-side filtering via the query parameter.
    """
    client = get_zscaler_client(service=service)
    api = client.zpa.server_groups

    qp = {"microtenant_id": microtenant_id}
    if search:
        qp["search"] = search
    if page:
        qp["page"] = page
    if page_size:
        qp["page_size"] = page_size

    groups, _, err = api.list_groups(query_params=qp)
    if err:
        raise Exception(f"Failed to list server groups: {err}")
    results = [g.as_dict() for g in (groups or [])]
    return apply_jmespath(results, query)


def zpa_get_server_group(
    group_id: Annotated[str, Field(description="Group ID for the server group.")],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA server group by ID."""
    if not group_id:
        raise ValueError("group_id is required")

    client = get_zscaler_client(service=service)
    api = client.zpa.server_groups

    group, _, err = api.get_group(group_id, query_params={"microtenant_id": microtenant_id})
    if err:
        raise Exception(f"Failed to get server group {group_id}: {err}")
    return group.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zpa_create_server_group(
    name: Annotated[str, Field(description="Name of the server group.")],
    app_connector_group_ids: Annotated[
        List[str],
        Field(
            description=(
                "REQUIRED. One or more existing App Connector Group IDs to bind this "
                "server group to. The ZPA API rejects creation if this is empty. "
                "If the admin did not supply IDs, discover existing groups first via "
                "`zpa_list_app_connector_groups(search='<name>')` — do not invent IDs."
            )
        ),
    ],
    description: Annotated[
        Optional[str], Field(description="Description of the server group.")
    ] = None,
    enabled: Annotated[bool, Field(description="Whether the group is enabled.")] = True,
    server_ids: Annotated[
        Optional[List[str]],
        Field(
            description=(
                "Application Server IDs to bind to this group. Required only when "
                "`dynamic_discovery=False` (the connector then routes only to these "
                "explicit servers). Ignored / not required when dynamic discovery is on. "
                "Discover existing servers via `zpa_list_application_servers` or create "
                "them via `zpa_create_application_server`."
            )
        ),
    ] = None,
    ip_anchored: Annotated[
        Optional[bool], Field(description="Whether the group is IP anchored.")
    ] = None,
    dynamic_discovery: Annotated[
        bool,
        Field(
            description=(
                "Defaults to True. When True, the App Connector resolves backend "
                "servers from each application segment's domain list at runtime — "
                "no static `server_ids` needed. Set False ONLY when the admin wants "
                "to pin the server group to an explicit list of Application Servers; "
                "in that case `server_ids` becomes REQUIRED."
            )
        ),
    ] = True,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Create a new ZPA server group.

    Business rules enforced by this tool:

    - ``app_connector_group_ids`` MUST be non-empty (the API rejects it otherwise).
    - ``dynamic_discovery`` defaults to ``True`` — most server groups should
      use dynamic discovery so the connector can resolve backends from app
      segment domain lists.
    - If the caller explicitly sets ``dynamic_discovery=False``, ``server_ids``
      is required and must be non-empty (a static server group with no
      servers is not useful and is rejected here before the API call).
    """
    if not name:
        raise ValueError("name is required")
    if not app_connector_group_ids:
        raise ValueError(
            "app_connector_group_ids is required and must contain at least one ID. "
            "Use zpa_list_app_connector_groups to discover existing groups."
        )
    if dynamic_discovery is False and not server_ids:
        raise ValueError(
            "dynamic_discovery=False requires server_ids to be a non-empty list. "
            "Either enable dynamic discovery (the default) or supply Application "
            "Server IDs via zpa_list_application_servers / zpa_create_application_server."
        )

    client = get_zscaler_client(service=service)
    api = client.zpa.server_groups

    body: Dict = {
        "name": name,
        "enabled": enabled,
        "app_connector_group_ids": app_connector_group_ids,
        "dynamic_discovery": dynamic_discovery,
    }
    if description is not None:
        body["description"] = description
    if server_ids:
        body["server_ids"] = server_ids
    if ip_anchored is not None:
        body["ip_anchored"] = ip_anchored
    if microtenant_id:
        body["microtenant_id"] = microtenant_id

    created, _, err = api.add_group(**body)
    if err:
        raise Exception(f"Failed to create server group: {err}")
    return created.as_dict()


def zpa_update_server_group(
    group_id: Annotated[str, Field(description="Group ID for the server group.")],
    name: Annotated[Optional[str], Field(description="Name of the server group.")] = None,
    description: Annotated[
        Optional[str], Field(description="Description of the server group.")
    ] = None,
    enabled: Annotated[Optional[bool], Field(description="Whether the group is enabled.")] = None,
    app_connector_group_ids: Annotated[
        Optional[List[str]],
        Field(
            description=(
                "Replace the bound App Connector Group IDs. Omit (None) to preserve "
                "the existing binding. Passing this with an empty list is rejected — "
                "a server group must always have at least one connector group."
            )
        ),
    ] = None,
    server_ids: Annotated[
        Optional[List[str]],
        Field(
            description=(
                "Replace the bound Application Server IDs. Omit to preserve existing. "
                "Required to be non-empty if `dynamic_discovery=False` is being set "
                "(or is already False on the group and is not being flipped on)."
            )
        ),
    ] = None,
    ip_anchored: Annotated[
        Optional[bool], Field(description="Whether the group is IP anchored.")
    ] = None,
    dynamic_discovery: Annotated[
        Optional[bool],
        Field(
            description=(
                "Omit to preserve the current value. Set False ONLY when pinning the "
                "group to explicit Application Server IDs — in that case `server_ids` "
                "must be supplied (or already populated on the existing group)."
            )
        ),
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA server group.

    Partial-update semantics: only the fields explicitly passed are sent to the API.
    Fields left at their default (None) preserve their existing values on the group.

    Business rules enforced by this tool:

    - ``app_connector_group_ids=[]`` is rejected — a server group must always
      have at least one connector group.
    - If ``dynamic_discovery=False`` is set, ``server_ids`` must be either
      supplied in this call OR already present on the existing group; the tool
      fetches the current state to verify before sending the PUT.
    """
    if not group_id:
        raise ValueError("group_id is required for update")

    if app_connector_group_ids is not None and len(app_connector_group_ids) == 0:
        raise ValueError(
            "app_connector_group_ids cannot be set to an empty list — server groups "
            "must always have at least one App Connector Group binding. Omit the "
            "parameter to preserve the existing binding."
        )

    client = get_zscaler_client(service=service)
    api = client.zpa.server_groups

    if dynamic_discovery is False and not server_ids:
        existing, _, err = api.get_group(
            group_id, query_params={"microtenant_id": microtenant_id}
        )
        if err:
            raise Exception(f"Failed to fetch server group {group_id} for validation: {err}")
        existing_servers = (
            getattr(existing, "servers", None) or existing.as_dict().get("servers") or []
        )
        if not existing_servers:
            raise ValueError(
                "dynamic_discovery=False requires server_ids to be non-empty. "
                "The existing group has no Application Servers bound, so you must "
                "supply server_ids in this update (or keep dynamic_discovery on)."
            )

    body: Dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if enabled is not None:
        body["enabled"] = enabled
    if app_connector_group_ids is not None:
        body["app_connector_group_ids"] = app_connector_group_ids
    if server_ids is not None:
        body["server_ids"] = server_ids
    if ip_anchored is not None:
        body["ip_anchored"] = ip_anchored
    if dynamic_discovery is not None:
        body["dynamic_discovery"] = dynamic_discovery
    if microtenant_id:
        body["microtenant_id"] = microtenant_id

    updated, _, err = api.update_group(group_id, **body)
    if err:
        raise Exception(f"Failed to update server group {group_id}: {err}")
    return updated.as_dict()


def zpa_delete_server_group(
    group_id: Annotated[str, Field(description="Group ID for the server group.")],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}",
) -> str:
    """Delete a ZPA server group."""
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    # Extract confirmation from kwargs (hidden from tool schema)
    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation("zpa_delete_server_group", confirmed, {"group_id": str(group_id)})
    if confirmation_check:
        return confirmation_check

    if not group_id:
        raise ValueError("group_id is required for delete")

    client = get_zscaler_client(service=service)
    api = client.zpa.server_groups

    _, _, err = api.delete_group(group_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete server group {group_id}: {err}")
    return f"Successfully deleted server group {group_id}"
