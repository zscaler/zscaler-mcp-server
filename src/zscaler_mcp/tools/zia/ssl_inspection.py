"""ZIA SSL Inspection rules — list, get, create, update, delete.

Mirrors v1's ``ssl_inspection.py`` (``client.zia.ssl_inspection_rules`` SDK calls).
Common rule fields are typed; the long tail rides an ``advanced`` dict (snake_case
keys, merged into the SDK payload). Writes are staged until
``zia_activate_configuration``.
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
    "SSL-inspection fields (action as a nested object, cloud_applications, platforms, road_warrior_for_kerberos), and any other SDK-supported field. List values may be JSON strings."
)

ACTION_DESC = "SSL inspection action object or string (see ZIA docs)."


class ListInput(BaseModel):
    """No parameters.

    The ZIA SSL Inspection rules API returns a flat list — it exposes neither a
    server-side search nor pagination, so the tool takes no filtering arguments.
    """


class GetInput(BaseModel):
    rule_id: Annotated[str, Field(description="Rule ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Rule name.")]
    action: Annotated[Optional[str], Field(default=None, description=ACTION_DESC)] = None
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
    toolset="zia_ssl_inspection",
    input_model=ListInput,
    is_list=True,
)
def zia_list_ssl_inspection_rules(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA SSL Inspection rules."""
    client = get_zscaler_client(service="zia")
    rules, _, err = client.zia.ssl_inspection_rules.list_rules()
    if err:
        raise RuntimeError(f"Failed to list SSL Inspection rules: {err}")
    return shape_many([r.as_dict() for r in (rules or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_ssl_inspection",
    input_model=GetInput,
    is_list=False,
)
def zia_get_ssl_inspection_rule(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA SSL Inspection rule by ID with member references."""
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.ssl_inspection_rules.get_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to get SSL Inspection rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_ssl_inspection",
    input_model=CreateInput,
    is_list=False,
)
def zia_create_ssl_inspection_rule(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA SSL Inspection rule (write). Activate after."""
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
    rule, _, err = client.zia.ssl_inspection_rules.add_rule(**payload)
    if err:
        raise RuntimeError(f"Failed to create SSL Inspection rule: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_ssl_inspection",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_ssl_inspection_rule(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA SSL Inspection rule (write, PUT-replace). Activate after."""
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
    rule, _, err = client.zia.ssl_inspection_rules.update_rule(args.rule_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update SSL Inspection rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_ssl_inspection",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_ssl_inspection_rule(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA SSL Inspection rule (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.ssl_inspection_rules.delete_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to delete SSL Inspection rule {args.rule_id}: {err}")
    return OperationResult(
        success=True, message=f"SSL Inspection rule {args.rule_id} deleted successfully."
    ).model_dump()
