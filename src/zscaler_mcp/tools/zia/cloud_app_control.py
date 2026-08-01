"""ZIA Cloud App Control — available actions + rules (list/get/create/update/delete).

Mirrors v1's ``client.zia.cloudappcontrol`` SDK calls. CAC is scoped per
``rule_type`` (category enum, e.g. WEBMAIL, FILE_SHARE, SOCIAL_NETWORKING) —
every CRUD call carries ``rule_type``. There is no fetch-by-rule_id-alone path.
Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.zia_helpers import (
    apply_default_order,
    apply_default_rank,
    build_rule_payload,
    validate_order,
    validate_rank,
)
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import shape_many, shape_one

from ._rules_common import (
    OperationResult,
)

_RULE_TYPE_DESC = (
    "Canonical CAC category enum scoping the rule, e.g. WEBMAIL, FILE_SHARE, "
    "SOCIAL_NETWORKING, INSTANT_MESSAGING, SYSTEM_AND_DEVELOPMENT. Required on "
    "every CAC call — the policy table is per-category."
)

_ADVANCED_DESC = (
    "Passthrough for less-common CAC fields (snake_case), merged into the payload: "
    "applications, cloud_apps, actions, locations, groups, departments, users, labels, "
    "time_windows, device_groups, devices, type, eun_template_id, validity_time_zone_id, "
    "cascading_enabled and any other SDK-supported field. List values may be JSON strings."
)


# =============================================================================
# INPUT MODELS
# =============================================================================


class ListActionsInput(BaseModel):
    rule_type: Annotated[str, Field(description=_RULE_TYPE_DESC)]
    cloud_apps: Annotated[
        Optional[list[str]],
        Field(default=None, description="Cloud app names to scope available actions."),
    ] = None


class ListRulesInput(BaseModel):
    rule_type: Annotated[str, Field(description=_RULE_TYPE_DESC)]


class GetRuleInput(BaseModel):
    rule_type: Annotated[str, Field(description=_RULE_TYPE_DESC)]
    rule_id: Annotated[str, Field(description="Rule ID (string, even if numeric).")]


class CreateRuleInput(BaseModel):
    rule_type: Annotated[str, Field(description=_RULE_TYPE_DESC)]
    name: Annotated[str, Field(description="Rule name.")]
    action: Annotated[
        Optional[str], Field(default=None, description="Rule action (category-specific).")
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[
        Optional[bool], Field(default=True, description="Whether the rule is on.")
    ] = True
    order: Annotated[
        Optional[int], Field(default=None, description="Evaluation order (lower=first).")
    ] = None
    rank: Annotated[Optional[int], Field(default=None, description="Admin rank (0..7).")] = None
    advanced: Annotated[
        Optional[dict[str, Any]], Field(default=None, description=_ADVANCED_DESC)
    ] = None


class UpdateRuleInput(BaseModel):
    rule_type: Annotated[str, Field(description=_RULE_TYPE_DESC)]
    rule_id: Annotated[str, Field(description="Rule ID to update.")]
    name: Annotated[Optional[str], Field(default=None, description="New name.")] = None
    action: Annotated[Optional[str], Field(default=None, description="New action.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[Optional[bool], Field(default=None, description="Enable/disable.")] = None
    order: Annotated[Optional[int], Field(default=None, description="New order.")] = None
    rank: Annotated[Optional[int], Field(default=None, description="New rank.")] = None
    advanced: Annotated[
        Optional[dict[str, Any]], Field(default=None, description=_ADVANCED_DESC)
    ] = None


class DeleteRuleInput(BaseModel):
    rule_type: Annotated[str, Field(description=_RULE_TYPE_DESC)]
    rule_id: Annotated[str, Field(description="Rule ID to delete.")]


# =============================================================================
# OUTPUT VIEW (actions)
# =============================================================================


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_app_control",
    input_model=ListActionsInput,
    is_list=True,
)
def zia_list_cloud_app_control_actions(args: ListActionsInput) -> list[dict[str, Any]]:
    """List the available CAC actions for a category (and optional cloud apps)."""
    client = get_zscaler_client(service="zia")
    actions, _, err = client.zia.cloudappcontrol.list_available_actions(
        rule_type=args.rule_type, cloud_apps=args.cloud_apps or []
    )
    if err:
        raise RuntimeError(f"Failed to list CAC actions for {args.rule_type}: {err}")
    return shape_many(list(actions or []))


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_app_control",
    input_model=ListRulesInput,
    is_list=True,
)
def zia_list_cloud_app_control_rules(args: ListRulesInput) -> list[dict[str, Any]]:
    """List ZIA Cloud App Control rules for a category."""
    client = get_zscaler_client(service="zia")
    rules, _, err = client.zia.cloudappcontrol.list_rules(args.rule_type)
    if err:
        raise RuntimeError(f"Failed to list CAC rules for {args.rule_type}: {err}")
    return shape_many([r.as_dict() for r in (rules or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_app_control",
    input_model=GetRuleInput,
    is_list=False,
)
def zia_get_cloud_app_control_rule(args: GetRuleInput) -> dict[str, Any]:
    """Get a single ZIA Cloud App Control rule by category + ID."""
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.cloudappcontrol.get_rule(args.rule_type, args.rule_id)
    if err:
        raise RuntimeError(f"Failed to get CAC rule {args.rule_id} ({args.rule_type}): {err}")
    return shape_one(rule.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_app_control",
    input_model=CreateRuleInput,
    is_list=False,
)
def zia_create_cloud_app_control_rule(args: CreateRuleInput) -> dict[str, Any]:
    """Create a ZIA Cloud App Control rule (write). Activate after."""
    payload = build_rule_payload(
        scalars={
            "name": args.name,
            "action": args.action,
            "description": args.description,
            "enabled": args.enabled,
            "order": apply_default_order(args.order),
            "rank": apply_default_rank(args.rank),
        },
        advanced=args.advanced,
    )
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.cloudappcontrol.add_rule(args.rule_type, **payload)
    if err:
        raise RuntimeError(f"Failed to create CAC rule ({args.rule_type}): {err}")
    return shape_one(rule.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_app_control",
    input_model=UpdateRuleInput,
    is_list=False,
)
def zia_update_cloud_app_control_rule(args: UpdateRuleInput) -> dict[str, Any]:
    """Update a ZIA Cloud App Control rule (write, PUT-replace). Activate after."""
    payload = build_rule_payload(
        scalars={
            "name": args.name,
            "action": args.action,
            "description": args.description,
            "enabled": args.enabled,
            "order": validate_order(args.order) if args.order is not None else None,
            "rank": validate_rank(args.rank) if args.rank is not None else None,
        },
        advanced=args.advanced,
    )
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.cloudappcontrol.update_rule(args.rule_type, args.rule_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update CAC rule {args.rule_id} ({args.rule_type}): {err}")
    return shape_one(rule.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_app_control",
    input_model=DeleteRuleInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_cloud_app_control_rule(args: DeleteRuleInput) -> dict[str, Any]:
    """Delete a ZIA Cloud App Control rule (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.cloudappcontrol.delete_rule(args.rule_type, args.rule_id)
    if err:
        raise RuntimeError(f"Failed to delete CAC rule {args.rule_id} ({args.rule_type}): {err}")
    return OperationResult(
        success=True,
        message=f"Cloud App Control rule {args.rule_id} ({args.rule_type}) deleted successfully.",
    ).model_dump()
