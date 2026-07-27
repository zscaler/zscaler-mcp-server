"""ZIA custom IPS signature rules — list, get, create, update, delete.

Mirrors v1's ``client.zia.ips_signature_rules`` SDK calls. These are
Snort/Suricata-style signature DEFINITIONS (not Cloud Firewall IPS policy
rules). The SDK pre-flight-validates ``rule_text`` on create. Update is
PUT-replace; the tool backfills the load-bearing ``name`` + ``rule_text`` when
omitted. Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on signature name.")
    ] = None


class GetInput(BaseModel):
    rule_id: Annotated[str, Field(description="IPS signature rule ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Signature name (max 31 chars).")]
    rule_text: Annotated[
        str,
        Field(
            description=(
                "Snort/Suricata signature body; must include a unique sid: and rev:. "
                "SDK pre-flight-validates this before create."
            )
        ),
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin note.")] = None


class UpdateInput(BaseModel):
    rule_id: Annotated[str, Field(description="Signature rule ID to update.")]
    name: Annotated[Optional[str], Field(default=None, description="New name (max 31 chars).")] = (
        None
    )
    rule_text: Annotated[Optional[str], Field(default=None, description="New signature body.")] = (
        None
    )
    description: Annotated[Optional[str], Field(default=None, description="New admin note.")] = None


class DeleteInput(BaseModel):
    rule_id: Annotated[str, Field(description="Signature rule ID to delete.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


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
def zia_list_ips_signature_rules(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA custom IPS signature rules."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    rules, _, err = client.zia.ips_signature_rules.list_ips_signature_rules(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IPS signature rules: {err}")
    return shape_many([r.as_dict() for r in (rules or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetInput,
    is_list=False,
)
def zia_get_ips_signature_rule(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA custom IPS signature rule by ID with its body."""
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.ips_signature_rules.get_ips_signature_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to get IPS signature rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=CreateInput,
    is_list=False,
)
def zia_create_ips_signature_rule(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA custom IPS signature rule (write). Activate after."""
    payload: dict[str, Any] = {"name": args.name, "rule_text": args.rule_text}
    if args.description is not None:
        payload["description"] = args.description
    client = get_zscaler_client(service="zia")
    rule, _, err = client.zia.ips_signature_rules.add_ips_signature_rule(**payload)
    if err:
        raise RuntimeError(f"Failed to create IPS signature rule: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_ips_signature_rule(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA custom IPS signature rule (PUT-replace; backfills name/rule_text). Activate after."""
    payload: dict[str, Any] = {}
    if args.name is not None:
        payload["name"] = args.name
    if args.rule_text is not None:
        payload["rule_text"] = args.rule_text
    if args.description is not None:
        payload["description"] = args.description

    client = get_zscaler_client(service="zia")
    if "name" not in payload or "rule_text" not in payload:
        existing, _, ferr = client.zia.ips_signature_rules.get_ips_signature_rule(args.rule_id)
        if ferr:
            raise RuntimeError(
                f"Failed to fetch IPS signature rule {args.rule_id} for backfill: {ferr}"
            )
        ed = existing.as_dict()
        payload.setdefault("name", ed.get("name"))
        payload.setdefault("rule_text", ed.get("rule_text") or ed.get("ruleText"))

    rule, _, err = client.zia.ips_signature_rules.update_ips_signature_rule(args.rule_id, **payload)
    if err:
        raise RuntimeError(f"Failed to update IPS signature rule {args.rule_id}: {err}")
    return shape_one(rule.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_ips_signature_rule(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA custom IPS signature rule (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.ips_signature_rules.delete_ips_signature_rule(args.rule_id)
    if err:
        raise RuntimeError(f"Failed to delete IPS signature rule {args.rule_id}: {err}")
    return OperationResult(
        success=True, message=f"IPS signature rule {args.rule_id} deleted successfully."
    ).model_dump()
