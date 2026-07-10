"""ZTW network services (read-only).

Mirrors v1's ``network_services.py``. Backed by ``client.ztw.nw_service`` —
individual network service definitions (protocol + port ranges).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, coalesce, pick, shape_many


class ListNetworkServicesInput(BaseModel):
    """Inputs for listing ZTW network services."""

    protocol: Annotated[
        Optional[str],
        Field(default=None, description="Filter by protocol (ICMP, TCP, UDP, GRE, ESP, OTHER)."),
    ] = None
    search: Annotated[
        Optional[str],
        Field(default=None, description="Server-side search on service name or description."),
    ] = None
    locale: Annotated[
        Optional[str],
        Field(default=None, description="Locale for localized descriptions (e.g. 'en-US')."),
    ] = None


class NetworkServiceSummary(AgentView):
    """Lean view of a ZTW network service definition."""

    id: str = Field(description="Network service ID.")
    name: str = Field(description="Service name.")
    type: Optional[str] = Field(
        default=None, description="Service type (STANDARD/PREDEFINED/CUSTOM)."
    )
    description: Optional[str] = Field(default=None, description="Description.")
    protocol: Optional[str] = Field(default=None, description="Protocol, if a single one applies.")
    tcp_port_count: int = Field(description="Number of TCP port ranges defined.")
    udp_port_count: int = Field(description="Number of UDP port ranges defined.")


def _port_ranges(raw: dict[str, Any], *keys: str) -> list[Any]:
    return coalesce(raw, *keys)


def shape_service(raw: dict[str, Any]) -> NetworkServiceSummary:
    return NetworkServiceSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        type=pick(raw, "type"),
        description=pick(raw, "description"),
        protocol=pick(raw, "protocol"),
        tcp_port_count=len(
            _port_ranges(raw, "src_tcp_ports", "srcTcpPorts", "dest_tcp_ports", "destTcpPorts")
        ),
        udp_port_count=len(
            _port_ranges(raw, "src_udp_ports", "srcUdpPorts", "dest_udp_ports", "destUdpPorts")
        ),
    )


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListNetworkServicesInput,
    output_view=NetworkServiceSummary,
    is_list=True,
)
def ztw_list_network_services(args: ListNetworkServicesInput) -> list[dict[str, Any]]:
    """List ZTW network services as curated, agent-facing summaries.

    Optionally filter by `protocol` or `search`. Read-only.
    """
    client = get_zscaler_client(service="ztw")
    api = client.ztw.nw_service

    qp: dict[str, Any] = {}
    if args.protocol:
        qp["protocol"] = args.protocol
    if args.search:
        qp["search"] = args.search
    if args.locale:
        qp["locale"] = args.locale

    services, _, err = api.list_network_services(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZTW network services: {err}")

    return shape_many([s.as_dict() for s in (services or [])], shape_service)
