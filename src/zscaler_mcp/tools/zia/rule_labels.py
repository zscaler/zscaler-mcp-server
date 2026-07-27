"""ZIA rule labels — list, get, create, update, delete.

Mirrors v1's ``client.zia.rule_labels`` SDK calls. Rule labels are referenced by
policy rules for organisation/reporting. Writes are staged until
``zia_activate_configuration``.
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
        Optional[str], Field(default=None, description="Substring match on label name.")
    ] = None


class GetInput(BaseModel):
    label_id: Annotated[str, Field(description="Rule label ID (string, even if numeric).")]


class CreateInput(BaseModel):
    name: Annotated[str, Field(description="Label name.")]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )


class UpdateInput(BaseModel):
    label_id: Annotated[str, Field(description="Label ID to update.")]
    name: Annotated[Optional[str], Field(default=None, description="New label name.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )


class DeleteInput(BaseModel):
    label_id: Annotated[str, Field(description="Label ID to delete.")]


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
    toolset="zia_rule_labels",
    input_model=ListInput,
    is_list=True,
)
def zia_list_rule_labels(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA rule labels."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    labels, _, err = client.zia.rule_labels.list_labels(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list rule labels: {err}")
    return shape_many([lbl.as_dict() for lbl in (labels or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_rule_labels",
    input_model=GetInput,
    is_list=False,
)
def zia_get_rule_label(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA rule label by ID."""
    client = get_zscaler_client(service="zia")
    label, _, err = client.zia.rule_labels.get_label(label_id=args.label_id)
    if err:
        raise RuntimeError(f"Failed to get rule label {args.label_id}: {err}")
    return shape_one(label.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_rule_labels",
    input_model=CreateInput,
    is_list=False,
)
def zia_create_rule_label(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA rule label (write). Activate after."""
    client = get_zscaler_client(service="zia")
    payload: dict[str, Any] = {"name": args.name}
    if args.description:
        payload["description"] = args.description
    label, _, err = client.zia.rule_labels.add_label(**payload)
    if err:
        raise RuntimeError(f"Failed to create rule label: {err}")
    return shape_one(label.as_dict())


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_rule_labels",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_rule_label(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA rule label (write). Activate after."""
    fields: dict[str, Any] = {}
    if args.name:
        fields["name"] = args.name
    if args.description is not None:
        fields["description"] = args.description
    if not fields:
        raise ValueError("At least one of name or description must be provided for update.")
    client = get_zscaler_client(service="zia")
    label, _, err = client.zia.rule_labels.update_label(label_id=args.label_id, **fields)
    if err:
        raise RuntimeError(f"Failed to update rule label {args.label_id}: {err}")
    return shape_one(label.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_rule_labels",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_rule_label(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA rule label (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.rule_labels.delete_label(label_id=args.label_id)
    if err:
        raise RuntimeError(f"Failed to delete rule label {args.label_id}: {err}")
    return OperationResult(
        success=True, message=f"Rule label {args.label_id} deleted successfully."
    ).model_dump()
