"""ZCC forwarding profiles — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zcc/list_forwarding_profiles.py``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


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


@tool(
    action=READ,
    service="zcc",
    toolset="zcc_forwarding_profiles",
    input_model=ListForwardingProfilesInput,
    is_list=True,
)
def zcc_list_forwarding_profiles(args: ListForwardingProfilesInput) -> list[dict[str, Any]]:
    """List ZCC forwarding profiles (by company). Read-only."""
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

    return shape_many([p.as_dict() for p in (profiles or [])])
