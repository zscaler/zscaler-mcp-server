"""ZMS resources — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/resources.py``:

    zms_list_resources, zms_get_resource_protection_status, zms_get_metadata

Resources are the workloads (VMs, containers, bare metal) managed by ZMS agents.
``list_resources`` returns a connection ``{nodes, page_info}`` and accepts a
GraphQL filter/order built from the SDK input models. The protection-status and
metadata tools return aggregate dicts. Requires ZSCALER_CUSTOMER_ID.
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


class ListResourcesInput(BaseModel):
    """Inputs for listing ZMS resources (workloads)."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    include_deleted: Annotated[
        bool, Field(default=False, description="Include deleted resources.")
    ] = False
    name: Annotated[
        Optional[str], Field(default=None, description="Filter by name (substring match).")
    ] = None
    status: Annotated[
        Optional[str], Field(default=None, description="Filter by status (exact match).")
    ] = None
    resource_type: Annotated[
        Optional[str],
        Field(default=None, description="Filter by type (VIRTUAL_MACHINE, CONTAINER, BARE_METAL)."),
    ] = None
    cloud_provider: Annotated[
        Optional[str],
        Field(default=None, description="Filter by cloud provider (AWS, AZURE, GCP, ON_PREMISES)."),
    ] = None
    cloud_region: Annotated[
        Optional[str], Field(default=None, description="Filter by cloud region (substring match).")
    ] = None
    platform_os: Annotated[
        Optional[str], Field(default=None, description="Filter by platform OS (LINUX, WINDOWS).")
    ] = None
    sort_order: Annotated[
        Optional[str], Field(default=None, description="Sort by name: ASC or DESC.")
    ] = None


class PageInput(BaseModel):
    """Paginated inputs for the resource aggregate endpoints."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[int, Field(default=20, ge=1, le=100, description="Items per page.")] = 20


class MetadataInput(BaseModel):
    """No-arg inputs for resource event metadata."""


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class AggregateStatus(AgentView):
    """Aggregate ZMS status/metadata payload — kept nested."""

    data: dict = Field(default_factory=dict, description="Aggregate payload (counts/percentages).")


def _build_resource_filter(args: ListResourcesInput):
    """Build a ResourceQueryFilter from the input model (SDK input models)."""
    if not any(
        [
            args.name,
            args.status,
            args.resource_type,
            args.cloud_provider,
            args.cloud_region,
            args.platform_os,
        ]
    ):
        return None
    from zscaler.zms.models.inputs import ResourceQueryFilter, StringExpression

    return ResourceQueryFilter(
        name=StringExpression(contains=args.name) if args.name else None,
        status=StringExpression(equals=args.status) if args.status else None,
        resource_type=StringExpression(equals=args.resource_type) if args.resource_type else None,
        cloud_provider=StringExpression(equals=args.cloud_provider)
        if args.cloud_provider
        else None,
        cloud_region=StringExpression(contains=args.cloud_region) if args.cloud_region else None,
        platform_os=StringExpression(contains=args.platform_os) if args.platform_os else None,
    )


def _build_resource_order(sort_order: Optional[str]):
    if not sort_order:
        return None
    from zscaler.zms.models.enums import SortDirection
    from zscaler.zms.models.inputs import ResourceQueryOrderBy

    return ResourceQueryOrderBy(name=SortDirection(sort_order.upper()))


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListResourcesInput,
    is_list=True,
)
def zms_list_resources(args: ListResourcesInput) -> list[dict[str, Any]]:
    """List ZMS resources (workloads).

    Read-only. Returns one row per workload (id, name, type, status, cloud
    provider/region, OS, IPs). Filter by name/status/type/provider/region/OS.
    Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": args.page_num,
        "page_size": args.page_size,
        "include_deleted": args.include_deleted,
    }
    filter_by = _build_resource_filter(args)
    if filter_by:
        kwargs["filter_by"] = filter_by
    order_by = _build_resource_order(args.sort_order)
    if order_by:
        kwargs["order_by"] = order_by

    result, _, err = client.zms.resources.list_resources(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS resources: {err}")
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
def zms_get_resource_protection_status(args: PageInput) -> dict[str, Any]:
    """Get the ZMS resource protection-status summary (curated aggregate view).

    Read-only. Returns protected vs unprotected counts and protection
    percentage — microsegmentation coverage at a glance. Requires
    ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    result, _, err = client.zms.resources.get_resource_protection_status(
        customer_id=customer_id, page_num=args.page_num, page_size=args.page_size
    )
    if err:
        raise RuntimeError(f"Failed to get ZMS resource protection status: {err}")
    return AggregateStatus(data=result if isinstance(result, dict) else {}).model_dump()


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=MetadataInput,
    output_view=AggregateStatus,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zms_get_metadata(args: MetadataInput) -> dict[str, Any]:
    """Get ZMS resource event metadata (full record).

    Read-only. Returns metadata about the resource-level events available in the
    deployment. Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    result, _, err = client.zms.resources.get_metadata(customer_id=customer_id)
    if err:
        raise RuntimeError(f"Failed to get ZMS metadata: {err}")
    return AggregateStatus(data=result if isinstance(result, dict) else {}).model_dump()
