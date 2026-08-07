"""ZTW network services (read-only).

Mirrors v1's ``network_services.py``. Backed by ``client.ztw.nw_service`` —
individual network service definitions (protocol + port ranges).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


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


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListNetworkServicesInput,
    is_list=True,
)
def ztw_list_network_services(args: ListNetworkServicesInput) -> list[dict[str, Any]]:
    """List ZTW network services.

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

    return shape_many([s.as_dict() for s in (services or [])])
