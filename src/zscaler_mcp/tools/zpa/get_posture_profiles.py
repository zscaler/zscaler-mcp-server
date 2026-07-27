"""ZPA Posture Profiles — read-only lookup.

Mirrors v1's ``get_posture_profiles.py``. Registered under the exact v1 tool
name ``get_zpa_posture_profile``: lists all posture profiles, or fetches one by
ID or by name. Output is the curated ``RefItem`` view (id + name).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class PostureProfileInput(BaseModel):
    """Inputs for reading ZPA posture profiles."""

    profile_id: Annotated[
        Optional[str], Field(default=None, description="Posture profile ID for direct lookup.")
    ] = None
    name: Annotated[
        Optional[str], Field(default=None, description="Exact posture profile name to match.")
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    name="get_zpa_posture_profile",
    input_model=PostureProfileInput,
    is_list=True,
)
def get_zpa_posture_profile(args: PostureProfileInput) -> list[dict[str, Any]]:
    """List ZPA posture profiles, or look one up by ID or name (read-only)."""
    client = get_zscaler_client(service="zpa")
    api = client.zpa.posture_profiles

    if args.profile_id:
        profile, _, err = api.get_profile(args.profile_id)
        if err:
            raise RuntimeError(f"Failed to fetch posture profile {args.profile_id}: {err}")
        return shape_many([profile.as_dict()])

    qp = {"search": args.name} if args.name else {}
    profiles, _, err = api.list_posture_profiles(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list posture profiles: {err}")
    rows = [p.as_dict() for p in (profiles or [])]
    if args.name:
        rows = [p for p in rows if p.get("name") == args.name]
        if not rows:
            raise ValueError(f"No posture profile found with name '{args.name}'")
    return shape_many(rows)
