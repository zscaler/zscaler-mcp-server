"""ZIA users — read-only manager.

Mirrors v1's ``list_users.py`` exactly: a single multiplexed read tool registered
under the v1 name ``get_zia_users`` (list users with optional filters, or fetch one
by ID). Backed by ``client.zia.user_management``.

Only the output is changed vs v1: the curated ``UserSummary`` view is returned
instead of the raw SDK dict, to keep token usage low.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many


class UsersInput(BaseModel):
    """Inputs for reading ZIA users.

    Provide nothing to list all; provide ``user_id`` to fetch one (returned as a
    single-item list); use ``name`` / ``dept`` / ``group`` to filter the list.
    """

    user_id: Annotated[
        Optional[str], Field(default=None, description="User ID for direct lookup.")
    ] = None
    name: Annotated[Optional[str], Field(default=None, description="Filter by user name.")] = None
    dept: Annotated[
        Optional[str], Field(default=None, description="Filter by department name.")
    ] = None
    group: Annotated[Optional[str], Field(default=None, description="Filter by group name.")] = None
    page: Annotated[Optional[int], Field(default=None, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, description="Items per page (max 1000).")
    ] = None


class UserSummary(AgentView):
    id: str = Field(description="User ID.")
    name: Optional[str] = Field(default=None, description="User display name.")
    email: Optional[str] = Field(default=None, description="User email.")
    department: Optional[str] = Field(default=None, description="Department name.")
    group_count: int = Field(description="Number of group memberships.")


def shape_summary(raw: dict[str, Any]) -> UserSummary:
    dept = raw.get("department")
    dept_name = dept.get("name") if isinstance(dept, dict) else dept
    groups = raw.get("groups") or []
    return UserSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        email=pick(raw, "email"),
        department=dept_name,
        group_count=len(groups) if isinstance(groups, list) else 0,
    )


@tool(
    action=READ,
    service="zia",
    toolset="zia_users",
    input_model=UsersInput,
    output_view=UserSummary,
    is_list=True,
)
def get_zia_users(args: UsersInput) -> list[dict[str, Any]]:
    """Read ZIA users: list with optional filters, or fetch one by ID (read-only)."""
    client = get_zscaler_client(service="zia")
    api = client.zia.user_management

    if args.user_id:
        user, _, err = api.get_user(args.user_id)
        if err:
            raise RuntimeError(f"Failed to get user {args.user_id}: {err}")
        return shape_many([user.as_dict()], shape_summary)

    qp: dict[str, Any] = {}
    for key in ("name", "dept", "group", "page", "page_size"):
        value = getattr(args, key)
        if value is not None:
            qp[key] = value
    if args.page_size is not None and (args.page_size <= 0 or args.page_size > 1000):
        raise ValueError("page_size must be between 1 and 1000")
    users, _, err = api.list_users(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list users: {err}")
    return shape_many([u.as_dict() for u in (users or [])], shape_summary)
