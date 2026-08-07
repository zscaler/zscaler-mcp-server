"""ZIA GRE tunnels — list, get, create, delete.

Mirrors v1's ``gre_tunnels.py``. Tunnel create/delete also touches
``client.zia.traffic_static_ip`` (a tunnel needs a backing static IP). Writes are
staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one


class ListTunnelsInput(BaseModel):
    pass


class GetTunnelInput(BaseModel):
    tunnel_id: Annotated[str, Field(description="GRE tunnel ID (string, even if numeric).")]


class CreateTunnelInput(BaseModel):
    static_ip_address: Annotated[
        str, Field(description="Static IP to associate or create for the tunnel source.")
    ]
    ip_unnumbered: Annotated[
        Optional[bool],
        Field(default=None, description="True = unnumbered; False = auto-pick a GRE IP range."),
    ] = None
    internal_ip_range: Annotated[
        Optional[str], Field(default=None, description="Internal IP range (numbered tunnels).")
    ] = None
    comment: Annotated[Optional[str], Field(default=None, description="Admin notes.")] = None


class DeleteTunnelInput(BaseModel):
    tunnel_id: Annotated[str, Field(description="GRE tunnel ID to delete.")]
    static_ip_id: Annotated[
        str, Field(description="Backing static IP ID; deleted after the tunnel.")
    ]


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=ListTunnelsInput,
    is_list=True,
)
def zia_list_gre_tunnels(args: ListTunnelsInput) -> list[dict[str, Any]]:
    """List ZIA GRE tunnels."""
    client = get_zscaler_client(service="zia")
    tunnels, _, err = client.zia.gre_tunnel.list_gre_tunnels()
    if err:
        raise RuntimeError(f"Failed to list GRE tunnels: {err}")
    return shape_many([t.as_dict() for t in (tunnels or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GetTunnelInput,
    is_list=False,
)
def zia_get_gre_tunnel(args: GetTunnelInput) -> dict[str, Any]:
    """Get a single ZIA GRE tunnel by ID."""
    client = get_zscaler_client(service="zia")
    tunnel, _, err = client.zia.gre_tunnel.get_gre_tunnel(args.tunnel_id)
    if err:
        raise RuntimeError(f"Failed to get GRE tunnel {args.tunnel_id}: {err}")
    return shape_one(tunnel.as_dict())


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_locations",
    input_model=CreateTunnelInput,
    is_list=False,
)
def zia_create_gre_tunnel(args: CreateTunnelInput) -> dict[str, Any]:
    """Create a ZIA GRE tunnel (write). Finds/creates the backing static IP first. Activate after."""
    client = get_zscaler_client(service="zia")
    gre_api = client.zia.gre_tunnel
    ip_api = client.zia.traffic_static_ip

    existing, _, err = ip_api.list_static_ips(query_params={"ip_address": args.static_ip_address})
    if err:
        raise RuntimeError(f"Failed to search static IP: {err}")
    if existing:
        static_ip = existing[0]
    else:
        static_ip, _, err = ip_api.add_static_ip(
            ip_address=args.static_ip_address, comment=args.comment
        )
        if err:
            raise RuntimeError(f"Failed to create static IP: {err}")

    payload: dict[str, Any] = {
        "source_ip": static_ip.ip_address,
        "ip_unnumbered": args.ip_unnumbered,
        "internal_ip_range": args.internal_ip_range,
        "comment": args.comment,
    }
    if not args.ip_unnumbered:
        ranges, _, err = gre_api.list_gre_ranges(query_params={"static_ip": static_ip.ip_address})
        if err:
            raise RuntimeError(f"Failed to fetch GRE ranges: {err}")
        if not ranges or "startIPAddress" not in ranges[0]:
            raise RuntimeError("No valid GRE internal IP ranges found.")
        payload["internal_ip_range"] = ranges[0]["startIPAddress"]

    tunnel, _, err = gre_api.add_gre_tunnel(**payload)
    if err:
        raise RuntimeError(f"Failed to create GRE tunnel: {err}")
    return shape_one(tunnel.as_dict())


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_locations",
    input_model=DeleteTunnelInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_gre_tunnel(args: DeleteTunnelInput) -> dict[str, Any]:
    """Delete a ZIA GRE tunnel and its backing static IP (destructive). Activate after.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.gre_tunnel.delete_gre_tunnel(args.tunnel_id)
    if err:
        raise RuntimeError(f"Failed to delete GRE tunnel {args.tunnel_id}: {err}")
    _, _, err = client.zia.traffic_static_ip.delete_static_ip(args.static_ip_id)
    if err:
        raise RuntimeError(f"Failed to delete static IP {args.static_ip_id}: {err}")
    return OperationResult(
        success=True,
        message=f"GRE tunnel {args.tunnel_id} and static IP {args.static_ip_id} deleted.",
    ).model_dump()
