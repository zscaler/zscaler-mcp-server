"""ZTW public-cloud account info — read-only.

Mirrors v1's ``public_cloud_info.py``. Backed by ``client.ztw.public_cloud_info``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


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


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListPublicCloudInfoInput,
    is_list=True,
)
def ztw_list_public_cloud_info(args: ListPublicCloudInfoInput) -> list[dict[str, Any]]:
    """List ZTW public-cloud account info (read-only)."""
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
    return shape_many([a.as_dict() for a in (accounts or [])])
