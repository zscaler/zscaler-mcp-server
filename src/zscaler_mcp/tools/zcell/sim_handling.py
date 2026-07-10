"""ZCell Sim Handling — agent-first v2 read tools.

Read-only surface over ``client.zcell.sim_handling``:

    * zcell_get_sim_details — the full record for one SIM (by ICCID)
    * zcell_list_sims        — search the SIM inventory with filters + pagination

``zcell_list_sims`` is backed by the SDK's ``create_sims_search`` (a POST). It is
semantically a read — browsing the SIM inventory — so it is exposed as a READ
tool. Both tools carry list/nested fields, so they are forced to JSON.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick
from zscaler_mcp.tools.zcell._common import as_dict

# =============================================================================
# INPUT MODELS
# =============================================================================


class GetSimDetailsInput(BaseModel):
    """Inputs for fetching one SIM's details by ICCID."""

    icc_id: Annotated[str, Field(description="ICCID of the SIM to retrieve.")]


class ListSimsInput(BaseModel):
    """Inputs for searching the SIM inventory (filters ride in the request body)."""

    iccid: Annotated[
        Optional[list[str]], Field(default=None, description="Filter to these ICCIDs.")
    ] = None
    status: Annotated[Optional[str], Field(default=None, description="Filter by SIM status.")] = (
        None
    )
    network_status: Annotated[
        Optional[str], Field(default=None, description="Filter by network status.")
    ] = None
    ip_address: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by IP address(es).")
    ] = None
    location_country: Annotated[
        Optional[str], Field(default=None, description="Filter by location country.")
    ] = None
    tag: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by tag name(s).")
    ] = None
    device_type: Annotated[
        Optional[str], Field(default=None, description="Filter by device type.")
    ] = None
    brand_name: Annotated[
        Optional[str], Field(default=None, description="Filter by device brand.")
    ] = None
    marketing_name: Annotated[
        Optional[str], Field(default=None, description="Filter by marketing name.")
    ] = None
    model_name: Annotated[
        Optional[str], Field(default=None, description="Filter by model name.")
    ] = None
    form_factor: Annotated[
        Optional[str], Field(default=None, description="Filter by form factor.")
    ] = None
    imei_status: Annotated[
        Optional[str],
        Field(
            default=None, description="Filter by IMEI lock status: Locked, Unlocked, InProgress."
        ),
    ] = None
    page: Annotated[
        Optional[int], Field(default=None, ge=0, description="Page number (0-based).")
    ] = None
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class SimDetail(AgentView):
    """Curated single-SIM record (identifying + status + device fields)."""

    iccid: Optional[str] = Field(default=None, description="ICCID of the SIM.")
    imsi: Optional[str] = Field(default=None, description="IMSI of the SIM.")
    imei: Optional[str] = Field(default=None, description="IMEI of the paired device.")
    msisdn: Optional[str] = Field(default=None, description="MSISDN (phone number), if any.")
    status: Optional[str] = Field(default=None, description="SIM status (decision-bearing).")
    network_status: Optional[str] = Field(
        default=None, description="Current network attachment status."
    )
    eid: Optional[str] = Field(default=None, description="eSIM EID, if applicable.")
    profile_name: Optional[str] = Field(default=None, description="Provisioning profile name.")
    apn: Optional[str] = Field(default=None, description="Access point name.")
    ip_address: list[str] = Field(default_factory=list, description="Assigned IP address(es).")
    location_country: Optional[str] = Field(default=None, description="Last-seen country.")
    location_mno: Optional[str] = Field(
        default=None, description="Last-seen mobile network operator."
    )
    activated_date: Optional[Any] = Field(default=None, description="Activation date.")
    last_session_updated_at: Optional[Any] = Field(
        default=None, description="Last session update time."
    )
    device_type: Optional[str] = Field(default=None, description="Device type.")
    brand_name: Optional[str] = Field(default=None, description="Device brand.")
    model_name: Optional[str] = Field(default=None, description="Device model.")
    form_factor: Optional[str] = Field(default=None, description="SIM form factor.")
    tags: list[str] = Field(default_factory=list, description="Tags assigned to the SIM.")
    assigned_to: Optional[str] = Field(default=None, description="Entity the SIM is assigned to.")
    usage: Optional[Any] = Field(default=None, description="Data usage (formatted).")


