"""
ZMS Resources Tools

Provides read-only tools for listing and inspecting Zscaler Microsegmentation resources
(workloads, servers, VMs, containers).
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zms import apply_jmespath_query


def _build_resource_filter(
    name: Optional[str] = None,
    status: Optional[str] = None,
    resource_type: Optional[str] = None,
    cloud_provider: Optional[str] = None,
    cloud_region: Optional[str] = None,
    platform_os: Optional[str] = None,
):
    """Build a ResourceQueryFilter from simple parameters."""
    from zscaler.zms.models.inputs import ResourceQueryFilter, StringExpression

    has_filter = any([name, status, resource_type, cloud_provider, cloud_region, platform_os])
    if not has_filter:
        return None

    return ResourceQueryFilter(
        name=StringExpression(contains=name) if name else None,
        status=StringExpression(equals=status) if status else None,
        resource_type=StringExpression(equals=resource_type) if resource_type else None,
        cloud_provider=StringExpression(equals=cloud_provider) if cloud_provider else None,
        cloud_region=StringExpression(contains=cloud_region) if cloud_region else None,
        platform_os=StringExpression(contains=platform_os) if platform_os else None,
    )


def _build_resource_order(sort_order: Optional[str] = None):
    """Build a ResourceQueryOrderBy from a sort direction string."""
    if not sort_order:
        return None
    from zscaler.zms.models.enums import SortDirection
    from zscaler.zms.models.inputs import ResourceQueryOrderBy

    return ResourceQueryOrderBy(name=SortDirection(sort_order.upper()))


def zms_list_resources(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    include_deleted: Annotated[
        bool,
        Field(description="Whether to include deleted resources (default false)."),
    ] = False,
    name: Annotated[
        Optional[str],
        Field(description="Filter by resource name (substring match)."),
    ] = None,
    status: Annotated[
        Optional[str],
        Field(description="Filter by resource status (exact match)."),
    ] = None,
    resource_type: Annotated[
        Optional[str],
        Field(description="Filter by resource type, e.g. 'VIRTUAL_MACHINE', 'CONTAINER', 'BARE_METAL' (exact match)."),
    ] = None,
    cloud_provider: Annotated[
        Optional[str],
        Field(description="Filter by cloud provider, e.g. 'AWS', 'AZURE', 'GCP', 'ON_PREMISES' (exact match)."),
    ] = None,
    cloud_region: Annotated[
        Optional[str],
        Field(description="Filter by cloud region (substring match)."),
    ] = None,
    platform_os: Annotated[
        Optional[str],
        Field(description="Filter by platform OS, e.g. 'LINUX', 'WINDOWS' (substring match)."),
    ] = None,
    sort_order: Annotated[
        Optional[str],
        Field(description="Sort order for resource name: 'ASC' or 'DESC'."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?cloud_provider=='AWS']\"."),
    ] = None,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
    use_legacy: Annotated[
        Optional[bool],
        Field(description="Whether to use the legacy API."),
    ] = False,
) -> List[Dict[str, Any]]:
    """
    List Zscaler Microsegmentation (ZMS) resources with pagination and filtering.

    Resources represent workloads (servers, VMs, containers) managed by
    microsegmentation agents. Returns resource type, status, cloud provider,
    region, hostname, OS, IP addresses, and app zone mappings.
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View all managed workloads and their protection status
    - Filter resources by cloud provider, region, type, OS, or status
    - Check resource cloud provider and region distribution
    - Identify workload OS and IP information
    - See which app zones resources are mapped to
    - Use JMESPath queries for advanced filtering (e.g., nodes[?cloud_provider=='AWS'])
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": page_num,
        "page_size": page_size,
        "include_deleted": include_deleted,
    }

    filter_by = _build_resource_filter(name, status, resource_type, cloud_provider, cloud_region, platform_os)
    if filter_by:
        kwargs["filter_by"] = filter_by

    order_by = _build_resource_order(sort_order)
    if order_by:
        kwargs["order_by"] = order_by

    result, response, err = client.zms.resources.list_resources(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No resources found."}]
    return apply_jmespath_query(result, query)


def zms_get_resource_protection_status(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20)."),
    ] = 20,
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
    use_legacy: Annotated[
        Optional[bool],
        Field(description="Whether to use the legacy API."),
    ] = False,
) -> List[Dict[str, Any]]:
    """
    Get protection status summary for ZMS resources.

    Returns protected vs unprotected resource counts and protection percentage.

    Use this tool to:
    - Get a high-level view of microsegmentation coverage
    - Track what percentage of workloads are protected
    - Identify unprotected resources that need attention
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.resources.get_resource_protection_status(
        customer_id=customer_id,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No resource protection status data found."}]
    return [result]


def zms_get_metadata(
    service: Annotated[
        Optional[str],
        Field(description="The service to use."),
    ] = None,
    use_legacy: Annotated[
        Optional[bool],
        Field(description="Whether to use the legacy API."),
    ] = False,
) -> List[Dict[str, Any]]:
    """
    Get event metadata for ZMS resources.

    Returns metadata about resource events for the customer.

    Use this tool to:
    - Retrieve metadata about resource-level events
    - Understand what event types are available in your ZMS deployment
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.resources.get_metadata(
        customer_id=customer_id,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No metadata found."}]
    return [result]
