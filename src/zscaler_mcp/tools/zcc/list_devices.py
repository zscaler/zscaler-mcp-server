"""ZCC device enrollment — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zcc/list_devices.py`` but adds the v2 shaping
layer: the verbose SDK device record (~40 fields of enrollment/telemetry detail)
is curated down to the identifying + decision-bearing subset an admin actually
reasons about. See DESIGN.md §5.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListDevicesInput(BaseModel):
    """Inputs for listing ZCC enrolled devices."""

    username: Annotated[
        Optional[str],
        Field(default=None, description="Filter by username (e.g. 'jdoe@acme.com')."),
    ] = None
    os_type: Annotated[
        Optional[str],
        Field(default=None, description="OS filter: ios, android, windows, macos, linux."),
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=5000, description="Items per page (default 50, max 5000)."),
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zcc",
    toolset="zcc_devices",
    input_model=ListDevicesInput,
    is_list=True,
)
def zcc_list_devices(args: ListDevicesInput) -> list[dict[str, Any]]:
    """List ZCC enrolled devices (read-only).

    Each row is the full device record — identity, OS, agent version,
    registration state, assigned `policy_name`, ownership, hardware,
    VPN/tunnel state, and the enrollment / keep-alive timestamps. Use the
    returned `udid` with `zcc_get_device_otp`.
    """
    client = get_zscaler_client(service="zcc")

    qp: dict[str, Any] = {}
    if args.username:
        qp["username"] = args.username
    if args.os_type:
        qp["os_type"] = args.os_type
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size

    devices, _, err = client.zcc.devices.list_devices(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZCC devices: {err}")

    return shape_many([d.as_dict() for d in (devices or [])])
