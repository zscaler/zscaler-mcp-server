"""ZIA policy-engine cloud-application catalog (read-only).

Mirrors v1's ``client.zia.cloud_applications`` SDK calls. This is the
policy-engine catalog (canonical UPPER_SNAKE_CASE enums such as ONEDRIVE,
SHAREPOINT_ONLINE) used by SSL Inspection / Web DLP / Cloud App Control / FTC
rules — NOT the Shadow IT analytics catalog (see shadow_it_report.py).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on app name.")
    ] = None
    app_class: Annotated[
        Optional[str], Field(default=None, description="Filter by application class.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, description="Page number.")] = None
    page_size: Annotated[Optional[int], Field(default=None, description="Items per page.")] = None
    group_results: Annotated[
        Optional[bool], Field(default=None, description="Group results by application class.")
    ] = None


def _query_params(args: ListInput) -> dict[str, Any]:
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.app_class:
        qp["app_class"] = args.app_class
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    if args.group_results is not None:
        qp["group_results"] = args.group_results
    return qp


@tool(
    action=READ,
    service="zia",
    toolset="zia_cloud_app_control",
    input_model=ListInput,
    is_list=True,
)
def zia_list_cloud_app_policy(args: ListInput) -> list[dict[str, Any]]:
    """List the ZIA policy-engine cloud-application catalog (Cloud App Control)."""
    client = get_zscaler_client(service="zia")
    apps, _, err = client.zia.cloud_applications.list_cloud_app_policy(
        query_params=_query_params(args) or None
    )
    if err:
        raise RuntimeError(f"Failed to list cloud app policy catalog: {err}")
    rows = [a if isinstance(a, dict) else a.as_dict() for a in (apps or [])]
    return shape_many(rows)


@tool(
    action=READ,
    service="zia",
    toolset="zia_ssl_inspection",
    input_model=ListInput,
    is_list=True,
)
def zia_list_cloud_app_ssl_policy(args: ListInput) -> list[dict[str, Any]]:
    """List the ZIA policy-engine cloud-application catalog (SSL Inspection)."""
    client = get_zscaler_client(service="zia")
    apps, _, err = client.zia.cloud_applications.list_cloud_app_ssl_policy(
        query_params=_query_params(args) or None
    )
    if err:
        raise RuntimeError(f"Failed to list cloud app SSL policy catalog: {err}")
    rows = [a if isinstance(a, dict) else a.as_dict() for a in (apps or [])]
    return shape_many(rows)
