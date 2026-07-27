"""ZIA GRE internal-IP ranges — read-only discovery.

Mirrors v1's ``gre_ranges.py``. Backed by ``client.zia.gre_tunnel`` (the
``list_gre_ranges`` endpoint). Used when provisioning numbered GRE tunnels.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class ListRangesInput(BaseModel):
    internal_ip_range: Annotated[
        Optional[str], Field(default=None, description="Filter by internal IP range.")
    ] = None
    static_ip: Annotated[
        Optional[str], Field(default=None, description="Filter by backing static IP.")
    ] = None
    limit: Annotated[
        Optional[int], Field(default=None, description="Max number of ranges to return.")
    ] = None


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=ListRangesInput,
    is_list=True,
)
def zia_list_gre_ranges(args: ListRangesInput) -> list[dict[str, Any]]:
    """List available ZIA GRE internal-IP ranges."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.internal_ip_range:
        qp["internal_ip_range"] = args.internal_ip_range
    if args.static_ip:
        qp["static_ip"] = args.static_ip
    if args.limit:
        qp["limit"] = args.limit
    ranges, _, err = client.zia.gre_tunnel.list_gre_ranges(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list GRE ranges: {err}")
    rows = [r if isinstance(r, dict) else r.as_dict() for r in (ranges or [])]
    return shape_many(rows)
