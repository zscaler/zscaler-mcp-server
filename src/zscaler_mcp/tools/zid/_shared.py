"""Shared ZIdentity (ZID) views + shapers.

The ZID user record surfaces in three places that should agree on shape:
``zid_list_users`` / ``zid_search_users`` (users.py) and ``zid_get_group_users``
/ ``zid_get_group_users_by_name`` (groups.py). Rather than redeclare the curated
user shape in both modules, the lean :class:`UserSummary` view and its shaper
live here so every "give me users" tool returns the identical agent-facing shape.

Mirrors the user fields of v1's ``zscaler_mcp/tools/zid/users.py`` and
``groups.py``.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from zscaler_mcp.shaping import AgentView, pick

__all__ = ["UserSummary", "shape_user_summary"]


class UserSummary(AgentView):
    """Lean view — what an agent needs to identify and reference a user."""

    id: str = Field(description="User ID. Use this in follow-up calls.")
    login_name: Optional[str] = Field(
        default=None, description="Login name (usually the username or UPN)."
    )
    display_name: Optional[str] = Field(default=None, description="Human-readable display name.")
    primary_email: Optional[str] = Field(default=None, description="Primary email address.")
    status: Optional[Any] = Field(
        default=None, description="Account status (decision-bearing; e.g. enabled flag)."
    )
    idp_name: Optional[str] = Field(
        default=None, description="Identity provider that owns this user, if any (relational)."
    )


def shape_user_summary(raw: dict[str, Any]) -> UserSummary:
    """Map a raw SDK user dict onto the lean user-summary view."""
    idp = raw.get("idp") if isinstance(raw.get("idp"), dict) else {}
    return UserSummary(
        id=str(pick(raw, "id", default="")),
        login_name=pick(raw, "login_name", "loginName"),
        display_name=pick(raw, "display_name", "displayName"),
        primary_email=pick(raw, "primary_email", "primaryEmail"),
        status=pick(raw, "status"),
        idp_name=pick(idp, "name", "display_name", "displayName"),
    )
