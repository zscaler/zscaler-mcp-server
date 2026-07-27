"""ZCell Audit Data Handling — agent-first v2 read tools.

Read-only surface over ``client.zcell.audit_data_handling``:

    * zcell_list_audit_customers_search — audit-log entries (filtered search)
    * zcell_list_audit_metadata          — the audit filter vocabulary

The search filter is sent as a flat JSON body carrying an epoch-seconds window,
so the shared :class:`WindowInput` ``days`` shorthand fills it server-side. The
before/after ``old_data`` / ``new_data`` blobs are intentionally dropped from
the curated row (large, provenance-only) — the identifying + operation fields
are what an agent needs to reason about the change.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import shape_many
from zscaler_mcp.tools.zcell._common import WindowInput, as_dicts

# =============================================================================
# INPUT MODELS
# =============================================================================


class AuditSearchInput(WindowInput):
    """Inputs for searching Zscaler Cellular audit entries (time-bounded)."""

    operation_type: Annotated[
        Optional[str],
        Field(default=None, description="Filter by operation: Create, Update, Delete, Export."),
    ] = None
    object_type: Annotated[
        Optional[str], Field(default=None, description="Filter by object type.")
    ] = None
    object_name: Annotated[
        Optional[str], Field(default=None, description="Filter by object name.")
    ] = None
    object_id: Annotated[Optional[str], Field(default=None, description="Filter by object ID.")] = (
        None
    )
    visibility: Annotated[
        Optional[str], Field(default=None, description="Filter by visibility: Customer or Root.")
    ] = None
    modified_by_user_id: Annotated[
        Optional[str], Field(default=None, description="Filter by the modifying user ID.")
    ] = None
    page: Annotated[
        Optional[int], Field(default=None, ge=0, description="Page number (0-based).")
    ] = None
    size: Annotated[
        Optional[int], Field(default=None, ge=1, le=100, description="Page size (1-100).")
    ] = None


class AuditMetadataInput(BaseModel):
    """Inputs for the audit filter vocabulary (no parameters)."""


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _body(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in pairs if value is not None}


# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_audit_data_handling",
    input_model=AuditSearchInput,
    is_list=True,
)
def zcell_list_audit_customers_search(args: AuditSearchInput) -> list[dict[str, Any]]:
    """Search Zscaler Cellular audit-log entries over a lookback window.

    Read-only. Returns curated audit rows (who changed what, when, and the
    operation) over a `days` window, with optional operation/object/visibility
    filters. The before/after data blobs are omitted from the row.
    """
    client = get_zscaler_client(service="zcell")

    entries, _, err = client.zcell.audit_data_handling.list_audit_customers_search(
        days=args.days,
        query_params=_body(("page", args.page), ("size", args.size)),
        **_body(
            ("operation_type", args.operation_type),
            ("object_type", args.object_type),
            ("object_name", args.object_name),
            ("object_id", args.object_id),
            ("visibility", args.visibility),
            ("modified_by_user_id", args.modified_by_user_id),
        ),
    )
    if err:
        raise RuntimeError(f"Failed to search audit entries: {err}")
    return shape_many(as_dicts(entries))


@tool(
    action=READ,
    service="zcell",
    toolset="zcell_audit_data_handling",
    input_model=AuditMetadataInput,
    is_list=True,
)
def zcell_list_audit_metadata(args: AuditMetadataInput) -> list[dict[str, Any]]:
    """List the Zscaler Cellular audit filter vocabulary.

    Read-only. Returns the valid operation types and object types you can pass
    to `zcell_list_audit_customers_search`.
    """
    client = get_zscaler_client(service="zcell")

    metadata, _, err = client.zcell.audit_data_handling.list_audit_metadata()
    if err:
        raise RuntimeError(f"Failed to list audit metadata: {err}")
    return shape_many(as_dicts(metadata))
