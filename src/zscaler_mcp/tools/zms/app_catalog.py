"""ZMS app catalog — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/app_catalog.py`` (zms_list_app_catalog).

The catalog holds discovered applications with their port/protocol specs and
associated processes. Returns a connection ``{nodes, page_info}``. The
port/protocol/process detail is nested, so the view keeps the identity fields
flat and carries the nested specs under `ports`. Requires ZSCALER_CUSTOMER_ID.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zms._common import nodes_of, require_customer_id

# =============================================================================
# INPUT MODEL
# =============================================================================


class ListAppCatalogInput(BaseModel):
    """Inputs for listing the ZMS application catalog."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    name: Annotated[
        Optional[str], Field(default=None, description="Filter by application name (substring).")
    ] = None
    category: Annotated[
        Optional[str], Field(default=None, description="Filter by category (substring match).")
    ] = None
    sort_by: Annotated[
        Optional[str],
        Field(
            default=None, description="Sort field: name, category, creation_time, modified_time."
        ),
    ] = None
    sort_order: Annotated[
        Optional[str], Field(default=None, description="Sort order: ASC or DESC (needs sort_by).")
    ] = None


# =============================================================================
# OUTPUT VIEW
# =============================================================================


def _build_filter(name: Optional[str], category: Optional[str]):
    if not any([name, category]):
        return None
    from zscaler.zms.models.inputs import AppCatalogFilter, StringExpression

    return AppCatalogFilter(
        name=StringExpression(contains=name) if name else None,
        category=StringExpression(contains=category) if category else None,
    )


def _build_order(sort_by: Optional[str], sort_order: Optional[str]):
    if not sort_by or not sort_order:
        return None
    from zscaler.zms.models.enums import SortDirection
    from zscaler.zms.models.inputs import AppCatalogQueryOrderBy

    direction = SortDirection(sort_order.upper())
    return AppCatalogQueryOrderBy(**{sort_by: direction})


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListAppCatalogInput,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zms_list_app_catalog(args: ListAppCatalogInput) -> list[dict[str, Any]]:
    """List the ZMS application catalog.

    Read-only. Returns one row per discovered application (id, name, category)
    plus its nested port/protocol/process specs — useful for policy planning.
    Filter by name/category, sort by name/category/time. Requires
    ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": args.page_num,
        "page_size": args.page_size,
    }
    filter_by = _build_filter(args.name, args.category)
    if filter_by:
        kwargs["filter_by"] = filter_by
    order_by = _build_order(args.sort_by, args.sort_order)
    if order_by:
        kwargs["order_by"] = order_by
    result, _, err = client.zms.app_catalog.list_app_catalog(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS app catalog: {err}")
    return shape_many(nodes_of(result))
