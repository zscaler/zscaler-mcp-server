"""ZCC trusted networks — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zcc/list_trusted_networks.py``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many


class ListTrustedNetworksInput(BaseModel):
    """Inputs for listing ZCC trusted networks."""

    search: Annotated[
        Optional[str],
        Field(default=None, description="Substring match on the network name."),
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, description="Items per page.")
    ] = None


class TrustedNetworkSummary(AgentView):
    """Lean view of a ZCC trusted network."""

    id: str = Field(description="Trusted network ID.")
    name: Optional[str] = Field(default=None, description="Network name.")
    network_id: Optional[str] = Field(default=None, description="Underlying network identifier.")
    active: Optional[bool] = Field(default=None, description="Whether the network is active.")


def _shape_network(raw: dict[str, Any]) -> TrustedNetworkSummary:
    return TrustedNetworkSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", "network_name", "networkName"),
        network_id=pick(raw, "network_id", "networkId"),
        active=pick(raw, "active"),
    )


@tool(
    action=READ,
    service="zcc",
    toolset="zcc_trusted_networks",
    input_model=ListTrustedNetworksInput,
    output_view=TrustedNetworkSummary,
    is_list=True,
)
def zcc_list_trusted_networks(args: ListTrustedNetworksInput) -> list[dict[str, Any]]:
    """List ZCC trusted networks (by company) as curated, agent-facing views. Read-only."""
    client = get_zscaler_client(service="zcc")

    qp: dict[str, Any] = {}
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    if args.search:
        qp["search"] = args.search

    networks, _, err = client.zcc.trusted_networks.list_by_company(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZCC trusted networks: {err}")

    return shape_many([n.as_dict() for n in (networks or [])], _shape_network)
