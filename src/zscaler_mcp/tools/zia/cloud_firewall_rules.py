"""ZIA Cloud Firewall rules — list, get, create, update, delete.

Mirrors v1's ``client.zia.cloud_firewall_rules`` SDK calls. Common rule fields
are typed; the long tail of relational/ID fields rides an ``advanced`` dict
(snake_case keys, merged into the SDK payload). Writes are staged until
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
    "Passthrough for less-common rule fields (snake_case): src_ips, dest_addresses, "
    "source_countries, dest_countries, exclude_src_countries, dest_ip_categories, "
    "device_trust_levels, nw_applications, app_services, app_service_groups, departments, "
    "dest_ip_groups, dest_ipv6_groups, devices, device_groups, groups, labels, locations, "
    "location_groups, nw_application_groups, nw_services, nw_service_groups, time_windows, "
    "users, workload_groups, enable_full_logging, predefined, default_rule. Merged into the "
    "payload; list values may be JSON strings."
)

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on rule name.")
    ] = None


class GetInput(BaseModel):
    rule_id: Annotated[str, Field(description="Rule ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Rule name.")]
    action: Annotated[str, Field(description="Rule action: ALLOW, BLOCK_DROP, BLOCK_RESET, etc.")]
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


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=ListInput,
    is_list=True,
)
def zia_list_cloud_firewall_rules(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA Cloud Firewall rules."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    rules, _, err = client.zia.cloud_firewall_rules.list_rules(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list cloud firewall rules: {err}")
    return shape_many([r.as_dict() for r in (rules or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetInput,
    is_list=False,
)
def zia_get_cloud_firewall_rule(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA Cloud Firewall rule by ID with member references."""
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.cloud_firewall_rules.get_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to get cloud firewall rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=CreateInput,
    is_list=False,
)
def zia_create_cloud_firewall_rule(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA Cloud Firewall rule (write). Activate after."""
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
    rule, _, err = client.zia.cloud_firewall_rules.add_rule(**payload)
    if err:
        raise RuntimeError(f"Failed to create cloud firewall rule: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_cloud_firewall_rule(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA Cloud Firewall rule (write, PUT-replace). Activate after."""
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
    rule, _, err = client.zia.cloud_firewall_rules.update_rule(args.rule_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update cloud firewall rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_cloud_firewall_rule(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA Cloud Firewall rule (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.cloud_firewall_rules.delete_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to delete cloud firewall rule {args.rule_id}: {err}")
    return OperationResult(
        success=True, message=f"Cloud firewall rule {args.rule_id} deleted successfully."
    ).model_dump()
