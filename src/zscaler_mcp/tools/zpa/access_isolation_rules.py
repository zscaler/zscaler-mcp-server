"""ZPA isolation policy rules (read + write).

Mirrors v1's ``access_isolation_rules.py`` — policy_type ``isolation``.

    zpa_list_isolation_policy_rules    (READ)
    zpa_get_isolation_policy_rule      (READ)
    zpa_create_isolation_policy_rule   (CREATE)
    zpa_update_isolation_policy_rule   (UPDATE)
    zpa_delete_isolation_policy_rule   (DELETE)
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.zpa_helpers import normalize_v2_rule_response
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import shape_one
from zscaler_mcp.tools.zpa._policy_common import (
    DeleteRuleInput,
    GetRuleInput,
    ListRulesInput,
    OperationResult,
    delete_rule,
    get_rule,
    list_rules,
    processed_conditions,
)


class CreateIsolationRuleInput(BaseModel):
    """Inputs for creating a ZPA isolation policy rule."""

    name: Annotated[str, Field(description="Display name for the rule.")]
    action_type: Annotated[str, Field(description="Action (e.g. isolate, bypass_isolate).")]
    zpn_isolation_profile_id: Annotated[
        Optional[str],
        Field(
            default=None, description="Isolation profile ID (required when action is 'isolate')."
        ),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    conditions: Annotated[
        Optional[Any], Field(default=None, description="Policy conditions in v2 (operands) shape.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateIsolationRuleInput(CreateIsolationRuleInput):
    """Inputs for updating a ZPA isolation policy rule (partial)."""

    rule_id: Annotated[str, Field(description="Policy rule ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    action_type: Annotated[Optional[str], Field(default=None, description="New action.")] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=ListRulesInput,
    is_list=True,
)
def zpa_list_isolation_policy_rules(args: ListRulesInput) -> list[dict[str, Any]]:
    """List ZPA isolation policy rules (read-only)."""
    return list_rules("isolation", args)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=GetRuleInput,
    is_list=False,
)
def zpa_get_isolation_policy_rule(args: GetRuleInput) -> dict[str, Any]:
    """Get one ZPA isolation policy rule (read-only)."""
    return get_rule("isolation", args)


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=CreateIsolationRuleInput,
    is_list=False,
)
def zpa_create_isolation_policy_rule(args: CreateIsolationRuleInput) -> dict[str, Any]:
    """Create a ZPA isolation policy rule (write). Requires `--write-tools`.

    `zpn_isolation_profile_id` is required when action_type is 'isolate'.
    """
    if not args.name or not args.action_type:
        raise ValueError("name and action_type are required")
    if args.action_type.lower() == "isolate" and not args.zpn_isolation_profile_id:
        raise ValueError("zpn_isolation_profile_id is required when action_type is 'isolate'")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "action": args.action_type,
        "zpn_isolation_profile_id": args.zpn_isolation_profile_id,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    created, response, err = client.zpa.policies.add_isolation_rule_v2(**payload)
    if err:
        raise RuntimeError(f"Failed to create isolation policy rule: {err}")
    return shape_one(normalize_v2_rule_response(created, response))


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=UpdateIsolationRuleInput,
    is_list=False,
)
def zpa_update_isolation_policy_rule(args: UpdateIsolationRuleInput) -> dict[str, Any]:
    """Update a ZPA isolation policy rule (write). Requires `--write-tools`."""
    if not args.rule_id:
        raise ValueError("rule_id is required")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "action": args.action_type,
        "zpn_isolation_profile_id": args.zpn_isolation_profile_id,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    updated, response, err = client.zpa.policies.update_isolation_rule_v2(args.rule_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update isolation policy rule {args.rule_id}: {err}")
    return shape_one(normalize_v2_rule_response(updated, response))


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=DeleteRuleInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_isolation_policy_rule(args: DeleteRuleInput) -> dict[str, Any]:
    """Delete a ZPA isolation policy rule (destructive write).

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    return delete_rule("isolation", args, "isolation")
