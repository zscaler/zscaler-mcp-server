"""ZCell Sim Analytics — agent-first v2 read tools.

Read-only analytics over ``client.zcell.sim_analytics``:

    * zcell_list_sim_analytics_map     — dashboard lat/lng points for SIMs
    * zcell_list_sim_analytics_summary — SIM status counts (total/active/…)
    * zcell_list_sim_usage_by_country  — top countries by data usage
    * zcell_list_sim_usage_by_day      — data usage per day in the window
    * zcell_list_sim_usage_by_sim      — top SIMs by data usage

The usage endpoints require an epoch-seconds window; the shared
:class:`WindowInput` ``days`` shorthand fills it server-side.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zcell._common import WindowInput, as_dicts

# =============================================================================
# INPUT MODELS
# =============================================================================


class SimAnalyticsMapInput(BaseModel):
    """Inputs for the SIM analytics map (dashboard lat/lng points)."""

    icc_ids: Annotated[
        Optional[list[str]],
        Field(default=None, description="Optional list of ICCIDs to scope the map to."),
    ] = None


class SimAnalyticsSummaryInput(BaseModel):
    """Inputs for the SIM status summary (no parameters)."""


class UsageCountriesInput(WindowInput):
    """Inputs for top-countries-by-usage (time-bounded)."""

    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=20, description="Max countries (<= 20).")
    ] = None


class UsageDayInput(WindowInput):
    """Inputs for usage-per-day (time-bounded)."""

    icc_id: Annotated[
        Optional[str], Field(default=None, description="Optional ICCID to scope the usage to.")
    ] = None


class UsageSimsInput(WindowInput):
    """Inputs for top-SIMs-by-usage (time-bounded)."""

    limit: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Max SIMs to return.")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class SimMapPoint(AgentView):
    """A dashboard map point: SIM identifiers + coordinates + tags (nested → JSON)."""

    iccid: list[str] = Field(default_factory=list, description="ICCID(s) at this point.")
    imsi: list[str] = Field(default_factory=list, description="IMSI(s) at this point.")
    lat: Optional[Any] = Field(default=None, description="Latitude.")
    lng: Optional[Any] = Field(default=None, description="Longitude.")
    tags: list[str] = Field(default_factory=list, description="Tags associated with the SIM(s).")


class SimStatusSummary(AgentView):
    """SIM status counts for the tenant."""

    total: Optional[Any] = Field(default=None, description="Total SIMs.")
    used: Optional[Any] = Field(default=None, description="SIMs that have been used.")
    active: Optional[Any] = Field(default=None, description="Active SIMs.")
    inactive: Optional[Any] = Field(default=None, description="Inactive SIMs.")


class CountryUsage(AgentView):
    """Data usage for one country."""

    country: Optional[str] = Field(default=None, description="Country name/code.")
    usage: Optional[Any] = Field(default=None, description="Data usage attributed to the country.")


class DayUsage(AgentView):
    """Data usage for one day in the window."""

    creation_time: Optional[Any] = Field(
        default=None, description="Day / timestamp of the usage bucket."
    )
    usage: Optional[Any] = Field(default=None, description="Data usage for the day.")


class SimUsage(AgentView):
    """Data usage for one SIM."""

    iccid: Optional[str] = Field(default=None, description="ICCID of the SIM.")
    usage: Optional[Any] = Field(default=None, description="Data usage attributed to the SIM.")


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_map(raw: dict[str, Any]) -> SimMapPoint:
    return SimMapPoint(
        iccid=pick(raw, "iccid", default=[]) or [],
        imsi=pick(raw, "imsi", default=[]) or [],
        lat=pick(raw, "lat"),
        lng=pick(raw, "lng"),
        tags=pick(raw, "tags", default=[]) or [],
    )


def _shape_summary(raw: dict[str, Any]) -> SimStatusSummary:
    return SimStatusSummary(
        total=pick(raw, "total"),
        used=pick(raw, "used"),
        active=pick(raw, "active"),
        inactive=pick(raw, "inactive"),
    )


def _shape_country(raw: dict[str, Any]) -> CountryUsage:
    return CountryUsage(country=pick(raw, "country"), usage=pick(raw, "usage"))


def _shape_day(raw: dict[str, Any]) -> DayUsage:
    return DayUsage(
        creation_time=pick(raw, "creation_time", "creationTime"), usage=pick(raw, "usage")
    )


def _shape_sim(raw: dict[str, Any]) -> SimUsage:
    return SimUsage(iccid=pick(raw, "iccid"), usage=pick(raw, "usage"))


def _query(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in pairs if value is not None}


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_analytics",
    input_model=SimAnalyticsMapInput,
    output_view=SimMapPoint,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zcell_list_sim_analytics_map(args: SimAnalyticsMapInput) -> list[dict[str, Any]]:
    """List Zscaler Cellular SIM map points (dashboard lat/lng summary).

    Read-only. Returns SIM location points with their ICCIDs, IMSIs, and tags —
    the data that backs the fleet map. Optionally scope to specific ICCIDs.
    """
    client = get_zscaler_client(service="zcell")

    body: dict[str, Any] = {}
    if args.icc_ids:
        body["iccIds"] = args.icc_ids

    points, _, err = client.zcell.sim_analytics.list_sim_analytics_map(**body)
    if err:
        raise RuntimeError(f"Failed to list SIM analytics map: {err}")
    return shape_many(as_dicts(points), _shape_map)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_analytics",
    input_model=SimAnalyticsSummaryInput,
    output_view=SimStatusSummary,
    is_list=True,
)
def zcell_list_sim_analytics_summary(args: SimAnalyticsSummaryInput) -> list[dict[str, Any]]:
    """List the Zscaler Cellular SIM status summary (total/used/active/inactive).

    Read-only. Returns the SIM-count breakdown for the tenant.
    """
    client = get_zscaler_client(service="zcell")

    summary, _, err = client.zcell.sim_analytics.list_sim_analytics_summary()
    if err:
        raise RuntimeError(f"Failed to list SIM analytics summary: {err}")
    return shape_many(as_dicts(summary), _shape_summary)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_analytics",
    input_model=UsageCountriesInput,
    output_view=CountryUsage,
    is_list=True,
)
def zcell_list_sim_usage_by_country(args: UsageCountriesInput) -> list[dict[str, Any]]:
    """List Zscaler Cellular data usage grouped by country (top countries).

    Read-only. Returns the top countries by data usage over a `days` lookback
    window.
    """
    client = get_zscaler_client(service="zcell")

    usage, _, err = client.zcell.sim_analytics.list_sim_analytics_usage_countries(
        days=args.days, query_params=_query(("limit", args.limit))
    )
    if err:
        raise RuntimeError(f"Failed to list SIM usage by country: {err}")
    return shape_many(as_dicts(usage), _shape_country)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_analytics",
    input_model=UsageDayInput,
    output_view=DayUsage,
    is_list=True,
)
def zcell_list_sim_usage_by_day(args: UsageDayInput) -> list[dict[str, Any]]:
    """List Zscaler Cellular data usage per day over the window.

    Read-only. Returns one usage bucket per day over a `days` lookback window,
    optionally scoped to a single ICCID.
    """
    client = get_zscaler_client(service="zcell")

    usage, _, err = client.zcell.sim_analytics.list_sim_analytics_usage_day(
        days=args.days, query_params=_query(("icc_id", args.icc_id))
    )
    if err:
        raise RuntimeError(f"Failed to list SIM usage by day: {err}")
    return shape_many(as_dicts(usage), _shape_day)


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_analytics",
    input_model=UsageSimsInput,
    output_view=SimUsage,
    is_list=True,
)
def zcell_list_sim_usage_by_sim(args: UsageSimsInput) -> list[dict[str, Any]]:
    """List Zscaler Cellular data usage grouped by SIM (top SIMs).

    Read-only. Returns the top SIMs by data usage over a `days` lookback window.
    """
    client = get_zscaler_client(service="zcell")

    usage, _, err = client.zcell.sim_analytics.list_sim_analytics_usage_sims(
        days=args.days, query_params=_query(("limit", args.limit))
    )
    if err:
        raise RuntimeError(f"Failed to list SIM usage by SIM: {err}")
    return shape_many(as_dicts(usage), _shape_sim)
