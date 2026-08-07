"""Z-Insights SaaS Security (CASB) analytics — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zins/saas_security.py``. Read-only analytics
over the Z-Insights GraphQL API for the Cloud Access Security Broker (CASB)
application report.

The report is a flat list of ``{name, total}`` SaaS-app usage buckets, so it
stays on the default AUTO wire format (CSV).
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


class CasbAppReportInput(TimeWindowInput):
    """Inputs for the CASB SaaS-application usage report (7-day default window)."""

    limit: Annotated[
        int, Field(default=50, ge=1, le=1000, description="Max application rows to return.")
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
    toolset="zins_saas",
    input_model=CasbAppReportInput,
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

    return shape_many(as_dicts(entries))
