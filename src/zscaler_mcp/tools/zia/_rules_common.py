"""Shared curated views + shaper for ZIA policy-rule families.

Every ZIA rule family (cloud firewall, URL filtering, SSL inspection, web DLP,
file-type control, sandbox, …) returns the same skeleton from the SDK: an id,
name, enabled flag, action, order/rank, and a constellation of relational
member lists (locations, groups, departments, labels, …). The agent rarely needs
the raw nested member objects — it needs the rule's identity, whether it's on,
what it does, where it sits in the table, and *how many* of each member type it
references. This module centralises that curated shape so each rule module stays
thin.

This is intentionally NOT in ``common/`` — these are ZIA-tool output views, not
cross-service infra. Per the helper-file convention, module-local shared code
lives next to its consumers.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from zscaler_mcp.shaping import AgentView, coalesce, pick

# Member-list fields counted in the summary. Each entry is (view_field, *aliases).
_MEMBER_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("locations", ("locations",)),
    ("location_groups", ("location_groups", "locationGroups")),
    ("groups", ("groups",)),
    ("departments", ("departments",)),
    ("users", ("users",)),
    ("labels", ("labels",)),
    ("dest_ip_groups", ("dest_ip_groups", "destIpGroups")),
    ("nw_services", ("nw_services", "nwServices")),
    ("url_categories", ("url_categories", "urlCategories")),
)


class RuleSummary(AgentView):
    """Lean, agent-facing view shared by every ZIA policy-rule family."""

    id: str = Field(description="Rule ID. Use this in get/update/delete calls.")
    name: str = Field(description="Rule name.")
    enabled: Optional[bool] = Field(default=None, description="Whether the rule is active.")
    action: Optional[str] = Field(default=None, description="Rule action (ALLOW/BLOCK/etc.).")
    order: Optional[int] = Field(default=None, description="Evaluation order (lower = first).")
    rank: Optional[int] = Field(default=None, description="Admin rank (0 highest .. 7 lowest).")
    description: Optional[str] = Field(default=None, description="Admin description.")
    member_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of referenced members by type (locations, groups, users, …).",
    )


class RuleDetail(RuleSummary):
    """Detail view — adds the resolved member ID lists for inspection."""

    member_ids: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Referenced member IDs by type. Empty types are omitted.",
    )
    state: Optional[str] = Field(default=None, description="Rule state, if reported.")


def _enabled(raw: dict[str, Any]) -> Optional[bool]:
    val = pick(raw, "enabled", "state")
    if isinstance(val, str):
        return val.upper() in ("ENABLED", "TRUE", "ON")
    return val if isinstance(val, bool) else None


def _action(raw: dict[str, Any]) -> Optional[str]:
    return pick(raw, "action", "rule_action")


def _member_counts(raw: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field, aliases in _MEMBER_FIELDS:
        members = coalesce(raw, *aliases)
        if members:
            counts[field] = len(members)
    return counts


def _member_ids(raw: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for field, aliases in _MEMBER_FIELDS:
        members = coalesce(raw, *aliases)
        ids = [str(m.get("id")) for m in members if isinstance(m, dict) and m.get("id") is not None]
        if ids:
            out[field] = ids
    return out


def shape_rule_summary(raw: dict[str, Any]) -> RuleSummary:
    return RuleSummary(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=_enabled(raw),
        action=_action(raw),
        order=pick(raw, "order"),
        rank=pick(raw, "rank"),
        description=pick(raw, "description"),
        member_counts=_member_counts(raw),
    )


def shape_rule_detail(raw: dict[str, Any]) -> RuleDetail:
    return RuleDetail(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name", default=""),
        enabled=_enabled(raw),
        action=_action(raw),
        order=pick(raw, "order"),
        rank=pick(raw, "rank"),
        description=pick(raw, "description"),
        member_counts=_member_counts(raw),
        member_ids=_member_ids(raw),
        state=pick(raw, "state"),
    )


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")
