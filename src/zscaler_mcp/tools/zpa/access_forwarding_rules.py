"""ZPA client forwarding policy rules (read + write).

Mirrors v1's ``access_forwarding_rules.py`` — policy_type ``client_forwarding``.

    zpa_list_forwarding_policy_rules    (READ)
    zpa_get_forwarding_policy_rule      (READ)
    zpa_create_forwarding_policy_rule   (CREATE)
    zpa_update_forwarding_policy_rule   (UPDATE)
    zpa_delete_forwarding_policy_rule   (DELETE)
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


class CreateForwardingRuleInput(BaseModel):
    """Inputs for creating a ZPA client forwarding policy rule."""

    name: Annotated[str, Field(description="Display name for the rule.")]
    action_type: Annotated[str, Field(description="Action (e.g. INTERCEPT, BYPASS).")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    conditions: Annotated[
        Optional[Any], Field(default=None, description="Policy conditions in v2 (operands) shape.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateForwardingRuleInput(CreateForwardingRuleInput):
    """Inputs for updating a ZPA client forwarding policy rule (partial)."""

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
def zpa_list_forwarding_policy_rules(args: ListRulesInput) -> list[dict[str, Any]]:
    """List ZPA client forwarding policy rules (read-only)."""
    return list_rules("client_forwarding", args)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=GetRuleInput,
    is_list=False,
)
def zpa_get_forwarding_policy_rule(args: GetRuleInput) -> dict[str, Any]:
    """Get one ZPA client forwarding policy rule (read-only)."""
    return get_rule("client_forwarding", args)


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=CreateForwardingRuleInput,
    is_list=False,
)
def zpa_create_forwarding_policy_rule(args: CreateForwardingRuleInput) -> dict[str, Any]:
    """Create a ZPA client forwarding policy rule (write). Gated by HMAC + `--write-tools`."""
    if not args.name or not args.action_type:
        raise ValueError("name and action_type are required")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "action": args.action_type,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    created, response, err = client.zpa.policies.add_client_forwarding_rule_v2(**payload)
    if err:
        raise RuntimeError(f"Failed to create forwarding policy rule: {err}")
    return shape_one(normalize_v2_rule_response(created, response))


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=UpdateForwardingRuleInput,
    is_list=False,
)
def zpa_update_forwarding_policy_rule(args: UpdateForwardingRuleInput) -> dict[str, Any]:
    """Update a ZPA client forwarding policy rule (write). Gated by HMAC + `--write-tools`."""
    if not args.rule_id:
        raise ValueError("rule_id is required")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "action": args.action_type,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    updated, response, err = client.zpa.policies.update_client_forwarding_rule_v2(
        args.rule_id, **payload
    )
    if err:
        raise RuntimeError(f"Failed to update forwarding policy rule {args.rule_id}: {err}")
    return shape_one(normalize_v2_rule_response(updated, response))


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=DeleteRuleInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_forwarding_policy_rule(args: DeleteRuleInput) -> dict[str, Any]:
    """Delete a ZPA client forwarding policy rule (destructive write)."""
    return delete_rule("client_forwarding", args, "forwarding")
