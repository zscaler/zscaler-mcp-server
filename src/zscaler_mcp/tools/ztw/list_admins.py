"""ZTW admin users — read-only.

Mirrors v1's ``list_admins.py``. Backed by ``client.ztw.admin_users``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class ListAdminsInput(BaseModel):
    """Inputs for listing ZTW admin users."""

    include_auditor_users: Annotated[
        Optional[bool], Field(default=None, description="Include auditor users.")
    ] = None
    include_admin_users: Annotated[
        Optional[bool], Field(default=None, description="Include admin users.")
    ] = None
    include_api_roles: Annotated[
        Optional[bool], Field(default=None, description="Include API roles.")
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Search string to filter by.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page offset.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=1000, description="Records per page.")
    ] = None
    version: Annotated[
        Optional[int], Field(default=None, description="Admins from a backup version.")
    ] = None




@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListAdminsInput,
    is_list=True,
)
def ztw_list_admins(args: ListAdminsInput) -> list[dict[str, Any]]:
    """List ZTW admin users (read-only)."""
    client = get_zscaler_client(service="ztw")

    qp: dict[str, Any] = {}
    if args.include_auditor_users is not None:
        qp["include_auditor_users"] = args.include_auditor_users
    if args.include_admin_users is not None:
        qp["include_admin_users"] = args.include_admin_users
    if args.include_api_roles is not None:
        qp["include_api_roles"] = args.include_api_roles
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        qp["page_size"] = args.page_size
    if args.version is not None:
        qp["version"] = args.version

    admins, _, err = client.ztw.admin_users.list_admins(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZTW admins: {err}")

    return shape_many([a.as_dict() for a in (admins or [])])
