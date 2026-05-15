"""ZIA Advanced Threat Protection (ATP) Policy MCP Tools.

This module exposes every tool backed by the SDK's
``zscaler.zia.atp_policy.ATPPolicyAPI``. All seven tools live in the
single ``zia_atp_policy`` toolset so admins can enable / audit the
entire ATP surface in one go.

Tools registered here:

* ``zia_get_atp_settings`` — read the full ATP policy block (50+ knobs:
  command-and-control blocking, malware sites, browser exploits,
  phishing, BitTorrent, Tor, crypto-mining, DGA, ad/spyware, etc.).
* ``zia_update_atp_settings`` — push an updated ATP policy block. The
  update is a PUT-replace, so omitted fields will be reset to their
  default; **always** call ``zia_get_atp_settings`` first and merge
  changes into the existing payload.
* ``zia_get_atp_security_exceptions`` — read the bypass URL list (the
  ATP-policy allowlist; URLs here are exempt from ATP enforcement).
* ``zia_update_atp_security_exceptions`` — replace the bypass URL list.
* ``zia_list_atp_malicious_urls`` — read the malicious-URL denylist
  (URLs ATP actively blocks).
* ``zia_add_atp_malicious_urls`` — append URLs to the denylist
  (additive — does not replace the list).
* ``zia_delete_atp_malicious_urls`` — remove URLs from the denylist;
  destructive, requires HMAC double-confirmation.

The two URL lists are conceptually opposite — security exceptions are
the allowlist (PUT-replace), malicious URLs are the denylist
(add/delete semantics).

Every successful update on this surface is **staged** until
``zia_activate_configuration`` is called.
"""

import json
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath

# =============================================================================
# READ-ONLY OPERATIONS
# =============================================================================


