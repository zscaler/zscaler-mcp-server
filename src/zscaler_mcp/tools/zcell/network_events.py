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
from zscaler_mcp.shaping import AgentView, pick, shape_many
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


class NetworkEventView(AgentView):
    """A curated network/session event row (decision-bearing subset)."""

    timestamp: Optional[Any] = Field(default=None, description="When the event occurred.")
    event_name: Optional[str] = Field(default=None, description="Event name/type.")
    outcome: Optional[str] = Field(default=None, description="Event outcome.")
    iccid: Optional[str] = Field(default=None, description="ICCID involved.")
    imsi: Optional[str] = Field(default=None, description="IMSI involved.")
    sim_name: Optional[str] = Field(default=None, description="Friendly SIM name.")
    country: Optional[str] = Field(default=None, description="Country the event occurred in.")
    operator_name: Optional[str] = Field(default=None, description="Mobile operator (carrier).")
    rat_type: Optional[str] = Field(
        default=None, description="Radio access technology (e.g. LTE, 5G)."
    )
    zone: Optional[str] = Field(default=None, description="Zone the event is attributed to.")
    ip_address: Optional[str] = Field(default=None, description="IP address assigned/observed.")
    data_cap_reached: Optional[bool] = Field(
        default=None, description="Whether the data cap was reached."
    )
    account_name: Optional[str] = Field(default=None, description="Account name.")


# =============================================================================
# SHAPER
# =============================================================================


def _shape_event(raw: dict[str, Any]) -> NetworkEventView:
    return NetworkEventView(
        timestamp=pick(raw, "timestamp"),
        event_name=pick(raw, "event_name", "eventName"),
        outcome=pick(raw, "outcome"),
        iccid=pick(raw, "iccid"),
        imsi=pick(raw, "imsi"),
        sim_name=pick(raw, "sim_name", "simName"),
        country=pick(raw, "country"),
        operator_name=pick(raw, "operator_name", "operatorName"),
        rat_type=pick(raw, "rat_type", "ratType"),
        zone=pick(raw, "zone"),
        ip_address=pick(raw, "ip_address", "ipAddress"),
        data_cap_reached=pick(raw, "data_cap_reached", "dataCapReached"),
        account_name=pick(raw, "account_name", "accountName"),
    )


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_network_events",
    input_model=NetworkEventsSearchInput,
    output_view=NetworkEventView,
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
    return shape_many(as_dicts(events), _shape_event)
