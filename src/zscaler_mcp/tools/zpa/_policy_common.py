"""Shared shaping + helpers for the five ZPA policy-rule families.

The public tools live in the v1-mirrored modules ``access_policy_rules.py``,
``access_forwarding_rules.py``, ``access_timeout_rules.py``,
``access_isolation_rules.py`` and ``access_app_protection_rules.py``. This
private module holds only the pieces those five files share — the curated
output views and the list/get/delete plumbing — so the token-shaping logic
stays in one place. It registers no tools itself (same internal pattern as
ZIA's ``_rules_common.py``).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.zpa_helpers import convert_v1_to_v2_response, convert_v2_to_sdk_format
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

__all__ = [
    "ListRulesInput",
    "GetRuleInput",
    "DeleteRuleInput",
    "OperationResult",
    "list_rules",
    "get_rule",
    "delete_rule",
    "processed_conditions",
]


# =============================================================================
# SHARED INPUT FRAGMENTS
# =============================================================================


class ListRulesInput(BaseModel):
    """Inputs for listing a ZPA policy-rule family."""

    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class GetRuleInput(BaseModel):
    """Inputs for getting one ZPA policy rule."""

    rule_id: Annotated[str, Field(description="Policy rule ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteRuleInput(BaseModel):
    """Inputs for deleting a ZPA policy rule (destructive)."""

    rule_id: Annotated[str, Field(description="Policy rule ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# SHARED PLUMBING
# =============================================================================


def list_rules(policy_type: str, args: ListRulesInput) -> list[dict[str, Any]]:
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    rules, _, err = client.zpa.policies.list_rules(policy_type, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list {policy_type} policy rules: {err}")
    return shape_many([r.as_dict() for r in (rules or [])])


def get_rule(policy_type: str, args: GetRuleInput) -> dict[str, Any]:
    if not args.rule_id:
        raise ValueError("rule_id is required")
    client = get_zscaler_client(service="zpa")
    result, _, err = client.zpa.policies.get_rule(
        policy_type, args.rule_id, query_params={"microtenantId": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get {policy_type} policy rule {args.rule_id}: {err}")
    raw = result.as_dict()
    if "conditions" in raw:
        raw["conditions"] = convert_v1_to_v2_response(raw["conditions"])
    return shape_one(raw)


def delete_rule(policy_type: str, args: DeleteRuleInput, label: str) -> dict[str, Any]:
    if not args.rule_id:
        raise ValueError("rule_id is required")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.policies.delete_rule(
        policy_type, args.rule_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete {label} policy rule {args.rule_id}: {err}")
    return OperationResult(
        success=True, message=f"{label} policy rule {args.rule_id} deleted successfully."
    ).model_dump()


def processed_conditions(conditions: Any) -> list:
    try:
        return convert_v2_to_sdk_format(conditions)
    except Exception as e:
        raise ValueError(f"Invalid conditions format: {e}")
