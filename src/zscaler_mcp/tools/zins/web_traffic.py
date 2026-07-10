"""Z-Insights web-traffic analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/web_traffic.py``. Read-only analytics over
the Z-Insights GraphQL API: traffic by location, total traffic, protocol mix,
and threat super-category / threat-class breakdowns.

These are aggregated/grouped reports, not CRUD objects. Each curated row carries
the meaningful summary fields (name/id + the aggregated total) and, when the
caller asks for trend data, the time-series under a nested ``trend`` field —
which is why the trend-capable tools are forced to JSON wire format.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zins._common import (
    VALID_ACTION_FILTERS,
    VALID_DLP_ENGINE_FILTERS,
    VALID_TRAFFIC_UNITS,
    VALID_TREND_INTERVALS,
    TimeWindowInput,
    as_dicts,
    raise_for_graphql_errors,
    resolve_window,
)

# =============================================================================
# INPUT MODELS
# =============================================================================


class WebTrafficByLocationInput(TimeWindowInput):
    """Inputs for web traffic grouped by location."""

    traffic_unit: Annotated[
        str,
        Field(
            default="TRANSACTIONS",
            description=f"Measurement unit. One of: {', '.join(VALID_TRAFFIC_UNITS)}.",
        ),
    ] = "TRANSACTIONS"
    include_trend: Annotated[
        bool,
        Field(default=False, description="Include per-location time-series trend data."),
    ] = False
    trend_interval: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                f"Trend granularity (only with include_trend=True). One of: "
                f"{', '.join(VALID_TREND_INTERVALS)}."
            ),
        ),
    ] = None
    limit: Annotated[
        int, Field(default=50, ge=1, le=1000, description="Max location rows to return.")
    ] = 50


class WebTrafficNoGroupingInput(TimeWindowInput):
    """Inputs for total (ungrouped) web traffic."""

    traffic_unit: Annotated[
        str,
        Field(
            default="TRANSACTIONS",
            description=f"Measurement unit. One of: {', '.join(VALID_TRAFFIC_UNITS)}.",
        ),
    ] = "TRANSACTIONS"
    dlp_engine_filter: Annotated[
        Optional[str],
        Field(
            default=None,
            description=f"Filter by DLP engine. One of: {', '.join(VALID_DLP_ENGINE_FILTERS)}.",
        ),
    ] = None
    action_filter: Annotated[
        Optional[str],
        Field(
            default=None,
            description=f"Filter by action taken. One of: {', '.join(VALID_ACTION_FILTERS)}.",
        ),
    ] = None
    include_trend: Annotated[
        bool,
        Field(default=False, description="Include overall time-series trend data."),
    ] = False
    trend_interval: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                f"Trend granularity (only with include_trend=True). One of: "
                f"{', '.join(VALID_TREND_INTERVALS)}."
            ),
        ),
    ] = None
    limit: Annotated[int, Field(default=50, ge=1, le=1000, description="Max rows to return.")] = 50


class TrafficCategoryInput(TimeWindowInput):
    """Inputs for the protocol / threat-category / threat-class breakdowns."""

    traffic_unit: Annotated[
        str,
        Field(
            default="TRANSACTIONS",
            description=f"Measurement unit. One of: {', '.join(VALID_TRAFFIC_UNITS)}.",
        ),
    ] = "TRANSACTIONS"
    limit: Annotated[
        int, Field(default=50, ge=1, le=1000, description="Max category rows to return.")
    ] = 50


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class TrafficRow(AgentView):
    """A single aggregated traffic bucket (flat → CSV-friendly)."""

    name: Optional[str] = Field(
        default=None, description="Bucket label (location / protocol / category name)."
    )
    id: Optional[str] = Field(
        default=None, description="Bucket identifier, when the API returns one."
    )
    total: Optional[float] = Field(
        default=None, description="Aggregated total (transactions or bytes) for this bucket."
    )


class TrafficTrendRow(AgentView):
    """An aggregated traffic bucket plus its optional time-series trend (nested → JSON)."""

    name: Optional[str] = Field(
        default=None, description="Bucket label (location name, or 'overall' when ungrouped)."
    )
    id: Optional[str] = Field(
        default=None, description="Bucket identifier, when the API returns one."
    )
    total: Optional[float] = Field(
        default=None, description="Aggregated total (transactions or bytes) for this bucket."
    )
    trend: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Time-series points for this bucket when include_trend=True; else empty.",
    )


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_row(raw: dict[str, Any]) -> TrafficRow:
    return TrafficRow(
        name=pick(raw, "name", "label", "key"),
        id=_as_opt_str(pick(raw, "id")),
        total=_as_opt_float(pick(raw, "total", "count", "value")),
    )


def _shape_trend_row(raw: dict[str, Any]) -> TrafficTrendRow:
    trend = raw.get("trend") or raw.get("trends") or raw.get("series") or []
    return TrafficTrendRow(
        name=pick(raw, "name", "label", "key"),
        id=_as_opt_str(pick(raw, "id")),
        total=_as_opt_float(pick(raw, "total", "count", "value")),
        trend=list(trend) if isinstance(trend, list) else [],
    )


def _as_opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _as_opt_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zins",
    toolset="zins_web_traffic",
    input_model=WebTrafficByLocationInput,
    output_view=TrafficTrendRow,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zins_get_web_traffic_by_location(args: WebTrafficByLocationInput) -> list[dict[str, Any]]:
    """Get web traffic aggregated per location. Read-only analytics.

    Each row is a location with its total transactions or bytes; pass
    `include_trend=True` for the per-location time-series under `trend`. Window
    must be a 7- or 14-day historical interval (see the time-window inputs).
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    kwargs: dict[str, Any] = {
        "start_time": start_ms,
        "end_time": end_ms,
        "traffic_unit": args.traffic_unit,
        "limit": args.limit,
    }
    if args.include_trend:
        kwargs["include_trend"] = True
    if args.trend_interval:
        kwargs["trend_interval"] = args.trend_interval

    entries, response, err = client.zins.web_traffic.get_traffic_by_location(**kwargs)
    if err:
        raise RuntimeError(f"Failed to get web traffic by location: {err}")
    raise_for_graphql_errors(response, "get_traffic_by_location")

    return shape_many(as_dicts(entries), _shape_trend_row)


