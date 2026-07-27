"""Shared result type for the ZIA policy-rule families.

Every ZIA rule family (cloud firewall, URL filtering, SSL inspection, web DLP,
file-type control, sandbox, …) returns the same skeleton from the SDK: an id,
name, enabled flag, action, order/rank, and a constellation of relational
member lists (locations, groups, departments, labels, …). The agent rarely needs
the raw nested member objects — it needs the rule's identity, whether it's on,
what it does, where it sits in the table, and *how many* of each member type it
references. This module centralises the shared result type so each rule module stays
thin.

This is intentionally NOT in ``common/`` — these are ZIA-tool output views, not
cross-service infra. Per the helper-file convention, module-local shared code
lives next to its consumers.
"""

from __future__ import annotations

from pydantic import Field

from zscaler_mcp.shaping import AgentView

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


class OperationResult(AgentView):
    """Result of a destructive operation (delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")
