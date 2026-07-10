"""OneAPI entitlement-driven tool downscoping.

The OneAPI bearer token issued by ZIdentity carries a ``service-info`` claim
(an array of ``{"prd": "...", "rnm": "...", "tnt": ...}`` objects). The ``prd``
field is the only part of that claim reliable for authorization decisions: it
tells us which Zscaler products this API client is entitled to call. Role names
(``rnm``) are free-form admin labels that cannot be used to infer read/write
permissions, so they are intentionally ignored.

This module uses ``prd`` (and only ``prd``) to downscope the tool surface at
server startup. If the token says the client is only entitled to ``ZPA`` and
``ZIA``, every other product's tools are stripped before registration runs.

**v2 design note.** v1 maps ``prd → service code → toolset IDs`` because v1's
unit of curation is the named *toolset*. v2's registry filters on the
``ToolSpec.service`` field directly, so this port stops one level earlier: it
resolves the token down to a set of *entitled service codes* and the registry
intersects each tool's ``service`` against that set. Same security outcome,
fewer moving parts (no separate toolset catalog needed yet).

Behaviour carried forward verbatim from v1:

* **Cache-first.** In ``zscaler`` MCP-auth mode the auth middleware already
  exchanged the same credentials for a token and cached it; we consult that
  cache before issuing our own ``/oauth2/v1/token`` call.
* **Cold-fetch fallback** via :func:`zscaler_mcp.security.auth.fetch_oneapi_token`.
* **Non-fatal.** Any failure (missing creds, network error, JWT decode failure,
  no ``service-info`` claim) logs a single WARN line and the filter is skipped;
  the user-selected tool surface passes through unchanged. Operators can also
  disable it explicitly with ``--no-entitlement-filter`` /
  ``ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true``.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Optional, Set, Tuple

__all__ = [
    "PRD_TO_SERVICE",
    "decode_oneapi_token",
    "extract_entitled_services",
    "obtain_oneapi_token",
    "apply_entitlement_filter",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping from JWT ``prd`` claim values to the internal service codes used by
# ``ToolSpec.service``. Keys are upper-cased on lookup so any case variant from
# ZIdentity is tolerated.
# ---------------------------------------------------------------------------
PRD_TO_SERVICE: dict[str, str] = {
    "ZIA": "zia",
    "ZPA": "zpa",
    "ZDX": "zdx",
    "ZCC": "zcc",
    "ZTW": "ztw",
    "ZIDENTITY": "zid",
    "ZID": "zid",
    "IDENTITY": "zid",
    "ZEASM": "zeasm",
    "EASM": "zeasm",
    "ZINS": "zins",
    "INSIGHTS": "zins",
    "ZMS": "zms",
    # ZCell (Zscaler Cellular). The exact `prd` claim value ZIdentity emits for
    # Cellular is not yet confirmed against a live token; map the likely variants
    # so the entitlement filter keeps zcell tools once the tenant is entitled.
    # TODO: pin the canonical value against a real OneAPI token.
    "ZCELL": "zcell",
    "ZCELLULAR": "zcell",
    "CELLULAR": "zcell",
}


# ---------------------------------------------------------------------------
# JWT decoding (no signature verification — OneAPI publishes no JWKS endpoint,
# and we don't need verification for a local entitlement check. The token was
# just minted by ZIdentity in response to our own credential exchange.)
# ---------------------------------------------------------------------------


def decode_oneapi_token(token: str) -> Optional[dict]:
    """Decode the payload of an unverified OneAPI JWT, or ``None`` on failure."""
    if not token or not isinstance(token, str):
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def extract_entitled_services(payload: dict) -> Set[str]:
    """Return the set of internal service codes the token is entitled to.

    Reads ``service-info`` from the payload, lifts each ``prd`` value, and maps
    known product codes to internal service identifiers (``zia`` / ``zpa`` /
    ...). Unknown product codes are silently skipped.
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

    Resolution order: env-var fallback for any ``None`` arg → cached token from
    a registered :class:`~zscaler_mcp.security.auth.ZscalerAuthProvider` (guaranteed
    hit in ``zscaler`` MCP-auth mode) → cold fetch via ``fetch_oneapi_token``.
    """
    client_id = client_id or os.getenv("ZSCALER_CLIENT_ID", "").strip() or None
    client_secret = client_secret or os.getenv("ZSCALER_CLIENT_SECRET", "").strip() or None
    vanity_domain = vanity_domain or os.getenv("ZSCALER_VANITY_DOMAIN", "").strip() or None
    cloud = cloud or os.getenv("ZSCALER_CLOUD", "production").strip() or "production"

    if not client_id or not client_secret or not vanity_domain:
        return None, "Missing OneAPI credentials (client_id / client_secret / vanity_domain)"

    # Step 1 — consult the auth-middleware cache.
    try:
        from zscaler_mcp.security.auth import get_registered_zscaler_providers

        for provider in get_registered_zscaler_providers():
            cached = provider.get_cached_token(client_id, client_secret)
            if cached:
                logger.debug("Entitlement filter using cached OneAPI token from auth provider.")
                return cached, None
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Entitlement filter cache lookup raised %s", exc)

    # Step 2 — cold fetch.
    from zscaler_mcp.security.auth import fetch_oneapi_token

    return fetch_oneapi_token(
        client_id=client_id,
        client_secret=client_secret,
        vanity_domain=vanity_domain,
        cloud=cloud,
    )


# ---------------------------------------------------------------------------
# Filter entry point used by build_server at startup.
# ---------------------------------------------------------------------------

# Service codes that are always preserved regardless of entitlement — the
# cross-service meta/discovery tools (v2 equivalent of v1's always-on meta
# toolset). Empty for now; add codes here if v2 grows service-agnostic tools.
_ALWAYS_KEEP_SERVICES: Set[str] = set()


def apply_entitlement_filter(
    available_services: Set[str],
    *,
    token_provider=None,
) -> Tuple[Optional[Set[str]], str]:
    """Resolve which of ``available_services`` the OneAPI token entitles.

    Args:
        available_services: Every service code present in the registered tool
            set (e.g. ``{"zpa", "zia"}``). The upper bound of what can be kept.
        token_provider: Callable returning ``(access_token, error)``. Defaults
            to :func:`obtain_oneapi_token`. Tests inject a stub here so they
            don't hit the network.

    Returns:
        ``(allowed_services, status_message)``.

        * ``allowed_services`` is ``None`` when the filter is skipped (any
          failure) — the caller treats ``None`` as "apply no entitlement
          downscoping". Otherwise it is the intersection of ``available_services``
          with the entitled services (plus any always-keep codes).
        * ``status_message`` is a short human-readable summary for a single
          INFO / WARN log line; the caller decides the level.
    """
    fetcher = token_provider or obtain_oneapi_token

    try:
        token, error = fetcher()
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Entitlement filter token provider raised %s", exc)
        return None, f"entitlement filter skipped: {exc.__class__.__name__}"

    if error or not token:
        return None, f"entitlement filter skipped ({error or 'no token returned'})"

    payload = decode_oneapi_token(token)
    if payload is None:
        return None, "entitlement filter skipped (token did not decode)"

    entitled_services = extract_entitled_services(payload)
    if not entitled_services:
        return None, "entitlement filter skipped (token had no recognizable service-info entries)"

    allowed = (set(available_services) & (entitled_services | _ALWAYS_KEEP_SERVICES)) | (
        _ALWAYS_KEEP_SERVICES & set(available_services)
    )

    removed = sorted(set(available_services) - allowed)
    kept = sorted(allowed)
    status = (
        f"entitlement filter applied: entitled services={sorted(entitled_services)}, "
        f"kept {len(kept)} service(s)"
        + (f", removed {len(removed)} service(s): {removed}" if removed else "")
    )
    return allowed, status
