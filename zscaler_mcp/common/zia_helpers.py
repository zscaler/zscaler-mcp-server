"""Shared helpers for ZIA tools.

Single home for cross-cutting ZIA helpers — extend this file rather than
adding new ``zia_*`` modules under ``common/``. Keep helpers grouped by
section header below.

Sections:
    1. Admin rank semantics (rule-based resources)
    2. Cloud-application enum resolver
    3. Cloud-application class (``app_class``) catalog
    4. URL categories (predefined-vs-custom resolution)

If you need to add a new helper, add a new section with a clear
``=========`` header in this file. Only split into a separate module
when (a) the helper has its own external dependencies that other ZIA
helpers don't share, OR (b) this file grows past ~600 lines.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Iterable, List, Literal, Optional, Tuple

# ============================================================================
# 1. Admin rank semantics
# ============================================================================
#
# Admin rank in ZIA (per https://help.zscaler.com/zia/about-admin-rank):
#
#     - Range: 0..7 inclusive
#     - 0  = highest rank (super admin)
#     - 7  = lowest rank (default for newly created rules)
#     - Lower-rank admins cannot override policies set by higher-rank admins.
#
# The MCP server defaults `rank` to 7 on create unless the admin explicitly
# specifies a different value. On update, `rank` is only included in the
# payload when the caller provides it (silent passthrough — we never
# "reset" rank on partial updates).

DEFAULT_RULE_RANK: int = 7

_VALID_RANK_RANGE = range(0, 8)  # 0..7 inclusive

# Canonical Field(description=...) for the `rank` parameter on every ZIA
# rule-create/update tool. Kept as a single string constant so we can
# update the wording in one place if Zscaler changes the documented
# behavior.
RANK_FIELD_DESCRIPTION: str = (
    "Admin rank of the rule. Integer in the inclusive range 0-7, where "
    "0 is the highest rank (super admin) and 7 is the lowest. New rules "
    "default to 7 when `rank` is omitted on create. On update, `rank` "
    "is only changed if explicitly provided. See "
    "https://help.zscaler.com/zia/about-admin-rank for what each level "
    "controls."
)


def validate_rank(rank: int) -> int:
    """Validate that ``rank`` is an integer in the inclusive range 0..7.

    Raises:
        ValueError: if ``rank`` is not an int or is outside 0..7.

    Returns:
        The validated rank.
    """
    if not isinstance(rank, int) or isinstance(rank, bool) or rank not in _VALID_RANK_RANGE:
        raise ValueError(
            f"rank must be an integer between 0 and 7 (inclusive). Got {rank!r}. "
            "0 = highest (super admin), 7 = lowest (default). "
            "See https://help.zscaler.com/zia/about-admin-rank."
        )
    return rank


def apply_default_rank(rank: int | None) -> int:
    """Return ``rank`` if provided (after validation), else the default 7.

    Use this on **create** paths only. On update paths, callers should
    instead validate-only-if-provided so missing `rank` is preserved.
    """
    if rank is None:
        return DEFAULT_RULE_RANK
    return validate_rank(rank)


# ----------------------------------------------------------------------------
# Rule order semantics
# ----------------------------------------------------------------------------
#
# Every ZIA policy-rule create endpoint REQUIRES the ``order`` field —
# the API rejects payloads where it is missing (or zero/negative) with a
# generic 400. ZIA admins typically want new rules at the top of the
# evaluation order so they take precedence over predefined defaults, so
# the MCP server defaults ``order`` to ``1`` on create unless the caller
# explicitly supplies a value. On update, the field is only included
# when provided — silent passthrough preserves the rule's existing
# position.
#
# Order is a positive integer (1-based). There is no documented upper
# bound — rules are renumbered/contiguous within a policy table and
# the API will accept any positive value, normalising it down to the
# next available slot.

DEFAULT_RULE_ORDER: int = 1


# Canonical Field(description=...) for the ``order`` parameter on every
# ZIA rule-create/update tool. Kept as a single string constant so
# wording changes (or a documented upper bound from Zscaler) only need
# updating in one place.
ORDER_FIELD_DESCRIPTION: str = (
    "Required by the ZIA API for every rule create call — positive "
    "integer (1-based) defining where the rule sits in the policy "
    "table's evaluation order. Lower numbers are evaluated first. "
    "Defaults to 1 (top) when omitted on create so new rules take "
    "precedence over predefined rules; on update, ``order`` is only "
    "changed when explicitly provided. Set this deliberately when "
    "creating multiple rules in one session so ordering reflects the "
    "intended policy precedence (e.g. ALLOW above BLOCK when both "
    "target overlapping traffic)."
)


def validate_order(order: int) -> int:
    """Validate that ``order`` is a positive integer.

    Raises:
        ValueError: if ``order`` is not an int or is < 1. ``True`` /
            ``False`` are rejected explicitly because ``bool`` is a
            subclass of ``int`` in Python.

    Returns:
        The validated order.
    """
    if not isinstance(order, int) or isinstance(order, bool) or order < 1:
        raise ValueError(
            f"order must be a positive integer (1-based, lower = evaluated first). "
            f"Got {order!r}."
        )
    return order


def apply_default_order(order: int | None) -> int:
    """Return ``order`` if provided (after validation), else the default 1.

    Use this on **create** paths only. On update paths, callers should
    instead validate-only-if-provided so the rule's existing position
    is preserved.
    """
    if order is None:
        return DEFAULT_RULE_ORDER
    return validate_order(order)


# ============================================================================
# 2. Cloud-application enum resolver
# ============================================================================
#
# Several ZIA policy resources (SSL Inspection, Web DLP, Cloud App Control,
# File Type Control, Bandwidth Classes, Advanced Settings) accept a
# ``cloud_applications`` field whose values are Zscaler's internal enum
# strings — for example ``ONEDRIVE``, ``ONEDRIVE_PERSONAL``, ``DROPBOX``,
# ``SHAREPOINT_ONLINE``. The ZIA API silently coerces unrecognised values
# to ``NONE`` instead of returning a validation error (issue #56).
#
# Users typically type the friendly display name ("OneDrive", "Google
# Drive", "share point online"). :func:`resolve_cloud_applications`
# translates those friendly inputs into canonical enum tokens by
# consulting the ZIA policy-engine catalog.
#
# The catalog is fetched lazily on first use and cached in-process for
# a short TTL (default 5 minutes), so repeated rule operations do not
# pay the network round-trip.

Scope = Literal["ssl", "policy"]

_CACHE_TTL_SECONDS = 300

# Cache key -> (expires_at_epoch, [{"app": ..., "app_name": ...}, ...])
_catalog_cache: dict[Tuple[Scope, str], Tuple[float, List[dict]]] = {}
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


def _entries_from_apps(apps: Iterable) -> List[dict]:
    """Project SDK cloud-app objects into the lightweight dict shape we cache."""
    entries: List[dict] = []
    for app in apps:
        entries.append(
            {
                "app": (getattr(app, "app", "") or "").strip(),
                "app_name": (getattr(app, "app_name", "") or "").strip(),
                "parent": (getattr(app, "parent", "") or "").strip(),
                "parent_name": (getattr(app, "parent_name", "") or "").strip(),
            }
        )
    return entries


_CATALOG_CACHE_PAGES = 3  # ~3000 most-common apps; long tail uses targeted search


def _fetch_catalog(scope: Scope, *, service: str) -> List[dict]:
    """Fetch (or return cached) policy-engine cloud-app catalog entries.

    The full ZIA catalog is large enough (~5-10k entries) that
    paginating it on first call adds an unacceptable ~2 minutes of
    latency. Instead we cache the first N pages (covering the most
    common apps) and rely on :func:`_lookup_canonical_by_search` to
    handle long-tail enums on demand.
    """
    key = (scope, service)
    now = time.time()

    with _cache_lock:
        cached = _catalog_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

    from zscaler_mcp.client import get_zscaler_client

    client = get_zscaler_client(service=service)
    cloud_apps = client.zia.cloud_applications

    fetcher = (
        cloud_apps.list_cloud_app_ssl_policy
        if scope == "ssl"
        else cloud_apps.list_cloud_app_policy
    )

    page_size = 1000
    all_entries: List[dict] = []
    seen_apps: set[str] = set()

    for page in range(1, _CATALOG_CACHE_PAGES + 1):
        apps, _, err = fetcher(query_params={"page_size": page_size, "page": page})
        if err:
            raise RuntimeError(
                f"Could not fetch ZIA cloud-application catalog "
                f"(scope={scope}, page={page}): {err}"
            )
        if not apps:
            break

        page_entries = _entries_from_apps(apps)
        new_entries = [e for e in page_entries if e["app"] and e["app"] not in seen_apps]
        for e in new_entries:
            seen_apps.add(e["app"])
        all_entries.extend(new_entries)

        if len(apps) < page_size:
            break

    with _cache_lock:
        _catalog_cache[key] = (now + _CACHE_TTL_SECONDS, all_entries)
    return all_entries


def _lookup_canonical_by_search(
    token: str, *, scope: Scope, service: str
) -> Optional[dict]:
    """Targeted SDK query for a single canonical enum that isn't cached yet.

    Used as a fallback when ``_fetch_catalog`` didn't return ``token``.
    The ZIA API supports a ``search`` substring filter on ``app_name``,
    so we search for the canonical token and look for an exact-app
    match in the (much smaller) result set. On hit, the entry is
    appended to the cache so subsequent calls skip the round-trip.
    """
    if not token:
        return None

    from zscaler_mcp.client import get_zscaler_client

    client = get_zscaler_client(service=service)
    fetcher = (
        client.zia.cloud_applications.list_cloud_app_ssl_policy
        if scope == "ssl"
        else client.zia.cloud_applications.list_cloud_app_policy
    )

    # The ZIA ``search`` parameter is a substring match on
    # ``app_name`` (the friendly display name with spaces), not on
    # ``app`` (the canonical UPPER_SNAKE token). Convert
    # ``AZURE_DEVOPS`` -> ``AZURE DEVOPS`` so the API can find it.
    upper = token.strip().upper()
    search_term = upper.replace("_", " ").strip()
    if not search_term:
        return None

    apps, _, err = fetcher(
        query_params={"search": search_term, "page_size": 100, "page": 1}
    )
    if err or not apps:
        return None

    page_entries = _entries_from_apps(apps)
    match = next(
        (e for e in page_entries if e["app"] and e["app"].upper() == upper), None
    )
    if not match:
        return None

    key = (scope, service)
    with _cache_lock:
        cached = _catalog_cache.get(key)
        if cached:
            expires_at, entries = cached
            if not any(e["app"] == match["app"] for e in entries):
                _catalog_cache[key] = (expires_at, entries + [match])
    return match


def lookup_cloud_app_entry(
    canonical_app: str, *, scope: Scope = "policy", service: str = "zia"
) -> Optional[dict]:
    """Return the catalog entry for ``canonical_app`` (incl. ``parent`` / ``parent_name``).

    Looks first in the in-process cache, then falls back to a targeted
    ``search=`` query (with ``_`` -> space conversion). Returns ``None``
    if the app isn't in the policy catalog at all.

    Use this when a tool needs the **category** an app belongs to —
    e.g. Cloud App Control's ``list_available_actions`` is scoped by
    rule type (= category), and the rule type for a given app is the
    app's ``parent`` field.
    """
    if not canonical_app:
        return None
    upper = canonical_app.strip().upper()
    if not upper:
        return None

    key = (scope, service)
    with _cache_lock:
        cached = _catalog_cache.get(key)
    if cached:
        for e in cached[1]:
            if e["app"] and e["app"].upper() == upper:
                return e

    return _lookup_canonical_by_search(canonical_app, scope=scope, service=service)


def list_apps_in_category(
    category: str,
    *,
    scope: Scope = "policy",
    service: str = "zia",
    limit: int = 50,
) -> List[dict]:
    """Return up to ``limit`` catalog entries in the given category.

    ``category`` may be either the canonical policy-endpoint enum
    (``STREAMING_MEDIA``, ``WEBMAIL``) or the catalog's own ``parent``
    value (``STREAMING``, ``WEB_MAIL``). Internally translates to the
    catalog vocabulary because the ``app_class`` query parameter on
    ``list_cloud_app_policy`` uses the catalog form.

    Used to find "representative" apps when probing
    ``list_available_actions`` — only some apps in a category surface
    the action set even though the actions are category-scoped, so we
    may need to walk a few candidates.
    """
    if not category:
        return []

    catalog_value = parent_for_app_class(category)
    if not catalog_value:
        return []

    from zscaler_mcp.client import get_zscaler_client

    client = get_zscaler_client(service=service)
    fetcher = (
        client.zia.cloud_applications.list_cloud_app_ssl_policy
        if scope == "ssl"
        else client.zia.cloud_applications.list_cloud_app_policy
    )

    apps, _, err = fetcher(
        query_params={"app_class": catalog_value, "page_size": max(limit, 100), "page": 1}
    )
    if err or not apps:
        return []
    return _entries_from_apps(apps)[:limit]


def _search_friendly_name(
    token: str, *, scope: Scope, service: str, page_size: int = 100
) -> List[dict]:
    """Targeted ``search=`` query for friendly-name resolution.

    Returns the catalog entries the API surfaces for ``token`` —
    stripped of the ``_`` separator since ``search`` matches on the
    spaced ``app_name`` field. Used to broaden resolution when the
    cached catalog pages only yielded a weak/empty match.
    """
    if not token or not token.strip():
        return []

    from zscaler_mcp.client import get_zscaler_client

    client = get_zscaler_client(service=service)
    fetcher = (
        client.zia.cloud_applications.list_cloud_app_ssl_policy
        if scope == "ssl"
        else client.zia.cloud_applications.list_cloud_app_policy
    )

    search_term = token.strip().replace("_", " ")
    apps, _, err = fetcher(
        query_params={"search": search_term, "page_size": page_size, "page": 1}
    )
    if err or not apps:
        return []
    return _entries_from_apps(apps)


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
        service: forwarded to the SDK client factory.
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
        scope, service=service
    )
    canonical_set = {e["app"].upper() for e in entries if e["app"]} if entries else set()

    for token in inputs_list:
        # Fast path: input already in canonical UPPER_SNAKE form.
        if _looks_like_canonical_enum(token):
            upper_token = token.upper()
            if entries and upper_token not in canonical_set:
                # The cached catalog page didn't include this enum.
                # Before declaring it invalid, try a targeted lookup —
                # the ZIA catalog has more entries than fit in one
                # page and the cached fetch can miss the long tail.
                fallback = _lookup_canonical_by_search(
                    token, scope=scope, service=service
                )
                if fallback:
                    entries.append(fallback)
                    canonical_set.add(fallback["app"].upper())
                    resolved.append(upper_token)
                    audit["resolved"][token] = {
                        "enums": [upper_token],
                        "match": "canonical",
                    }
                    continue
                audit["unresolved"].append(token)
                if strict:
                    suggestions = _format_suggestions(token, entries)
                    raise ValueError(
                        f"'{token}' is not a recognized ZIA cloud-application enum "
                        f"for scope='{scope}'."
                        + (f" Did you mean: {', '.join(suggestions)}?" if suggestions else "")
                    )
                continue
            resolved.append(upper_token)
            audit["resolved"][token] = {"enums": [upper_token], "match": "canonical"}
            continue

        # Slow path: friendly name / partial — needs catalog lookup.
        hits, kind = _match_one(token, entries)

        # If the cached pages only produced a weak ``substring`` hit
        # (or no hit at all), do a targeted server-side ``search``
        # query before trusting the result. The cached pages cover a
        # small slice of a large catalog, and a substring match
        # against that slice can silently pick the wrong app
        # (e.g. ``"Github"`` matching ``GITHUB_COPILOT`` because the
        # real ``GITHUB`` entry isn't in the cached pages).
        if not hits or kind == "substring":
            extra_entries = _search_friendly_name(
                token, scope=scope, service=service
            )
            if extra_entries:
                # Merge into the in-process catalog view so subsequent
                # tokens benefit from the broader entry set.
                for new_e in extra_entries:
                    if new_e["app"].upper() not in canonical_set:
                        entries.append(new_e)
                        canonical_set.add(new_e["app"].upper())
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
    """Drop the in-process cloud-app catalog cache (test helper / refresh hook)."""
    with _cache_lock:
        _catalog_cache.clear()


# ============================================================================
# 3. Cloud-application class (``app_class`` / ``rule_type``) catalog
# ============================================================================
#
# Two distinct vocabularies coexist in ZIA for the same set of app
# categories, and they don't fully agree:
#
#   - **Policy vocabulary** — the value the policy endpoints (URL
#     Filtering, SSL Inspection, Cloud App Control) accept on their
#     ``rule_type`` parameter. The SDK exposes this as a
#     display_name -> enum map via
#     ``client.zia.cloudappcontrol.get_rule_type_mapping()``. Examples:
#     ``WEBMAIL``, ``STREAMING_MEDIA``, ``AI_ML``.
#
#   - **Catalog vocabulary** — the value stored in the ``parent`` field
#     of each cloud-app catalog entry, also accepted by the
#     ``app_class`` query parameter on
#     ``cloud_applications.list_cloud_app_policy``. Examples:
#     ``WEB_MAIL`` (vs ``WEBMAIL``), ``STREAMING`` (vs ``STREAMING_MEDIA``).
#     Most categories happen to match both vocabularies; only the two
#     listed here differ.
#
# We treat the SDK ``get_rule_type_mapping()`` response as the single
# source of truth for the policy vocabulary (cached in-process for
# ``_CACHE_TTL_SECONDS``). The catalog-only oddities live in the small
# static table below — extend it here if Zscaler ever adds more
# mismatches.
#
# A static fallback list (``_CLOUD_APP_CLASSES_STATIC``) mirrors the
# current policy vocabulary so the agent gets the full enum list in
# tool descriptions even before any API call has populated the cache.
# Keep it in sync with the SDK mapping when Zscaler adds new categories.

# Catalog-vocabulary <-> policy-vocabulary edge cases. Most categories
# are identical in both vocabularies, so this map only carries the
# divergences.
_PARENT_TO_APP_CLASS: dict[str, str] = {
    "STREAMING": "STREAMING_MEDIA",
    "WEB_MAIL": "WEBMAIL",
}

_APP_CLASS_TO_PARENT: dict[str, str] = {v: k for k, v in _PARENT_TO_APP_CLASS.items()}

# Static fallback for ``Field(description=...)`` strings — the agent
# sees this list at tool-search time without paying for an API call.
# Runtime validation prefers the live SDK mapping.
_CLOUD_APP_CLASSES_STATIC: Tuple[str, ...] = (
    "SOCIAL_NETWORKING",
    "STREAMING_MEDIA",
    "WEBMAIL",
    "INSTANT_MESSAGING",
    "BUSINESS_PRODUCTIVITY",
    "ENTERPRISE_COLLABORATION",
    "SALES_AND_MARKETING",
    "SYSTEM_AND_DEVELOPMENT",
    "CONSUMER",
    "HOSTING_PROVIDER",
    "IT_SERVICES",
    "FILE_SHARE",
    "DNS_OVER_HTTPS",
    "HUMAN_RESOURCES",
    "LEGAL",
    "HEALTH_CARE",
    "FINANCE",
    "CUSTOM_CAPP",
    "AI_ML",
)

# Backwards-compatible re-export for callers that imported the static
# tuple. New code should use :func:`get_cloud_app_classes` to pick up
# any newly-added categories from the live SDK mapping.
CLOUD_APP_CLASSES: Tuple[str, ...] = _CLOUD_APP_CLASSES_STATIC

_rule_type_cache: dict[str, Tuple[float, dict[str, str]]] = {}
_rule_type_cache_lock = threading.Lock()


def get_rule_type_mapping(service: str = "zia") -> dict[str, str]:
    """Return the live ``display_name -> rule_type_enum`` map for ZIA categories.

    Cached in-process for :data:`_CACHE_TTL_SECONDS`. Falls back to a
    static map derived from :data:`_CLOUD_APP_CLASSES_STATIC` if the
    SDK call fails — no fatal errors for a metadata lookup.

    Example response::

        {
            "Webmail": "WEBMAIL",
            "Video Streaming": "STREAMING_MEDIA",
            "AI & ML Applications": "AI_ML",
            ...
        }
    """
    now = time.time()
    with _rule_type_cache_lock:
        cached = _rule_type_cache.get(service)
        if cached and cached[0] > now:
            return cached[1]

    from zscaler_mcp.client import get_zscaler_client

    try:
        client = get_zscaler_client(service=service)
        mapping, _, err = client.zia.cloudappcontrol.get_rule_type_mapping()
        if err or not isinstance(mapping, dict) or not mapping:
            raise RuntimeError(err or "empty mapping")
    except Exception:
        # Fall back to the static list; better to be slightly stale
        # than to break tool registration on a transient API failure.
        mapping = {enum.replace("_", " ").title(): enum for enum in _CLOUD_APP_CLASSES_STATIC}

    with _rule_type_cache_lock:
        _rule_type_cache[service] = (now + _CACHE_TTL_SECONDS, mapping)
    return mapping


def get_cloud_app_classes(service: str = "zia") -> Tuple[str, ...]:
    """Return the canonical (policy-vocabulary) category enums.

    Sourced live from the SDK's rule-type mapping with a static
    fallback for tool description strings.
    """
    mapping = get_rule_type_mapping(service=service)
    return tuple(sorted(set(mapping.values()))) if mapping else _CLOUD_APP_CLASSES_STATIC


def canonical_app_class_for_parent(parent: Optional[str]) -> Optional[str]:
    """Map a catalog ``parent`` value to its canonical ``app_class`` enum.

    The ZIA cloud-app catalog stores some categories under a different
    name than the one the policy endpoints accept. For example an app
    in the catalog has ``parent="STREAMING"``, but the SSL Inspection
    / Cloud App Control APIs reject ``rule_type=STREAMING`` and only
    accept ``rule_type=STREAMING_MEDIA``. This helper applies the
    translation table so callers pass the right value to the API.

    Returns ``None`` if ``parent`` is empty/None.
    """
    if not parent:
        return None
    canonical = parent.strip().upper()
    if not canonical:
        return None
    return _PARENT_TO_APP_CLASS.get(canonical, canonical)


def parent_for_app_class(app_class: Optional[str]) -> Optional[str]:
    """Inverse of :func:`canonical_app_class_for_parent`.

    Given a canonical ``app_class`` enum (the value the policy
    endpoints accept), return the catalog's ``parent`` value — needed
    when calling ``list_cloud_app_policy(query_params={"app_class":
    ...})`` because the catalog query uses the catalog vocabulary,
    not the policy-endpoint vocabulary.
    """
    if not app_class:
        return None
    canonical = app_class.strip().upper()
    if not canonical:
        return None
    return _APP_CLASS_TO_PARENT.get(canonical, canonical)


# Canonical Field(description=...) for the ``app_class`` parameter on
# every ZIA cloud-application list tool. Embedding the full enum list
# in the description lets the agent pick the right value directly from
# the user's intent without a separate lookup round-trip. The list
# uses the static fallback at module load time; runtime validation
# uses the live SDK mapping (so a category Zscaler adds tomorrow is
# accepted immediately even if this string is stale).
APP_CLASS_FIELD_DESCRIPTION: str = (
    "Filter the cloud-application catalog by category (``app_class``). "
    "Use this when the user describes a kind of application — e.g. "
    "'webmail', 'AI tools', 'file sharing', 'streaming' — rather than "
    "a specific app. Must be one of the canonical ZIA enum values: "
    + ", ".join(f"``{c}``" for c in _CLOUD_APP_CLASSES_STATIC)
    + ". The full live list is whatever "
    "``client.zia.cloudappcontrol.get_rule_type_mapping()`` returns."
)


def validate_app_class(
    app_class: Optional[str], *, service: str = "zia"
) -> Optional[str]:
    """Validate and canonicalize an ``app_class`` value.

    Accepts either vocabulary — catalog-form (``WEB_MAIL``,
    ``STREAMING``) is translated to the canonical policy form
    (``WEBMAIL``, ``STREAMING_MEDIA``). Validation is performed
    against the live SDK rule-type mapping
    (:func:`get_rule_type_mapping`) with the static fallback as a
    backstop if the SDK call has not yet populated the cache.

    Args:
        app_class: The raw input from the caller. ``None`` and empty
            strings pass through as ``None`` (no filter applied).
        service: SDK service identifier for the live mapping lookup.

    Returns:
        The canonical ``UPPER_SNAKE_CASE`` value in the **policy
        vocabulary** (the form ``rule_type`` parameters accept), or
        ``None`` if no filter was requested.

    Raises:
        ValueError: when ``app_class`` is non-empty but not in the
            recognized set.
    """
    if app_class is None:
        return None
    candidate = app_class.strip().upper()
    if not candidate:
        return None

    candidate = canonical_app_class_for_parent(candidate) or candidate

    valid = set(get_cloud_app_classes(service=service))
    if candidate not in valid:
        valid_sorted = ", ".join(sorted(valid))
        raise ValueError(
            f"app_class={app_class!r} is not a recognized ZIA "
            f"cloud-application category. Valid values: {valid_sorted}."
        )
    return candidate


# ============================================================================
# 4. URL categories (predefined-vs-custom resolution)
# ============================================================================
#
# ZIA exposes two flavors of URL categories that share the same API
# surface but have very different lifecycle semantics:
#
#   - **Custom** categories — the admin owns them. They can be created,
#     fully replaced (PUT), and deleted. The MCP exposes them via
#     ``zia_create_url_category`` / ``zia_update_url_category`` /
#     ``zia_delete_url_category``.
#
#   - **Predefined** categories — Zscaler owns them (e.g. ``FINANCE``,
#     ``NEWS_AND_MEDIA``, ``OTHER_ADULT_MATERIAL``). They cannot be
#     created or deleted. They CAN be modified, but only in
#     well-defined ways:
#
#       * Incrementally adding URLs / IP ranges via
#         ``add_urls_to_category`` (``?action=ADD_TO_LIST``) or
#         removing via ``delete_urls_from_category``
#         (``?action=REMOVE_FROM_LIST``) — both already exposed as
#         ``zia_add_urls_to_category`` / ``zia_remove_urls_from_category``
#         and work identically against custom and predefined IDs.
#
#       * Full-PUT replacement of the keyword fields and any other
#         editable list fields via ``zia_update_url_category_predefined``
#         — this is the new entry point this section supports.
#
#     A naive full-PUT ``zia_update_url_category`` against a predefined
#     ID would obliterate Zscaler's curated URL list, which is why the
#     custom-category tools refuse predefined IDs (the safety guard
#     calls into :func:`resolve_predefined_category` below).
#
# ``resolve_predefined_category`` is the single source of truth for
# "is this identifier a predefined category, and if so what is its
# canonical ID and current state?". Both predefined-category tools and
# both safety guards on the custom-category tools call it.


def resolve_predefined_category(
    client,
    identifier: str,
) -> dict:
    """Resolve a predefined URL category by canonical ID or display name.

    Mirrors the resolution behavior of the Terraform
    ``resource_zia_url_categories_predefined`` resource: accepts either
    the canonical ID (``"FINANCE"``) or the configured display name
    (``"Finance"``), case-insensitively, and refuses to return a custom
    category.

    Args:
        client: A ready-to-use Zscaler SDK client (the caller is
            responsible for obtaining it from
            :func:`zscaler_mcp.client.get_zscaler_client`).
        identifier: Either the canonical predefined ID or the
            ``configured_name``. Case-insensitive.

    Returns:
        The matched category as a plain dict (the SDK object's
        ``as_dict()`` payload).

    Raises:
        ValueError: if ``identifier`` is empty, the category cannot be
            found, or the match is a custom category (which would be
            wrong to feed into the predefined-category tools).
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError("identifier is required and must be a non-empty string")

    api = client.zia.url_categories
    needle = identifier.strip()
    if not needle:
        raise ValueError("identifier is required and must be a non-empty string")

    # Try a direct GET first — fastest path when the caller already
    # passed a canonical predefined ID like "FINANCE".
    direct, _, err = api.get_category(category_id=needle)
    if not err and direct is not None:
        entry = direct.as_dict() if hasattr(direct, "as_dict") else dict(direct)
        if entry.get("custom_category"):
            raise ValueError(
                f"{identifier!r} resolves to a custom URL category. The "
                "predefined-category tools only accept Zscaler's curated "
                "categories. Use the custom-category tools "
                "(zia_get_url_category / zia_update_url_category / "
                "zia_delete_url_category) instead."
            )
        return entry

    # Fall back to scanning the full catalog by ``configured_name``.
    # Mirrors the Terraform ``Importer.StateContext`` resolution path:
    # case-insensitive match on ID or ``configured_name``, predefined
    # only.
    candidates, _, err = api.list_categories(query_params={})
    if err:
        raise ValueError(
            f"failed to list URL categories while resolving {identifier!r}: {err}"
        )

    needle_ci = needle.casefold()
    for cat in candidates or []:
        entry = cat.as_dict() if hasattr(cat, "as_dict") else dict(cat)
        if entry.get("custom_category"):
            continue
        canonical = str(entry.get("id") or "").casefold()
        display = str(entry.get("configured_name") or "").casefold()
        if needle_ci in (canonical, display):
            return entry

    raise ValueError(
        f"{identifier!r} did not match any predefined URL category. "
        "Pass either the canonical ID (e.g. 'FINANCE') or the display "
        "name (e.g. 'Finance')."
    )


__all__ = [
    # Admin rank
    "DEFAULT_RULE_RANK",
    "RANK_FIELD_DESCRIPTION",
    "validate_rank",
    "apply_default_rank",
    # Rule order
    "DEFAULT_RULE_ORDER",
    "ORDER_FIELD_DESCRIPTION",
    "validate_order",
    "apply_default_order",
    # Cloud-app resolver
    "Scope",
    "resolve_cloud_applications",
    "lookup_cloud_app_entry",
    "list_apps_in_category",
    "clear_cache",
    # Cloud-app class catalog
    "CLOUD_APP_CLASSES",
    "APP_CLASS_FIELD_DESCRIPTION",
    "validate_app_class",
    "get_rule_type_mapping",
    "get_cloud_app_classes",
    "canonical_app_class_for_parent",
    "parent_for_app_class",
    # URL categories
    "resolve_predefined_category",
]
