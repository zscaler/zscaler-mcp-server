"""
ZMS Policy Rules Tools

Provides read-only tools for listing Zscaler Microsegmentation policy rules.
"""

import os
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.tools.zms import apply_jmespath_query


def _build_policy_rule_filter(
    name: Optional[str] = None,
    action: Optional[str] = None,
):
    """Build a PolicyRuleFilter from simple parameters."""
    from zscaler.zms.models.inputs import PolicyRuleFilter, StringExpression

    if not any([name, action]):
        return None

    return PolicyRuleFilter(
        name=StringExpression(contains=name) if name else None,
        action=StringExpression(equals=action) if action else None,
    )


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
    name: Annotated[
        Optional[str],
        Field(description="Filter by policy rule name (substring match)."),
    ] = None,
    action: Annotated[
        Optional[str],
        Field(description="Filter by policy action: 'ALLOW' or 'BLOCK' (exact match)."),
    ] = None,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?action=='ALLOW'].{name: name, priority: priority}\"."),
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
    List Zscaler Microsegmentation (ZMS) policy rules with pagination and filtering.

    Policy rules define allowed/blocked communication between resource groups.
    Returns rule name, action, priority, source/destination target types,
    port/protocol specifications, creation time, and last hit time.
    Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View all microsegmentation policy rules
    - Filter rules by name or action (ALLOW/BLOCK)
    - Understand allowed communication paths between workloads
    - Check rule priorities and ordering
    - See port and protocol restrictions
    - Identify recently matched rules via lastHit timestamp
    - Use JMESPath queries for advanced filtering (e.g., nodes[?action=='ALLOW'])
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

    filter_by = _build_policy_rule_filter(name, action)
    if filter_by:
        kwargs["filter_by"] = filter_by

    result, response, err = client.zms.policy_rules.list_policy_rules(**kwargs)

    if err:
        return [{"error": f"SDK error: {err}"}]
    if not result:
        return [{"status": "no_data", "message": "No policy rules found."}]
    return apply_jmespath_query(result, query)


def zms_list_default_policy_rules(
    page_num: Annotated[
        int,
        Field(description="Page number (default 1)."),
    ] = 1,
    page_size: Annotated[
        int,
        Field(description="Number of items per page (default 20)."),
    ] = 20,
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection on the result. Example: \"nodes[?action=='BLOCK']\"."),
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
    List default policy rules for Zscaler Microsegmentation (ZMS).

    Default rules are system-defined baseline rules that apply when no
    custom policy matches. Returns rule name, action, direction, scope type,
    and description. Supports JMESPath client-side filtering via the query parameter.

    Use this tool to:
    - View the baseline microsegmentation policies
    - Understand the default allow/deny posture
    - Check the direction (inbound/outbound) of default rules
    - Use JMESPath queries for advanced filtering (e.g., nodes[?action=='BLOCK'])
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
    return apply_jmespath_query(result, query)
