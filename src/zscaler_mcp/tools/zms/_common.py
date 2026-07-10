"""Shared ZMS tool helpers (v2).

ZMS is a GraphQL service (``POST /zms/graphql``). Two things are common to every
ZMS tool and worth factoring out so the per-domain modules stay focused on
shaping:

* **customer_id resolution.** Every ZMS query requires the tenant
  ``ZSCALER_CUSTOMER_ID``. :func:`require_customer_id` reads it from the
  environment and raises a clear error if it is missing (mirrors v1's
  per-tool guard, but as an exception so the v2 bridge surfaces it uniformly).
* **Connection unwrapping.** List queries return a GraphQL *connection* dict
  ``{"nodes": [...], "page_info": {...}}`` (camelCase ``pageInfo`` in some
  responses). :func:`nodes_of` extracts the row list regardless of casing.
  Single-object / statistics queries return a plain dict and are shaped directly.

These mirror the logic in v1's ``zscaler_mcp/tools/zms/*`` modules, but ZMS
results are already plain dicts (no SDK ``as_dict()`` round-trip needed).
"""

from __future__ import annotations

import os
from typing import Any

__all__ = ["require_customer_id", "nodes_of", "page_info_of"]


def require_customer_id() -> str:
    """Return ``ZSCALER_CUSTOMER_ID`` or raise a clear, agent-facing error."""
    customer_id = os.environ.get("ZSCALER_CUSTOMER_ID", "")
    if not customer_id:
        raise RuntimeError(
            "ZSCALER_CUSTOMER_ID is required for ZMS tools. Set it in the server "
            "environment (the tenant/customer ID)."
        )
    return customer_id


def nodes_of(result: Any) -> list[dict[str, Any]]:
    """Extract the ``nodes`` row list from a ZMS GraphQL connection dict.

    Tolerates ``nodes`` / ``Nodes`` and a missing/None connection (returns []).
    """
    if not isinstance(result, dict):
        return []
    nodes = result.get("nodes")
    if nodes is None:
        nodes = result.get("Nodes")
    return [n for n in nodes if isinstance(n, dict)] if isinstance(nodes, list) else []


def page_info_of(result: Any) -> dict[str, Any]:
    """Extract the ``page_info`` block from a ZMS connection dict (camel/snake)."""
    if not isinstance(result, dict):
        return {}
    info = result.get("page_info")
    if info is None:
        info = result.get("pageInfo")
    return info if isinstance(info, dict) else {}
