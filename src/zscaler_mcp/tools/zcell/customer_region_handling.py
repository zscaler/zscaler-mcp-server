"""ZCell Customer Region Handling — agent-first v2 read tools.

Read-only surface over ``client.zcell.customer_region_handling``:

    * zcell_list_regions                    — available/configured regions
    * zcell_list_region_operational_status  — configured regions + BC/AC status

The operational-status response nests BC/AC status blocks, so it is forced to
JSON.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zcell._common import as_dicts

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListRegionsInput(BaseModel):
    """Inputs for listing available/configured regions."""

    skip_sku_check: Annotated[
        Optional[bool],
        Field(default=None, description="Skip the SKU-entitlement check when listing regions."),
    ] = None


class RegionOperationalStatusInput(BaseModel):
    """Inputs for listing configured regions and their operational status."""

    bc_size: Annotated[
        Optional[str],
        Field(default=None, description="Optional broker-cluster size filter."),
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


def _query(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in pairs if value is not None}


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_customer_region_handling",
    input_model=ListRegionsInput,
    is_list=True,
)
def zcell_list_regions(args: ListRegionsInput) -> list[dict[str, Any]]:
    """List the Zscaler Cellular regions available/configured for the customer.

    Read-only. Returns each region and whether it is configured.
    """
    client = get_zscaler_client(service="zcell")

    regions, _, err = client.zcell.customer_region_handling.list_regions(
        query_params=_query(("skip_sku_check", args.skip_sku_check))
    )
    if err:
        raise RuntimeError(f"Failed to list regions: {err}")
    return shape_many(as_dicts(regions))


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_customer_region_handling",
    input_model=RegionOperationalStatusInput,
    is_list=True,
    wire_format=WireFormat.JSON,
)
def zcell_list_region_operational_status(
    args: RegionOperationalStatusInput,
) -> list[dict[str, Any]]:
    """List Zscaler Cellular configured regions with their operational status.

    Read-only. Returns each configured region plus the broker-cluster (BC) and
    app-connector (AC) status blocks and the MAP A-C / B-C link statuses.
    """
    client = get_zscaler_client(service="zcell")

    statuses, _, err = client.zcell.customer_region_handling.list_regions_operational_status(
        query_params=_query(("bc_size", args.bc_size))
    )
    if err:
        raise RuntimeError(f"Failed to list region operational status: {err}")
    return shape_many(as_dicts(statuses))
