"""ZPA Privileged Remote Access (PRA) credentials (v2).

Mirrors v1's ``pra_credential.py``:

    zpa_list/get/create/update/delete_pra_credential

PRA portals live in the sibling ``pra_portal.py`` module — the two PRA
resources are kept in separate files to mirror v1's layout.

Security note: PRA credential secrets (password / private_key) are *inputs*
only. The curated credential views deliberately NEVER echo the secret back —
they surface the credential's identity, type, and provenance, nothing more.
The shared output sanitizer is a second line of defence, but the right place
to keep secrets off the wire is to not put them in the view at all.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListCredentialsInput(BaseModel):
    """Inputs for listing PRA credentials."""

    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match on `name`.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class GetCredentialInput(BaseModel):
    """Inputs for getting one PRA credential."""

    credential_id: Annotated[str, Field(description="PRA credential ID (string, even if numeric).")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


CredentialType = Literal["USERNAME_PASSWORD", "PASSWORD", "SSH_KEY"]


class CreateCredentialInput(BaseModel):
    """Inputs for creating a PRA credential. Secrets are write-only inputs."""

    name: Annotated[str, Field(description="Display name for the credential.")]
    credential_type: Annotated[CredentialType, Field(description="Credential type.")]
    username: Annotated[
        Optional[str], Field(default=None, description="Username (USERNAME_PASSWORD / SSH_KEY).")
    ] = None
    password: Annotated[
        Optional[str],
        Field(default=None, description="Password (USERNAME_PASSWORD / PASSWORD). Write-only."),
    ] = None
    private_key: Annotated[
        Optional[str], Field(default=None, description="Private key (SSH_KEY). Write-only.")
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    user_domain: Annotated[Optional[str], Field(default=None, description="User domain.")] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateCredentialInput(BaseModel):
    """Inputs for updating a PRA credential. credential_type cannot change."""

    credential_id: Annotated[str, Field(description="PRA credential ID (string, even if numeric).")]
    credential_type: Annotated[
        CredentialType, Field(description="Must match the existing credential type.")
    ]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    username: Annotated[
        Optional[str], Field(default=None, description="Username (USERNAME_PASSWORD / SSH_KEY).")
    ] = None
    password: Annotated[
        Optional[str],
        Field(default=None, description="Password (USERNAME_PASSWORD / PASSWORD). Write-only."),
    ] = None
    private_key: Annotated[
        Optional[str], Field(default=None, description="Private key (SSH_KEY). Write-only.")
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    user_domain: Annotated[Optional[str], Field(default=None, description="User domain.")] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteCredentialInput(BaseModel):
    """Inputs for deleting a PRA credential (destructive)."""

    credential_id: Annotated[str, Field(description="PRA credential ID (string, even if numeric).")]
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


def _credential_body(
    *,
    credential_type: str,
    name,
    description,
    user_domain,
    microtenant_id,
    username,
    password,
    private_key,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": name,
        "description": description,
        "credential_type": credential_type,
        "user_domain": user_domain,
        "microtenant_id": microtenant_id,
    }
    if credential_type == "USERNAME_PASSWORD":
        if not username or not password:
            raise ValueError("USERNAME_PASSWORD requires 'username' and 'password'")
        body.update({"user_name": username, "password": password})
    elif credential_type == "PASSWORD":
        if not password:
            raise ValueError("PASSWORD type requires 'password'")
        body.update({"password": password})
    elif credential_type == "SSH_KEY":
        if not username or not private_key:
            raise ValueError("SSH_KEY requires 'username' and 'private_key'")
        body.update({"user_name": username, "private_key": private_key})
    else:
        raise ValueError(f"Invalid credential_type: {credential_type}")
    return body


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_pra",
    input_model=ListCredentialsInput,
    is_list=True,
)
def zpa_list_pra_credentials(args: ListCredentialsInput) -> list[dict[str, Any]]:
    """List ZPA PRA credentials (read-only). Secrets are never returned."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    creds, _, err = client.zpa.pra_credential.list_credentials(query_params=qp)
    if err:
        raise RuntimeError(f"Failed to list PRA credentials: {err}")
    return shape_many([c.as_dict() for c in (creds or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_pra",
    input_model=GetCredentialInput,
    is_list=False,
)
def zpa_get_pra_credential(args: GetCredentialInput) -> dict[str, Any]:
    """Get one ZPA PRA credential by ID (read-only). Secrets are never returned."""
    if not args.credential_id:
        raise ValueError("credential_id is required")
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    result, _, err = client.zpa.pra_credential.get_credential(args.credential_id, query_params=qp)
    if err:
        raise RuntimeError(f"Failed to get PRA credential {args.credential_id}: {err}")
    return shape_one(result.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_pra",
    input_model=CreateCredentialInput,
    is_list=False,
)
def zpa_create_pra_credential(args: CreateCredentialInput) -> dict[str, Any]:
    """Create a ZPA PRA credential (write). Requires `--write-tools`.

    Secrets (password / private_key) are write-only — they are sent to the API
    but never echoed back in the response.
    """
    if not args.name or not args.credential_type:
        raise ValueError("name and credential_type are required")
    client = get_zscaler_client(service="zpa")
    body = _credential_body(
        credential_type=args.credential_type,
        name=args.name,
        description=args.description,
        user_domain=args.user_domain,
        microtenant_id=args.microtenant_id,
        username=args.username,
        password=args.password,
        private_key=args.private_key,
    )
    created, _, err = client.zpa.pra_credential.add_credential(**body)
    if err:
        raise RuntimeError(f"Failed to create PRA credential: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_pra",
    input_model=UpdateCredentialInput,
    is_list=False,
)
def zpa_update_pra_credential(args: UpdateCredentialInput) -> dict[str, Any]:
    """Update a ZPA PRA credential (write). credential_type cannot change.

    Requires `--write-tools`. Secrets are write-only.
    """
    if not args.credential_id:
        raise ValueError("credential_id is required")
    client = get_zscaler_client(service="zpa")
    existing, _, err = client.zpa.pra_credential.get_credential(
        args.credential_id, query_params=None
    )
    if err:
        raise RuntimeError(f"Failed to fetch existing credential: {err}")
    existing_type = getattr(existing, "credential_type", None)
    if existing_type and existing_type != args.credential_type:
        raise ValueError(
            "Cannot change credential_type. Delete and recreate the credential instead."
        )
    body = _credential_body(
        credential_type=args.credential_type,
        name=args.name,
        description=args.description,
        user_domain=args.user_domain,
        microtenant_id=args.microtenant_id,
        username=args.username,
        password=args.password,
        private_key=args.private_key,
    )
    updated, _, err = client.zpa.pra_credential.update_credential(args.credential_id, **body)
    if err:
        raise RuntimeError(f"Failed to update PRA credential {args.credential_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_pra",
    input_model=DeleteCredentialInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_pra_credential(args: DeleteCredentialInput) -> dict[str, Any]:
    """Delete a ZPA PRA credential (destructive write).

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.credential_id:
        raise ValueError("credential_id is required")
    client = get_zscaler_client(service="zpa")
    _, _, err = client.zpa.pra_credential.delete_credential(
        args.credential_id, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete PRA credential {args.credential_id}: {err}")
    return OperationResult(
        success=True, message=f"PRA credential {args.credential_id} deleted successfully."
    ).model_dump()
