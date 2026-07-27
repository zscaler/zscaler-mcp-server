"""ZIA Shadow IT analytics — apps, custom tags, bulk sanction update.

Mirrors v1's ``client.zia.shadow_it_report`` SDK calls. This is the analytics
catalog (numeric IDs + friendly names), NOT the policy-engine enum catalog.
Bulk update is a write (sanction state + tags).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.registry import READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many


class ListAppsInput(BaseModel):
    page_number: Annotated[Optional[int], Field(default=None, description="Page number.")] = None
    limit: Annotated[
        Optional[int], Field(default=None, description="Result limit (max 1000 recommended).")
    ] = None


class _NoArgs(BaseModel):
    pass


class BulkUpdateInput(BaseModel):
    sanction_state: Annotated[str, Field(description="One of: sanctioned, unsanctioned, any.")]
    application_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Application IDs to update.")
    ] = None
    custom_tag_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Custom tag IDs to apply.")
    ] = None


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


@tool(
    action=READ,
    service="zia",
    toolset="zia_shadow_it",
    input_model=ListAppsInput,
    is_list=True,
)
def zia_list_shadow_it_apps(args: ListAppsInput) -> list[dict[str, Any]]:
    """List ZIA Shadow IT applications (analytics catalog)."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.page_number is not None:
        qp["page_number"] = args.page_number
    if args.limit is not None:
        qp["limit"] = args.limit
    apps, _, err = client.zia.shadow_it_report.list_apps(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list shadow IT apps: {err}")
    return shape_many([a.as_dict() for a in (apps or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_shadow_it",
    input_model=_NoArgs,
    is_list=True,
)
def zia_list_shadow_it_custom_tags(args: _NoArgs) -> list[dict[str, Any]]:
    """List ZIA Shadow IT custom tags."""
    client = get_zscaler_client(service="zia")
    tags, _, err = client.zia.shadow_it_report.list_custom_tags()
    if err:
        raise RuntimeError(f"Failed to list shadow IT custom tags: {err}")
    return shape_many([t.as_dict() for t in (tags or [])])


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_shadow_it",
    input_model=BulkUpdateInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_bulk_update_shadow_it_apps(args: BulkUpdateInput) -> dict[str, Any]:
    """Bulk-apply sanction state and/or custom tags to Shadow IT apps (write)."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.shadow_it_report.bulk_update(
        args.sanction_state,
        application_ids=parse_list(args.application_ids) if args.application_ids else None,
        custom_tag_ids=parse_list(args.custom_tag_ids) if args.custom_tag_ids else None,
    )
    if err:
        raise RuntimeError(f"Shadow IT bulk update failed: {err}")
    n = len(args.application_ids or [])
    return OperationResult(
        success=True, message=f"Bulk-updated {n} app(s) to sanction state '{args.sanction_state}'."
    ).model_dump()
