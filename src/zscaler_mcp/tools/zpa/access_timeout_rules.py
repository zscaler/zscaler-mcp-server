"""ZPA timeout policy rules (read + write).

Mirrors v1's ``access_timeout_rules.py`` — policy_type ``timeout``.

    zpa_list_timeout_policy_rules    (READ)
    zpa_get_timeout_policy_rule      (READ)
    zpa_create_timeout_policy_rule   (CREATE)
    zpa_update_timeout_policy_rule   (UPDATE)
    zpa_delete_timeout_policy_rule   (DELETE)
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


class CreateTimeoutRuleInput(BaseModel):
    """Inputs for creating a ZPA timeout policy rule."""

    name: Annotated[str, Field(description="Display name for the rule.")]
    action_type: Annotated[
        str, Field(default="RE_AUTH", description="Action (default RE_AUTH).")
    ] = "RE_AUTH"
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    custom_msg: Annotated[
        Optional[str], Field(default=None, description="Custom re-auth message.")
    ] = None
    reauth_timeout: Annotated[
        str, Field(default="172800", description="Re-auth timeout (seconds).")
    ] = "172800"
    reauth_idle_timeout: Annotated[
        str, Field(default="600", description="Re-auth idle timeout (seconds).")
    ] = "600"
    conditions: Annotated[
        Optional[Any], Field(default=None, description="Policy conditions in v2 (operands) shape.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateTimeoutRuleInput(CreateTimeoutRuleInput):
    """Inputs for updating a ZPA timeout policy rule (partial)."""

    rule_id: Annotated[str, Field(description="Policy rule ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    action_type: Annotated[Optional[str], Field(default=None, description="New action.")] = None
    reauth_timeout: Annotated[
        Optional[str], Field(default=None, description="New re-auth timeout.")
    ] = None
    reauth_idle_timeout: Annotated[
        Optional[str], Field(default=None, description="New re-auth idle timeout.")
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=ListRulesInput,
    is_list=True,
)
def zpa_list_timeout_policy_rules(args: ListRulesInput) -> list[dict[str, Any]]:
    """List ZPA timeout policy rules (read-only)."""
    return list_rules("timeout", args)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=GetRuleInput,
    is_list=False,
)
def zpa_get_timeout_policy_rule(args: GetRuleInput) -> dict[str, Any]:
    """Get one ZPA timeout policy rule (read-only)."""
    return get_rule("timeout", args)


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=CreateTimeoutRuleInput,
    is_list=False,
)
def zpa_create_timeout_policy_rule(args: CreateTimeoutRuleInput) -> dict[str, Any]:
    """Create a ZPA timeout policy rule (write). Gated by HMAC + `--write-tools`."""
    if not args.name:
        raise ValueError("name is required")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "custom_msg": args.custom_msg,
        "action": args.action_type,
        "reauth_timeout": args.reauth_timeout,
        "reauth_idle_timeout": args.reauth_idle_timeout,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    created, response, err = client.zpa.policies.add_timeout_rule_v2(**payload)
    if err:
        raise RuntimeError(f"Failed to create timeout policy rule: {err}")
    return shape_one(normalize_v2_rule_response(created, response))


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=UpdateTimeoutRuleInput,
    is_list=False,
)
def zpa_update_timeout_policy_rule(args: UpdateTimeoutRuleInput) -> dict[str, Any]:
    """Update a ZPA timeout policy rule (write). Gated by HMAC + `--write-tools`."""
    if not args.rule_id:
        raise ValueError("rule_id is required")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "custom_msg": args.custom_msg,
        "action": args.action_type,
        "reauth_timeout": args.reauth_timeout,
        "reauth_idle_timeout": args.reauth_idle_timeout,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    updated, response, err = client.zpa.policies.update_timeout_rule_v2(args.rule_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update timeout policy rule {args.rule_id}: {err}")
    return shape_one(normalize_v2_rule_response(updated, response))


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=DeleteRuleInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_timeout_policy_rule(args: DeleteRuleInput) -> dict[str, Any]:
    """Delete a ZPA timeout policy rule (destructive write)."""
    return delete_rule("timeout", args, "timeout")
