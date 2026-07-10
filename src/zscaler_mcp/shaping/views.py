"""Curated agent-facing view base — DESIGN.md §5 Pillar A/B.

:class:`AgentView` is the contract every curated output model inherits. It does
two jobs:

1. Enforces the field policy at construction time via ``extra="forbid"`` — a
   shaper that tries to leak an un-curated SDK field fails loudly instead of
   silently widening the agent-facing surface.
2. Produces the JSON Schema the tool advertises as ``outputSchema``
   (:meth:`AgentView.output_schema`), so the curated view and the advertised
   schema can never drift.

Public API is re-exported from ``zscaler_mcp.shaping``; import from there.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = ["AgentView"]


class AgentView(BaseModel):
    """Base class for every curated, agent-facing output view.

    Subclasses declare ONLY the fields an agent needs to reason or act (see the
    field-policy checklist in DESIGN.md §5 Pillar A). The JSON Schema generated
    here is what the tool advertises as its ``outputSchema``.
    """

    model_config = {
        # Reject unexpected fields at construction time so a shaper that leaks
        # an un-curated SDK field fails loudly in tests instead of silently
        # widening the agent-facing surface.
        "extra": "forbid",
    }

    @classmethod
    def output_schema(cls) -> dict[str, Any]:
        """JSON Schema (2020-12) for this view — the tool's ``outputSchema``."""
        return cls.model_json_schema()
