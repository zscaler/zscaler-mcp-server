"""ZPA provisioning keys (read + write).

Mirrors v1's ``provisioning_key.py``. Provisioning keys enroll app connectors
or service edges into their respective groups.

    zpa_list_provisioning_keys     (READ)
    zpa_get_provisioning_key       (READ)
    zpa_create_provisioning_key    (CREATE)
    zpa_update_provisioning_key    (UPDATE)
    zpa_delete_provisioning_key    (DELETE)
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

KeyType = Literal["connector", "service_edge"]


class ListKeysInput(BaseModel):
    """Inputs for listing provisioning keys."""

    key_type: Annotated[KeyType, Field(description="Key type: 'connector' or 'service_edge'.")]
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


class GetKeyInput(BaseModel):
    """Inputs for getting one provisioning key."""

    key_id: Annotated[str, Field(description="Provisioning key ID (string, even if numeric).")]
    key_type: Annotated[KeyType, Field(description="Key type: 'connector' or 'service_edge'.")]


class CreateKeyInput(BaseModel):
    """Inputs for creating a provisioning key."""

    name: Annotated[str, Field(description="Display name for the key.")]
    key_type: Annotated[KeyType, Field(description="Key type: 'connector' or 'service_edge'.")]
    max_usage: Annotated[int, Field(ge=1, description="Maximum enrollment count for the key.")]
    component_id: Annotated[
        str,
        Field(description="App Connector Group ID or Service Edge Group ID this key enrolls into."),
    ]
    enrollment_cert_id: Annotated[
        Optional[str],
        Field(default=None, description="Enrollment certificate ID (required for 'connector')."),
    ] = None
    description: Annotated[Optional[str], Field(default=None, description="Admin description.")] = (
        None
    )
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class UpdateKeyInput(BaseModel):
    """Inputs for updating a provisioning key (partial)."""

    key_id: Annotated[str, Field(description="Provisioning key ID (string, even if numeric).")]
    key_type: Annotated[KeyType, Field(description="Key type: 'connector' or 'service_edge'.")]
    name: Annotated[Optional[str], Field(default=None, description="New display name.")] = None
    description: Annotated[Optional[str], Field(default=None, description="New description.")] = (
        None
    )
    max_usage: Annotated[Optional[int], Field(default=None, ge=1, description="New max usage.")] = (
        None
    )
    component_id: Annotated[Optional[str], Field(default=None, description="New component ID.")] = (
        None
    )
    enrollment_cert_id: Annotated[
        Optional[str], Field(default=None, description="Enrollment certificate ID.")
    ] = None
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class DeleteKeyInput(BaseModel):
    """Inputs for deleting a provisioning key (destructive)."""

    key_id: Annotated[str, Field(description="Provisioning key ID (string, even if numeric).")]
    key_type: Annotated[KeyType, Field(description="Key type: 'connector' or 'service_edge'.")]
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=ListKeysInput,
    is_list=True,
)
def zpa_list_provisioning_keys(args: ListKeysInput) -> list[dict[str, Any]]:
    """List ZPA provisioning keys of a given type (read-only)."""
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
    keys, _, err = client.zpa.provisioning.list_provisioning_keys(
        key_type=args.key_type, query_params=qp
    )
    if err:
        raise RuntimeError(f"Failed to list provisioning keys: {err}")
    return shape_many([k.as_dict() for k in (keys or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=GetKeyInput,
    is_list=False,
)
def zpa_get_provisioning_key(args: GetKeyInput) -> dict[str, Any]:
    """Get one ZPA provisioning key by ID and type (read-only)."""
    if not args.key_id:
        raise ValueError("key_id is required")
    client = get_zscaler_client(service="zpa")
    result, _, err = client.zpa.provisioning.get_provisioning_key(
        key_id=args.key_id, key_type=args.key_type, query_params=None
    )
    if err:
        raise RuntimeError(f"Failed to get provisioning key {args.key_id}: {err}")
    return shape_one(result.as_dict())


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=CreateKeyInput,
    is_list=False,
)
def zpa_create_provisioning_key(args: CreateKeyInput) -> dict[str, Any]:
    """Create a ZPA provisioning key (write). Requires `--write-tools`.

    `enrollment_cert_id` is required when `key_type` is 'connector'.
    """
    if not args.name or not args.component_id:
        raise ValueError("name and component_id are required")
    if args.key_type == "connector" and not args.enrollment_cert_id:
        raise ValueError("enrollment_cert_id is required for 'connector' key_type")
    client = get_zscaler_client(service="zpa")
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "max_usage": args.max_usage,
        "component_id": args.component_id,
        "enrollment_cert_id": args.enrollment_cert_id,
    }
    if args.microtenant_id:
        payload["microtenant_id"] = args.microtenant_id
    created, _, err = client.zpa.provisioning.add_provisioning_key(
        key_type=args.key_type, **payload
    )
    if err:
        raise RuntimeError(f"Failed to create provisioning key: {err}")
    return shape_one(created.as_dict())


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=UpdateKeyInput,
    is_list=False,
)
def zpa_update_provisioning_key(args: UpdateKeyInput) -> dict[str, Any]:
    """Update a ZPA provisioning key (write). Requires `--write-tools`."""
    if not args.key_id:
        raise ValueError("key_id is required")
    client = get_zscaler_client(service="zpa")
    update_data: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
        "max_usage": args.max_usage,
        "component_id": args.component_id,
        "enrollment_cert_id": args.enrollment_cert_id,
    }
    if args.microtenant_id:
        update_data["microtenant_id"] = args.microtenant_id
    updated, _, err = client.zpa.provisioning.update_provisioning_key(
        key_id=args.key_id, key_type=args.key_type, **update_data
    )
    if err:
        raise RuntimeError(f"Failed to update provisioning key {args.key_id}: {err}")
    return shape_one(updated.as_dict())


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=DeleteKeyInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_provisioning_key(args: DeleteKeyInput) -> dict[str, Any]:
    """Delete a ZPA provisioning key (destructive write).

    If the key was already removed (e.g. its component was deleted) this reports
    success with an explanatory message rather than erroring.

    Confirmation required — the first call returns a prompt, not a deletion.
    Gated by `--write-tools`.
    """
    if not args.key_id:
        raise ValueError("key_id is required")
    client = get_zscaler_client(service="zpa")
    existing, _, err = client.zpa.provisioning.get_provisioning_key(
        key_id=args.key_id, key_type=args.key_type, query_params=None
    )
    if err or not existing:
        return OperationResult(
            success=True,
            message=f"Provisioning key {args.key_id} does not exist or was already deleted.",
        ).model_dump()
    _, _, err = client.zpa.provisioning.delete_provisioning_key(
        key_id=args.key_id, key_type=args.key_type, microtenant_id=args.microtenant_id
    )
    if err:
        raise RuntimeError(f"Failed to delete provisioning key {args.key_id}: {err}")
    return OperationResult(
        success=True, message=f"Provisioning key {args.key_id} deleted successfully."
    ).model_dump()
