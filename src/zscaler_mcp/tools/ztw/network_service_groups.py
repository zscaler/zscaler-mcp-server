"""ZTW network service groups (read-only).

Mirrors v1's ``network_service_groups.py``. Backed by
``client.ztw.nw_service_groups`` — named collections of network services.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class ListNetworkServiceGroupsInput(BaseModel):
    """Inputs for listing ZTW network service groups."""

    search: Annotated[
        Optional[str],
        Field(default=None, description="Server-side search on group name or description."),
    ] = None


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListNetworkServiceGroupsInput,
    is_list=True,
)
def ztw_list_network_service_groups(args: ListNetworkServiceGroupsInput) -> list[dict[str, Any]]:
    """List ZTW network service groups (read-only)."""
    client = get_zscaler_client(service="ztw")
    api = client.ztw.nw_service_groups

    qp: dict[str, Any] = {"search": args.search} if args.search else {}
    groups, _, err = api.list_network_svc_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZTW network service groups: {err}")

    return shape_many([g.as_dict() for g in (groups or [])])
