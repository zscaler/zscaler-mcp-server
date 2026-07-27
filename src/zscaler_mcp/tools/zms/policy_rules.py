"""ZMS policy rules — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zms/policy_rules.py``:

    zms_list_policy_rules, zms_list_default_policy_rules

Both return a connection ``{nodes, page_info}``. ``fetch_all=True`` bypasses
pagination on the custom-rule list (use sparingly on large tenants). Requires
ZSCALER_CUSTOMER_ID.
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


class ListPolicyRulesInput(BaseModel):
    """Inputs for listing ZMS policy rules."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[
        int, Field(default=20, ge=1, le=100, description="Items per page (default 20, max 100).")
    ] = 20
    fetch_all: Annotated[
        bool,
        Field(default=False, description="Bypass pagination and fetch all rules (use sparingly)."),
    ] = False
    name: Annotated[
        Optional[str], Field(default=None, description="Filter by rule name (substring match).")
    ] = None
    action: Annotated[
        Optional[str], Field(default=None, description="Filter by action: ALLOW or BLOCK.")
    ] = None


class ListDefaultPolicyRulesInput(BaseModel):
    """Inputs for listing ZMS default policy rules."""

    page_num: Annotated[int, Field(default=1, ge=1, description="Page number.")] = 1
    page_size: Annotated[int, Field(default=20, ge=1, le=100, description="Items per page.")] = 20


# =============================================================================
# OUTPUT VIEW
# =============================================================================


def _build_rule_filter(args: ListPolicyRulesInput):
    if not any([args.name, args.action]):
        return None
    from zscaler.zms.models.inputs import PolicyRuleFilter, StringExpression

    return PolicyRuleFilter(
        name=StringExpression(contains=args.name) if args.name else None,
        action=StringExpression(equals=args.action) if args.action else None,
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListPolicyRulesInput,
    is_list=True,
)
def zms_list_policy_rules(args: ListPolicyRulesInput) -> list[dict[str, Any]]:
    """List ZMS microsegmentation policy rules.

    Read-only. Returns one row per rule (id, name, action, priority, enabled).
    Filter by name/action. `fetch_all` bypasses pagination — use sparingly.
    Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    kwargs: dict[str, Any] = {
        "customer_id": customer_id,
        "page_num": args.page_num,
        "page_size": args.page_size,
        "fetch_all": args.fetch_all,
    }
    filter_by = _build_rule_filter(args)
    if filter_by:
        kwargs["filter_by"] = filter_by
    result, _, err = client.zms.policy_rules.list_policy_rules(**kwargs)
    if err:
        raise RuntimeError(f"Failed to list ZMS policy rules: {err}")
    return shape_many(nodes_of(result))


@tool(
    action=READ,
    service="zms",
    toolset="zms",
    input_model=ListDefaultPolicyRulesInput,
    is_list=True,
)
def zms_list_default_policy_rules(args: ListDefaultPolicyRulesInput) -> list[dict[str, Any]]:
    """List ZMS default policy rules.

    Read-only. The built-in default rules evaluated when no custom rule matches.
    Requires ZSCALER_CUSTOMER_ID.
    """
    customer_id = require_customer_id()
    client = get_zscaler_client(service="zms")
    result, _, err = client.zms.policy_rules.list_default_policy_rules(
        customer_id=customer_id, page_num=args.page_num, page_size=args.page_size
    )
    if err:
        raise RuntimeError(f"Failed to list ZMS default policy rules: {err}")
    return shape_many(nodes_of(result))
