"""Shared helpers for ZPA app connectors and service edges.

App connectors and service edges are near-identical runtime resources (both
enroll via a provisioning key, both report control-channel health), so the
public ``app_connectors.py`` and ``service_edges.py`` modules share this
query-param builder and delete-result type. Registers no tools itself.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from zscaler_mcp.shaping import AgentView

__all__ = [
    "OperationResult",
    "query_params",
]


class OperationResult(AgentView):
    """Result of a destructive operation (delete / bulk delete)."""

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable result summary.")


def query_params(*, search=None, page=None, page_size=None, microtenant_id=None) -> dict[str, Any]:
    qp: dict[str, Any] = {}
    if microtenant_id:
        qp["microtenant_id"] = microtenant_id
    if search:
        qp["search"] = search
    if page is not None:
        qp["page"] = str(page)
    if page_size is not None:
        qp["page_size"] = str(page_size)
    return qp
