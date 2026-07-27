"""ZEASM organizations — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/easm/organizations.py`` but adds the v2 shaping
layer: the SDK ``Organizations`` wrapper (next_page / prev_page / results /
total_results) is unwrapped to one row per organization, carrying the
identifying fields an agent needs to scope every other EASM call.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListOrganizationsInput(BaseModel):
    """Inputs for listing ZEASM organizations (no filters; tenant-scoped)."""


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


# =============================================================================
# TOOL
# =============================================================================


@tool(
    action=READ,
    service="zeasm",
    toolset="zeasm",
    input_model=ListOrganizationsInput,
    is_list=True,
)
def zeasm_list_organizations(args: ListOrganizationsInput) -> list[dict[str, Any]]:
    """List ZEASM organizations.

    Read-only. Returns one row per organization configured in the EASM Admin
    Portal, carrying just the `id` + `name`. Use the returned `id` as the
    `org_id` argument for `zeasm_list_findings`, `zeasm_list_lookalike_domains`,
    and the other EASM tools.
    """
    client = get_zscaler_client(service="zeasm")

    orgs, _, err = client.zeasm.organizations.list_organizations()
    if err:
        raise RuntimeError(f"Failed to list EASM organizations: {err}")

    results = getattr(orgs, "results", None) or []
    return shape_many([o.as_dict() for o in results])