def zia_get_atp_settings(
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection of "
                "the returned settings dict (e.g. \"{tor: tor_blocked, "
                "bittorrent: bit_torrent_blocked}\")."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """Retrieve the current ZIA Advanced Threat Protection (ATP) policy settings.

    Returns a dict with 50+ fields covering command-and-control blocking
    (``cmd_ctl_server_blocked``, ``cmd_ctl_traffic_blocked``), malware
    sites (``malware_sites_blocked``), browser exploits, file-format
    vulnerabilities, phishing (``known_phishing_sites_blocked``,
    ``suspected_phishing_sites_blocked``), risky protocols
    (``bit_torrent_blocked``, ``tor_blocked``, ``ssh_tunnelling_blocked``,
    ``crypto_mining_blocked``), DGA domains, ad/spyware sites, and
    capture toggles for each. Always call this before
    ``zia_update_atp_settings`` so partial updates can be merged onto
    the existing payload.

    Supports JMESPath client-side filtering via the ``query`` parameter.
    """
    client = get_zscaler_client(service=service)

    settings, _, err = client.zia.atp_policy.get_atp_settings()
    if err:
        raise Exception(f"ATP settings retrieval failed: {err}")

    if settings is None:
        result: Dict[str, Any] = {}
    elif hasattr(settings, "as_dict"):
        result = settings.as_dict()
    elif isinstance(settings, dict):
        result = settings
    else:
        result = {k: v for k, v in vars(settings).items() if not k.startswith("_")}

    return apply_jmespath(result, query)


def zia_get_atp_security_exceptions(
    query: Annotated[
        Optional[str],
        Field(
            description=(
                "JMESPath expression for client-side filtering/projection of "
                "the returned bypass URL list."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """Retrieve the URLs currently bypassed by ZIA ATP security exceptions.

    Returns the list of bypass URLs (``bypassUrls`` on the API). These
    URLs are exempt from ATP enforcement.

    Supports JMESPath client-side filtering via the ``query`` parameter.
    """
    client = get_zscaler_client(service=service)

    bypass_urls, _, err = client.zia.atp_policy.get_atp_security_exceptions()
    if err:
        raise Exception(f"ATP security-exceptions retrieval failed: {err}")

    results = bypass_urls or []
    return apply_jmespath(results, query)


def zia_list_atp_malicious_urls(
    query: Annotated[
        Optional[str],
        Field(description="JMESPath expression for client-side filtering/projection of results."),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """Retrieve the current malicious URL denylist from ZIA ATP policy.

    Returns the list of URLs that ATP actively blocks (the denylist —
    opposite of the security-exceptions allowlist).

    Supports JMESPath client-side filtering via the ``query`` parameter.
    """
    client = get_zscaler_client(service=service)

    url_list, _, err = client.zia.atp_policy.get_atp_malicious_urls()
    if err:
        raise Exception(f"ATP URL list retrieval failed: {err}")
    results = getattr(url_list, "malicious_urls", url_list or [])
    return apply_jmespath(results, query)


# =============================================================================
# WRITE OPERATIONS
# =============================================================================


def zia_update_atp_settings(
    settings: Annotated[
        Union[Dict[str, Any], str],
        Field(
            description=(
                "Full ATP policy settings payload. Accepts a dict or a JSON "
                "string. PUT-replace semantics: any field omitted here will "
                "be reset to its default value by the API. Always fetch the "
                "current payload via zia_get_atp_settings first and merge "
                "changes onto it. Common fields (snake_case): "
                "risk_tolerance (int), cmd_ctl_server_blocked (bool), "
                "cmd_ctl_traffic_blocked (bool), malware_sites_blocked (bool), "
                "active_x_blocked (bool), browser_exploits_blocked (bool), "
                "file_format_vunerabilites_blocked (bool, note SDK typo), "
                "known_phishing_sites_blocked (bool), "
                "suspected_phishing_sites_blocked (bool), "
                "blocked_countries (list[str]), bit_torrent_blocked (bool), "
                "tor_blocked (bool), google_talk_blocked (bool), "
                "ssh_tunnelling_blocked (bool), crypto_mining_blocked (bool), "
                "ad_spyware_sites_blocked (bool), dga_domains_blocked (bool), "
                "alert_for_unknown_or_suspicious_c2_traffic (bool), and "
                "matching *_capture toggles. See the SDK's "
                "AdvancedThreatProtectionSettings model for the complete list."
            )
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Dict[str, Any]:
    """Update the ZIA Advanced Threat Protection (ATP) policy settings.

    PUT-replace under the hood — any field not present in the payload
    will be reset to its API default. Use ``zia_get_atp_settings`` first
    to fetch the existing block, mutate the fields you want to change,
    then pass the whole dict back here.

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

    updated, _, err = client.zia.atp_policy.update_atp_settings(**payload)
    if err:
        raise Exception(f"Failed to update ATP settings: {err}")

    if updated is None:
        return {}
    if hasattr(updated, "as_dict"):
        return updated.as_dict()
    if isinstance(updated, dict):
        return updated
    return {k: v for k, v in vars(updated).items() if not k.startswith("_")}


def zia_update_atp_security_exceptions(
    bypass_urls: Annotated[
        Union[List[str], str],
        Field(
            description=(
                "Full list of URLs to bypass ATP security checks (PUT-replace; "
                "the list provided here REPLACES the existing list, it does "
                "not merge). Accepts a list of strings or a JSON-array string. "
                "Pass an empty list to clear all exceptions."
            )
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[str]:
    """Replace the ZIA ATP security-exception bypass URL list.

    PUT-replace under the hood — the list you pass here becomes the new
    canonical list. To add/remove a single URL, fetch the current list
    via ``zia_get_atp_security_exceptions`` first and pass back the
    mutated list.

    After a successful update, remember to call
    ``zia_activate_configuration`` so the change takes effect.
    """
    processed_urls: List[str]
    if isinstance(bypass_urls, str):
        try:
            parsed = json.loads(bypass_urls)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for bypass_urls: {e}")
        if not isinstance(parsed, list):
            raise ValueError("bypass_urls must be a list or JSON-array string")
        processed_urls = parsed
    else:
        processed_urls = bypass_urls

    if not isinstance(processed_urls, list):
        raise ValueError("bypass_urls must be a list of strings")

    client = get_zscaler_client(service=service)

    updated, _, err = client.zia.atp_policy.update_atp_security_exceptions(processed_urls)
    if err:
        raise Exception(f"Failed to update ATP security exceptions: {err}")

    return updated or []


def zia_add_atp_malicious_urls(
    malicious_urls: Annotated[
        Union[List[str], str],
        Field(
            description="List of malicious URLs to add to denylist. Accepts list or JSON string."
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> List[str]:
    """Add URLs to the malicious URL denylist in ZIA ATP policy.

    Additive — the URLs you pass here are appended to the existing
    denylist. Use :func:`zia_delete_atp_malicious_urls` to remove URLs
    instead. The result is the full denylist after the add.

    After a successful update, remember to call
    ``zia_activate_configuration`` so the change takes effect.
    """
    processed_urls = malicious_urls
    if isinstance(malicious_urls, str):
        try:
            processed_urls = json.loads(malicious_urls)
            if not isinstance(processed_urls, list):
                raise ValueError("malicious_urls must be a list or JSON array string")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for malicious_urls: {e}")

    if not processed_urls:
        raise ValueError("You must provide a list of malicious URLs to add")

    client = get_zscaler_client(service=service)

    url_list, _, err = client.zia.atp_policy.add_atp_malicious_urls(processed_urls)
    if err:
        raise Exception(f"Failed to add malicious URLs: {err}")
    return getattr(url_list, "malicious_urls", url_list or [])


def zia_delete_atp_malicious_urls(
    malicious_urls: Annotated[
        Union[List[str], str],
        Field(
            description="List of malicious URLs to remove from denylist. Accepts list or JSON string."
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> Union[str, List[str]]:
    """Remove URLs from the malicious URL denylist in ZIA ATP policy.

    🚨 DESTRUCTIVE OPERATION - Requires double confirmation.
    This action cannot be undone.

    After a successful update, remember to call
    ``zia_activate_configuration`` so the change takes effect.
    """
    from zscaler_mcp.common.elicitation import check_confirmation, extract_confirmed_from_kwargs

    confirmed = extract_confirmed_from_kwargs(kwargs)

    confirmation_check = check_confirmation(
        "zia_delete_atp_malicious_urls",
        confirmed,
        {"malicious_urls": str(malicious_urls)},
    )
    if confirmation_check:
        return confirmation_check

    processed_urls = malicious_urls
    if isinstance(malicious_urls, str):
        try:
            processed_urls = json.loads(malicious_urls)
            if not isinstance(processed_urls, list):
                raise ValueError("malicious_urls must be a list or JSON array string")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for malicious_urls: {e}")

    if not processed_urls:
        raise ValueError("You must provide a list of malicious URLs to delete")

    client = get_zscaler_client(service=service)

    url_list, _, err = client.zia.atp_policy.delete_atp_malicious_urls(processed_urls)
    if err:
        raise Exception(f"Failed to delete malicious URLs: {err}")
    return getattr(url_list, "malicious_urls", url_list or [])
