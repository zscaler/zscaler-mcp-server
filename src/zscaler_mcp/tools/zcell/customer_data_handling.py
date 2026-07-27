"""ZCell Customer Data Handling — agent-first v2 read tool.

Read-only surface over ``client.zcell.customer_data_handling``:

    * zcell_get_customer_data_handling — the logged-in customer's profile/summary

The record nests ZIA/ZPA cloud metadata, the SIM provider, and the MVNO list, so
it is forced to JSON and returns a single object.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_one
from zscaler_mcp.tools.zcell._common import as_dict

# =============================================================================
# INPUT MODEL
# =============================================================================


class GetCustomerDataInput(BaseModel):
    """Inputs for the customer profile (no parameters — scoped by ZCELL_CUSTOMER_ID)."""


# =============================================================================
# OUTPUT VIEW
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_customer_data_handling",
    input_model=GetCustomerDataInput,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zcell_get_customer_data_handling(args: GetCustomerDataInput) -> dict[str, Any]:
    """Get the logged-in Zscaler Cellular customer's profile and SIM totals.

    Read-only. Returns the customer record: identity, activation state, platform,
    configured regions, SIM counts, current usage, and the linked ZIA/ZPA cloud
    and SIM-provider metadata. Scoped by ZCELL_CUSTOMER_ID.
    """
    client = get_zscaler_client(service="zcell")

    customer, _, err = client.zcell.customer_data_handling.get_customer_data_handling()
    if err:
        raise RuntimeError(f"Failed to get customer data: {err}")
    return shape_one(as_dict(customer))
