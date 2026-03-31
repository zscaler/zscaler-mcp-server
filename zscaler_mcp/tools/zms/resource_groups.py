"""
ZMS Resource Groups Tools

Provides read-only tools for listing and inspecting Zscaler Microsegmentation
resource groups and their members.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zms_list_resource_groups(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
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
    List Zscaler Microsegmentation (ZMS) resource groups with pagination.

    Resource groups are logical groupings of workloads. They can be managed
    (membership defined by tags/rules) or unmanaged (membership defined by
    CIDRs/FQDNs). Returns group name, type, origin, member count, and
    for unmanaged groups: CIDRs and FQDNs.

    Use this tool to:
    - View all resource groups in the microsegmentation deployment
    - Understand how workloads are grouped
    - Check managed vs unmanaged group types
    - See group member counts
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.resource_groups.list_resource_groups(
        customer_id=customer_id,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No resource groups found."}]
    return [result]


def zms_get_resource_group_members(
    group_id: Annotated[
        str,
        Field(description="The resource group ID. Use zms_list_resource_groups to find group IDs."),
    ],
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
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
    Get members of a specific ZMS resource group.

    Returns resources (workloads) that belong to the specified group,
    including resource type, status, cloud provider, region, hostname, and OS.

    Use this tool to:
    - View which workloads are in a specific group
    - Inspect the cloud distribution of a resource group
    - Verify expected workloads are grouped correctly
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.resource_groups.get_resource_group_members(
        customer_id=customer_id,
        group_id=group_id,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No members found for this resource group."}]
    return [result]


def zms_get_resource_group_protection_status(
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
    Get protection status summary for ZMS resource groups.

    Returns protected vs unprotected group counts and coverage percentage.

    Use this tool to:
    - Get a high-level view of resource group protection coverage
    - Track which resource groups have microsegmentation policies applied
    - Identify unprotected groups that need attention
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.resource_groups.get_resource_group_protection_status(
        customer_id=customer_id,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No resource group protection status data found."}]
    return [result]
