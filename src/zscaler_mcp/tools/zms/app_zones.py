"""ZMS app zones — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/app_zones.py`` (zms_list_app_zones).

Returns a connection ``{nodes, page_info}``. Requires ZSCALER_CUSTOMER_ID.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zms._common import nodes_of, require_customer_id

# =============================================================================
# INPUT MODEL
# =============================================================================


class ListAppZonesInput(BaseModel):
    """Inputs for listing ZMS app zones."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    name: Annotated[
        Optional[str], Field(default=None, description="Filter by app-zone name (substring match).")
    ] = None
    sort_order: Annotated[
        Optional[str], Field(default=None, description="Sort by name: ASC or DESC.")
    ] = None


# =============================================================================
# OUTPUT VIEW
# =============================================================================


def _build_zone_order(sort_order: Optional[str]):
    if not sort_order:
        return None
    from zscaler.zms.models.inputs import AppZoneQueryOrderBy

    return AppZoneQueryOrderBy(app_zone_name=sort_order.upper())


def _build_zone_filter(name: Optional[str]):
    if not name:
        return None
    from zscaler.zms.models.inputs import AppZoneFilter, StringExpression

    return AppZoneFilter(app_zone_name=StringExpression(contains=name))


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListAppZonesInput,
    is_list=True,
)
def zms_list_app_zones(args: ListAppZonesInput) -> list[dict[str, Any]]:
    """List ZMS app zones.

    Read-only. Returns one row per app zone (id, name, description, resource
    count). Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": args.page_num,
        "page_size": args.page_size,
    }
    filter_by = _build_zone_filter(args.name)
    if filter_by:
        kwargs["filter_by"] = filter_by
    order_by = _build_zone_order(args.sort_order)
    if order_by:
        kwargs["order_by"] = order_by
    result, _, err = client.zms.app_zones.list_app_zones(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS app zones: {err}")
    return shape_many(nodes_of(result))
