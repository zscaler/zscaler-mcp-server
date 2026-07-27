"""Agent-facing view base — DESIGN.md §5 Pillar A/B.

:class:`AgentView` is the contract every output view inherits. It does
two jobs:

1. Declares the *highlighted* fields (typed, documented) while preserving every
   un-declared SDK attribute via ``extra="allow"`` — views normalize and
   annotate the full record, they never strip it (issue #88).
2. Produces the JSON Schema the tool advertises as ``outputSchema``
   (:meth:`AgentView.output_schema`), whose ``additionalProperties: true``
   matches the full-record-plus-highlights contract on the wire.

Public API is re-exported from ``zscaler_mcp.shaping``; import from there.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = ["AgentView"]


class AgentView(BaseModel):
    """Base class for every agent-facing output view.

    Subclasses declare the *highlighted* fields — the identifying, decision-
    bearing, and normalized fields an agent reasons about most — and give them a
    typed, documented schema. They are NOT a whitelist: the tool returns the
    FULL SDK record (every attribute ``as_dict()`` produced), and the view's
    fields are merged on top to normalize/annotate the important ones (see
    :func:`zscaler_mcp.shaping.shape_many` / :func:`shape_one`).

    Concretely this means the view must NOT drop data. ``extra="allow"`` keeps
    any un-declared SDK attribute that flows through the merge, and — because
    Pydantic emits ``additionalProperties: true`` for an ``extra="allow"``
    model — the generated ``outputSchema`` advertises "these typed fields, plus
    whatever else the resource carries", which is exactly the contract the tool
    honors on the wire.

    Historical note: this base previously used ``extra="forbid"``, which turned
    every view into a hard whitelist and silently stripped every attribute the
    view didn't re-declare. That was the root cause of the regression class in
    issue #88 (``policy_name`` and ~34 other device fields disappearing). We no
    longer strip: token efficiency comes from toolset selection + the CSV wire
    format, never from dropping fields.
    """

    model_config = {
        # Keep any SDK attribute the view doesn't explicitly declare. This is
        # what guarantees the agent-facing surface is a SUPERSET of the curated
        # fields (never a subset) and makes the advertised outputSchema
        # (additionalProperties: true) match the full record returned on the wire.
        "extra": "allow",
    }

    @classmethod
    def output_schema(cls) -> dict[str, Any]:
        """JSON Schema (2020-12) for this view — the tool's ``outputSchema``."""
        return cls.model_json_schema()