class SimSearchResult(AgentView):
    """The SIM-inventory search envelope: the SIM page plus total usage."""

    total_usage: Optional[Any] = Field(
        default=None, description="Aggregate usage across the result set."
    )
    total_count: Optional[Any] = Field(
        default=None, description="Total matching SIMs, if reported."
    )
    page_number: Optional[Any] = Field(
        default=None, description="Current page number, if reported."
    )
    total_pages: Optional[Any] = Field(default=None, description="Total pages, if reported.")
    sims: list[dict[str, Any]] = Field(
        default_factory=list, description="The SIM records on this page."
    )


# =============================================================================
# SHAPERS
# =============================================================================


def _shape_sim(raw: dict[str, Any]) -> SimDetail:
    return SimDetail(
        iccid=pick(raw, "iccid"),
        imsi=pick(raw, "imsi"),
        imei=pick(raw, "imei"),
        msisdn=pick(raw, "msisdn"),
        status=pick(raw, "status"),
        network_status=pick(raw, "network_status", "networkStatus"),
        eid=pick(raw, "eid"),
        profile_name=pick(raw, "profile_name", "profileName"),
        apn=pick(raw, "apn"),
        ip_address=pick(raw, "ip_address", "ipAddress", default=[]) or [],
        location_country=pick(raw, "location_country", "locationCountry"),
        location_mno=pick(raw, "location_mno", "locationMno"),
        activated_date=pick(raw, "activated_date", "activatedDate"),
        last_session_updated_at=pick(raw, "last_session_updated_at", "lastSessionUpdatedAt"),
        device_type=pick(raw, "device_type", "deviceType"),
        brand_name=pick(raw, "brand_name", "brandName"),
        model_name=pick(raw, "model_name", "modelName"),
        form_factor=pick(raw, "form_factor", "formFactor"),
        tags=pick(raw, "tags", default=[]) or [],
        assigned_to=pick(raw, "assigned_to", "assignedTo"),
        usage=pick(raw, "usage"),
    )


def _shape_search(raw: dict[str, Any]) -> SimSearchResult:
    page = pick(raw, "page_details", "pageDetails", default={})
    if not isinstance(page, dict):
        page = {}
    content = pick(page, "content", default=[])
    sims = (
        [_shape_sim(as_dict(item)).model_dump() for item in content]
        if isinstance(content, list)
        else []
    )
    return SimSearchResult(
        total_usage=pick(raw, "total_usage", "totalUsage"),
        total_count=pick(page, "total_elements", "totalElements", "total_count", "totalCount"),
        page_number=pick(page, "page_number", "pageNumber", "number"),
        total_pages=pick(page, "total_pages", "totalPages"),
        sims=sims,
    )


def _body(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in pairs if value is not None}


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_handling",
    input_model=GetSimDetailsInput,
    output_view=SimDetail,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zcell_get_sim_details(args: GetSimDetailsInput) -> dict[str, Any]:
    """Get the full Zscaler Cellular record for one SIM by ICCID.

    Read-only. Returns the identifying, status, and device fields for the SIM
    (ICCID, IMSI/IMEI, status, network status, APN, IP, device, tags, usage).
    """
    if not args.icc_id:
        raise ValueError("icc_id is required")

    client = get_zscaler_client(service="zcell")

    sim, _, err = client.zcell.sim_handling.list_sims_details(icc_id=args.icc_id)
    if err:
        raise RuntimeError(f"Failed to get SIM details for {args.icc_id}: {err}")
    return _shape_sim(as_dict(sim)).model_dump()


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_sim_handling",
    input_model=ListSimsInput,
    output_view=SimSearchResult,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zcell_list_sims(args: ListSimsInput) -> dict[str, Any]:
    """Search the Zscaler Cellular SIM inventory with filters and pagination.

    Read-only (browses the inventory). Returns a page of curated SIM records
    plus the aggregate usage/pagination envelope. Filter by ICCID, status,
    network status, country, tag, device attributes, or IMEI lock status.
    """
    client = get_zscaler_client(service="zcell")

    body = _body(
        ("iccid", args.iccid),
        ("status", args.status),
        ("network_status", args.network_status),
        ("ip_address", args.ip_address),
        ("location_country", args.location_country),
        ("tag", args.tag),
        ("device_type", args.device_type),
        ("brand_name", args.brand_name),
        ("marketing_name", args.marketing_name),
        ("model_name", args.model_name),
        ("form_factor", args.form_factor),
        ("imei_status", args.imei_status),
        ("page", args.page),
        ("size", args.size),
    )

    result, _, err = client.zcell.sim_handling.create_sims_search(**body)
    if err:
        raise RuntimeError(f"Failed to search SIMs: {err}")
    return _shape_search(as_dict(result)).model_dump()
