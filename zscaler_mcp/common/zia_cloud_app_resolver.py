"""Resolve user-friendly cloud-application names to ZIA canonical enum tokens.

Several ZIA policy resources (SSL Inspection, Web DLP, Cloud App Control,
File Type Control, Bandwidth Classes, Advanced Settings) accept a
``cloud_applications`` field whose values are Zscaler's internal enum
strings — for example ``ONEDRIVE``, ``ONEDRIVE_PERSONAL``, ``DROPBOX``,
``SHAREPOINT_ONLINE``. The ZIA API silently coerces unrecognised values
to ``NONE`` instead of returning a validation error, which is the source
of `issue #56`_ and similar reports.

Users typically type the friendly display name ("OneDrive", "Google Drive",
"share point online"). This module exposes :func:`resolve_cloud_applications`
to translate those friendly inputs into the canonical enum tokens by
consulting the ZIA policy-engine catalog.

The catalog is fetched lazily on first use and cached in-process for a
short TTL (default 5 minutes), so repeated rule operations do not pay the
network round-trip.

.. _issue #56: https://github.com/zscaler/zscaler-mcp-server/issues/56
"""

from __future__ import annotations

import re
import threading
import time
from typing import Iterable, List, Literal, Tuple

Scope = Literal["ssl", "policy"]

_CACHE_TTL_SECONDS = 300

# Cache key -> (expires_at_epoch, [{"app": ..., "app_name": ...}, ...])
_catalog_cache: dict[Tuple[Scope, bool, str], Tuple[float, List[dict]]] = {}
_cache_lock = threading.Lock()


def _normalize(token: str) -> str:
    """Normalize an input/catalog string for fuzzy matching.

    Lowercase, strip non-alphanumerics. ``"OneDrive Personal"`` and
    ``"ONEDRIVE_PERSONAL"`` and ``"one-drive personal"`` all collapse to
    ``"onedrivepersonal"``.
    """
    return re.sub(r"[^a-z0-9]+", "", token.strip().lower())


def _looks_like_canonical_enum(token: str) -> bool:
    """Return True when the input is already in canonical ``UPPER_SNAKE_CASE``."""
    if not token:
        return False
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", token))


def _fetch_catalog(scope: Scope, *, use_legacy: bool, service: str) -> List[dict]:
    """Fetch (or return cached) policy-engine cloud-app catalog entries."""
    key = (scope, use_legacy, service)
    now = time.time()

    with _cache_lock:
        cached = _catalog_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

    # Imported lazily to avoid circular imports during module load.
    from zscaler_mcp.client import get_zscaler_client

    client = get_zscaler_client(use_legacy=use_legacy, service=service)
    cloud_apps = client.zia.cloud_applications

    fetcher = (
        cloud_apps.list_cloud_app_ssl_policy
        if scope == "ssl"
        else cloud_apps.list_cloud_app_policy
    )
    apps, _, err = fetcher(query_params={"page_size": 1000})
    if err:
        raise RuntimeError(
            f"Could not fetch ZIA cloud-application catalog (scope={scope}): {err}"
        )

    entries: List[dict] = []
    for app in apps:
        entries.append(
            {
                "app": (app.app or "").strip(),
                "app_name": (app.app_name or "").strip(),
                "parent": (app.parent or "").strip(),
                "parent_name": (app.parent_name or "").strip(),
            }
        )

    with _cache_lock:
        _catalog_cache[key] = (now + _CACHE_TTL_SECONDS, entries)
    return entries


def _match_one(token: str, entries: List[dict]) -> Tuple[List[str], str]:
    """Return (matched_canonical_enums, match_kind) for a single user input.

    Match precedence:
      1. exact canonical ``app`` match (``ONEDRIVE_PERSONAL``)
      2. exact ``app_name`` match (``OneDrive Personal``), case/space-insensitive
      3. unique substring match against ``app`` or ``app_name`` (normalized)

    Multiple matches at the same precedence return all candidates and the
    caller decides whether to fail (ambiguity) or accept (multi-app input).
    """
    norm_input = _normalize(token)
    if not norm_input:
        return [], "empty"

    # 1. canonical app exact match (case-insensitive)
    upper_token = token.strip().upper()
    canonical_hits = [e["app"] for e in entries if e["app"] and e["app"].upper() == upper_token]
    if canonical_hits:
        return list(dict.fromkeys(canonical_hits)), "canonical"

    # 2. exact app_name match (normalized)
    name_hits = [
        e["app"] for e in entries if e["app"] and _normalize(e["app_name"]) == norm_input
    ]
    if name_hits:
        return list(dict.fromkeys(name_hits)), "display_name"

    # 3. substring match against app or app_name (normalized)
    substr_hits = [
        e["app"]
        for e in entries
        if e["app"]
        and (norm_input in _normalize(e["app"]) or norm_input in _normalize(e["app_name"]))
    ]
    return list(dict.fromkeys(substr_hits)), "substring"


