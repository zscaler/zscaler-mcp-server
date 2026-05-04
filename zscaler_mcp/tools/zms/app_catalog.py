"""
ZMS App Catalog Tools

Provides read-only tools for listing Zscaler Microsegmentation application catalog entries.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zms import apply_jmespath_query


def _build_app_catalog_filter(
    name: Optional[str] = None,
    category: Optional[str] = None,
):
    """Build an AppCatalogQueryFilter from simple parameters."""
    from zscaler.zms.models.inputs import AppCatalogQueryFilter, StringExpression

    if not any([name, category]):
        return None

    return AppCatalogQueryFilter(
        name=StringExpression(contains=name) if name else None,
        category=StringExpression(contains=category) if category else None,
    )


def _build_app_catalog_order(
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
):
    """Build an AppCatalogQueryOrderBy from sort parameters."""
    if not sort_by or not sort_order:
        return None
    from zscaler.zms.models.enums import SortDirection
    from zscaler.zms.models.inputs import AppCatalogQueryOrderBy

    direction = SortDirection(sort_order.upper())
    field_map = {
        "name": "name",
        "category": "category",
        "creation_time": "creation_time",
        "modified_time": "modified_time",
    }
    field = field_map.get(sort_by.lower())
    if not field:
        return None

    return AppCatalogQueryOrderBy(**{field: direction})


def zms_list_app_catalog(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    name: Annotated[
        Optional[str],
        Field(description="Filter by application name (substring match)."),
    ] = None,
    category: Annotated[
        Optional[str],
        Field(description="Filter by application category (substring match)."),
    ] = None,
    sort_by: Annotated[
        Optional[str],
        Field(description="Sort by field: 'name', 'category', 'creation_time', or 'modified_time'."),
    ] = None,
    sort_order: Annotated[
        Optional[str],
        Field(description="Sort order: 'ASC' or 'DESC'. Requires sort_by to be set."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?category=='Database'].{name: name, category: category}\"."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    List Zscaler Microsegmentation (ZMS) application catalog entries with pagination and filtering.

    The app catalog contains discovered applications with their port/protocol
    specifications and associated processes. Returns application name, category,
    creation/modification times, and detailed port/protocol/process info.
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View all discovered applications in the microsegmentation environment
    - Filter applications by name or category
    - Sort by name, category, creation time, or modification time
    - Check port and protocol requirements for each application
    - See which processes are associated with each application
    - Understand the application landscape for policy planning
    - Use JMESPath queries for advanced filtering (e.g., nodes[?category=='Database'])
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": page_num,
        "page_size": page_size,
    }

    filter_by = _build_app_catalog_filter(name, category)
    if filter_by:
        kwargs["filter_by"] = filter_by

    order_by = _build_app_catalog_order(sort_by, sort_order)
    if order_by:
        kwargs["order_by"] = order_by

    result, response, err = client.zms.app_catalog.list_app_catalog(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No app catalog entries found."}]
    return apply_jmespath_query(result, query)
