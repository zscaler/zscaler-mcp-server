"""ZDX application users — agent-first v2 tools.

Mirrors v1's ``zscaler_mcp/tools/zdx/get_application_user.py``
(zdx_list_application_users, zdx_get_application_user).

ZDX SDK quirk: ``list_app_users`` returns ``[users_obj]`` whose rows hang off
``users_obj.users``; ``get_app_user`` returns ``[user_detail]``. The list view is
a lean triage row; the single-user view keeps the nested per-device detail.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many, shape_one
from zscaler_mcp.tools.zdx._common import scope_query_params, unwrap_nested

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListApplicationUsersInput(BaseModel):
    """Inputs for listing users/devices that accessed a ZDX application."""

    app_id: Annotated[str, Field(description="Application ID (string, even if numeric).")]
    score_bucket: Annotated[
        Optional[Literal["poor", "okay", "good"]],
        Field(
            default=None,
            description="ZDX score bucket: 'poor' (0-33), 'okay' (34-65), 'good' (66-100).",
        ),
    ] = None
    location_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by location ID(s).")
    ] = None
    department_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by department ID(s).")
    ] = None
    geo_id: Annotated[
        Optional[list[str]], Field(default=None, description="Filter by geolocation ID(s).")
    ] = None
    since: Annotated[
        Optional[int],
        Field(default=None, ge=1, description="Look-back window in HOURS (ZDX default 2h)."),
    ] = None


class GetApplicationUserInput(BaseModel):
    """Inputs for getting one user's detail for a ZDX application."""

    app_id: Annotated[str, Field(description="Application ID (string, even if numeric).")]
    user_id: Annotated[str, Field(description="User ID (string, even if numeric).")]
    since: Annotated[
        Optional[int],
        Field(default=None, ge=1, description="Look-back window in HOURS (ZDX default 2h)."),
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=ListApplicationUsersInput,
    is_list=True,
)
def zdx_list_application_users(args: ListApplicationUsersInput) -> list[dict[str, Any]]:
    """List users/devices that accessed a ZDX application, as curated rows.

    Read-only. Returns one triage row per user (id, name, email, ZDX score).
    Filter by `score_bucket` (poor/okay/good), location/department/geo, and the
    `since` HOURS window (default 2h). Use a returned `id` with
    `zdx_get_application_user`.
    """
    if not args.app_id:
        raise ValueError("app_id is required")

    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(
        location_id=args.location_id,
        department_id=args.department_id,
        geo_id=args.geo_id,
        since=args.since,
        score_bucket=args.score_bucket,
    )

    result, _, err = client.zdx.apps.list_app_users(args.app_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list ZDX application users for {args.app_id}: {err}")

    raw_users = unwrap_nested(result, "users")
    return shape_many(raw_users)


@tool(
    action=READ,
    service="zdx",
    toolset="zdx_reports",
    input_model=GetApplicationUserInput,
    is_list=False,
    wire_format=WireFormat.JSON,
)
def zdx_get_application_user(args: GetApplicationUserInput) -> dict[str, Any]:
    """Get one user's ZDX detail for an application (per-device breakdown).

    Read-only. Returns the user's score plus the nested per-device metrics for
    the `since` HOURS window (default 2h). Use `app_id` from
    `zdx_list_applications` and `user_id` from `zdx_list_application_users`.
    """
    if not args.app_id:
        raise ValueError("app_id is required")
    if not args.user_id:
        raise ValueError("user_id is required")

    client = get_zscaler_client(service="zdx")
    qp = scope_query_params(since=args.since)

    result, _, err = client.zdx.apps.get_app_user(args.app_id, args.user_id, query_params=qp)
    if err:
        raise RuntimeError(
            f"Failed to get ZDX application user {args.user_id} for {args.app_id}: {err}"
        )

    if result and len(result) > 0:
        return shape_one(result[0].as_dict())
    return shape_one({})
