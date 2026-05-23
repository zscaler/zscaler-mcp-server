from typing import Annotated, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zpa_list_service_edges(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring match on the service edge's `name` field. "
                "Returns the full set of matches in this tenant — no fuzzy matching, no "
                "synonym expansion. An empty list means no service edge name contains "
                "this string; do not retry with split keywords or no filter."
            )
        ),
    ] = None,
    page: Annotated[Optional[int], Field(ge=1, description="Page number for pagination.")] = None,
    page_size: Annotated[
        Optional[int],
        Field(ge=1, description="Number of items per page. Default 20, max 500."),
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[Dict]:
    """List individual ZPA Service Edges with optional filtering and pagination.

    Returns each service edge's id, name, control-channel state, runtime
    status, version, geographic location, enrollment certificate, and the
    `serviceEdgeGroupId` it's attached to. Distinct from
    `zpa_list_service_edge_groups` (the parent group resource) and
    `zpa_list_provisioning_keys` (the bootstrap tokens used to enroll
    these edges into a group).

    Supports JMESPath client-side filtering via the `query` parameter.
    """
    client = get_zscaler_client(service=service)
    api = client.zpa.service_edges

    qp: Dict = {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    if search:
        qp["search"] = search
    if page is not None:
        qp["page"] = str(page)
    if page_size is not None:
        qp["page_size"] = str(page_size)

    edges, _, err = api.list_service_edges(query_params=qp)
    if err:
        raise Exception(f"Failed to list service edges: {err}")
    results = [e.as_dict() for e in (edges or [])]
    return apply_jmespath(results, query)


def zpa_get_service_edge(
    service_edge_id: Annotated[str, Field(description="The unique ID of the ZPA Service Edge.")],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA Service Edge by ID.

    Returns the full record — control-channel state, runtime status,
    version, location, enrollment certificate, parent service edge group
    membership, and provisioning key reference.
    """
    if not service_edge_id:
        raise ValueError("service_edge_id is required")

    client = get_zscaler_client(service=service)
    api = client.zpa.service_edges

    kwargs: Dict = {}
    if microtenant_id:
        kwargs["microtenant_id"] = microtenant_id

    edge = api.get_service_edge(service_edge_id, **kwargs)
    if edge is None:
        raise Exception(f"Failed to get service edge {service_edge_id}")
    return edge.as_dict()


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zpa_update_service_edge(
    service_edge_id: Annotated[str, Field(description="The unique ID of the ZPA Service Edge.")],
    name: Annotated[Optional[str], Field(description="Name of the service edge.")] = None,
    description: Annotated[
        Optional[str], Field(description="Description of the service edge.")
    ] = None,
    enabled: Annotated[
        Optional[bool], Field(description="Whether the service edge is enabled.")
    ] = None,
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Update an existing ZPA Service Edge.

    The SDK call is PUT under the hood, but only the keyword arguments
    explicitly passed in this tool become part of the body — the SDK
    forwards exactly what's in `**kwargs` rather than full-replacing
    every field. Use this to enable/disable an edge or rename it; group
    re-membership and provisioning-key assignment are managed via the
    Service Edge Group / Provisioning Key tools.
    """
    if not service_edge_id:
        raise ValueError("service_edge_id is required for update")

    client = get_zscaler_client(service=service)
    api = client.zpa.service_edges

    body: Dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if enabled is not None:
        body["enabled"] = enabled
    if microtenant_id:
        body["microtenant_id"] = microtenant_id

    updated, _, err = api.update_service_edge(service_edge_id, **body)
    if err:
        raise Exception(f"Failed to update service edge {service_edge_id}: {err}")
    return updated.as_dict()


def zpa_delete_service_edge(
    service_edge_id: Annotated[
        str, Field(description="The unique ID of the ZPA Service Edge to delete.")
    ],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}",
) -> str:
    """Delete a single ZPA Service Edge.

    Removes the edge from the ZPA cloud; it must be re-provisioned (with
    a fresh provisioning key) to reconnect. HMAC double-confirmed.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation(
        "zpa_delete_service_edge",
        confirmed,
        {"service_edge_id": str(service_edge_id)},
    )
    if confirmation_check:
        return confirmation_check

    if not service_edge_id:
        raise ValueError("service_edge_id is required for delete")

    client = get_zscaler_client(service=service)
    api = client.zpa.service_edges

    _, _, err = api.delete_service_edge(service_edge_id, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to delete service edge {service_edge_id}: {err}")
    return f"Successfully deleted service edge {service_edge_id}"


def zpa_bulk_delete_service_edges(
    service_edge_ids: Annotated[
        List[str], Field(description="List of Service Edge IDs to delete.")
    ],
    microtenant_id: Annotated[
        Optional[str], Field(description="Microtenant ID for scoping.")
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
    kwargs: str = "{}",
) -> str:
    """Bulk delete multiple ZPA Service Edges in a single API call.

    Backed by `POST /serviceEdge/bulkDelete`. Removes every specified
    edge from the ZPA cloud; each must be re-provisioned to reconnect.
    HMAC double-confirmed.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation(
        "zpa_bulk_delete_service_edges",
        confirmed,
        {"service_edge_ids": str(service_edge_ids)},
    )
    if confirmation_check:
        return confirmation_check

    if not service_edge_ids:
        raise ValueError("service_edge_ids is required and must not be empty")

    client = get_zscaler_client(service=service)
    api = client.zpa.service_edges

    _, _, err = api.bulk_delete_service_edges(service_edge_ids, microtenant_id=microtenant_id)
    if err:
        raise Exception(f"Failed to bulk delete service edges: {err}")
    return f"Successfully deleted {len(service_edge_ids)} service edges"
