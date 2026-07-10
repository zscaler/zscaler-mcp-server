"""Z-Insights Shadow IT analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/shadow_it.py``. Read-only analytics over
the Z-Insights GraphQL API for discovered Shadow IT applications and the
aggregate Shadow IT summary.

- ``zins_get_shadow_it_apps`` returns one curated row per discovered app
  (name, category, risk, sanctioned state, data volume, user count). The row is
  flat, so it stays AUTO (CSV).
- ``zins_get_shadow_it_summary`` is a single dashboard object with grouped
  breakdowns (by category, by risk index, …) — nested, so it is forced to JSON
  and returns one object (is_list=False).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
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


class ShadowItApp(AgentView):
    """A single discovered Shadow IT application (flat → CSV-friendly)."""

    application: Optional[str] = Field(default=None, description="Application name.")
    application_category: Optional[str] = Field(default=None, description="Application category.")
    risk_index: Optional[float] = Field(default=None, description="Risk score (higher = riskier).")
    sanctioned_state: Optional[str] = Field(
        default=None, description="Sanctioned / unsanctioned governance state (decision-bearing)."
    )
    data_consumed: Optional[float] = Field(
        default=None, description="Total bytes transferred to/from the app."
    )
    authenticated_users: Optional[float] = Field(
        default=None, description="Number of authenticated users of the app."
    )


class ShadowItSummary(AgentView):
    """Aggregate Shadow IT dashboard (nested breakdowns → JSON)."""

    total_apps: Optional[float] = Field(
        default=None, description="Total number of discovered shadow apps."
    )
    total_bytes: Optional[float] = Field(
        default=None, description="Total bytes transferred across all shadow apps."
    )
    total_upload_bytes: Optional[float] = Field(default=None, description="Total uploaded bytes.")
    total_download_bytes: Optional[float] = Field(
        default=None, description="Total downloaded bytes."
    )
    by_category: list[dict[str, Any]] = Field(
        default_factory=list, description="Apps grouped by application category."
    )
    by_risk_index: list[dict[str, Any]] = Field(
        default_factory=list, description="Apps grouped by risk-index band."
    )


# =============================================================================
# SHAPERS
# =============================================================================


def _as_opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _as_opt_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[dict[str, Any]]:
    return list(value) if isinstance(value, list) else []


def _shape_app(raw: dict[str, Any]) -> ShadowItApp:
    return ShadowItApp(
        application=pick(raw, "application", "app", "name"),
        application_category=pick(raw, "application_category", "applicationCategory", "category"),
        risk_index=_as_opt_float(pick(raw, "risk_index", "riskIndex")),
        sanctioned_state=_as_opt_str(pick(raw, "sanctioned_state", "sanctionedState")),
        data_consumed=_as_opt_float(
            pick(raw, "data_consumed", "dataConsumed", "total_bytes", "totalBytes")
        ),
        authenticated_users=_as_opt_float(
            pick(raw, "authenticated_users", "authenticatedUsers", "user_count", "userCount")
        ),
    )


def _shape_summary(raw: dict[str, Any]) -> ShadowItSummary:
    return ShadowItSummary(
        total_apps=_as_opt_float(pick(raw, "total_apps", "totalApps")),
        total_bytes=_as_opt_float(pick(raw, "total_bytes", "totalBytes")),
        total_upload_bytes=_as_opt_float(pick(raw, "total_upload_bytes", "totalUploadBytes")),
        total_download_bytes=_as_opt_float(pick(raw, "total_download_bytes", "totalDownloadBytes")),
        by_category=_as_list(
            pick(raw, "group_by_app_cat_for_app", "groupByAppCatForApp", "by_category")
        ),
        by_risk_index=_as_list(
            pick(raw, "group_by_risk_index_for_app", "groupByRiskIndexForApp", "by_risk_index")
        ),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zins",
    toolset="zins_shadow_it",
    input_model=ShadowItAppsInput,
    output_view=ShadowItApp,
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

    return shape_many(as_dicts(entries), _shape_app)


@tool(
    action=READ,
    service="zins",
    toolset="zins_shadow_it",
    input_model=ShadowItSummaryInput,
    output_view=ShadowItSummary,
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
    return _shape_summary(raw).model_dump()
