"""ZIA configuration activation — status + activate.

Mirrors v1's ``client.zia.activate`` SDK calls. ZIA stages every config change
until activation; call ``zia_activate_configuration`` after any ZIA write.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import UPDATE, READ, tool
from zscaler_mcp.shaping import AgentView, pick


class _NoArgs(BaseModel):
    pass


class ActivationStatus(AgentView):
    status: str = Field(description="Current activation status (e.g. ACTIVE, PENDING).")


def _shape_status(raw: Any) -> ActivationStatus:
    if isinstance(raw, dict):
        return ActivationStatus(status=str(pick(raw, "status", default="UNKNOWN")))
    return ActivationStatus(status=str(raw))


@tool(
    action=READ,
    service="zia",
    toolset="zia_admin",
    input_model=_NoArgs,
    output_view=ActivationStatus,
    is_list=False,
)
def zia_get_activation_status(args: _NoArgs) -> dict[str, Any]:
    """Get the current ZIA configuration activation status."""
    client = get_zscaler_client(service="zia")
    status_obj, _, err = client.zia.activate.status()
    if err:
        raise RuntimeError(f"Failed to get activation status: {err}")
    raw = status_obj.as_dict() if hasattr(status_obj, "as_dict") else status_obj
    return _shape_status(raw).model_dump()


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_admin",
    input_model=_NoArgs,
    output_view=ActivationStatus,
    is_list=False,
)
def zia_activate_configuration(args: _NoArgs) -> dict[str, Any]:
    """Activate staged ZIA configuration changes (write). Run after any ZIA write."""
    client = get_zscaler_client(service="zia")
    result, _, err = client.zia.activate.activate()
    if err:
        raise RuntimeError(f"Failed to activate configuration: {err}")
    raw = result.as_dict() if hasattr(result, "as_dict") else result
    return _shape_status(raw).model_dump()
