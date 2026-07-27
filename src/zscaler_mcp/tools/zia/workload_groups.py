"""ZIA workload groups — list, get (read-only).

Mirrors v1's ``client.zia.workload_groups`` SDK calls. Workload groups are
referenced by policy rules; they are read-only in the MCP surface.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    page: Annotated[Optional[int], Field(default=None, description="Page number (1-based).")] = None
    page_size: Annotated[Optional[int], Field(default=None, description="Items per page.")] = None


class GetInput(BaseModel):
    group_id: Annotated[str, Field(description="Workload group ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================




# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_workload_groups",
    input_model=ListInput,
    is_list=True,
)
def zia_list_workload_groups(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA workload groups."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.page:
        qp["page"] = args.page
    if args.page_size:
        qp["page_size"] = args.page_size
    groups, _, err = client.zia.workload_groups.list_groups(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list workload groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_workload_groups",
    input_model=GetInput,
    is_list=False,
)
def zia_get_workload_group(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA workload group by ID."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.workload_groups.get_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get workload group {args.group_id}: {err}")
    return shape_one(group.as_dict())