def _format_suggestions(token: str, entries: List[dict], limit: int = 8) -> List[str]:
    """Best-effort suggestion list for an unresolvable input."""
    norm = _normalize(token)
    if not norm:
        return []
    pairs = [
        (e["app"], e["app_name"])
        for e in entries
        if e["app"]
        and (norm[:4] and (norm[:4] in _normalize(e["app"]) or norm[:4] in _normalize(e["app_name"])))
    ]
    return [f"{app} ({name})" if name else app for app, name in pairs[:limit]]


def resolve_cloud_applications(
    inputs: Iterable[str],
    *,
    scope: Scope = "ssl",
    use_legacy: bool = False,
    service: str = "zia",
    strict: bool = True,
) -> Tuple[List[str], dict]:
    """Translate user-supplied cloud-app names into canonical ZIA enum tokens.

    Args:
        inputs: Iterable of user-provided strings — friendly names, canonical
            enums, or partial matches. Each entry may itself resolve to one
            or more canonical enums (e.g. an input like ``"sharepoint"`` may
            match ``SHAREPOINT_ONLINE`` and ``SHAREPOINT_FOR_BUSINESS``).
        scope: ``"ssl"`` resolves against ``list_cloud_app_ssl_policy`` (the
            catalog used by SSL Inspection rules). ``"policy"`` resolves
            against ``list_cloud_app_policy`` (the catalog used by Web DLP,
            Cloud App Control, etc.).
        use_legacy / service: forwarded to the SDK client factory.
        strict: when ``True`` (default), raises :class:`ValueError` if any
            input fails to resolve or yields multiple canonical hits at the
            substring-match level (which would otherwise broaden the rule
            beyond what the user asked for). When ``False``, ambiguous
            inputs return *all* their candidate enums and unresolved inputs
            are silently dropped.

    Returns:
        ``(resolved, audit)`` where ``resolved`` is the de-duplicated list
        of canonical enum tokens to send to the ZIA API and ``audit`` is a
        mapping of every input to the enum(s) it resolved to and the match
        kind, useful for surfacing the resolution to the agent/user.
    """
    inputs_list = [str(i) for i in inputs if str(i).strip()]
    if not inputs_list:
        return [], {"resolved": {}, "unresolved": [], "ambiguous": {}}

    audit = {"resolved": {}, "unresolved": [], "ambiguous": {}}
    resolved: List[str] = []

    # Skip the catalog fetch only when every input already looks canonical
    # AND we don't need to validate against the catalog.
    skip_catalog = not strict and all(_looks_like_canonical_enum(t) for t in inputs_list)
    entries: List[dict] = [] if skip_catalog else _fetch_catalog(
        scope, use_legacy=use_legacy, service=service
    )
    canonical_set = {e["app"].upper() for e in entries if e["app"]} if entries else set()

    for token in inputs_list:
        # Fast path: input already in canonical UPPER_SNAKE form.
        if _looks_like_canonical_enum(token):
            if entries and token.upper() not in canonical_set:
                audit["unresolved"].append(token)
                if strict:
                    suggestions = _format_suggestions(token, entries)
                    raise ValueError(
                        f"'{token}' is not a recognized ZIA cloud-application enum "
                        f"for scope='{scope}'."
                        + (f" Did you mean: {', '.join(suggestions)}?" if suggestions else "")
                    )
                continue
            resolved.append(token.upper())
            audit["resolved"][token] = {"enums": [token.upper()], "match": "canonical"}
            continue

        # Slow path: friendly name / partial — needs catalog lookup.
        hits, kind = _match_one(token, entries)
        if not hits:
            audit["unresolved"].append(token)
            if strict:
                suggestions = _format_suggestions(token, entries)
                raise ValueError(
                    f"Could not resolve cloud application '{token}' to a canonical "
                    f"ZIA enum (scope='{scope}')."
                    + (f" Closest matches: {', '.join(suggestions)}." if suggestions else "")
                )
            continue

        if kind == "substring" and len(hits) > 1:
            audit["ambiguous"][token] = hits
            if strict:
                raise ValueError(
                    f"Cloud application '{token}' is ambiguous — matches "
                    f"{len(hits)} canonical enums: {', '.join(hits)}. "
                    "Please use the exact canonical enum (e.g. "
                    f"'{hits[0]}') or a more specific name."
                )

        resolved.extend(hits)
        audit["resolved"][token] = {"enums": hits, "match": kind}

    seen: set[str] = set()
    deduped: List[str] = []
    for enum in resolved:
        if enum and enum not in seen:
            seen.add(enum)
            deduped.append(enum)

    return deduped, audit


def clear_cache() -> None:
    """Drop the in-process catalog cache (test helper / refresh hook)."""
    with _cache_lock:
        _catalog_cache.clear()
