"""ZPA SCIM Groups — read-only lookup.

Mirrors v1's ``get_scim_groups.py``. Registered under the exact v1 tool name
``get_zpa_scim_group``: fetches one SCIM group by ID, or lists all SCIM groups
under a named IdP (resolved to its ID internally). Output is the curated
``RefItem`` view (id + name).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zpa._refs import resolve_idp_id


class ScimGroupInput(BaseModel):
    """Inputs for reading ZPA SCIM groups."""

    scim_group_id: Annotated[
        Optional[str], Field(default=None, description="SCIM group ID for direct lookup.")
    ] = None
    idp_name: Annotated[
        Optional[str],
        Field(default=None, description="IdP display name (required when listing groups)."),
    ] = None
    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match.")
    ] = None


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_idp",
    name="get_zpa_scim_group",
    input_model=ScimGroupInput,
    is_list=True,
)
def get_zpa_scim_group(args: ScimGroupInput) -> list[dict[str, Any]]:
    """Fetch one ZPA SCIM group by ID, or list all groups under a named IdP (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search

    if args.scim_group_id:
        group, _, err = client.zpa.scim_groups.get_scim_group(args.scim_group_id, query_params=qp)
        if err:
            raise RuntimeError(f"Failed to fetch SCIM group {args.scim_group_id}: {err}")
        return shape_many([group.as_dict()])

    if not args.idp_name:
        raise ValueError("idp_name is required to list SCIM groups")
    idp_id = resolve_idp_id(client, args.idp_name)
    groups, _, err = client.zpa.scim_groups.list_scim_groups(idp_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list SCIM groups for IdP '{args.idp_name}': {err}")
    return shape_many([g.as_dict() for g in (groups or [])])
