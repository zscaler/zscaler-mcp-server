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
from zscaler_mcp.shaping import AgentView, pick, shape_many

KeyType = Literal["connector", "service_edge"]


class ListKeysInput(BaseModel):
    """Inputs for listing provisioning keys."""

    key_type: Annotated[KeyType, Field(description="Key type: 'connector' or 'service_edge'.")]
    search: Annotated[
        Optional[str], Field(default=None, description="Server-side substring match on `name`.")
    ] = None
    detail: Annotated[
        str, Field(default="summary", pattern="^(summary|full)$", description="Response verbosity.")
    ] = "summary"
    microtenant_id: Annotated[
        Optional[str], Field(default=None, description="Microtenant ID for scoping.")
    ] = None


class GetKeyInput(BaseModel):
    """Inputs for getting one provisioning key."""

    key_id: Annotated[str, Field(description="Provisioning key ID (string, even if numeric).")]
    key_type: Annotated[KeyType, Field(description="Key type: 'connector' or 'service_edge'.")]
    detail: Annotated[
        str, Field(default="full", pattern="^(summary|full)$", description="Response verbosity.")
    ] = "full"


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


class KeySummary(AgentView):
    """Lean view — identify a provisioning key and its usage budget."""

    id: str = Field(description="Provisioning key ID. Use this in follow-up calls.")
    name: str = Field(description="Display name.")
    enabled: Optional[bool] = Field(default=None, description="Whether the key is enabled.")
    max_usage: Optional[str] = Field(default=None, description="Maximum enrollment count.")
    usage_count: Optional[str] = Field(default=None, description="Current enrollment count.")


class KeyDetail(KeySummary):
    """Full view — summary plus component binding + provenance."""

    enrollment_cert_id: Optional[str] = Field(default=None, description="Bound enrollment cert ID.")
    zcomponent_id: Optional[str] = Field(default=None, description="Bound component (group) ID.")
    zcomponent_name: Optional[str] = Field(
        default=None, description="Bound component (group) name."
    )
    microtenant_id: Optional[str] = Field(default=None, description="Owning microtenant, if any.")
    created_time: Optional[str] = Field(default=None, description="Creation timestamp.")
    modified_time: Optional[str] = Field(default=None, description="Last-modified timestamp.")


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _key_summary(raw: dict[str, Any]) -> KeySummary:
    return KeySummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=pick(raw, "enabled"),
        max_usage=_opt_str(pick(raw, "max_usage", "maxUsage")),
        usage_count=_opt_str(pick(raw, "usage_count", "usageCount")),
    )


def _key_detail(raw: dict[str, Any]) -> KeyDetail:
    return KeyDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=pick(raw, "enabled"),
        max_usage=_opt_str(pick(raw, "max_usage", "maxUsage")),
        usage_count=_opt_str(pick(raw, "usage_count", "usageCount")),
        enrollment_cert_id=_opt_str(pick(raw, "enrollment_cert_id", "enrollmentCertId")),
        zcomponent_id=_opt_str(
            pick(raw, "zcomponent_id", "zcomponentId", "component_id", "componentId")
        ),
        zcomponent_name=pick(raw, "zcomponent_name", "zcomponentName"),
        microtenant_id=pick(raw, "microtenant_id", "microtenantId"),
        created_time=pick(raw, "creation_time", "creationTime"),
        modified_time=pick(raw, "modified_time", "modifiedTime"),
    )


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=ListKeysInput,
    output_view=KeySummary,
    is_list=True,
)
def zpa_list_provisioning_keys(args: ListKeysInput) -> list[dict[str, Any]]:
    """List ZPA provisioning keys of a given type (read-only)."""
    client = get_zscaler_client(service="zpa")
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.microtenant_id:
        qp["microtenant_id"] = args.microtenant_id
    keys, _, err = client.zpa.provisioning.list_provisioning_keys(
        key_type=args.key_type, query_params=qp
    )
    if err:
        raise RuntimeError(f"Failed to list provisioning keys: {err}")
    shaper = _key_detail if args.detail == "full" else _key_summary
    return shape_many([k.as_dict() for k in (keys or [])], shaper)


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=GetKeyInput,
    output_view=KeyDetail,
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
    shaper = _key_detail if args.detail == "full" else _key_summary
    return shaper(result.as_dict()).model_dump()


@tool(
    action=CREATE,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=CreateKeyInput,
    output_view=KeyDetail,
    is_list=False,
)
def zpa_create_provisioning_key(args: CreateKeyInput) -> dict[str, Any]:
    """Create a ZPA provisioning key (write). Gated by HMAC + `--write-tools`.

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
    return _key_detail(created.as_dict()).model_dump()


@tool(
    action=UPDATE,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=UpdateKeyInput,
    output_view=KeyDetail,
    is_list=False,
)
def zpa_update_provisioning_key(args: UpdateKeyInput) -> dict[str, Any]:
    """Update a ZPA provisioning key (write). Gated by HMAC + `--write-tools`."""
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
    return _key_detail(updated.as_dict()).model_dump()


@tool(
    action=DELETE,
    service="zpa",
    toolset="zpa_provisioning_keys",
    input_model=DeleteKeyInput,
    output_view=OperationResult,
    is_list=False,
)
def zpa_delete_provisioning_key(args: DeleteKeyInput) -> dict[str, Any]:
    """Delete a ZPA provisioning key (destructive write). Gated by HMAC + `--write-tools`.

    If the key was already removed (e.g. its component was deleted) this reports
    success with an explanatory message rather than erroring.
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
