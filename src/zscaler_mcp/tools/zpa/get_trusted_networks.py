"""ZPA Trusted Networks — read-only lookup.

Mirrors v1's ``get_trusted_networks.py``. Registered under the exact v1 tool
name ``get_zpa_trusted_network``: lists all trusted networks, or fetches one by
ID or by name. Output is the curated ``RefItem`` view (id + name).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class TrustedNetworkInput(BaseModel):
    """Inputs for reading ZPA trusted networks."""

    network_id: Annotated[
        Optional[str], Field(default=None, description="Trusted network ID for direct lookup.")
    ] = None
    name: Annotated[
        Optional[str], Field(default=None, description="Exact trusted network name to match.")
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    name="get_zpa_trusted_network",
    input_model=TrustedNetworkInput,
    is_list=True,
)
def get_zpa_trusted_network(args: TrustedNetworkInput) -> list[dict[str, Any]]:
    """List ZPA trusted networks, or look one up by ID or name (read-only)."""
    client = get_zscaler_client(service="zpa")
    api = client.zpa.trusted_networks

    if args.network_id:
        network, _, err = api.get_network(args.network_id)
        if err:
            raise RuntimeError(f"Failed to fetch trusted network {args.network_id}: {err}")
        return shape_many([network.as_dict()])

    qp = {"search": args.name} if args.name else {}
    networks, _, err = api.list_trusted_networks(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list trusted networks: {err}")
    rows = [n.as_dict() for n in (networks or [])]
    if args.name:
        rows = [n for n in rows if n.get("name") == args.name]
        if not rows:
            raise ValueError(f"No trusted network found with name '{args.name}'")
    return shape_many(rows)
