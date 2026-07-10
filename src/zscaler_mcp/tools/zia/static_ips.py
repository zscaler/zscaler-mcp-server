"""ZIA static IPs — list, get, create, update, delete.

Mirrors v1's ``client.zia.traffic_static_ip`` SDK calls. Static IPs are a
traffic-forwarding prerequisite for locations/GRE. Writes are staged until
``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on IP/comment.")
    ] = None


class GetInput(BaseModel):
    static_ip_id: Annotated[str, Field(description="Static IP ID (string, even if numeric).")]


class CreateInput(BaseModel):
    ip_address: Annotated[str, Field(description="The static IP address.")]
    comment: Annotated[Optional[str], Field(default=None, description="Admin notes.")] = None
    geo_override: Annotated[
        Optional[bool], Field(default=None, description="Override geolocation with lat/long.")
    ] = None
    routable_ip: Annotated[Optional[bool], Field(default=None, description="Routable IP flag.")] = (
        None
    )
    latitude: Annotated[
        Optional[float], Field(default=None, description="Latitude (geo override).")
    ] = None
    longitude: Annotated[
        Optional[float], Field(default=None, description="Longitude (geo override).")
    ] = None


class UpdateInput(BaseModel):
    static_ip_id: Annotated[str, Field(description="Static IP ID to update.")]
    comment: Annotated[Optional[str], Field(default=None, description="Admin notes.")] = None
    geo_override: Annotated[
        Optional[bool], Field(default=None, description="Geo override flag.")
    ] = None
    routable_ip: Annotated[Optional[bool], Field(default=None, description="Routable IP flag.")] = (
        None
    )
    latitude: Annotated[Optional[float], Field(default=None, description="Latitude.")] = None
    longitude: Annotated[Optional[float], Field(default=None, description="Longitude.")] = None


class DeleteInput(BaseModel):
    static_ip_id: Annotated[str, Field(description="Static IP ID to delete.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class StaticIpSummary(AgentView):
    id: str = Field(description="Static IP ID. Use in location/GRE payloads.")
    ip_address: Optional[str] = Field(default=None, description="The static IP address.")
    comment: Optional[str] = Field(default=None, description="Admin notes.")
    routable_ip: Optional[bool] = Field(default=None, description="Routable IP flag.")
    geo_override: Optional[bool] = Field(default=None, description="Geo override flag.")


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# SHAPERS
# =============================================================================


def shape_summary(raw: dict[str, Any]) -> StaticIpSummary:
    return StaticIpSummary(
        id=str(pick(raw, "id", default="")),
        ip_address=pick(raw, "ip_address", "ipAddress"),
        comment=pick(raw, "comment"),
        routable_ip=pick(raw, "routable_ip", "routableIP"),
        geo_override=pick(raw, "geo_override", "geoOverride"),
    )


def _optional_kwargs(args: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in ("comment", "geo_override", "routable_ip", "latitude", "longitude"):
        v = getattr(args, k, None)
        if v is not None:
            out[k] = v
    return out


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=ListInput,
    output_view=StaticIpSummary,
    is_list=True,
)
def zia_list_static_ips(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA static IPs as curated summaries."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    ips, _, err = client.zia.traffic_static_ip.list_static_ips(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list static IPs: {err}")
    return shape_many([i.as_dict() for i in (ips or [])], shape_summary)


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GetInput,
    output_view=StaticIpSummary,
    is_list=False,
)
def zia_get_static_ip(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA static IP by ID."""
    client = get_zscaler_client(service="zia")
    ip, _, err = client.zia.traffic_static_ip.get_static_ip(args.static_ip_id)
    if err:
        raise RuntimeError(f"Failed to get static IP {args.static_ip_id}: {err}")
    return shape_summary(ip.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_locations",
    input_model=CreateInput,
    output_view=StaticIpSummary,
    is_list=False,
)
def zia_create_static_ip(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA static IP (write). Activate after."""
    client = get_zscaler_client(service="zia")
    ip, _, err = client.zia.traffic_static_ip.add_static_ip(
        ip_address=args.ip_address, **_optional_kwargs(args)
    )
    if err:
        raise RuntimeError(f"Failed to create static IP: {err}")
    return shape_summary(ip.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_locations",
    input_model=UpdateInput,
    output_view=StaticIpSummary,
    is_list=False,
)
def zia_update_static_ip(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA static IP (write). Activate after."""
    client = get_zscaler_client(service="zia")
    ip, _, err = client.zia.traffic_static_ip.update_static_ip(
        args.static_ip_id, **_optional_kwargs(args)
    )
    if err:
        raise RuntimeError(f"Failed to update static IP {args.static_ip_id}: {err}")
    return shape_summary(ip.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_locations",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_static_ip(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA static IP (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.traffic_static_ip.delete_static_ip(args.static_ip_id)
    if err:
        raise RuntimeError(f"Failed to delete static IP {args.static_ip_id}: {err}")
    return OperationResult(
        success=True, message=f"Static IP {args.static_ip_id} deleted successfully."
    ).model_dump()
