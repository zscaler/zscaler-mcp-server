"""Z-Insights firewall analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/firewall.py``. Read-only analytics over
the Z-Insights GraphQL API for Zero Trust Firewall traffic: grouped by action
(allow/block), by location, and by network service.

All three return a flat list of ``{id?, name, total}`` buckets, so they stay on
the default AUTO wire format (CSV) — the column header is stated once and each
bucket is one row.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zins._common import (
    TimeWindowInput,
    as_dicts,
    raise_for_graphql_errors,
    resolve_window,
)

# =============================================================================
# INPUT MODEL
# =============================================================================


class FirewallInput(TimeWindowInput):
    """Inputs for the firewall traffic breakdowns (7-day default window)."""

    limit: Annotated[
        int, Field(default=50, ge=1, le=1000, description="Max buckets to return.")
    ] = 50


# =============================================================================
# OUTPUT VIEW
# =============================================================================


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zins",
    toolset="zins_firewall",
    input_model=FirewallInput,
    is_list=True,
)
def zins_get_firewall_by_action(args: FirewallInput) -> list[dict[str, Any]]:
    """Get Zero Trust Firewall traffic grouped by action (allow/block). Read-only analytics.

    One row per action with its aggregated total — the allowed-vs-blocked
    split. Window must be a 7- or 14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.firewall.get_traffic_by_action(
        start_time=start_ms, end_time=end_ms, limit=args.limit
    )
    if err:
        raise RuntimeError(f"Failed to get firewall traffic by action: {err}")
    raise_for_graphql_errors(response, "get_traffic_by_action")

    return shape_many(as_dicts(entries))


@tool(
    action=READ,
    service="zins",
    toolset="zins_firewall",
    input_model=FirewallInput,
    is_list=True,
)
def zins_get_firewall_by_location(args: FirewallInput) -> list[dict[str, Any]]:
    """Get Zero Trust Firewall traffic grouped by location. Read-only analytics.

    One id/name/total row per location, for ranking which sites drive the most
    firewall traffic. Window must be a 7- or 14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.firewall.get_traffic_by_location(
        start_time=start_ms, end_time=end_ms, limit=args.limit
    )
    if err:
        raise RuntimeError(f"Failed to get firewall traffic by location: {err}")
    raise_for_graphql_errors(response, "get_traffic_by_location")

    return shape_many(as_dicts(entries))


@tool(
    action=READ,
    service="zins",
    toolset="zins_firewall",
    input_model=FirewallInput,
    is_list=True,
)
def zins_get_firewall_network_services(args: FirewallInput) -> list[dict[str, Any]]:
    """Get Zero Trust Firewall traffic grouped by network service. Read-only analytics.

    One row per network service (protocol/port) with its aggregated total.
    Window must be a 7- or 14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.firewall.get_network_services(
        start_time=start_ms, end_time=end_ms, limit=args.limit
    )
    if err:
        raise RuntimeError(f"Failed to get firewall network services: {err}")
    raise_for_graphql_errors(response, "get_network_services")

    return shape_many(as_dicts(entries))
