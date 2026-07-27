"""ZDX historical (ended) alerts — agent-first v2 tool.

Mirrors v1's ``zscaler_mcp/tools/zdx/list_historical_alerts.py``:

    zdx_list_historical_alerts

Shares the alert scope filters and summary shaper with the ongoing-alerts module
(``list_alerts.py``); only the SDK endpoint (``list_historical``) differs.
"""

from __future__ import annotations

from typing import Any

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zdx._common import scope_query_params, unwrap_nested
from zscaler_mcp.tools.zdx.list_alerts import (
    _AlertScopeInput,
)


class ListHistoricalAlertsInput(_AlertScopeInput):
    """Inputs for listing historical (ended) ZDX alerts."""


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_alerts",
    input_model=ListHistoricalAlertsInput,
    is_list=True,
)
def zdx_list_historical_alerts(args: ListHistoricalAlertsInput) -> list[dict[str, Any]]:
    """List historical (ended) ZDX alerts.

    Read-only. Like `zdx_list_alerts` but for alert rules that have an Ended On
    date. `since` is in HOURS (default 2h, max 14 days = 336h).
    """
    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
        offset=args.offset,
        limit=args.limit,
    )
    result, _, err = client.zdx.alerts.list_historical(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX historical alerts: {err}")
    return shape_many(unwrap_nested(result, "alerts"))
