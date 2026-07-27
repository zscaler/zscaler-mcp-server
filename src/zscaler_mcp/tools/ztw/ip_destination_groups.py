"""ZTW IP destination groups — list, list-lite, create, delete.

Mirrors v1's ``zscaler_mcp/tools/ztw/ip_destination_groups.py`` SDK calls
(``client.ztw.ip_destination_groups``) but returns full records. The full and
``*_lite`` list endpoints are exposed as separate tools, matching v1.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.utils import parse_list
from zscaler_mcp.common.ztw_helpers import validate_and_convert_country_codes
from zscaler_mcp.registry import CREATE, DELETE, READ, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListDestinationGroupsInput(BaseModel):
    """Inputs for listing ZTW IP destination groups."""

    exclude_type: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Exclude groups of this type (DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, DSTN_OTHER).",
        ),
    ] = None


class CreateDestinationGroupInput(BaseModel):
    """Inputs for creating a ZTW IP destination group."""

    name: Annotated[str, Field(description="Name of the destination group.")]
    type: Annotated[
        str,
        Field(
            pattern="^(DSTN_IP|DSTN_FQDN|DSTN_DOMAIN|DSTN_OTHER)$",
            description="Group type: DSTN_IP, DSTN_FQDN, DSTN_DOMAIN, or DSTN_OTHER.",
        ),
    ]
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    addresses: Annotated[
        Optional[list[str]],
        Field(default=None, description="IPs/FQDNs. Required for DSTN_IP or DSTN_FQDN."),
    ] = None
    countries: Annotated[
        Optional[list[str]],
        Field(
            default=None,
            description=(
                "Country names or ISO codes (e.g. 'Canada', 'US'); converted to "
                "COUNTRY_XX. Only valid when type is DSTN_OTHER."
            ),
        ),
    ] = None


class DeleteDestinationGroupInput(BaseModel):
    """Inputs for deleting a ZTW IP destination group (destructive)."""

    group_id: Annotated[str, Field(description="Group ID (string, even if numeric).")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")






# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListDestinationGroupsInput,
    is_list=True,
)
def ztw_list_ip_destination_groups(args: ListDestinationGroupsInput) -> list[dict[str, Any]]:
    """List ZTW IP destination groups.

    Use `exclude_type` to omit a group type (e.g. exclude DSTN_FQDN). Read-only.
    """
    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_destination_groups

    qp: dict[str, Any] = {"exclude_type": args.exclude_type} if args.exclude_type else {}
    groups, _, err = api.list_ip_destination_groups(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP destination groups: {err}")

    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=READ,
    service="ztw",
    toolset="ztw",
    input_model=ListDestinationGroupsInput,
    is_list=True,
)
def ztw_list_ip_destination_groups_lite(
    args: ListDestinationGroupsInput,
) -> list[dict[str, Any]]:
    """List ZTW IP destination groups via the lighter SDK endpoint (read-only).

    Same records as `ztw_list_ip_destination_groups`; uses the lite endpoint.
    """
    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_destination_groups

    qp: dict[str, Any] = {"exclude_type": args.exclude_type} if args.exclude_type else {}
    groups, _, err = api.list_ip_destination_groups_lite(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list IP destination groups (lite): {err}")

    return shape_many([g.as_dict() for g in (groups or [])])


@tool(
    action=CREATE,
    service="ztw",
    toolset="ztw",
    input_model=CreateDestinationGroupInput,
    is_list=False,
)
def ztw_create_ip_destination_group(args: CreateDestinationGroupInput) -> dict[str, Any]:
    """Create a ZTW IP destination group (write).

    Country names/codes are converted to COUNTRY_XX and are only valid for
    DSTN_OTHER groups. Gated by HMAC write-confirmation and `--write-tools`.
    """
    addresses = parse_list(args.addresses) if args.addresses is not None else None

    countries = None
    if args.countries:
        if args.type != "DSTN_OTHER":
            raise ValueError("Countries are only supported when type is DSTN_OTHER")
        countries = validate_and_convert_country_codes(args.countries)

    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_destination_groups

    group, _, err = api.add_ip_destination_group(
        name=args.name,
        description=args.description,
        type=args.type,
        addresses=addresses,
        countries=countries,
    )
    if err:
        raise RuntimeError(f"Failed to create IP destination group: {err}")
    return shape_one(group.as_dict())


@tool(
    action=DELETE,
    service="ztw",
    toolset="ztw",
    input_model=DeleteDestinationGroupInput,
    output_view=OperationResult,
    is_list=False,
)
def ztw_delete_ip_destination_group(args: DeleteDestinationGroupInput) -> dict[str, Any]:
    """Delete a ZTW IP destination group (destructive write).

    Cannot be undone. Gated by HMAC write-confirmation and `--write-tools`.
    """
    if not args.group_id:
        raise ValueError("group_id is required for delete")

    client = get_zscaler_client(service="ztw")
    api = client.ztw.ip_destination_groups

    _, _, err = api.delete_ip_destination_group(args.group_id)
    if err:
        raise RuntimeError(f"Failed to delete IP destination group {args.group_id}: {err}")
    return OperationResult(
        success=True, message=f"IP destination group {args.group_id} deleted successfully."
    ).model_dump()
