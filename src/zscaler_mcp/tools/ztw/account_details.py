"""ZTW public-cloud account details — read-only.

Mirrors v1's ``account_details.py``. Backed by ``client.ztw.account_details``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class ListAccountDetailsInput(BaseModel):
    """Inputs for listing ZTW public-cloud account details."""

    page: Annotated[Optional[int], Field(default=None, ge=0, description="Page offset.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Per page (default 250).")
    ] = None


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListAccountDetailsInput,
    is_list=True,
)
def ztw_list_public_account_details(args: ListAccountDetailsInput) -> list[dict[str, Any]]:
    """List ZTW public-cloud account details (read-only)."""
    client = get_zscaler_client(service="ztw")
    qp: dict[str, Any] = {}
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    details, _, err = client.ztw.account_details.list_public_account_details(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZTW public account details: {err}")
    rows = [d.as_dict() if hasattr(d, "as_dict") else d for d in (details or [])]
    return shape_many([r for r in rows if isinstance(r, dict)])
