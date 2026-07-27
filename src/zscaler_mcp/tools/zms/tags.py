"""ZMS tags — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/tags.py``:

    zms_list_tag_namespaces, zms_list_tag_keys, zms_list_tag_values

The tag hierarchy is three levels: namespace -> key -> value. To list values you
need the tag key id (`tag_id`) plus the `namespace_origin`. All return
connections ``{nodes, page_info}``. Requires ZSCALER_CUSTOMER_ID.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zms._common import nodes_of, require_customer_id

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListTagNamespacesInput(BaseModel):
    """Inputs for listing ZMS tag namespaces."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    name: Annotated[
        Optional[str], Field(default=None, description="Filter by name (substring match).")
    ] = None
    origin: Annotated[
        Optional[str],
        Field(default=None, description="Filter by origin: CUSTOM, EXTERNAL, ML, UNKNOWN (exact)."),
    ] = None
    sort_order: Annotated[
        Optional[str], Field(default=None, description="Sort by name: ASC or DESC.")
    ] = None


class ListTagKeysInput(BaseModel):
    """Inputs for listing ZMS tag keys within a namespace."""

    namespace_id: Annotated[str, Field(description="Tag namespace ID (from list_tag_namespaces).")]
    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[int, Field(default=20, ge=1, le=100, description="Items per page.")] = 20
    key_name: Annotated[
        Optional[str], Field(default=None, description="Filter by key name (substring match).")
    ] = None
    sort_order: Annotated[
        Optional[str], Field(default=None, description="Sort by name: ASC or DESC.")
    ] = None


class ListTagValuesInput(BaseModel):
    """Inputs for listing ZMS tag values for a key."""

    tag_id: Annotated[str, Field(description="Tag key ID (from list_tag_keys).")]
    namespace_origin: Annotated[
        str, Field(description="Namespace origin: CUSTOM, EXTERNAL, ML, or UNKNOWN.")
    ]
    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[int, Field(default=20, ge=1, le=100, description="Items per page.")] = 20
    name: Annotated[
        Optional[str], Field(default=None, description="Filter by value name (substring match).")
    ] = None
    sort_order: Annotated[
        Optional[str], Field(default=None, description="Sort by name: ASC or DESC.")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


def _sort_direction(sort_order: Optional[str]):
    if not sort_order:
        return None
    from zscaler.zms.models.enums import SortDirection

    return SortDirection(sort_order.upper())


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListTagNamespacesInput,
    is_list=True,
)
def zms_list_tag_namespaces(args: ListTagNamespacesInput) -> list[dict[str, Any]]:
    """List ZMS tag namespaces.

    Read-only. Top of the tag hierarchy (namespace -> key -> value). Returns one
    row per namespace (id, name, origin, key count). Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": args.page_num,
        "page_size": args.page_size,
    }
    if args.name or args.origin:
        from zscaler.zms.models.inputs import NamespaceFilter, StringExpression

        kwargs["filter_by"] = NamespaceFilter(
            name=StringExpression(contains=args.name) if args.name else None,
            origin=StringExpression(equals=args.origin) if args.origin else None,
        )
    direction = _sort_direction(args.sort_order)
    if direction:
        from zscaler.zms.models.inputs import NamespaceQueryOrderBy

        kwargs["order_by"] = NamespaceQueryOrderBy(name=direction)
    result, _, err = client.zms.tags.list_tag_namespaces(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS tag namespaces: {err}")
    return shape_many(nodes_of(result))


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListTagKeysInput,
    is_list=True,
)
def zms_list_tag_keys(args: ListTagKeysInput) -> list[dict[str, Any]]:
    """List ZMS tag keys within a namespace.

    Read-only. Middle of the tag hierarchy. Returns one row per key (id,
    key_name, value count). Obtain `namespace_id` from `zms_list_tag_namespaces`.
    Requires ZSCALER_CUSTOMER_ID.
    """
    if not args.namespace_id:
        raise ValueError("namespace_id is required")
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "namespace_id": args.namespace_id,
        "page_num": args.page_num,
        "page_size": args.page_size,
    }
    if args.key_name:
        from zscaler.zms.models.inputs import StringExpression, TagKeyFilter

        kwargs["filter_by"] = TagKeyFilter(key_name=StringExpression(contains=args.key_name))
    direction = _sort_direction(args.sort_order)
    if direction:
        from zscaler.zms.models.inputs import TagKeyQueryOrderBy

        kwargs["order_by"] = TagKeyQueryOrderBy(name=direction)
    result, _, err = client.zms.tags.list_tag_keys(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS tag keys: {err}")
    return shape_many(nodes_of(result))


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListTagValuesInput,
    is_list=True,
)
def zms_list_tag_values(args: ListTagValuesInput) -> list[dict[str, Any]]:
    """List ZMS tag values for a key.

    Read-only. Bottom of the tag hierarchy. Returns one row per value (id, name).
    Needs the `tag_id` (from `zms_list_tag_keys`) and the `namespace_origin`
    (CUSTOM / EXTERNAL / ML / UNKNOWN). Requires ZSCALER_CUSTOMER_ID.
    """
    if not args.tag_id:
        raise ValueError("tag_id is required")
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "tag_id": args.tag_id,
        "namespace_origin": args.namespace_origin,
        "page_num": args.page_num,
        "page_size": args.page_size,
    }
    if args.name:
        from zscaler.zms.models.inputs import StringExpression, TagValueFilter

        kwargs["filter_by"] = TagValueFilter(name=StringExpression(contains=args.name))
    direction = _sort_direction(args.sort_order)
    if direction:
        from zscaler.zms.models.inputs import TagValueQueryOrderBy

        kwargs["order_by"] = TagValueQueryOrderBy(name=direction)
    result, _, err = client.zms.tags.list_tag_values(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS tag values: {err}")
    return shape_many(nodes_of(result))
