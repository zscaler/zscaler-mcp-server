"""ZIA Advanced Settings MCP Tools.

This module exposes the ZIA tenant-wide **Advanced Settings** singleton
— the configuration block surfaced under *Administration → Advanced
Settings* in the ZIA Admin Portal. Like the ATP policy and malware
policy surfaces, this is a single mutable object (not a rule family),
so the tool surface is just get / update.

Tools registered here:

* ``zia_get_advanced_settings`` — read the full Advanced Settings
  block (~50 knobs spanning DNS optimization on transparent proxy,
  authentication bypass URLs/apps, surrogate IP, HTTP tunnel tracking,
  HTTP/2 / ECS / SIPA toggles, Office 365 one-click, UI session
  timeout, and many bypass / apps lists).
* ``zia_update_advanced_settings`` — push an updated Advanced Settings
  block. The SDK passes the body through as ``**kwargs``, so this is a
  **PUT-replace** under the hood: any field omitted from the payload is
  reset to its API default (or ``[]`` for list fields). Always call
  ``zia_get_advanced_settings`` first, merge your changes onto the
  response, and submit the complete payload back.

Backed by ``zscaler.zia.advanced_settings.AdvancedSettingsAPI``
(``get_advanced_settings`` / ``update_advanced_settings``).

Like every ZIA write operation, a successful update here is **staged**
until ``zia_activate_configuration`` is called.
"""

import json
from typing import Annotated, Any, Dict, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_get_advanced_settings(
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection of "
                "the returned settings dict (e.g. "
                "\"{office365: enable_office365, timeout: ui_session_timeout}\")."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """Retrieve the current ZIA Advanced Settings (tenant-wide singleton).

    Returns a dict with ~50 fields, including:

    * **Authentication / bypass** — ``auth_bypass_urls``,
      ``auth_bypass_apps``, ``kerberos_bypass_urls`` /
      ``kerberos_bypass_apps``, ``basic_bypass_apps``,
      ``digest_auth_bypass_urls`` / ``digest_auth_bypass_apps``, and
      the matching ``*_url_categories`` lists.
    * **DNS optimization on transparent proxy** —
      ``enable_dns_resolution_on_transparent_proxy``,
      ``enable_ipv6_dns_resolution_on_transparent_proxy``,
      ``enable_ipv6_dns_optimization_on_all_transparent_proxy``, and
      the URL / app / category include + exempt lists for both IPv4
      and IPv6.
    * **Session / security** — ``enable_office365``,
      ``log_internal_ip``, ``enforce_surrogate_ip_for_windows_app``,
      ``track_http_tunnel_on_http_ports``,
      ``block_http_tunnel_on_non_http_ports``,
      ``block_domain_fronting_on_host_header``,
      ``cascade_url_filtering``,
      ``enable_policy_for_unauthenticated_traffic``,
      ``block_non_compliant_http_request_on_http_ports``,
      ``enable_admin_rank_access``, ``ui_session_timeout`` (seconds).
    * **Advanced security** — ``http2_nonbrowser_traffic_enabled``,
      ``ecs_for_all_enabled``, ``dynamic_user_risk_enabled``,
      ``block_connect_host_sni_mismatch``,
      ``prefer_sni_over_conn_host``, ``sipa_xff_header_enabled``,
      ``block_non_http_on_http_port_enabled``.

    Always call this before ``zia_update_advanced_settings`` so partial
    updates can be merged onto the existing payload (the update is
    PUT-replace).

    Supports JMESPath client-side filtering via the ``query`` parameter.
    """
    client = get_zscaler_client(service=service)

    settings, _, err = client.zia.advanced_settings.get_advanced_settings()
    if err:
        raise Exception(f"Advanced settings retrieval failed: {err}")

    if settings is None:
        result: Dict[str, Any] = {}
    elif hasattr(settings, "as_dict"):
        result = settings.as_dict()
    elif isinstance(settings, dict):
        result = settings
    else:
        result = {k: v for k, v in vars(settings).items() if not k.startswith("_")}

    return apply_jmespath(result, query)


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zia_update_advanced_settings(
    settings: Annotated[
        Union[Dict[str, Any], str],
        Field(
            description=(
                "Full Advanced Settings payload. Accepts a dict or a JSON "
                "string. PUT-replace semantics: any field omitted here will "
                "be reset to its API default (or [] for list fields). "
                "Always fetch the current payload via "
                "zia_get_advanced_settings first and merge changes onto it. "
                "Common fields (snake_case): enable_office365 (bool), "
                "ui_session_timeout (int — seconds, ZIA Admin Portal idle "
                "timeout), log_internal_ip (bool), "
                "enforce_surrogate_ip_for_windows_app (bool), "
                "track_http_tunnel_on_http_ports (bool), "
                "block_http_tunnel_on_non_http_ports (bool), "
                "block_domain_fronting_on_host_header (bool), "
                "cascade_url_filtering (bool), "
                "enable_policy_for_unauthenticated_traffic (bool), "
                "enable_admin_rank_access (bool), "
                "http2_nonbrowser_traffic_enabled (bool), "
                "ecs_for_all_enabled (bool), dynamic_user_risk_enabled "
                "(bool), block_connect_host_sni_mismatch (bool), "
                "prefer_sni_over_conn_host (bool), "
                "sipa_xff_header_enabled (bool), "
                "enable_dns_resolution_on_transparent_proxy (bool), "
                "enable_ipv6_dns_resolution_on_transparent_proxy (bool), "
                "auth_bypass_urls (list[str]), auth_bypass_apps "
                "(list[str]), kerberos_bypass_urls (list[str]), "
                "kerberos_bypass_apps (list[str]), "
                "digest_auth_bypass_urls (list[str]), "
                "digest_auth_bypass_apps (list[str]), "
                "basic_bypass_apps (list[str]), and the various "
                "*_url_categories list[str] fields. See the SDK's "
                "AdvancedSettings model for the complete list."
            )
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Update the ZIA Advanced Settings (tenant-wide singleton).

    PUT-replace under the hood — any field not present in the payload
    will be reset to its API default (or ``[]`` for list fields). Use
    ``zia_get_advanced_settings`` first to fetch the existing block,
    mutate the fields you want to change, then pass the whole dict
    back here.

    After a successful update, remember to call
    ``zia_activate_configuration`` so the change takes effect.
    """
    payload = settings
    if isinstance(settings, str):
        try:
            payload = json.loads(settings)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for settings: {e}")

    if not isinstance(payload, dict):
        raise ValueError("settings must be a dict or a JSON-object string")

    client = get_zscaler_client(service=service)

    updated, _, err = client.zia.advanced_settings.update_advanced_settings(**payload)
    if err:
        raise Exception(f"Failed to update advanced settings: {err}")

    if updated is None:
        return {}
    if hasattr(updated, "as_dict"):
        return updated.as_dict()
    if isinstance(updated, dict):
        return updated
    return {k: v for k, v in vars(updated).items() if not k.startswith("_")}
