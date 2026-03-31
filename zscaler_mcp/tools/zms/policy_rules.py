"""
ZMS Policy Rules Tools

Provides read-only tools for listing Zscaler Microsegmentation policy rules.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client


def zms_list_policy_rules(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20, max 100)."),
    ] = 20,
    fetch_all: Annotated[
        bool,
        Field(description="Whether to fetch all rules ignoring pagination (default false)."),
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
    List Zscaler Microsegmentation (ZMS) policy rules with pagination.

    Policy rules define allowed/blocked communication between resource groups.
    Returns rule name, action, priority, source/destination target types,
    port/protocol specifications, creation time, and last hit time.

    Use this tool to:
    - View all microsegmentation policy rules
    - Understand allowed communication paths between workloads
    - Check rule priorities and ordering
    - See port and protocol restrictions
    - Identify recently matched rules via lastHit timestamp
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    kwargs: Dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": page_num,
        "page_size": page_size,
        "fetch_all": fetch_all,
    }

    result, response, err = client.zms.policy_rules.list_policy_rules(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No policy rules found."}]
    return [result]


def zms_list_default_policy_rules(
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
    List default policy rules for Zscaler Microsegmentation (ZMS).

    Default rules are system-defined baseline rules that apply when no
    custom policy matches. Returns rule name, action, direction, scope type,
    and description.

    Use this tool to:
    - View the baseline microsegmentation policies
    - Understand the default allow/deny posture
    - Check the direction (inbound/outbound) of default rules
    """
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        return [{"error": "ZSCALER_CUSTOMER_ID environment variable is required for ZMS tools."}]

    client = get_zscaler_client(use_legacy=use_legacy, service="zms")

    result, response, err = client.zms.policy_rules.list_default_policy_rules(
        customer_id=customer_id,
        page_num=page_num,
        page_size=page_size,
    )

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No default policy rules found."}]
    return [result]
