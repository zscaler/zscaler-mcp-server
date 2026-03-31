"""
ZMS Agent Groups Tools

Provides read-only tools for listing and inspecting Zscaler Microsegmentation agent groups.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zms_list_agent_groups(
    page: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    search: Annotated[
        Optional[str],
        Field(description="Search filter string to narrow agent groups."),
    ] = None,
    sort: Annotated[
        Optional[str],
        Field(description="Sort field (e.g., 'name')."),
    ] = None,
    sort_dir: Annotated[
        Optional[str],
        Field(description="Sort direction: ASC or DESC."),
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
    List Zscaler Microsegmentation (ZMS) agent groups with pagination and search.

    Returns agent groups with their type, cloud provider, agent count,
    policy status, upgrade settings, and tamper protection status.

    Use this tool to:
    - View all configured agent groups
    - Check upgrade schedules and auto-upgrade settings
    - Monitor policy and tamper protection status per group
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "page": page,
        "page_size": page_size,
    }
    if search is not None:
        kwargs["search"] = search
    if sort is not None:
        kwargs["sort"] = sort
    if sort_dir is not None:
        kwargs["sort_dir"] = sort_dir

    result, response, err = client.zms.agent_groups.list_agent_groups(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No agent groups found."}]
    return [result]


def zms_get_agent_group_totp_secrets(
    eyez_id: Annotated[
        str,
        Field(description="The agent group eyez ID. Use zms_list_agent_groups to find eyez IDs."),
    ],
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
    Get TOTP secrets for a specific ZMS agent group.

    Returns the TOTP secret, QR code, and generation timestamp for the group.

    Use this tool to:
    - Retrieve TOTP provisioning secrets for agent enrollment
    - Get QR codes for agent group registration
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.agent_groups.get_agent_group_totp_secrets(
        customer_id=customer_id,
        eyez_id=eyez_id,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No TOTP secrets found for this agent group."}]
    return [result]
