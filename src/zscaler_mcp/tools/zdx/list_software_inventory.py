"""ZDX software inventory — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/list_software_inventory.py``:

    zdx_list_software, zdx_get_software_details

``list_softwares`` returns a flat list of software-inventory models; the
software ``key`` (name + version) from a row is what you pass to
``zdx_get_software_details`` (SDK ``list_software_keys``) to expand the
per-user / per-device install rows.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zdx._common import scope_query_params

# =============================================================================
# INPUT MODELS
# =============================================================================


class _InventoryScopeInput(BaseModel):
    """Shared scope filters for the software-inventory endpoints."""

    location_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by location ID(s).")
    ] = None
    department_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by department ID(s).")
    ] = None
    geo_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by geolocation ID(s).")
    ] = None
    user_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by user ID(s).")
    ] = None
    device_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by device ID(s).")
    ] = None


class ListSoftwareInput(_InventoryScopeInput):
    """Inputs for listing the ZDX software inventory."""


class GetSoftwareDetailsInput(_InventoryScopeInput):
    """Inputs for expanding one software key into its install rows."""

    software_key: Annotated[
        str,
        Field(
            description="Software name+version key from `zdx_list_software` (e.g. 'Chrome_120')."
        ),
    ]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_software_inventory",
    input_model=ListSoftwareInput,
    is_list=True,
)
def zdx_list_software(args: ListSoftwareInput) -> list[dict[str, Any]]:
    """List the ZDX software inventory.

    Read-only. Returns one row per software title (key, name, vendor, version,
    install/user counts). Filter by location/department/geo/user/device. Use a
    returned `software_key` with `zdx_get_software_details` to see who has it.
    """
    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        user_ids=args.user_ids,
        device_ids=args.device_ids,
    )
    result, _, err = client.zdx.inventory.list_softwares(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX software inventory: {err}")
    return shape_many([s.as_dict() for s in (result or [])])


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_software_inventory",
    input_model=GetSoftwareDetailsInput,
    is_list=True,
)
def zdx_get_software_details(args: GetSoftwareDetailsInput) -> list[dict[str, Any]]:
    """Expand one ZDX software key into its per-user/device install rows.

    Read-only. Returns the users and devices that have the given `software_key`
    installed. Obtain the key from `zdx_list_software`.
    """
    if not args.software_key:
        raise ValueError("software_key is required")
    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        user_ids=args.user_ids,
        device_ids=args.device_ids,
    )
    result, _, err = client.zdx.inventory.list_software_keys(args.software_key, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get ZDX software details for {args.software_key}: {err}")
    return shape_many([s.as_dict() for s in (result or [])])
