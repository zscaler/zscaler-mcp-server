"""ZCell Network Events — agent-first v2 read tool.

Read-only surface over ``client.zcell.network_events``:

    * zcell_list_network_events — searches network/session events for the tenant

The time window (startTime/endTime) is a URL-path window filled by the shared
:class:`WindowInput` ``days`` shorthand; the filter/pagination options ride in a
flat JSON body. The curated row keeps the decision-bearing fields (who, where,
what happened) and drops the low-level location/id noise.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zcell._common import WindowInput, as_dicts

# =============================================================================
# INPUT MODEL
# =============================================================================


class NetworkEventsSearchInput(WindowInput):
    """Inputs for searching Zscaler Cellular network events (time-bounded)."""

    filter_by: Annotated[
        Optional[list[dict[str, Any]]],
        Field(
            default=None,
            description=(
                "List of filters, each: {filterName, operator (EQ|NE|LIKE|NOT_LIKE), "
                "values: [..]}. e.g. [{'filterName':'country','operator':'EQ','values':['US']}]."
            ),
        ),
    ] = None
    sort_by: Annotated[
        Optional[dict[str, Any]],
        Field(default=None, description="Sort object, e.g. {'name': 'DESC'} (ASC|DESC)."),
    ] = None
    exclude_apn_config: Annotated[
        Optional[bool],
        Field(default=None, description="Whether to exclude APN config from results."),
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=0, description="Page number (>= 0).")] = (
        None
    )
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


# =============================================================================
# OUTPUT VIEW
# =============================================================================


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_network_events",
    input_model=NetworkEventsSearchInput,
    is_list=True,
)
def zcell_list_network_events(args: NetworkEventsSearchInput) -> list[dict[str, Any]]:
    """Search Zscaler Cellular network/session events over a lookback window.

    Read-only. Returns curated event rows (timestamp, event, outcome, SIM/ICCID,
    country, carrier, RAT, IP) over a `days` window, with optional `filter_by`
    conditions, `sort_by`, and pagination.
    """
    client = get_zscaler_client(service="zcell")

    body: dict[str, Any] = {}
    if args.filter_by is not None:
        body["filter_by"] = args.filter_by
    if args.sort_by is not None:
        body["sort_by"] = args.sort_by
    if args.exclude_apn_config is not None:
        body["exclude_apn_config"] = args.exclude_apn_config
    if args.page is not None:
        body["page"] = args.page
    if args.size is not None:
        body["size"] = args.size

    events, _, err = client.zcell.network_events.list_network_events_search(days=args.days, **body)
    if err:
        raise RuntimeError(f"Failed to search network events: {err}")
    return shape_many(as_dicts(events))
