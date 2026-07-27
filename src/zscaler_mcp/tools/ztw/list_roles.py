"""ZTW admin roles — read-only.

Mirrors v1's ``list_roles.py``. Backed by ``client.ztw.admin_roles``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class ListRolesInput(BaseModel):
    """Inputs for listing ZTW admin roles."""

    include_auditor_role: Annotated[
        Optional[bool], Field(default=None, description="Include auditor roles.")
    ] = None
    include_partner_role: Annotated[
        Optional[bool], Field(default=None, description="Include partner/admin roles.")
    ] = None
    include_api_roles: Annotated[
        Optional[bool], Field(default=None, description="Include API roles.")
    ] = None
    role_ids: Annotated[
        Optional[list[str]], Field(default=None, description="Filter to these role IDs.")
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Search string to filter roles by name.")
    ] = None


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListRolesInput,
    is_list=True,
)
def ztw_list_roles(args: ListRolesInput) -> list[dict[str, Any]]:
    """List ZTW admin roles (read-only)."""
    client = get_zscaler_client(service="ztw")

    qp: dict[str, Any] = {}
    if args.include_auditor_role is not None:
        qp["include_auditor_role"] = args.include_auditor_role
    if args.include_partner_role is not None:
        qp["include_partner_role"] = args.include_partner_role
    if args.include_api_roles is not None:
        qp["include_api_roles"] = args.include_api_roles
    if args.role_ids:
        qp["id"] = args.role_ids
    if args.search:
        qp["search"] = args.search

    roles, _, err = client.ztw.admin_roles.list_roles(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZTW admin roles: {err}")

    return shape_many([r.as_dict() for r in (roles or [])])
