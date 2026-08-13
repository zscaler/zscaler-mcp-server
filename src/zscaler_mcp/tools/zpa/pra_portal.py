"""ZPA Privileged Remote Access (PRA) portals (v2).

Mirrors v1's ``pra_portal.py``:

    zpa_list/get/create/update/delete_pra_portal

PRA credentials live in the sibling ``pra_credential.py`` module — the two PRA
resources are kept in separate files to mirror v1's layout.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListPortalsInput(BaseModel):
    """Inputs for listing PRA portals."""

    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match on `name`.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=500, description="Items per page (API default 20, max 500)."),
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class GetPortalInput(BaseModel):
    """Inputs for getting one PRA portal."""

    portal_id: Annotated[str, Field(description="PRA portal ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class CreatePortalInput(BaseModel):
    """Inputs for creating a PRA portal."""

    name: Annotated[str, Field(description="Display name for the portal.")]
    domain: Annotated[str, Field(description="Portal domain (FQDN users browse to).")]
    certificate_id: Annotated[
        Optional[str],
        Field(default=None, description="BA certificate ID. Auto-resolved from `name` if omitted."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    enabled: Annotated[bool, Field(default=True, description="Whether the portal is enabled.")] = (
        True
    )
    user_notification: Annotated[
        Optional[str], Field(default=None, description="User notification message.")
    ] = None
    user_notification_enabled: Annotated[
        Optional[bool], Field(default=None, description="Whether user notifications are enabled.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdatePortalInput(BaseModel):
    """Inputs for updating a PRA portal (partial)."""

    portal_id: Annotated[str, Field(description="PRA portal ID (string, even if numeric).")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    domain: Annotated[Optional[str], Field(default=None, description="New portal domain.")] = None
    certificate_id: Annotated[
        Optional[str], Field(default=None, description="BA certificate ID.")
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    enabled: Annotated[
        Optional[bool], Field(default=None, description="Enable/disable the portal.")
    ] = None
    user_notification: Annotated[
        Optional[str], Field(default=None, description="User notification message.")
    ] = None
    user_notification_enabled: Annotated[
        Optional[bool], Field(default=None, description="Whether user notifications are enabled.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeletePortalInput(BaseModel):
    """Inputs for deleting a PRA portal (destructive)."""

    portal_id: Annotated[str, Field(description="PRA portal ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_pra",
    input_model=ListPortalsInput,
    is_list=True,
)
def zpa_list_pra_portals(args: ListPortalsInput) -> list[dict[str, Any]]:
    """List ZPA PRA portals (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    portals, _, err = client.zpa.pra_portal.list_portals(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list PRA portals: {err}")
    return shape_many([p.as_dict() for p in (portals or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_pra",
    input_model=GetPortalInput,
    is_list=False,
)
def zpa_get_pra_portal(args: GetPortalInput) -> dict[str, Any]:
    """Get one ZPA PRA portal by ID (read-only)."""
    if not args.portal_id:
        raise ValueError("portal_id is required")
    client = get_zscaler_client(service="zpa")
    result, _, err = client.zpa.pra_portal.get_portal(
        args.portal_id, query_params={"microtenant_id": args.microtenant_id}
    )
    if err:
        raise RuntimeError(f"Failed to get PRA portal {args.portal_id}: {err}")
    return shape_one(result.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_pra",
    input_model=CreatePortalInput,
    is_list=False,
)
def zpa_create_pra_portal(args: CreatePortalInput) -> dict[str, Any]:
    """Create a ZPA PRA portal (write). Requires `--write-tools`.

    If `certificate_id` is omitted, the BA certificate is resolved by searching
    issued certificates for one whose name matches the portal `name`.
    """
    if not args.name or not args.domain:
        raise ValueError("name and domain are required")
    client = get_zscaler_client(service="zpa")
    certificate_id = args.certificate_id
    if not certificate_id:
        certs, _, err = client.zpa.certificates.list_issued_certificates(
            query_params={"search": args.name}
        )
        if err:
            raise RuntimeError(f"Failed to resolve certificate: {err}")
        if not certs:
            raise ValueError(
                f"No certificate found matching name '{args.name}'. Provide certificate_id explicitly."
            )
        certificate_id = certs[0].id
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "enabled": args.enabled,
        "domain": args.domain,
        "certificate_id": certificate_id,
        "user_notification": args.user_notification,
        "user_notification_enabled": args.user_notification_enabled,
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    created, _, err = client.zpa.pra_portal.add_portal(**payload)
    if err:
        raise RuntimeError(f"Failed to create PRA portal: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_pra",
    input_model=UpdatePortalInput,
    is_list=False,
)
def zpa_update_pra_portal(args: UpdatePortalInput) -> dict[str, Any]:
    """Update a ZPA PRA portal (write). Requires `--write-tools`."""
    if not args.portal_id:
        raise ValueError("portal_id is required")
    client = get_zscaler_client(service="zpa")
    fields: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "enabled": args.enabled,
        "domain": args.domain,
        "certificate_id": args.certificate_id,
        "user_notification": args.user_notification,
        "user_notification_enabled": args.user_notification_enabled,
    }
    if args.microtenant_id:
        fields["microtenant_id"] = args.microtenant_id
    updated, _, err = client.zpa.pra_portal.update_portal(args.portal_id, **fields)
    if err:
        raise RuntimeError(f"Failed to update PRA portal {args.portal_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_pra",
    input_model=DeletePortalInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_pra_portal(args: DeletePortalInput) -> dict[str, Any]:
    """Delete a ZPA PRA portal (destructive write).

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.portal_id:
        raise ValueError("portal_id is required")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.pra_portal.delete_portal(
        args.portal_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete PRA portal {args.portal_id}: {err}")
    return OperationResult(
        success=True, message=f"PRA portal {args.portal_id} deleted successfully."
    ).model_dump()
