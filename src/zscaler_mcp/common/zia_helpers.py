"""Shared helpers for ZIA tools (v2).

Single home for cross-cutting ZIA helpers — extend this file rather than adding
new ``zia_*`` modules under ``common/`` (Helper-File Convention). Sections are
delimited with ``====`` headers.

Sections:
    1. Admin rank semantics (rule-based resources)
    2. Rule order semantics (rule-based resources)
"""

from __future__ import annotations

from typing import Any, Optional

from zscaler_mcp.common.utils import parse_list

__all__ = [
    "DEFAULT_RULE_RANK",
    "DEFAULT_RULE_ORDER",
    "RANK_FIELD_DESCRIPTION",
    "ORDER_FIELD_DESCRIPTION",
    "validate_rank",
    "apply_default_rank",
    "validate_order",
    "apply_default_order",
    "merge_advanced",
    "build_rule_payload",
    "resolve_predefined_category",
]

# =============================================================================
# 1. Admin rank semantics
# =============================================================================
#
# Admin rank in ZIA (https://help.zscaler.com/zia/about-admin-rank):
#   - Range 0..7 inclusive; 0 = highest (super admin), 7 = lowest (default).
# New rules default to rank 7 on create unless the caller specifies one. On
# update, rank is only sent when provided (never reset on partial updates).

DEFAULT_RULE_RANK: int = 7
_VALID_RANK_RANGE = range(0, 8)

RANK_FIELD_DESCRIPTION: str = (
    "Admin rank (0-7 inclusive; 0 = highest/super admin, 7 = lowest). New "
    "rules default to 7 when omitted on create; on update, only changed if "
    "explicitly provided."
)


def validate_rank(rank: int) -> int:
    """Validate ``rank`` is an int in 0..7 (bools rejected)."""
    if not isinstance(rank, int) or isinstance(rank, bool) or rank not in _VALID_RANK_RANGE:
        raise ValueError(
            f"rank must be an integer between 0 and 7 (inclusive). Got {rank!r}. "
            "0 = highest (super admin), 7 = lowest (default)."
        )
    return rank


def apply_default_rank(rank: Optional[int]) -> int:
    """Return validated ``rank`` or the default 7. Create paths only."""
    return DEFAULT_RULE_RANK if rank is None else validate_rank(rank)


# =============================================================================
# 2. Rule order semantics
# =============================================================================
#
# Every ZIA policy-rule create REQUIRES ``order`` (positive, 1-based) — the API
# rejects payloads missing it. Default to 1 (top) on create when omitted; on
# update, only send when provided (silent passthrough preserves position).

DEFAULT_RULE_ORDER: int = 1

ORDER_FIELD_DESCRIPTION: str = (
    "Positive integer (1-based) for the rule's position in the policy table; "
    "lower = evaluated first. Required by the ZIA API on create — defaults to "
    "1 (top) when omitted; on update, only changed when explicitly provided."
)


def validate_order(order: int) -> int:
    """Validate ``order`` is a positive int (bools rejected)."""
    if not isinstance(order, int) or isinstance(order, bool) or order < 1:
        raise ValueError(
            f"order must be a positive integer (1-based, lower = evaluated first). Got {order!r}."
        )
    return order


def apply_default_order(order: Optional[int]) -> int:
    """Return validated ``order`` or the default 1. Create paths only."""
    return DEFAULT_RULE_ORDER if order is None else validate_order(order)


# =============================================================================
# 3. Policy-rule payload assembly
# =============================================================================
#
# Every ZIA rule family (cloud firewall, URL filtering, SSL inspection, web DLP,
# file-type control, sandbox, …) shares the same "scalar fields + list-of-IDs
# fields + advanced passthrough" payload shape. These helpers keep the per-module
# create/update tools thin: the module declares its common typed fields, calls
# ``build_rule_payload`` to assemble + parse them, and the SDK call stays uniform.

# List-valued rule fields that may arrive as JSON strings and need parse_list().
_RULE_LIST_FIELDS = frozenset(
    {
        "src_ips",
        "dest_addresses",
        "source_countries",
        "dest_countries",
        "dest_ip_categories",
        "device_trust_levels",
        "nw_applications",
        "app_services",
        "app_service_groups",
        "departments",
        "dest_ip_groups",
        "dest_ipv6_groups",
        "devices",
        "device_groups",
        "groups",
        "labels",
        "locations",
        "location_groups",
        "nw_application_groups",
        "nw_services",
        "nw_service_groups",
        "time_windows",
        "users",
        "workload_groups",
        "url_categories",
        "request_methods",
        "user_agent_types",
        "protocols",
        "file_types",
        "cloud_applications",
        "applications",
        "dlp_engines",
        "categories",
        "tenancy_profile_ids",
        "cbi_profile",
        "zpa_app_segments",
    }
)


def merge_advanced(payload: dict[str, Any], advanced: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Merge an ``advanced`` passthrough dict into ``payload`` in place.

    Values for keys in :data:`_RULE_LIST_FIELDS` are run through ``parse_list``
    so callers can pass JSON-string lists in ``advanced`` too. Returns
    ``payload`` for chaining.
    """
    if not advanced:
        return payload
    for key, value in advanced.items():
        if value is None:
            continue
        payload[key] = parse_list(value) if key in _RULE_LIST_FIELDS else value
    return payload


def build_rule_payload(
    scalars: dict[str, Any],
    lists: Optional[dict[str, Any]] = None,
    advanced: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Assemble a ZIA rule payload.

    Args:
        scalars: name/description/action/enabled/rank/order/booleans — included
            verbatim when not ``None``.
        lists: list-of-IDs fields — each non-``None`` value is ``parse_list``-ed.
        advanced: free-form passthrough merged last (so it can override).

    Returns:
        The assembled payload dict (omitting ``None`` values).
    """
    payload: dict[str, Any] = {k: v for k, v in scalars.items() if v is not None}
    for key, value in (lists or {}).items():
        if value is not None:
            payload[key] = parse_list(value)
    return merge_advanced(payload, advanced)


# =============================================================================
# 4. URL categories (predefined-vs-custom resolution)
# =============================================================================


def resolve_predefined_category(client: Any, identifier: str) -> dict[str, Any]:
    """Resolve a predefined URL category by canonical ID or display name.

    Accepts either the canonical ID (``"FINANCE"``) or the configured display
    name (``"Finance"``), case-insensitively, and refuses to return a custom
    category.

    Raises:
        ValueError: if ``identifier`` is empty, the category cannot be found, or
            the match is a custom category.
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError("identifier is required and must be a non-empty string")

    api = client.zia.url_categories
    needle = identifier.strip()
    if not needle:
        raise ValueError("identifier is required and must be a non-empty string")

    direct, _, err = api.get_category(category_id=needle)
    if not err and direct is not None:
        entry = direct.as_dict() if hasattr(direct, "as_dict") else dict(direct)
        if entry.get("custom_category"):
            raise ValueError(
                f"{identifier!r} resolves to a custom URL category. The "
                "predefined-category tools only accept Zscaler's curated "
                "categories. Use zia_get_url_category / zia_update_url_category / "
                "zia_delete_url_category instead."
            )
        return entry

    candidates, _, err = api.list_categories(query_params={})
    if err:
        raise ValueError(f"failed to list URL categories while resolving {identifier!r}: {err}")

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
