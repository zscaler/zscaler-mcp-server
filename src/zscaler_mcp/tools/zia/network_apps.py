"""ZIA network applications — read-only.

Mirrors v1's ``network_apps.py``. Network apps are predefined/standard and
read-only. Backed by ``client.zia.cloud_firewall``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one


class ListAppsInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on app name/description.")
    ] = None
    locale: Annotated[
        Optional[str],
        Field(default=None, description="Locale: en-US, de-DE, es-ES, fr-FR, ja-JP, zh-CN."),
    ] = None


class GetAppInput(BaseModel):
    app_id: Annotated[str, Field(description="Network app ID (e.g. 'ICMP_ANY', 'HTTP').")]


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=ListAppsInput,
    is_list=True,
)
def zia_list_network_apps(args: ListAppsInput) -> list[dict[str, Any]]:
    """List ZIA network applications (predefined + custom)."""
    client = get_zscaler_client(service="zia")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.locale:
        qp["locale"] = args.locale
    apps, _, err = client.zia.cloud_firewall.list_network_apps(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list network applications: {err}")
    return shape_many([a.as_dict() for a in (apps or [])])


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_firewall",
    input_model=GetAppInput,
    is_list=False,
)
def zia_get_network_app(args: GetAppInput) -> dict[str, Any]:
    """Get a single ZIA network application by ID."""
    client = get_zscaler_client(service="zia")
    app, _, err = client.zia.cloud_firewall.get_network_app(args.app_id)
    if err:
        raise RuntimeError(f"Failed to get network application {args.app_id}: {err}")
    return shape_one(app.as_dict())
