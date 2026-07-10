"""Z-Insights SaaS Security (CASB) analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/saas_security.py``. Read-only analytics
over the Z-Insights GraphQL API for the Cloud Access Security Broker (CASB)
application report.

The report is a flat list of ``{name, total}`` SaaS-app usage buckets, so it
stays on the default AUTO wire format (CSV).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many
from zscaler_mcp.tools.zins._common import (
    TimeWindowInput,
    as_dicts,
    raise_for_graphql_errors,
    resolve_window,
)

# =============================================================================
# INPUT MODEL
# =============================================================================


class CasbAppReportInput(TimeWindowInput):
    """Inputs for the CASB SaaS-application usage report (7-day default window)."""

    limit: Annotated[
        int, Field(default=50, ge=1, le=1000, description="Max application rows to return.")
    ] = 50


# =============================================================================
# OUTPUT VIEW
# =============================================================================


class CasbAppRow(AgentView):
    """A single CASB SaaS-application usage bucket."""

    id: Optional[str] = Field(
        default=None, description="Application identifier, when the API returns one."
    )
    name: Optional[str] = Field(default=None, description="SaaS application name.")
    total: Optional[float] = Field(
        default=None, description="Aggregated usage total for this application."
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


def _shape_row(raw: dict[str, Any]) -> CasbAppRow:
    return CasbAppRow(
        id=_as_opt_str(pick(raw, "id")),
        name=pick(raw, "name", "label", "key", "application"),
        total=_as_opt_float(pick(raw, "total", "count", "value")),
    )


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zins",
    toolset="zins_saas",
    input_model=CasbAppReportInput,
    output_view=CasbAppRow,
    is_list=True,
)
def zins_get_casb_app_report(args: CasbAppReportInput) -> list[dict[str, Any]]:
    """Get the CASB (Cloud Access Security Broker) SaaS-application usage report. Read-only analytics.

    One row per SaaS application with its aggregated usage total, for seeing
    which cloud apps are being accessed. Window must be a 7- or 14-day
    historical interval.
    """
    start_ms, end_ms = resolve_window(args)
    client = get_zscaler_client(service="zins")

    entries, response, err = client.zins.saas_security.get_casb_app_report(
        start_time=start_ms, end_time=end_ms, limit=args.limit
    )
    if err:
        raise RuntimeError(f"Failed to get CASB app report: {err}")
    raise_for_graphql_errors(response, "get_casb_app_report")

    return shape_many(as_dicts(entries), _shape_row)
