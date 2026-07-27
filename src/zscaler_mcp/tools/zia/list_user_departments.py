"""ZIA user departments — read-only manager.

Mirrors v1's ``list_user_departments.py`` exactly: a single multiplexed read tool
registered under the v1 name ``get_zia_user_departments`` (list with optional
filters/sorting, or fetch one by ID via the full or lite endpoint). Backed by
``client.zia.user_management``.

The department records are returned exactly as the ZIA API provides them
instead of the raw SDK dict, to keep token usage low.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many


class DepartmentInput(BaseModel):
    """Inputs for reading ZIA user departments.

    Provide nothing to list all; provide ``department_id`` to fetch one (returned as
    a single-item list); use ``action='read_lite'`` with ``department_id`` for the
    lite get endpoint.
    """

    action: Annotated[
        Literal["read", "read_lite"],
        Field(default="read", description="'read' for full data, 'read_lite' for the lite get."),
    ] = "read"
    department_id: Annotated[
        Optional[str], Field(default=None, description="Department ID for direct lookup.")
    ] = None
    limit_search: Annotated[
        Optional[bool],
        Field(default=None, description="If true, limit the search to the department name only."),
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on department name.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, description="Items per page (max 1000).")
    ] = None
    sort_by: Annotated[
        Optional[Literal["id", "name", "expiry", "status", "external_id", "rank"]],
        Field(default=None, description="Sort field."),
    ] = None
    sort_order: Annotated[
        Optional[Literal["asc", "desc", "rule_execution"]],
        Field(default=None, description="Sort order."),
    ] = None


@tool(
    action=READ,
    service="zia",
    toolset="zia_users",
    input_model=DepartmentInput,
    is_list=True,
)
def get_zia_user_departments(args: DepartmentInput) -> list[dict[str, Any]]:
    """Read ZIA user departments: list with filters, or fetch one by ID (read-only)."""
    client = get_zscaler_client(service="zia")
    api = client.zia.user_management

    if args.department_id:
        if args.action == "read_lite":
            dept, _, err = api.get_department_lite(args.department_id)
        else:
            dept, _, err = api.get_department(args.department_id)
        if err:
            raise RuntimeError(f"Failed to get department {args.department_id}: {err}")
        return shape_many([dept.as_dict()])

    qp: dict[str, Any] = {}
    if args.limit_search is not None:
        qp["limit_search"] = args.limit_search
    if args.search is not None:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = args.page
    if args.page_size is not None:
        if args.page_size <= 0 or args.page_size > 1000:
            raise ValueError("page_size must be between 1 and 1000")
        qp["page_size"] = args.page_size
    if args.sort_by is not None:
        qp["sort_by"] = args.sort_by
    if args.sort_order is not None:
        qp["sort_order"] = args.sort_order
    depts, _, err = api.list_departments(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list departments: {err}")
    return shape_many([d.as_dict() for d in (depts or [])])
