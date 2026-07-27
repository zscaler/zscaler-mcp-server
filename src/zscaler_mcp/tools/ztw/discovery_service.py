"""ZTW workload-discovery settings — read-only singleton.

Mirrors v1's ``discovery_service.py``. Backed by ``client.ztw.discovery_service``.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick


class DiscoverySettingsInput(BaseModel):
    """No inputs — ZTW discovery settings are a tenant-wide singleton."""


class DiscoverySettings(AgentView):
    """ZTW workload-discovery settings (tenant-wide singleton).

    The SDK object's exact field set varies; the full record surfaces the
    decision-bearing knobs and keeps the rest in a nested `settings` payload so
    nothing is silently dropped for a config singleton.
    """

    discovery_role: Optional[str] = Field(default=None, description="Discovery IAM role, if set.")
    external_id: Optional[str] = Field(default=None, description="External ID, if set.")
    settings: dict = Field(
        default_factory=dict, description="Full discovery-settings payload (curated container)."
    )


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=DiscoverySettingsInput,
    output_view=DiscoverySettings,
    is_list=False,
)
def ztw_get_discovery_settings(args: DiscoverySettingsInput) -> dict[str, Any]:
    """Get ZTW workload-discovery settings (read-only singleton).

    Returns the decision-bearing knobs plus the full payload in `settings`.
    """
    client = get_zscaler_client(service="ztw")
    settings, _, err = client.ztw.discovery_service.get_discovery_settings()
    if err:
        raise RuntimeError(f"Failed to get ZTW discovery settings: {err}")
    raw = settings.as_dict() if hasattr(settings, "as_dict") else dict(settings or {})
    return DiscoverySettings(
        discovery_role=pick(raw, "discovery_role", "discoveryRole"),
        external_id=pick(raw, "external_id", "externalId"),
        settings=raw,
    ).model_dump()
