"""Z-Insights IoT analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/iot.py``. Read-only analytics over the
Z-Insights GraphQL API for IoT Device Visibility.

``zins_get_iot_device_stats`` returns a single current-state object: top-level
device counts plus a nested list of per-classification entries. There is no
time window — IoT stats reflect the present state, not a historical interval.
Because the object nests the classification list, it is forced to JSON and
returns one object (is_list=False).
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_one
from zscaler_mcp.tools.zins._common import raise_for_graphql_errors

# =============================================================================
# INPUT MODEL
# =============================================================================


class IotDeviceStatsInput(BaseModel):
    """Inputs for IoT device statistics (no time window — current state)."""

    limit: Annotated[
        int,
        Field(
            default=50,
            ge=1,
            le=1000,
            description="Max device-classification entries to return.",
        ),
    ] = 50


# =============================================================================
# OUTPUT VIEW
# =============================================================================


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zins",
    toolset="zins_iot",
    input_model=IotDeviceStatsInput,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zins_get_iot_device_stats(args: IotDeviceStatsInput) -> dict[str, Any]:
    """Get IoT device statistics and classifications. Read-only analytics.

    A single current-state object: total/IoT/user/server/unclassified device
    counts plus a per-classification breakdown under `entries`. No time window —
    this reflects the present network state. An empty/zeroed result means no IoT
    devices were detected or IoT Device Visibility is not enabled.
    """
    client = get_zscaler_client(service="zins")

    stats, response, err = client.zins.iot.get_device_stats(limit=args.limit)
    if err:
        raise RuntimeError(f"Failed to get IoT device stats: {err}")
    raise_for_graphql_errors(response, "get_device_stats")

    raw = stats.as_dict() if hasattr(stats, "as_dict") else (stats or {})
    if not isinstance(raw, dict):
        raw = {}
    return shape_one(raw)
