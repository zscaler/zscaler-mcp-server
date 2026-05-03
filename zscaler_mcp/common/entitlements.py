"""OneAPI entitlement-driven toolset filtering.

The OneAPI bearer token issued by ZIdentity carries a ``service-info`` claim
(an array of ``{"prd": "...", "rnm": "...", "tnt": ...}`` objects). The
``prd`` field is the only piece of that claim that is reliable for
authorization decisions: it tells us which Zscaler products this API client
is entitled to call. Role names (``rnm``) are free-form admin labels that
cannot be used to infer read/write permissions.

This module uses ``prd`` (and only ``prd``) to filter the set of toolsets
loaded at server startup. If the token says the client is only entitled to
``ZPA`` and ``ZIA``, every other product's toolsets are stripped before
tool registration runs.

Design notes
============
* **Cache-first.** When the operator runs the server in ``zscaler``
  MCP-auth mode, the auth middleware has already exchanged the same
  credentials for a token and cached it. We consult that cache before
  issuing our own ``/oauth2/v1/token`` call.
* **Cold-fetch fallback.** If the cache miss (different MCP-auth mode, or
  no MCP auth at all), we exchange the OneAPI credentials directly via
  :func:`zscaler_mcp.auth.fetch_oneapi_token`. This is always possible
  because OneAPI credentials are required for the SDK regardless of which
  MCP-auth mode is active.
* **Non-fatal.** Any failure (missing creds, network error, JWT decode
  failure, no ``service-info`` claim) results in a single ``WARN`` log
  line and the filter is skipped entirely. The server falls back to the
  user-selected toolsets unchanged. Operators can also disable the
  filter explicitly with ``--no-entitlement-filter`` /
  ``ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true`` for emergencies.
* **Meta toolset is never touched.** The always-on meta toolset
  (server-introspection tools) survives entitlement filtering by
  construction.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Iterable, Optional, Set, Tuple

from zscaler_mcp.common.toolsets import (
    META_TOOLSET_ID,
    TOOLSETS,
    ToolsetCatalog,
)

__all__ = [
    "PRD_TO_SERVICE",
    "decode_oneapi_token",
    "extract_entitled_services",
    "obtain_oneapi_token",
    "apply_entitlement_filter",
]


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping from the JWT ``prd`` claim values to the internal service codes
# used by the toolset catalog. Keys are upper-cased on lookup so any
# case variant from ZIdentity is tolerated.
# ---------------------------------------------------------------------------
PRD_TO_SERVICE: dict[str, str] = {
    "ZIA": "zia",
    "ZPA": "zpa",
    "ZDX": "zdx",
    "ZCC": "zcc",
    "ZTW": "ztw",
    # ZIdentity surfaces under several aliases across consoles.
    "ZIDENTITY": "zid",
    "ZID": "zid",
    "IDENTITY": "zid",
    # External attack surface management.
    "ZEASM": "zeasm",
    "EASM": "zeasm",
    # Z-Insights / threat insights.
    "ZINS": "zins",
    "INSIGHTS": "zins",
    # Microsegmentation (ZMS).
    "ZMS": "zms",
}


# ---------------------------------------------------------------------------
# JWT decoding (no signature verification — OneAPI does not publish a JWKS
# endpoint, but we don't need verification for an entitlement check that
# only filters the local tool list. The token was just minted by ZIdentity
# in response to our own credential exchange.)
# ---------------------------------------------------------------------------


def decode_oneapi_token(token: str) -> Optional[dict]:
    """Decode the payload portion of an unverified OneAPI JWT.

    Returns the decoded payload dict, or ``None`` if the input does not
    parse as a three-part JWT with a valid base64url JSON payload.
    """
    if not token or not isinstance(token, str):
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload_b64 = parts[1]
    # JWT spec uses base64url without padding; pad to a multiple of 4 first.
    padding = "=" * (-len(payload_b64) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def extract_entitled_services(payload: dict) -> Set[str]:
    """Return the set of internal service codes the token is entitled to.

    Reads the ``service-info`` array from the JWT payload, lifts the
    ``prd`` value out of every entry, and maps each known product code
    to its internal service identifier (``zia``, ``zpa``, ...).

    Unknown product codes are silently skipped — they don't correspond
    to any toolset the server can offer, so there's nothing to filter.
    """
    services: Set[str] = set()

    service_info = payload.get("service-info") or payload.get("serviceInfo")
    if not isinstance(service_info, list):
        return services

    for entry in service_info:
        if not isinstance(entry, dict):
            continue
        prd = entry.get("prd")
        if not isinstance(prd, str):
            continue
        mapped = PRD_TO_SERVICE.get(prd.strip().upper())
        if mapped:
            services.add(mapped)

    return services


# ---------------------------------------------------------------------------
# Token acquisition — cache-first, then cold-fetch, then give up.
# ---------------------------------------------------------------------------


def obtain_oneapi_token(
    *,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    vanity_domain: Optional[str] = None,
    cloud: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(access_token, error_message)`` for the configured creds.

    Resolution order:

    1. Fall back to environment variables (``ZSCALER_CLIENT_ID``,
       ``ZSCALER_CLIENT_SECRET``, ``ZSCALER_VANITY_DOMAIN``,
       ``ZSCALER_CLOUD``) for any argument left as ``None``.
    2. Look in the registered :class:`~zscaler_mcp.auth.ZscalerAuthProvider`
       instances for a still-valid cached token for these credentials.
       In ``zscaler`` MCP-auth mode this is a guaranteed hit and saves
       a network round-trip.
    3. Otherwise call :func:`~zscaler_mcp.auth.fetch_oneapi_token` to
       exchange the credentials at ZIdentity.

    Returns ``(token, None)`` on success or ``(None, "<reason>")`` on
    failure. The caller decides whether the failure is fatal (it isn't,
    for the entitlement filter).
    """
    client_id = client_id or os.getenv("ZSCALER_CLIENT_ID", "").strip() or None
    client_secret = client_secret or os.getenv("ZSCALER_CLIENT_SECRET", "").strip() or None
    vanity_domain = vanity_domain or os.getenv("ZSCALER_VANITY_DOMAIN", "").strip() or None
    cloud = cloud or os.getenv("ZSCALER_CLOUD", "production").strip() or "production"

    if not client_id or not client_secret or not vanity_domain:
        return None, "Missing OneAPI credentials (client_id / client_secret / vanity_domain)"

    # Step 1 — consult the auth-middleware cache.
    try:
        from zscaler_mcp.auth import get_registered_zscaler_providers

        for provider in get_registered_zscaler_providers():
            cached = provider.get_cached_token(client_id, client_secret)
            if cached:
                logger.debug("Entitlement filter using cached OneAPI token from auth provider.")
                return cached, None
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Entitlement filter cache lookup raised %s", exc)

    # Step 2 — cold fetch.
    from zscaler_mcp.auth import fetch_oneapi_token

    return fetch_oneapi_token(
        client_id=client_id,
        client_secret=client_secret,
        vanity_domain=vanity_domain,
        cloud=cloud,
    )


