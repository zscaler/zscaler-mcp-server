"""ZPA App Protection (Inspection) Profiles — read-only lookup.

Mirrors v1's ``get_app_protection_profile.py``. Registered under the exact v1
tool name ``get_zpa_app_protection_profile``: lists all profiles, or filters by
name. Output is the curated ``RefItem`` view (id + name) to keep tokens low.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class AppProtectionProfileInput(BaseModel):
    """Inputs for reading ZPA App Protection (inspection) profiles."""

    name: Annotated[
        Optional[str], Field(default=None, description="Optional exact name to filter by.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=500, description="Items per page (API default 20, max 500)."),
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    name="get_zpa_app_protection_profile",
    input_model=AppProtectionProfileInput,
    is_list=True,
)
def get_zpa_app_protection_profile(args: AppProtectionProfileInput) -> list[dict[str, Any]]:
    """List ZPA App Protection (inspection) profiles, or filter by name (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp = {"search": args.name} if args.name else {}
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    profiles, _, err = client.zpa.app_protection.list_profiles(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list app protection profiles: {err}")
    rows = [p.as_dict() for p in (profiles or [])]
    if args.name:
        rows = [p for p in rows if p.get("name") == args.name]
        if not rows:
            raise ValueError(f"No profile found with name: {args.name}")
    return shape_many(rows)
