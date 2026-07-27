"""ZDX device cloud-path probes — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/device_cloudpath_probes.py``:

    zdx_list_cloudpath_probes

Returns the cloud-path-probe rows for a device+app. The returned ``id`` is the
``cloudpath_probe_id`` you feed into ``zdx_start_deeptrace``.
"""

from __future__ import annotations

from typing import Any

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zdx._common import ProbeInput


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_troubleshooting",
    input_model=ProbeInput,
    is_list=True,
)
def zdx_list_cloudpath_probes(args: ProbeInput) -> list[dict[str, Any]]:
    """List cloud-path probes for an app on a ZDX device (full records).

    Read-only. Call this BEFORE `zdx_start_deeptrace` to obtain the
    `cloudpath_probe_id` the deep-trace payload needs.
    """
    if not args.device_id or not args.app_id:
        raise ValueError("device_id and app_id are required")
    client = get_zscaler_client(service="zdx")
    qp: dict[str, Any] = {}
    if args.since is not None:
        qp["since"] = args.since
    result, _, err = client.zdx.devices.list_cloudpath_probes(
        args.device_id, args.app_id, query_params=qp
    )
    if err:
        raise RuntimeError(f"Failed to list ZDX cloud-path probes: {err}")
    raw = [item.as_dict() if hasattr(item, "as_dict") else item for item in (result or [])]
    return shape_many(raw)
