"""ZIA Sandbox rules — list, get, create, update, delete.

Mirrors v1's ``client.zia.sandbox_rules`` SDK calls. Common rule fields are typed; the
long tail rides an ``advanced`` dict (snake_case keys, merged into the SDK
payload). Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.zia_helpers import (
    ORDER_FIELD_DESCRIPTION,
    RANK_FIELD_DESCRIPTION,
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

_ADVANCED_DESC = (
    "Passthrough for less-common rule fields (snake_case), merged into the "
    "payload. Includes relational ID lists (locations, location_groups, groups, "
    "departments, users, labels, time_windows, devices, device_groups), "
    "sandbox fields (ba_rule_action, file_types, protocols, ba_policy_categories, first_time_enable, first_time_operation, ml_action_enabled), and any other SDK-supported field. List values may be JSON strings."
)

ACTION_DESC = "Sandbox rule action: ALLOW, BLOCK, etc."


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on rule name.")
    ] = None


class GetInput(BaseModel):
    rule_id: Annotated[str, Field(description="Rule ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Rule name.")]
    action: Annotated[str, Field(description=ACTION_DESC)]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[
        Optional[bool], Field(default=True, description="Whether the rule is on.")
    ] = True
    order: Annotated[Optional[int], Field(default=None, description=ORDER_FIELD_DESCRIPTION)] = None
    rank: Annotated[Optional[int], Field(default=None, description=RANK_FIELD_DESCRIPTION)] = None
    advanced: Annotated[
        Optional[dict[str, Any]], Field(default=None, description=_ADVANCED_DESC)
    ] = None


class UpdateInput(BaseModel):
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


class DeleteInput(BaseModel):
    rule_id: Annotated[str, Field(description="Rule ID to delete.")]


@tool(
    action=READ,
    service="zia",
    toolset="zia_sandbox",
    input_model=ListInput,
    is_list=True,
)
def zia_list_sandbox_rules(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA Sandbox rules."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    rules, _, err = client.zia.sandbox_rules.list_rules(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list Sandbox rules: {err}")
    return shape_many([r.as_dict() for r in (rules or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_sandbox",
    input_model=GetInput,
    is_list=False,
)
def zia_get_sandbox_rule(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA Sandbox rule by ID with member references."""
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.sandbox_rules.get_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to get Sandbox rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_sandbox",
    input_model=CreateInput,
    is_list=False,
)
def zia_create_sandbox_rule(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA Sandbox rule (write). Activate after."""
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
    rule, _, err = client.zia.sandbox_rules.add_rule(**payload)
    if err:
        raise RuntimeError(f"Failed to create Sandbox rule: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_sandbox",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_sandbox_rule(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA Sandbox rule (write, PUT-replace). Activate after."""
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
    rule, _, err = client.zia.sandbox_rules.update_rule(args.rule_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update Sandbox rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_sandbox",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_sandbox_rule(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA Sandbox rule (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.sandbox_rules.delete_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to delete Sandbox rule {args.rule_id}: {err}")
    return OperationResult(
        success=True, message=f"Sandbox rule {args.rule_id} deleted successfully."
    ).model_dump()
