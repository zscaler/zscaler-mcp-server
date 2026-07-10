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
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many

__all__ = [
    "ListRulesInput",
    "GetRuleInput",
    "DeleteRuleInput",
    "PolicyRuleSummary",
    "PolicyRuleDetail",
    "OperationResult",
    "shape_summary",
    "shape_detail",
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

    detail: Annotated[
        str, Field(default="summary", pattern="^(summary|full)$", description="Response verbosity.")
    ] = "summary"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class GetRuleInput(BaseModel):
    """Inputs for getting one ZPA policy rule."""

    rule_id: Annotated[str, Field(description="Policy rule ID (string, even if numeric).")]
    detail: Annotated[
        str, Field(default="full", pattern="^(summary|full)$", description="Response verbosity.")
    ] = "full"
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


class PolicyRuleSummary(AgentView):
    """Lean view — identify and reason about a policy rule."""

    id: str = Field(description="Policy rule ID. Use this in follow-up calls.")
    name: str = Field(description="Display name.")
    action: Optional[str] = Field(default=None, description="Rule action (decision-bearing).")
    rule_order: Optional[str] = Field(default=None, description="Evaluation order (top-to-bottom).")
    description: Optional[str] = Field(default=None, description="Admin description.")
    condition_count: int = Field(description="Number of condition blocks (complexity signal).")


class PolicyRuleDetail(PolicyRuleSummary):
    """Full view — summary plus the v2-shaped conditions + provenance."""

    conditions: list[dict] = Field(
        default_factory=list, description="Conditions in v2 (operator/operands) shape."
    )
    microtenant_id: Optional[str] = Field(default=None, description="Owning microtenant, if any.")
    created_time: Optional[str] = Field(default=None, description="Creation timestamp.")
    modified_time: Optional[str] = Field(default=None, description="Last-modified timestamp.")


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _conditions(raw: dict[str, Any]) -> list[dict]:
    conds = coalesce(raw, "conditions")
    return [c for c in conds if isinstance(c, dict)]


def shape_summary(raw: dict[str, Any]) -> PolicyRuleSummary:
    return PolicyRuleSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        action=pick(raw, "action", "action_type", "actionType"),
        rule_order=_opt_str(pick(raw, "rule_order", "ruleOrder", "order")),
        description=pick(raw, "description"),
        condition_count=len(_conditions(raw)),
    )


def shape_detail(raw: dict[str, Any]) -> PolicyRuleDetail:
    conds = _conditions(raw)
    return PolicyRuleDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        action=pick(raw, "action", "action_type", "actionType"),
        rule_order=_opt_str(pick(raw, "rule_order", "ruleOrder", "order")),
        description=pick(raw, "description"),
        condition_count=len(conds),
        conditions=conds,
        microtenant_id=pick(raw, "microtenant_id", "microtenantId"),
        created_time=pick(raw, "creation_time", "creationTime"),
        modified_time=pick(raw, "modified_time", "modifiedTime"),
    )


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
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shape_many([r.as_dict() for r in (rules or [])], shaper)


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
    shaper = shape_detail if args.detail == "full" else shape_summary
    return shaper(raw).model_dump()


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
