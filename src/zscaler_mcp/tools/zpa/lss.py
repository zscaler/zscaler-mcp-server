"""ZPA Log Streaming Service (LSS) — read-only config + catalog tools.

Mirrors v1's ``client.zpa.lss`` surface. The LSS API is configuration-only: it
exposes the LSS config records that route ZPA logs to a SIEM, plus metadata
catalogs (log types, log formats, status codes, client types). It does NOT
stream log content. All tools are read-only.

    zpa_list_lss_configs        (READ)
    zpa_get_lss_config          (READ)
    zpa_list_lss_log_types      (READ — catalog)
    zpa_get_lss_log_format      (READ — catalog)
    zpa_list_lss_status_codes   (READ — catalog)
    zpa_list_lss_client_types   (READ — catalog)
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.registry import READ, tool
from zscaler_mcp.shaping import AgentView, shape_many, shape_one

# =============================================================================
# INPUT MODELS
# =============================================================================


class ListLssConfigsInput(BaseModel):
    """Inputs for listing ZPA LSS configurations."""

    search: Annotated[
        Optional[str], Field(default=None, description="Server-side name substring match.")
    ] = None
    page: Annotated[Optional[int], Field(default=None, ge=1, description="Page number.")] = None
    page_size: Annotated[
        Optional[int], Field(default=None, ge=1, le=500, description="Per page.")
    ] = None


class GetLssConfigInput(BaseModel):
    """Inputs for getting one ZPA LSS configuration."""

    lss_config_id: Annotated[str, Field(description="LSS config ID (string).")]


class NoInput(BaseModel):
    """No inputs — returns a fixed catalog."""


class LogFormatInput(BaseModel):
    """Inputs for fetching pre-built LSS log-format templates for a log type."""

    log_type: Annotated[
        str,
        Field(description="Human-readable LSS log type (e.g. user_activity, audit_logs)."),
    ]


class StatusCodesInput(BaseModel):
    """Inputs for listing LSS session status codes (optionally per log type)."""

    log_type: Annotated[
        Optional[str], Field(default=None, description="Optional log type filter; omit for all.")
    ] = None


# =============================================================================
# OUTPUT VIEWS
# =============================================================================


class Catalog(AgentView):
    """Generic catalog wrapper — keeps the SDK payload intact under `items`.

    The LSS metadata endpoints return free-form dicts/lists (log types, format
    templates, status codes, client types). We pass them through under a single
    curated container rather than inventing per-catalog schemas.
    """

    kind: str = Field(description="Catalog kind (e.g. log_types, log_format, status_codes).")
    items: Any = Field(description="The catalog payload as returned by ZPA.")


def _opt_str(value: Any) -> Optional[str]:
    return None if value is None else str(value)






# =============================================================================
# TOOLS
# =============================================================================


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    input_model=ListLssConfigsInput,
    is_list=True,
)
def zpa_list_lss_configs(args: ListLssConfigsInput) -> list[dict[str, Any]]:
    """List ZPA LSS configurations — what log feed streams where (read-only)."""
    client = get_zscaler_client(service="zpa")
    api = client.zpa.lss
    qp: dict[str, Any] = {}
    if args.search:
        qp["search"] = args.search
    if args.page is not None:
        qp["page"] = str(args.page)
    if args.page_size is not None:
        qp["page_size"] = str(args.page_size)
    configs, _, err = api.list_configs(query_params=qp or None)
    if err:
        raise RuntimeError(f"Failed to list LSS configs: {err}")
    return shape_many([c.as_dict() for c in (configs or [])])


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    input_model=GetLssConfigInput,
    is_list=False,
)
def zpa_get_lss_config(args: GetLssConfigInput) -> dict[str, Any]:
    """Get one ZPA LSS configuration by ID (read-only)."""
    if not args.lss_config_id:
        raise ValueError("lss_config_id is required")
    client = get_zscaler_client(service="zpa")
    result, _, err = client.zpa.lss.get_config(args.lss_config_id)
    if err:
        raise RuntimeError(f"Failed to get LSS config {args.lss_config_id}: {err}")
    return shape_one(result.as_dict())


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    input_model=NoInput,
    output_view=Catalog,
    is_list=False,
)
def zpa_list_lss_log_types(args: NoInput) -> dict[str, Any]:
    """List the human-readable LSS source log types ZPA supports (read-only catalog)."""
    client = get_zscaler_client(service="zpa")
    return Catalog(
        kind="log_types", items=sorted(client.zpa.lss.source_log_map.keys())
    ).model_dump()


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    input_model=LogFormatInput,
    output_view=Catalog,
    is_list=False,
)
def zpa_get_lss_log_format(args: LogFormatInput) -> dict[str, Any]:
    """Get the pre-built LSS log-format templates (csv/json/tsv) for a log type (read-only)."""
    if not args.log_type:
        raise ValueError("log_type is required")
    client = get_zscaler_client(service="zpa")
    api = client.zpa.lss
    internal = api.source_log_map.get(args.log_type)
    if not internal:
        valid = ", ".join(sorted(api.source_log_map.keys()))
        raise ValueError(f"Unknown log_type {args.log_type!r}. Valid values: {valid}")
    formats = api.get_all_log_formats(log_type=internal)
    if formats is None:
        raise RuntimeError(f"Failed to fetch LSS log formats for {args.log_type}")
    return Catalog(kind="log_format", items=formats).model_dump()


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    input_model=StatusCodesInput,
    output_view=Catalog,
    is_list=False,
)
def zpa_list_lss_status_codes(args: StatusCodesInput) -> dict[str, Any]:
    """List ZPA LSS session status codes used in config filters (read-only catalog)."""
    client = get_zscaler_client(service="zpa")
    codes = client.zpa.lss.get_status_codes(log_type=args.log_type or "all")
    if codes is None:
        raise RuntimeError("Failed to fetch LSS status codes")
    return Catalog(kind="status_codes", items=codes).model_dump()


@tool(
    action=READ,
    service="zpa",
    toolset="zpa_misc",
    input_model=NoInput,
    output_view=Catalog,
    is_list=False,
)
def zpa_list_lss_client_types(args: NoInput) -> dict[str, Any]:
    """List ZPA LSS client types for the current customer (read-only catalog)."""
    client = get_zscaler_client(service="zpa")
    types = client.zpa.lss.get_client_types()
    if types is None:
        raise RuntimeError("Failed to fetch LSS client types")
    return Catalog(kind="client_types", items=types).model_dump()
