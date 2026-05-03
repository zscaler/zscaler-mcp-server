"""
ZMS App Zones Tools

Provides read-only tools for listing Zscaler Microsegmentation app zones.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zms import apply_jmespath_query


def _build_app_zone_filter(name: Optional[str] = None):
    """Build an AppZoneFilter from simple parameters."""
    if not name:
        return None
    from zscaler.zms.models.inputs import AppZoneFilter, StringExpression

    return AppZoneFilter(app_zone_name=StringExpression(contains=name))


def _build_app_zone_order(sort_order: Optional[str] = None):
    """Build an AppZoneQueryOrderBy from a sort direction string."""
    if not sort_order:
        return None
    from zscaler.zms.models.inputs import AppZoneQueryOrderBy

    return AppZoneQueryOrderBy(app_zone_name=sort_order.upper())


def zms_list_app_zones(
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
        Field(description="Filter by app zone name (substring match)."),
    ] = None,
    sort_order: Annotated[
        Optional[str],
        Field(description="Sort order for app zone name: 'ASC' or 'DESC'."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?member_count>`0`].{name: app_zone_name}\"."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
) -> List[Dict[str, Any]]:
    """
    List Zscaler Microsegmentation (ZMS) app zones with pagination and filtering.

    App zones define logical boundaries for application communication.
    Returns zone name, description, member count, and VPC/subnet inclusion settings.
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View all configured app zones
    - Filter app zones by name
    - Understand application communication boundaries
    - Check member counts and inclusion settings per zone
    - Use JMESPath queries for advanced filtering (e.g., nodes[?member_count>`0`])
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

    filter_by = _build_app_zone_filter(name)
    if filter_by:
        kwargs["filter_by"] = filter_by

    order_by = _build_app_zone_order(sort_order)
    if order_by:
        kwargs["order_by"] = order_by

    result, response, err = client.zms.app_zones.list_app_zones(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No app zones found."}]
    return apply_jmespath_query(result, query)
