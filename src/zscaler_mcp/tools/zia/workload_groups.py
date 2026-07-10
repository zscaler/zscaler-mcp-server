"""ZIA workload groups — list, get (read-only).

Mirrors v1's ``client.zia.workload_groups`` SDK calls. Workload groups are
referenced by policy rules; they are read-only in the MCP surface.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

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


class WorkloadGroupSummary(AgentView):
    id: str = Field(description="Workload group ID. Use in policy-rule payloads.")
    name: str = Field(description="Display name.")
    description: Optional[str] = Field(default=None, description="Admin description.")
    expression_count: int = Field(description="Number of tag/match expressions in the group.")


class WorkloadGroupDetail(WorkloadGroupSummary):
    expression: Optional[str] = Field(default=None, description="Raw expression string, if any.")


# =============================================================================
# SHAPERS
# =============================================================================


def _expr_count(raw: dict[str, Any]) -> int:
    exprs = coalesce(raw, "expressions", "expression_containers", "expressionContainers")
    return len(exprs)


def shape_summary(raw: dict[str, Any]) -> WorkloadGroupSummary:
    return WorkloadGroupSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        description=pick(raw, "description"),
        expression_count=_expr_count(raw),
    )


def shape_detail(raw: dict[str, Any]) -> WorkloadGroupDetail:
    return WorkloadGroupDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        description=pick(raw, "description"),
        expression_count=_expr_count(raw),
        expression=pick(raw, "expression"),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_workload_groups",
    input_model=ListInput,
    output_view=WorkloadGroupSummary,
    is_list=True,
)
def zia_list_workload_groups(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA workload groups as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.page:
        qp["page"] = args.page
    if args.page_size:
        qp["page_size"] = args.page_size
    groups, _, err = client.zia.workload_groups.list_groups(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list workload groups: {err}")
    return shape_many([g.as_dict() for g in (groups or [])], shape_summary)


@tool(
    action=READ,
    service="zia",
    toolset="zia_workload_groups",
    input_model=GetInput,
    output_view=WorkloadGroupDetail,
    is_list=False,
)
def zia_get_workload_group(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA workload group by ID."""
    client = get_zscaler_client(service="zia")
    group, _, err = client.zia.workload_groups.get_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to get workload group {args.group_id}: {err}")
    return shape_detail(group.as_dict()).model_dump()
