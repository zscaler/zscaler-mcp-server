"""Z-Insights Shadow IT analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/shadow_it.py``. Read-only analytics over
the Z-Insights GraphQL API for discovered Shadow IT applications and the
aggregate Shadow IT summary.

- ``zins_get_shadow_it_apps`` returns one row per discovered app
  (name, category, risk, sanctioned state, data volume, user count). The row is
  flat, so it stays AUTO (CSV).
- ``zins_get_shadow_it_summary`` is a single dashboard object with grouped
  breakdowns (by category, by risk index, …) — nested, so it is forced to JSON
  and returns one object (is_list=False).
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one
from zscaler_mcp.tools.zins._common import (
    TimeWindowInput,
    as_dicts,
    raise_for_graphql_errors,
    resolve_window,
)

# =============================================================================
# INPUT MODELS
# =============================================================================


class ShadowItAppsInput(TimeWindowInput):
    """Inputs for the discovered Shadow IT applications list (7-day default window)."""

    limit: Annotated[
        int, Field(default=50, ge=1, le=1000, description="Max application rows to return.")
    ] = 50


class ShadowItSummaryInput(TimeWindowInput):
    """Inputs for the Shadow IT summary (14-day default window)."""

    start_days_ago: Annotated[
        int,
        Field(
            default=16,
            ge=1,
            description=(
                "Days ago for the window start. Default 16 (14-day interval with "
                "end_days_ago=2). Use 9 for a 7-day interval. Only 7- or 14-day "
                "intervals are accepted."
            ),
        ),
    ] = 16


# =============================================================================
# OUTPUT VIEWS
# =============================================================================








# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zins",
    toolset="zins_shadow_it",
    input_model=ShadowItAppsInput,
    is_list=True,
)
def zins_get_shadow_it_apps(args: ShadowItAppsInput) -> list[dict[str, Any]]:
    """Get discovered Shadow IT applications with risk and usage detail. Read-only analytics.

    One row per unsanctioned/discovered app: category, risk index, sanctioned
    state, data volume, and user count. An empty result means no shadow apps
    were detected. Window must be a 7- or 14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.shadow_it.get_apps(
        start_time=start_ms, end_time=end_ms, limit=args.limit
    )
    if err:
        raise RuntimeError(f"Failed to get shadow IT apps: {err}")
    raise_for_graphql_errors(response, "get_apps")

    return shape_many(as_dicts(entries))


@tool(
    action=READ,
    service="zins",
    toolset="zins_shadow_it",
    input_model=ShadowItSummaryInput,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zins_get_shadow_it_summary(args: ShadowItSummaryInput) -> dict[str, Any]:
    """Get the aggregate Shadow IT summary dashboard. Read-only analytics.

    A single object with org-wide totals (apps, bytes, upload/download) plus
    breakdowns grouped by category and by risk index. Window must be a 7- or
    14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    summary, response, err = client.zins.shadow_it.get_shadow_it_summary(
        start_time=start_ms, end_time=end_ms
    )
    if err:
        raise RuntimeError(f"Failed to get shadow IT summary: {err}")
    raise_for_graphql_errors(response, "get_shadow_it_summary")

    raw = summary.as_dict() if hasattr(summary, "as_dict") else (summary or {})
    if not isinstance(raw, dict):
        raw = {}
    return shape_one(raw)
