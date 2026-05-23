"""ZPA Log Streaming Service (LSS) read-only tools.

The ZPA LSS API is **configuration-only** — it exposes the LSS config records
that route logs from ZPA to a customer-side LSS Connector / SIEM, plus the
metadata catalogs (log types, status codes, client types, log formats). It
does **not** stream or query the log content itself; that ships from the
LSS Connector to the SIEM out-of-band.

These tools cover the read-only surface needed for the
`zpa/audit-baseline-compliance` skill to verify a tenant's LSS posture matches
the ZPA Baseline Recommendations v1.0:

- A dedicated LSS App Connector Group is configured (and not bound to apps).
- LSS configs exist for the baseline log feeds (User Activity, User Status,
  Audit Logs, App Connector Status, App Connector Metrics).
- LSS configs apply filters (status codes) instead of catch-all streaming.

Write tools (create / update / delete LSS config) are intentionally not
exposed in this batch — the audit-first direction means we want read-only
LSS coverage before we add bulk-configuration skills.
"""

from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zpa_list_lss_configs(
    search: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side substring match on the LSS config's `name` field. "
                "An empty list means no LSS config name contains this string; "
                "do not retry with split keywords."
            )
        ),
    ] = None,
    page: Annotated[Optional[int], Field(ge=1, description="Page number for pagination.")] = None,
    page_size: Annotated[
        Optional[int], Field(ge=1, description="Items per page for pagination (max 500).")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection of results."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Any:
    """List ZPA Log Streaming Service (LSS) configurations.

    Each LSS config defines: a log type (e.g. user activity, audit, app
    connector metrics), a destination LSS host/port, a TLS toggle, the
    associated App Connector Group(s), an optional policy-rule scope, and an
    optional status-code filter. Use this tool to inventory which log feeds
    a tenant streams to its SIEM.

    The happy-path response is a list of LSS config dicts. JMESPath
    expressions like `length(@)` or `[*].config.name` may return scalars or
    differently shaped lists.

    Supports JMESPath client-side filtering via the `query` parameter.
    """
    client = get_zscaler_client(service=service)
    api = client.zpa.lss

    qp: Dict[str, Any] = {}
    if search:
        qp["search"] = search
    if page is not None:
        qp["page"] = str(page)
    if page_size is not None:
        qp["page_size"] = str(page_size)

    configs, _, err = api.list_configs(query_params=qp or None)
    if err:
        raise Exception(f"Failed to list LSS configs: {err}")
    results = [c.as_dict() for c in (configs or [])]
    return apply_jmespath(results, query)


def zpa_get_lss_config(
    lss_config_id: Annotated[str, Field(description="ID of the LSS configuration.")],
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get a specific ZPA LSS configuration by ID.

    Returns the full LSS config record including: source log type, log format
    template, destination host/port, TLS setting, associated App Connector
    Groups, policy-rule scope, and any filter status codes.
    """
    if not lss_config_id:
        raise ValueError("lss_config_id is required")

    client = get_zscaler_client(service=service)
    api = client.zpa.lss

    result, _, err = api.get_config(lss_config_id)
    if err:
        raise Exception(f"Failed to get LSS config {lss_config_id}: {err}")
    return result.as_dict()


def zpa_list_lss_log_types(
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> List[str]:
    """List the human-readable LSS source log types supported by ZPA.

    These are the inputs to the `source_log_type` field on an LSS
    configuration. Examples: `user_activity`, `user_status`, `audit_logs`,
    `app_connector_status`, `app_connector_metrics`, `browser_access`,
    `web_inspection`, `private_svc_edge_status`.

    Used by the audit skill to verify a tenant streams the baseline log
    feeds.
    """
    client = get_zscaler_client(service=service)
    api = client.zpa.lss
    # source_log_map is a class attribute on the LSS controller — its keys
    # are the human-readable names the SDK accepts.
    return sorted(api.source_log_map.keys())


def zpa_get_lss_log_format(
    log_type: Annotated[
        str,
        Field(
            description=(
                "Human-readable LSS log type (e.g. `user_activity`, `audit_logs`, "
                "`app_connector_metrics`). Use `zpa_list_lss_log_types` to discover "
                "the valid values."
            )
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """Get the pre-configured LSS log format templates for a specific log type.

    ZPA returns a dict keyed by format (`csv`, `json`, `tsv`) with the
    template string LSS uses to serialize each log record. Useful when an
    administrator wants to confirm the exact field set being shipped to the
    SIEM, or when authoring a custom `log_stream_content`.
    """
    if not log_type:
        raise ValueError("log_type is required")

    client = get_zscaler_client(service=service)
    api = client.zpa.lss
    # The SDK's source_log_map translates the human-readable name to the
    # ZPA internal log code; pass the internal code to get_all_log_formats.
    internal = api.source_log_map.get(log_type)
    if not internal:
        valid = ", ".join(sorted(api.source_log_map.keys()))
        raise ValueError(
            f"Unknown log_type {log_type!r}. Valid values: {valid}"
        )
    formats = api.get_all_log_formats(log_type=internal)
    if formats is None:
        raise Exception(f"Failed to fetch LSS log formats for {log_type}")
    return formats


def zpa_list_lss_status_codes(
    log_type: Annotated[
        Optional[str],
        Field(
            description=(
                "Optional human-readable LSS log type to filter status codes "
                "(e.g. `user_activity`). Omit to return all status codes across "
                "all log types."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """List ZPA LSS session status codes used in LSS config filters.

    The result is a dict keyed by status code (e.g. `ZPN_STATUS_AUTH_FAILED`)
    with metadata about each code, including the log types it applies to.
    Use this tool when authoring a status-code filter on an LSS config or
    when interpreting a streamed event.
    """
    client = get_zscaler_client(service=service)
    api = client.zpa.lss
    codes = api.get_status_codes(log_type=log_type or "all")
    if codes is None:
        raise Exception("Failed to fetch LSS status codes")
    return codes


def zpa_list_lss_client_types(
    service: Annotated[str, Field(description="The service to use.")] = "zpa",
) -> Dict:
    """List ZPA LSS client types for the current customer.

    Returns a dict mapping the human-readable client type (e.g.
    `web_browser`, `client_connector`, `machine_tunnel`, `zpa_lss`) to the
    internal identifier ZPA uses in LSS policy rule conditions.
    """
    client = get_zscaler_client(service=service)
    api = client.zpa.lss
    types = api.get_client_types()
    if types is None:
        raise Exception("Failed to fetch LSS client types")
    return types
