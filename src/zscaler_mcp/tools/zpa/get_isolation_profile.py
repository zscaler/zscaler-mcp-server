"""ZPA Cloud Browser Isolation (CBI) profiles — read-only lookup.

Mirrors v1's ``get_isolation_profile.py``. Registered under the exact v1 tool
name ``get_zpa_isolation_profile``: lists all CBI profiles, or returns the one
matching an exact name. Output is the curated ``RefItem`` view (id + name).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class IsolationProfileInput(BaseModel):
    """Inputs for reading ZPA isolation (CBI) profiles."""

    name: Annotated[
        Optional[str], Field(default=None, description="Optional exact name to filter by.")
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    name="get_zpa_isolation_profile",
    input_model=IsolationProfileInput,
    is_list=True,
)
def get_zpa_isolation_profile(args: IsolationProfileInput) -> list[dict[str, Any]]:
    """List ZPA Cloud Browser Isolation (CBI) profiles, or filter by exact name (read-only)."""
    client = get_zscaler_client(service="zpa")
    profiles, _, err = client.zpa.cbi_profile.list_cbi_profiles()
    if err:
        raise RuntimeError(f"Failed to list CBI profiles: {err}")
    rows = [p.as_dict() for p in (profiles or [])]
    if args.name:
        rows = [p for p in rows if p.get("name") == args.name]
        if not rows:
            raise ValueError(f"No CBI profile found with name: {args.name}")
    return shape_many(rows)
