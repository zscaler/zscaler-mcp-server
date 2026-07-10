"""ZTW public-cloud account info — read-only.

Mirrors v1's ``public_cloud_info.py``. Backed by ``client.ztw.public_cloud_info``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many


class ListPublicCloudInfoInput(BaseModel):
    """Inputs for listing ZTW public-cloud account info."""

    page: Annotated[Optional[int], Field(default=None, ge=0, description="Page offset.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Per page (default 100).")
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Search filter for account name/metadata.")
    ] = None
    cloud_type: Annotated[
        Optional[str], Field(default=None, description="Cloud provider filter: AWS, AZURE, GCP.")
    ] = None


class PublicCloudInfoSummary(AgentView):
    """Lean view — identify a public-cloud account/integration record."""

    id: Optional[str] = Field(default=None, description="Account/record ID, if present.")
    name: Optional[str] = Field(default=None, description="Account name.")
    cloud_type: Optional[str] = Field(default=None, description="Cloud provider (AWS/AZURE/GCP).")
    account_id: Optional[str] = Field(default=None, description="Cloud account identifier.")
    region: Optional[str] = Field(default=None, description="Cloud region, if present.")
    status: Optional[str] = Field(
        default=None, description="Integration status (decision-bearing)."
    )


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _shape_cloud_info(raw: dict[str, Any]) -> PublicCloudInfoSummary:
    return PublicCloudInfoSummary(
        id=_opt_str(pick(raw, "id")),
        name=pick(raw, "name", "account_name", "accountName"),
        cloud_type=pick(raw, "cloud_type", "cloudType", "cloud_provider", "cloudProvider"),
        account_id=_opt_str(pick(raw, "account_id", "accountId")),
        region=pick(raw, "region"),
        status=pick(raw, "status", "state"),
    )


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListPublicCloudInfoInput,
    output_view=PublicCloudInfoSummary,
    is_list=True,
)
def ztw_list_public_cloud_info(args: ListPublicCloudInfoInput) -> list[dict[str, Any]]:
    """List ZTW public-cloud account info as curated, agent-facing views (read-only)."""
    client = get_zscaler_client(service="ztw")
    qp: dict[str, Any] = {}
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    if args.search:
        qp["search"] = args.search
    if args.cloud_type:
        qp["cloud_type"] = args.cloud_type
    accounts, _, err = client.ztw.public_cloud_info.list_public_cloud_info(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZTW public cloud info: {err}")
    return shape_many([a.as_dict() for a in (accounts or [])], _shape_cloud_info)
