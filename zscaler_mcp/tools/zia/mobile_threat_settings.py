"""ZIA Mobile Advanced Threat Settings MCP Tools.

This module exposes the ZIA tenant-wide **Mobile Advanced Threat
Settings** singleton — the configuration block that governs the Mobile
Malware Protection policy applied to traffic from mobile clients
(iOS / Android via the Zscaler Client Connector). Like the regular
Advanced Settings, ATP policy, and ATP malware policy surfaces, this is
a single mutable object (not a rule family), so the tool surface is
just get / update.

Tools registered here:

* ``zia_get_mobile_advanced_settings`` — read the full Mobile Advanced
  Threat Settings block. The current SDK model exposes 8 boolean
  knobs covering applications with malicious activity, applications
  with known vulnerabilities or insecure modules, applications that
  leak unencrypted credentials / location / PII / device IDs,
  applications communicating with known ad websites, and applications
  communicating with unknown remote servers.
* ``zia_update_mobile_advanced_settings`` — push an updated Mobile
  Advanced Threat Settings block. The SDK passes the body through as
  ``**kwargs``, so this is a **PUT-replace** under the hood: any field
  omitted from the payload is reset to its API default. Always call
  ``zia_get_mobile_advanced_settings`` first, merge your changes onto
  the response, and submit the complete payload back.

Backed by ``zscaler.zia.mobile_threat_settings.MobileAdvancedSettingsAPI``
(``get_mobile_advanced_settings`` / ``update_mobile_advanced_settings``,
exposed on the SDK client as ``client.zia.mobile_threat_settings``).

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


def zia_get_mobile_advanced_settings(
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection of "
                "the returned settings dict (e.g. "
                "\"{malicious: block_apps_with_malicious_activity, "
                "vuln: block_apps_with_known_vulnerabilities}\")."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """Retrieve the current ZIA Mobile Advanced Threat Settings (tenant-wide singleton).

    Returns a dict with the Mobile Malware Protection policy knobs:

    * ``block_apps_with_malicious_activity`` (bool) — block known-bad
      / hidden mobile applications.
    * ``block_apps_with_known_vulnerabilities`` (bool) — block apps
      with known vulnerabilities or insecure modules.
    * ``block_apps_sending_unencrypted_user_credentials`` (bool) —
      block apps leaking user credentials in the clear.
    * ``block_apps_sending_location_info`` (bool) — block apps leaking
      device location unencrypted for unknown purposes.
    * ``block_apps_sending_personally_identifiable_info`` (bool) —
      block apps leaking PII unencrypted for unknown purposes.
    * ``block_apps_sending_device_identifier`` (bool) — block apps
      leaking device IDs unencrypted or for unknown purposes.
    * ``block_apps_communicating_with_ad_websites`` (bool) — block
      apps communicating with known ad websites.
    * ``block_apps_communicating_with_remote_unknown_servers`` (bool)
      — block apps communicating with unknown remote servers.

    Always call this before ``zia_update_mobile_advanced_settings`` so
    partial updates can be merged onto the existing payload (the update
    is PUT-replace — omitted fields are reset to API defaults).

    Supports JMESPath client-side filtering via the ``query`` parameter.
    """
    client = get_zscaler_client(service=service)

    settings, _, err = client.zia.mobile_threat_settings.get_mobile_advanced_settings()
    if err:
        raise Exception(f"Mobile advanced threat settings retrieval failed: {err}")

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


def zia_update_mobile_advanced_settings(
    settings: Annotated[
        Union[Dict[str, Any], str],
        Field(
            description=(
                "Full Mobile Advanced Threat Settings payload. Accepts a "
                "dict or a JSON string. PUT-replace semantics: any field "
                "omitted here will be reset to its API default. Always "
                "fetch the current payload via "
                "zia_get_mobile_advanced_settings first and merge changes "
                "onto it. Supported fields (all bool, snake_case): "
                "block_apps_with_malicious_activity, "
                "block_apps_with_known_vulnerabilities, "
                "block_apps_sending_unencrypted_user_credentials, "
                "block_apps_sending_location_info, "
                "block_apps_sending_personally_identifiable_info, "
                "block_apps_sending_device_identifier, "
                "block_apps_communicating_with_ad_websites, "
                "block_apps_communicating_with_remote_unknown_servers."
            )
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Update the ZIA Mobile Advanced Threat Settings (tenant-wide singleton).

    PUT-replace under the hood — any field not present in the payload
    will be reset to its API default. Use
    ``zia_get_mobile_advanced_settings`` first to fetch the existing
    block, mutate the fields you want to change, then pass the whole
    dict back here.

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

    updated, _, err = client.zia.mobile_threat_settings.update_mobile_advanced_settings(
        **payload
    )
    if err:
        raise Exception(f"Failed to update mobile advanced threat settings: {err}")

    if updated is None:
        return {}
    if hasattr(updated, "as_dict"):
        return updated.as_dict()
    if isinstance(updated, dict):
        return updated
    return {k: v for k, v in vars(updated).items() if not k.startswith("_")}