# ---------------------------------------------------------------------------
# Filter entry point used by ZscalerMCPServer at startup.
# ---------------------------------------------------------------------------


def apply_entitlement_filter(
    selected_toolsets: Optional[Set[str]],
    *,
    catalog: Optional[ToolsetCatalog] = None,
    token_provider: Optional["callable[[], tuple[Optional[str], Optional[str]]]"] = None,
) -> Tuple[Optional[Set[str]], Optional[str]]:
    """Trim ``selected_toolsets`` down to what the OneAPI token entitles.

    Args:
        selected_toolsets: The set of toolset IDs the operator already
            chose (via ``--toolsets`` / ``ZSCALER_MCP_TOOLSETS``), or
            ``None`` meaning "all toolsets" (the no-selection default).
        catalog: Toolset catalog to consult. Defaults to the canonical
            :data:`TOOLSETS` registry; tests can inject a custom one.
        token_provider: Callable returning ``(access_token, error)``.
            Defaults to :func:`obtain_oneapi_token`. Tests inject a
            stub here so they don't hit the network.

    Returns:
        ``(filtered_set, status_message)``. ``filtered_set`` is:

        * the input unchanged if the filter was skipped (any failure);
        * the input intersected with the entitled service codes
          otherwise.

        ``status_message`` is a short human-readable summary suitable
        for a single ``INFO`` / ``WARN`` log line; the caller decides
        the log level.

    The meta toolset is always preserved — it is forced back into the
    result even if no entitled service explicitly maps to it.
    """
    catalog = catalog or TOOLSETS
    fetcher = token_provider or obtain_oneapi_token

    try:
        token, error = fetcher()
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Entitlement filter token provider raised %s", exc)
        return selected_toolsets, f"entitlement filter skipped: {exc.__class__.__name__}"

    if error or not token:
        return (
            selected_toolsets,
            f"entitlement filter skipped ({error or 'no token returned'})",
        )

    payload = decode_oneapi_token(token)
    if payload is None:
        return selected_toolsets, "entitlement filter skipped (token did not decode)"

    entitled_services = extract_entitled_services(payload)
    if not entitled_services:
        return (
            selected_toolsets,
            "entitlement filter skipped (token had no recognizable service-info entries)",
        )

    # Translate entitled service codes → entitled toolset IDs.
    entitled_toolsets: Set[str] = {META_TOOLSET_ID}
    for service in entitled_services:
        for ts in catalog.for_service(service):
            entitled_toolsets.add(ts.id)

    # If the operator hasn't chosen anything, "selected" == every toolset
    # in the catalog. We still want to honour that as the upper bound.
    if selected_toolsets is None:
        baseline: Set[str] = set(catalog.all_ids())
    else:
        baseline = set(selected_toolsets)

    filtered = (baseline & entitled_toolsets) | {META_TOOLSET_ID}

    removed = sorted(baseline - filtered)
    kept = sorted(filtered - {META_TOOLSET_ID})
    status = (
        f"entitlement filter applied: entitled services="
        f"{sorted(entitled_services)}, kept {len(kept)} toolset(s)"
        + (f", removed {len(removed)} toolset(s)" if removed else "")
    )
    return filtered, status


def _iter_service_codes(items: Iterable[Any]) -> Set[str]:  # pragma: no cover
    """Internal helper kept for symmetry with future extensions."""
    out: Set[str] = set()
    for item in items:
        if isinstance(item, str):
            out.add(item.strip().lower())
    return out
