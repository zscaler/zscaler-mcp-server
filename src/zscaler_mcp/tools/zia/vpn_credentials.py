"""ZIA VPN credentials — list, get, create, update, delete.

Mirrors v1's ``client.zia.traffic_vpn_credentials`` SDK calls. VPN credentials
back IPSec/IKE location onboarding. Writes are staged until
``zia_activate_configuration``.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, pick, shape_many

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListInput(BaseModel):
    search: Annotated[
        Optional[str], Field(default=None, description="Substring match on fqdn/ip/comments.")
    ] = None


class GetInput(BaseModel):
    credential_id: Annotated[str, Field(description="VPN credential ID (string, even if numeric).")]


class CreateInput(BaseModel):
    credential_type: Annotated[
        str,
        Field(pattern="^(IP|UFQDN)$", description="Credential type: IP or UFQDN."),
    ]
    pre_shared_key: Annotated[str, Field(description="IKE pre-shared key.")]
    ip_address: Annotated[
        Optional[str], Field(default=None, description="Static IP. Required for type IP.")
    ] = None
    fqdn: Annotated[
        Optional[str], Field(default=None, description="UFQDN. Required for type UFQDN.")
    ] = None
    comments: Annotated[Optional[str], Field(default=None, description="Admin notes.")] = None


class UpdateInput(BaseModel):
    credential_id: Annotated[str, Field(description="Credential ID to update.")]
    pre_shared_key: Annotated[
        Optional[str], Field(default=None, description="New IKE pre-shared key.")
    ] = None
    comments: Annotated[Optional[str], Field(default=None, description="New admin notes.")] = None


class DeleteInput(BaseModel):
    credential_id: Annotated[str, Field(description="Credential ID to delete.")]


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class VpnCredentialSummary(AgentView):
    id: str = Field(description="VPN credential ID. Use in location vpnCredentials payloads.")
    type: Optional[str] = Field(default=None, description="IP or UFQDN.")
    ip_address: Optional[str] = Field(default=None, description="Static IP (type IP).")
    fqdn: Optional[str] = Field(default=None, description="UFQDN (type UFQDN).")
    comments: Optional[str] = Field(default=None, description="Admin notes.")


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


# =============================================================================
# SHAPERS
# =============================================================================


def shape_summary(raw: dict[str, Any]) -> VpnCredentialSummary:
    return VpnCredentialSummary(
        id=str(pick(raw, "id", default="")),
        type=pick(raw, "type"),
        ip_address=pick(raw, "ip_address", "ipAddress"),
        fqdn=pick(raw, "fqdn"),
        comments=pick(raw, "comments"),
    )


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=ListInput,
    output_view=VpnCredentialSummary,
    is_list=True,
)
def zia_list_vpn_credentials(args: ListInput) -> list[dict[str, Any]]:
    """List ZIA VPN credentials as curated summaries (PSK never returned)."""
    client = get_zscaler_client(service="zia")
    qp = {"search": args.search} if args.search else {}
    creds, _, err = client.zia.traffic_vpn_credentials.list_vpn_credentials(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list VPN credentials: {err}")
    return shape_many([c.as_dict() for c in (creds or [])], shape_summary)


@tool(
    action=READ,
    service="zia",
    toolset="zia_locations",
    input_model=GetInput,
    output_view=VpnCredentialSummary,
    is_list=False,
)
def zia_get_vpn_credential(args: GetInput) -> dict[str, Any]:
    """Get a single ZIA VPN credential by ID."""
    client = get_zscaler_client(service="zia")
    cred, _, err = client.zia.traffic_vpn_credentials.get_vpn_credential(args.credential_id)
    if err:
        raise RuntimeError(f"Failed to get VPN credential {args.credential_id}: {err}")
    return shape_summary(cred.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zia",
    toolset="zia_locations",
    input_model=CreateInput,
    output_view=VpnCredentialSummary,
    is_list=False,
)
def zia_create_vpn_credential(args: CreateInput) -> dict[str, Any]:
    """Create a ZIA VPN credential (write). Activate after."""
    if args.credential_type == "IP" and not args.ip_address:
        raise ValueError("ip_address is required when credential_type is IP.")
    if args.credential_type == "UFQDN" and not args.fqdn:
        raise ValueError("fqdn is required when credential_type is UFQDN.")
    client = get_zscaler_client(service="zia")
    cred, _, err = client.zia.traffic_vpn_credentials.add_vpn_credential(
        credential_type=args.credential_type,
        pre_shared_key=args.pre_shared_key,
        ip_address=args.ip_address,
        fqdn=args.fqdn,
        comments=args.comments,
    )
    if err:
        raise RuntimeError(f"Failed to create VPN credential: {err}")
    return shape_summary(cred.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zia",
    toolset="zia_locations",
    input_model=UpdateInput,
    output_view=VpnCredentialSummary,
    is_list=False,
)
def zia_update_vpn_credential(args: UpdateInput) -> dict[str, Any]:
    """Update a ZIA VPN credential (write). Activate after."""
    client = get_zscaler_client(service="zia")
    cred, _, err = client.zia.traffic_vpn_credentials.update_vpn_credential(
        credential_id=args.credential_id,
        pre_shared_key=args.pre_shared_key,
        comments=args.comments,
    )
    if err:
        raise RuntimeError(f"Failed to update VPN credential {args.credential_id}: {err}")
    return shape_summary(cred.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zia",
    toolset="zia_locations",
    input_model=DeleteInput,
    output_view=OperationResult,
    is_list=False,
)
def zia_delete_vpn_credential(args: DeleteInput) -> dict[str, Any]:
    """Delete a ZIA VPN credential (destructive). Activate after."""
    client = get_zscaler_client(service="zia")
    _, _, err = client.zia.traffic_vpn_credentials.delete_vpn_credential(args.credential_id)
    if err:
        raise RuntimeError(f"Failed to delete VPN credential {args.credential_id}: {err}")
    return OperationResult(
        success=True, message=f"VPN credential {args.credential_id} deleted successfully."
    ).model_dump()
