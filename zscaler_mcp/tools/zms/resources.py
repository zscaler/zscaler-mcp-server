"""
ZMS Resources Tools

Provides read-only tools for listing and inspecting Zscaler Microsegmentation resources
(workloads, servers, VMs, containers).
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


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
    List Zscaler Microsegmentation (ZMS) resources with pagination.

    Resources represent workloads (servers, VMs, containers) managed by
    microsegmentation agents. Returns resource type, status, cloud provider,
    region, hostname, OS, IP addresses, and app zone mappings.

    Use this tool to:
    - View all managed workloads and their protection status
    - Check resource cloud provider and region distribution
    - Identify workload OS and IP information
    - See which app zones resources are mapped to
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

    result, response, err = client.zms.resources.list_resources(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No resources found."}]
    return [result]


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
