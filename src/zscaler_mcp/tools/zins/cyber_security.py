"""Z-Insights cyber-security analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/cyber_security.py``. Read-only analytics
over the Z-Insights GraphQL API for security incidents: grouped by category,
grouped by location/dimension, daily trend, and the threat-category × app
correlation.

All four are backed by the same SDK surface (``client.zins.cyber_security``).
Three of them produce nested or time-series data (category buckets that may
carry sub-buckets, daily series, threat×app correlation), so they use JSON
wire format and surface the breakdown under a nested ``entries`` field. The
by-location report is a flat id/name/total list and stays AUTO (CSV).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zins._common import (
    VALID_INCIDENTS_CATEGORIZE_BY,
    VALID_INCIDENTS_CATEGORIZE_BY_WITH_ID,
    TimeWindowInput,
    as_dicts,
    raise_for_graphql_errors,
    resolve_window,
)

# =============================================================================
# INPUT MODELS
# =============================================================================
# Cyber-incident reports default to a 14-day interval (start 16, end 2).


class _IncidentWindowInput(TimeWindowInput):
    """Cyber-incident window defaults: 14-day interval (start 16, end 2)."""

    start_days_ago: Annotated[
        int,
        Field(
            default=16,
            ge=1,
            description=(
                "Days ago for the window start. Default 16, which with "
                "end_days_ago=2 yields a 14-day interval. Use 9 for a 7-day "
                "interval. Only 7- or 14-day intervals are accepted."
            ),
        ),
    ] = 16


class CyberIncidentsInput(_IncidentWindowInput):
    """Inputs for incidents grouped by one or more categories."""

    categorize_by: Annotated[
        Optional[list[str]],
        Field(
            default=None,
            description=(
                "Categories to group incidents by (default ['THREAT_CATEGORY_ID']). "
                f"Values: {', '.join(VALID_INCIDENTS_CATEGORIZE_BY)}."
            ),
        ),
    ] = None
    limit: Annotated[
        int, Field(default=50, ge=1, le=1000, description="Max incident rows to return.")
    ] = 50


class CyberIncidentsByLocationInput(_IncidentWindowInput):
    """Inputs for incidents grouped by location (or another id-bearing dimension)."""

    categorize_by: Annotated[
        str,
        Field(
            default="LOCATION_ID",
            description=(
                "Dimension to group by (default LOCATION_ID). "
                f"Values: {', '.join(VALID_INCIDENTS_CATEGORIZE_BY_WITH_ID)}."
            ),
        ),
    ] = "LOCATION_ID"
    limit: Annotated[int, Field(default=50, ge=1, le=1000, description="Max rows to return.")] = 50


class CyberIncidentsTrendInput(_IncidentWindowInput):
    """Inputs for the daily incident trend / threat×app correlation."""

    limit: Annotated[int, Field(default=50, ge=1, le=1000, description="Max rows to return.")] = 50


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zins",
    toolset="zins_cyber_security",
    input_model=CyberIncidentsInput,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zins_get_cyber_incidents(args: CyberIncidentsInput) -> list[dict[str, Any]]:
    """Get cyber-security incidents grouped by category. Read-only analytics.

    Groups incidents by one or more dimensions (default THREAT_CATEGORY_ID);
    multi-dimension groupings surface their breakdown under nested `entries`.
    An empty result means no incidents were detected. Window must be a 7- or
    14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    categorize_by = args.categorize_by or ["THREAT_CATEGORY_ID"]
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.cyber_security.get_incidents(
        start_time=start_ms,
        end_time=end_ms,
        categorize_by=categorize_by,
        limit=args.limit,
    )
    if err:
        raise RuntimeError(f"Failed to get cyber incidents: {err}")
    raise_for_graphql_errors(response, "get_incidents")

    return shape_many(as_dicts(entries))


@tool(
    action=READ,
    service="zins",
    toolset="zins_cyber_security",
    input_model=CyberIncidentsByLocationInput,
    is_list=True,
)
def zins_get_cyber_incidents_by_location(
    args: CyberIncidentsByLocationInput,
) -> list[dict[str, Any]]:
    """Get cyber-security incidents grouped by location (or app/user/department). Read-only analytics.

    One id/name/total row per location (or the chosen id-bearing dimension),
    useful for ranking which sites carry the most incidents. Window must be a
    7- or 14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.cyber_security.get_incidents_by_location(
        start_time=start_ms,
        end_time=end_ms,
        categorize_by=args.categorize_by,
        limit=args.limit,
    )
    if err:
        raise RuntimeError(f"Failed to get cyber incidents by location: {err}")
    raise_for_graphql_errors(response, "get_incidents_by_location")

    return shape_many(as_dicts(entries))


@tool(
    action=READ,
    service="zins",
    toolset="zins_cyber_security",
    input_model=CyberIncidentsTrendInput,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zins_get_cyber_incidents_daily(args: CyberIncidentsTrendInput) -> list[dict[str, Any]]:
    """Get the daily cyber-security incident trend over time. Read-only analytics.

    Groups incidents by day (categorize_by=TIME) so you can spot spikes across
    the window. Window must be a 7- or 14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.cyber_security.get_incidents(
        start_time=start_ms,
        end_time=end_ms,
        categorize_by=["TIME"],
        limit=args.limit,
    )
    if err:
        raise RuntimeError(f"Failed to get daily cyber incidents: {err}")
    raise_for_graphql_errors(response, "get_incidents_daily")

    return shape_many(as_dicts(entries))


@tool(
    action=READ,
    service="zins",
    toolset="zins_cyber_security",
    input_model=CyberIncidentsTrendInput,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zins_get_cyber_incidents_by_threat_and_app(
    args: CyberIncidentsTrendInput,
) -> list[dict[str, Any]]:
    """Get cyber-security incidents correlated by threat category and application. Read-only analytics.

    Groups by THREAT_CATEGORY_ID × APP_ID so each top-level threat-category
    bucket carries its per-application breakdown under nested `entries` —
    useful for finding the most-targeted apps. Window must be a 7- or 14-day
    historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.cyber_security.get_incidents(
        start_time=start_ms,
        end_time=end_ms,
        categorize_by=["THREAT_CATEGORY_ID", "APP_ID"],
        limit=args.limit,
    )
    if err:
        raise RuntimeError(f"Failed to get cyber incidents by threat and app: {err}")
    raise_for_graphql_errors(response, "get_incidents_by_threat_and_app")

    return shape_many(as_dicts(entries))
