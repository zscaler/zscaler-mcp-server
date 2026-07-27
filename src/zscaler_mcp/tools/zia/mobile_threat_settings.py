"""ZIA Mobile Advanced Threat Settings (tenant-wide singleton).

Mirrors v1's ``client.zia.mobile_threat_settings`` SDK calls. PUT-replace: fetch,
merge, send the full dict. Writes are staged until ``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, UPDATE, tool
from zscaler_mcp.shaping import shape_one


class _NoArgs(BaseModel):
    pass


class UpdateInput(BaseModel):
    settings: Annotated[
        dict[str, Any],
        Field(description="Complete mobile-threat settings dict (PUT-replace)."),
    ]


@tool(
    action=READ,
    service="zia",
    toolset="zia_misc",
    input_model=_NoArgs,
    is_list=False,
)
def zia_get_mobile_advanced_settings(args: _NoArgs) -> dict[str, Any]:
    """Get the ZIA Mobile Advanced Threat Settings object."""
    client = get_zscaler_client(service="zia")
    settings, _, err = client.zia.mobile_threat_settings.get_mobile_advanced_settings()
    if err:
        raise RuntimeError(f"Failed to get mobile advanced settings: {err}")
    return shape_one(settings)


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_misc",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_mobile_advanced_settings(args: UpdateInput) -> dict[str, Any]:
    """Update ZIA Mobile Advanced Threat Settings (PUT-replace write). Activate after."""
    client = get_zscaler_client(service="zia")
    updated, _, err = client.zia.mobile_threat_settings.update_mobile_advanced_settings(
        **args.settings
    )
    if err:
        raise RuntimeError(f"Failed to update mobile advanced settings: {err}")
    return shape_one(updated)
