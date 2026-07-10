"""ZCell Customer Data Handling — agent-first v2 read tool.

Read-only surface over ``client.zcell.customer_data_handling``:

    * zcell_get_customer_data_handling — the logged-in customer's profile/summary

The record nests ZIA/ZPA cloud metadata, the SIM provider, and the MVNO list, so
it is forced to JSON and returns a single object.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick
from zscaler_mcp.tools.zcell._common import as_dict

# =============================================================================
# INPUT MODEL
# =============================================================================


class GetCustomerDataInput(BaseModel):
    """Inputs for the customer profile (no parameters — scoped by ZCELL_CUSTOMER_ID)."""


# =============================================================================
# OUTPUT VIEW
# =============================================================================


class CustomerDataView(AgentView):
    """The logged-in customer's Zscaler Cellular profile + SIM totals (nested → JSON)."""

    id: Optional[str] = Field(default=None, description="Customer ID.")
    name: Optional[str] = Field(default=None, description="Customer name.")
    email: Optional[str] = Field(default=None, description="Contact email.")
    user_name: Optional[str] = Field(default=None, description="Account username.")
    parent_id: Optional[str] = Field(default=None, description="Parent customer ID, if any.")
    is_activated: Optional[bool] = Field(
        default=None, description="Whether the customer is activated."
    )
    platform_type: Optional[str] = Field(default=None, description="Platform type.")
    bc_size: Optional[Any] = Field(default=None, description="Broker-cluster size.")
    regions: list[str] = Field(default_factory=list, description="Configured region codes.")
    total_sims: Optional[Any] = Field(default=None, description="Total SIMs.")
    active_sims: Optional[Any] = Field(default=None, description="Active SIMs.")
    inactive_sims: Optional[Any] = Field(default=None, description="Inactive SIMs.")
    current_usage: Optional[Any] = Field(default=None, description="Current aggregate data usage.")
    zia: Optional[Any] = Field(default=None, description="ZIA cloud/org metadata.")
    zpa: Optional[Any] = Field(default=None, description="ZPA cloud/org metadata.")
    sim_provider: Optional[Any] = Field(default=None, description="SIM provider metadata.")
    mvno_ids: list[Any] = Field(default_factory=list, description="Associated MVNO entries.")


# =============================================================================
# SHAPER
# =============================================================================


def _shape_customer(raw: dict[str, Any]) -> CustomerDataView:
    return CustomerDataView(
        id=_opt_str(pick(raw, "id")),
        name=pick(raw, "name"),
        email=pick(raw, "email"),
        user_name=pick(raw, "user_name", "userName"),
        parent_id=_opt_str(pick(raw, "parent_id", "parentId")),
        is_activated=pick(raw, "is_activated", "isActivated"),
        platform_type=pick(raw, "platform_type", "platformType"),
        bc_size=pick(raw, "bc_size", "bcSize"),
        regions=pick(raw, "regions", default=[]) or [],
        total_sims=pick(raw, "total_sims", "totalSims"),
        active_sims=pick(raw, "active_sims", "activeSims"),
        inactive_sims=pick(raw, "inactive_sims", "inactiveSims"),
        current_usage=pick(raw, "current_usage", "currentUsage"),
        zia=pick(raw, "zia"),
        zpa=pick(raw, "zpa"),
        sim_provider=pick(raw, "sim_provider", "simProvider"),
        mvno_ids=pick(raw, "mvno_ids", "mvnoIds", default=[]) or [],
    )


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
    output_view=CustomerDataView,
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
    return _shape_customer(as_dict(customer)).model_dump()
