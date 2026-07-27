"""Shared container for ZIA tenant-wide singleton settings.

ATP policy, malware protection, advanced settings, and mobile-threat settings are
single mutable objects with dozens of boolean/scalar knobs. The agent needs the
*values*, not a remodeled subset — so we surface them under a ``settings`` dict.
This keeps the output schema declared (Pillar B) while preserving the full
settings payload for read-merge-write workflows (these singletons are strict
PUT-replace on the API side).
"""

from __future__ import annotations

from pydantic import Field

from zscaler_mcp.shaping import AgentView


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")
