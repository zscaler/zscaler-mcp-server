"""ZTW network service groups (read-only).

Mirrors v1's ``network_service_groups.py``. Backed by
``client.ztw.nw_service_groups`` — named collections of network services.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many


class ListNetworkServiceGroupsInput(BaseModel):
    """Inputs for listing ZTW network service groups."""

    search: Annotated[
        Optional[str],
        Field(default=None, description="Server-side search on group name or description."),
    ] = None


class NetworkServiceGroupSummary(AgentView):
    """Lean view of a ZTW network service group."""

    id: str = Field(description="Network service group ID.")
    name: str = Field(description="Group name.")
    description: Optional[str] = Field(default=None, description="Description.")
    service_count: int = Field(description="Number of member network services.")


def shape_group(raw: dict[str, Any]) -> NetworkServiceGroupSummary:
    return NetworkServiceGroupSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        description=pick(raw, "description"),
        service_count=len(coalesce(raw, "services", "nw_services", "nwServices")),
    )


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListNetworkServiceGroupsInput,
    output_view=NetworkServiceGroupSummary,
    is_list=True,
)
def ztw_list_network_service_groups(args: ListNetworkServiceGroupsInput) -> list[dict[str, Any]]:
    """List ZTW network service groups as curated, agent-facing summaries (read-only)."""
    client = get_zscaler_client(service="ztw")
    api = client.ztw.nw_service_groups

    qp: dict[str, Any] = {"search": args.search} if args.search else {}
    groups, _, err = api.list_network_svc_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZTW network service groups: {err}")

    return shape_many([g.as_dict() for g in (groups or [])], shape_group)
