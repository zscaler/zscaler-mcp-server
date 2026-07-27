"""ZIA Administration → Advanced Settings (tenant-wide singleton).

Mirrors v1's ``client.zia.advanced_settings`` SDK calls. Strict PUT-replace:
fetch via the get tool, merge changes, then send the full dict back. Writes are
staged until ``zia_activate_configuration``.
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
        Field(
            description=(
                "Complete advanced-settings dict (PUT-replace). Fetch via "
                "zia_get_advanced_settings first, mutate, then send the whole dict."
            )
        ),
    ]


@tool(
    action=READ,
    service="zia",
    toolset="zia_advanced_settings",
    input_model=_NoArgs,
    is_list=False,
)
def zia_get_advanced_settings(args: _NoArgs) -> dict[str, Any]:
    """Get the ZIA tenant-wide Advanced Settings object."""
    client = get_zscaler_client(service="zia")
    settings, _, err = client.zia.advanced_settings.get_advanced_settings()
    if err:
        raise RuntimeError(f"Failed to get advanced settings: {err}")
    return shape_one(settings)


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_advanced_settings",
    input_model=UpdateInput,
    is_list=False,
)
def zia_update_advanced_settings(args: UpdateInput) -> dict[str, Any]:
    """Update ZIA Advanced Settings (strict PUT-replace write). Activate after."""
    client = get_zscaler_client(service="zia")
    updated, _, err = client.zia.advanced_settings.update_advanced_settings(**args.settings)
    if err:
        raise RuntimeError(f"Failed to update advanced settings: {err}")
    return shape_one(updated)
