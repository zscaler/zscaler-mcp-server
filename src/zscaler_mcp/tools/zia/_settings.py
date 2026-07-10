"""Shared curated container for ZIA tenant-wide singleton settings.

ATP policy, malware protection, advanced settings, and mobile-threat settings are
single mutable objects with dozens of boolean/scalar knobs. The agent needs the
*values*, not a remodeled subset — so we surface them under a ``settings`` dict.
This keeps the output schema declared (Pillar B) while preserving the full
settings payload for read-merge-write workflows (these singletons are strict
PUT-replace on the API side).
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from zscaler_mcp.shaping import AgentView


class Settings(AgentView):
    """Container wrapping a tenant-wide settings dict.

    The ``settings`` field holds the full knob set. For PUT-replace singletons,
    read this first, mutate the dict, then submit the complete dict back.
    """

    settings: dict[str, Any] = Field(
        default_factory=dict, description="The full settings object (knob name -> value)."
    )


class OperationResult(AgentView):
    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def to_settings(raw: Any) -> Settings:
    if hasattr(raw, "as_dict"):
        raw = raw.as_dict()
    if not isinstance(raw, dict):
        raw = {"value": raw}
    return Settings(settings=raw)
