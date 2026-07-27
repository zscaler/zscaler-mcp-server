"""ZMS resource groups — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/resource_groups.py``:

    zms_list_resource_groups, zms_get_resource_group_members,
    zms_get_resource_group_protection_status

Resource groups are managed (tag/rule membership) or unmanaged (CIDR/FQDN
membership). ``list_resource_groups`` returns a connection ``{nodes, page_info}``;
the members and protection-status tools return connections / aggregates.
Requires ZSCALER_CUSTOMER_ID.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, shape_many
from zscaler_mcp.tools.zms._common import nodes_of, require_customer_id

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListResourceGroupsInput(BaseModel):
    """Inputs for listing ZMS resource groups."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    name: Annotated[
        Optional[str], Field(default=None, description="Filter by group name (substring match).")
    ] = None
    resource_hostname: Annotated[
        Optional[str],
        Field(default=None, description="Filter by member resource hostname (substring match)."),
    ] = None


class GroupMembersInput(BaseModel):
    """Inputs for listing a resource group's members."""

    group_id: Annotated[str, Field(description="Resource group ID.")]
    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[int, Field(default=20, ge=1, le=100, description="Items per page.")] = 20


class PageInput(BaseModel):
    """Paginated inputs for the resource-group protection-status aggregate."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[int, Field(default=20, ge=1, le=100, description="Items per page.")] = 20


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class AggregateStatus(AgentView):
    """Aggregate ZMS protection-status payload — kept nested."""

    data: dict = Field(default_factory=dict, description="Aggregate payload (counts/percentages).")


def _build_groups_filter(args: ListResourceGroupsInput):
    if not any([args.name, args.resource_hostname]):
        return None
    from zscaler.zms.models.inputs import ResourceGroupsFilter, StringExpression

    return ResourceGroupsFilter(
        name=StringExpression(contains=args.name) if args.name else None,
        resource_hostname=(
            StringExpression(contains=args.resource_hostname) if args.resource_hostname else None
        ),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListResourceGroupsInput,
    is_list=True,
)
def zms_list_resource_groups(args: ListResourceGroupsInput) -> list[dict[str, Any]]:
    """List ZMS resource groups.

    Read-only. Returns one row per group (id, name, managed/unmanaged type,
    origin, member count, and CIDRs/FQDNs for unmanaged groups). Requires
    ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": args.page_num,
        "page_size": args.page_size,
    }
    filter_by = _build_groups_filter(args)
    if filter_by:
        kwargs["filter_by"] = filter_by
    result, _, err = client.zms.resource_groups.list_resource_groups(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS resource groups: {err}")
    return shape_many(nodes_of(result))


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=GroupMembersInput,
    is_list=True,
)
def zms_get_resource_group_members(args: GroupMembersInput) -> list[dict[str, Any]]:
    """List the members of a ZMS resource group.

    Read-only. Returns one row per member workload. Obtain `group_id` from
    `zms_list_resource_groups`. Requires ZSCALER_CUSTOMER_ID.
    """
    if not args.group_id:
        raise ValueError("group_id is required")
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    result, _, err = client.zms.resource_groups.get_resource_group_members(
        customer_id=customer_id,
        group_id=args.group_id,
        page_num=args.page_num,
        page_size=args.page_size,
    )
    if err:
        raise RuntimeError(f"Failed to get ZMS resource group members: {err}")
    return shape_many(nodes_of(result))


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=PageInput,
    output_view=AggregateStatus,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zms_get_resource_group_protection_status(args: PageInput) -> dict[str, Any]:
    """Get the ZMS resource-group protection-status summary (aggregate view).

    Read-only. Returns protected vs unprotected group counts and percentage.
    Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    result, _, err = client.zms.resource_groups.get_resource_group_protection_status(
        customer_id=customer_id, page_num=args.page_num, page_size=args.page_size
    )
    if err:
        raise RuntimeError(f"Failed to get ZMS resource group protection status: {err}")
    return AggregateStatus(data=result if isinstance(result, dict) else {}).model_dump()
