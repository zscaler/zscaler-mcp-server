"""ZPA app-protection (inspection) policy rules (read + write).

Mirrors v1's ``access_app_protection_rules.py`` — policy_type ``inspection``.

    zpa_list_app_protection_rules    (READ)
    zpa_get_app_protection_rule      (READ)
    zpa_create_app_protection_rule   (CREATE)
    zpa_update_app_protection_rule   (UPDATE)
    zpa_delete_app_protection_rule   (DELETE)
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


class CreateAppProtectionRuleInput(BaseModel):
    """Inputs for creating a ZPA app-protection (inspection) policy rule."""

    name: Annotated[str, Field(description="Display name for the rule.")]
    action_type: Annotated[str, Field(description="Action (e.g. inspect, bypass_inspect).")]
    zpn_inspection_profile_id: Annotated[
        Optional[str],
        Field(
            default=None, description="Inspection profile ID (required when action is 'inspect')."
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


class UpdateAppProtectionRuleInput(CreateAppProtectionRuleInput):
    """Inputs for updating a ZPA app-protection (inspection) policy rule (partial)."""

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
def zpa_list_app_protection_rules(args: ListRulesInput) -> list[dict[str, Any]]:
    """List ZPA app-protection (inspection) policy rules (read-only)."""
    return list_rules("inspection", args)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=GetRuleInput,
    is_list=False,
)
def zpa_get_app_protection_rule(args: GetRuleInput) -> dict[str, Any]:
    """Get one ZPA app-protection (inspection) policy rule (read-only)."""
    return get_rule("inspection", args)


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=CreateAppProtectionRuleInput,
    is_list=False,
)
def zpa_create_app_protection_rule(args: CreateAppProtectionRuleInput) -> dict[str, Any]:
    """Create a ZPA app-protection (inspection) policy rule (write).

    Gated by HMAC + `--write-tools`. `zpn_inspection_profile_id` is required
    when action_type is 'inspect'.
    """
    if not args.name or not args.action_type:
        raise ValueError("name and action_type are required")
    if args.action_type.lower() == "inspect" and not args.zpn_inspection_profile_id:
        raise ValueError("zpn_inspection_profile_id is required when action_type is 'inspect'")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "action": args.action_type,
        "zpn_inspection_profile_id": args.zpn_inspection_profile_id,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    created, response, err = client.zpa.policies.add_app_protection_rule_v2(**payload)
    if err:
        raise RuntimeError(f"Failed to create app protection rule: {err}")
    return shape_one(normalize_v2_rule_response(created, response))


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=UpdateAppProtectionRuleInput,
    is_list=False,
)
def zpa_update_app_protection_rule(args: UpdateAppProtectionRuleInput) -> dict[str, Any]:
    """Update a ZPA app-protection (inspection) policy rule (write)."""
    if not args.rule_id:
        raise ValueError("rule_id is required")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "action": args.action_type,
        "zpn_inspection_profile_id": args.zpn_inspection_profile_id,
        "conditions": processed_conditions(args.conditions),
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    updated, response, err = client.zpa.policies.update_app_protection_rule_v2(
        args.rule_id, **payload
    )
    if err:
        raise RuntimeError(f"Failed to update app protection rule {args.rule_id}: {err}")
    return shape_one(normalize_v2_rule_response(updated, response))


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_access_policies",
    input_model=DeleteRuleInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_app_protection_rule(args: DeleteRuleInput) -> dict[str, Any]:
    """Delete a ZPA app-protection (inspection) policy rule (destructive write)."""
    return delete_rule("inspection", args, "app protection")