@tool(
    action=READ,
    service="zins",
    toolset="zins_web_traffic",
    input_model=WebTrafficNoGroupingInput,
    output_view=TrafficTrendRow,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zins_get_web_traffic_no_grouping(args: WebTrafficNoGroupingInput) -> list[dict[str, Any]]:
    """Get overall web traffic volume with no grouping. Read-only analytics.

    Returns total organization traffic, optionally filtered by DLP engine or
    action (ALLOW/BLOCK), and optionally with an overall time-series `trend`.
    Window must be a 7- or 14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    kwargs: dict[str, Any] = {
        "start_time": start_ms,
        "end_time": end_ms,
        "traffic_unit": args.traffic_unit,
        "limit": args.limit,
    }
    if args.dlp_engine_filter:
        kwargs["dlp_engine_filter"] = args.dlp_engine_filter
    if args.action_filter:
        kwargs["action_filter"] = args.action_filter
    if args.include_trend:
        kwargs["include_trend"] = True
    if args.trend_interval:
        kwargs["trend_interval"] = args.trend_interval

    entries, response, err = client.zins.web_traffic.get_no_grouping(**kwargs)
    if err:
        raise RuntimeError(f"Failed to get total web traffic: {err}")
    raise_for_graphql_errors(response, "get_no_grouping")

    return shape_many(as_dicts(entries), _shape_trend_row)


@tool(
    action=READ,
    service="zins",
    toolset="zins_web_traffic",
    input_model=TrafficCategoryInput,
    output_view=TrafficRow,
    is_list=True,
)
def zins_get_web_protocols(args: TrafficCategoryInput) -> list[dict[str, Any]]:
    """Get web traffic broken down by protocol (HTTP, HTTPS, SSL, …). Read-only analytics.

    One row per protocol with its aggregated total. Window must be a 7- or
    14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.web_traffic.get_protocols(
        start_time=start_ms,
        end_time=end_ms,
        traffic_unit=args.traffic_unit,
        limit=args.limit,
    )
    if err:
        raise RuntimeError(f"Failed to get web protocols: {err}")
    raise_for_graphql_errors(response, "get_protocols")

    return shape_many(as_dicts(entries), _shape_row)


@tool(
    action=READ,
    service="zins",
    toolset="zins_web_traffic",
    input_model=TrafficCategoryInput,
    output_view=TrafficRow,
    is_list=True,
)
def zins_get_threat_super_categories(args: TrafficCategoryInput) -> list[dict[str, Any]]:
    """Get threat super-categories (malware, phishing, spyware, …) from web traffic. Read-only analytics.

    One row per threat super-category with its aggregated total. An empty
    result means no threats were detected in the window. Window must be a 7- or
    14-day historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.web_traffic.get_threat_super_categories(
        start_time=start_ms,
        end_time=end_ms,
        traffic_unit=args.traffic_unit,
        limit=args.limit,
    )
    if err:
        raise RuntimeError(f"Failed to get threat super categories: {err}")
    raise_for_graphql_errors(response, "get_threat_super_categories")

    return shape_many(as_dicts(entries), _shape_row)


@tool(
    action=READ,
    service="zins",
    toolset="zins_web_traffic",
    input_model=TrafficCategoryInput,
    output_view=TrafficRow,
    is_list=True,
)
def zins_get_threat_class(args: TrafficCategoryInput) -> list[dict[str, Any]]:
    """Get threat-class distribution (Virus/Spyware, Advanced, Behavioral). Read-only analytics.

    One row per threat class with its aggregated total. An empty result means
    no threats of these classes were detected. Window must be a 7- or 14-day
    historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.web_traffic.get_threat_class(
        start_time=start_ms,
        end_time=end_ms,
        traffic_unit=args.traffic_unit,
        limit=args.limit,
    )
    if err:
        raise RuntimeError(f"Failed to get threat class: {err}")
    raise_for_graphql_errors(response, "get_threat_class")

    return shape_many(as_dicts(entries), _shape_row)
