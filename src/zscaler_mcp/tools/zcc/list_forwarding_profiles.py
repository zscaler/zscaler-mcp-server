"""ZCC forwarding profiles — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zcc/list_forwarding_profiles.py``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many


class ListForwardingProfilesInput(BaseModel):
    """Inputs for listing ZCC forwarding profiles."""

    search: Annotated[
        Optional[str],
        Field(default=None, description="Substring match on the profile name."),
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, description="Items per page.")
    ] = None


class ForwardingProfileSummary(AgentView):
    """Lean view of a ZCC forwarding profile."""

    id: str = Field(description="Forwarding profile ID.")
    name: Optional[str] = Field(default=None, description="Profile name.")
    active: Optional[bool] = Field(default=None, description="Whether the profile is active.")


def _shape_profile(raw: dict[str, Any]) -> ForwardingProfileSummary:
    return ForwardingProfileSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        active=pick(raw, "active"),
    )


@tool(
    action=READ,
    service="zcc",
    toolset="zcc_forwarding_profiles",
    input_model=ListForwardingProfilesInput,
    output_view=ForwardingProfileSummary,
    is_list=True,
)
def zcc_list_forwarding_profiles(args: ListForwardingProfilesInput) -> list[dict[str, Any]]:
    """List ZCC forwarding profiles (by company) as curated, agent-facing views. Read-only."""
    client = get_zscaler_client(service="zcc")

    qp: dict[str, Any] = {}
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    if args.search:
        qp["search"] = args.search

    profiles, _, err = client.zcc.forwarding_profile.list_by_company(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZCC forwarding profiles: {err}")

    return shape_many([p.as_dict() for p in (profiles or [])], _shape_profile)
