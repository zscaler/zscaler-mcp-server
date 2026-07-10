"""Shared reference view + IdP resolver for the ZPA ``get_zpa_*`` lookup tools.

The reference-data lookups (profiles, identity attributes, trusted networks)
all return objects that are referenced *by ID* inside other ZPA configs. The
agent needs them only to resolve a human name -> the ID a write tool expects,
so they all share the same lean ``id`` + ``name`` curated view. Registers no
tools itself.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from zscaler_mcp.shaping import AgentView, pick

__all__ = ["RefItem", "shape_ref", "resolve_idp_id"]


class RefItem(AgentView):
    """Generic reference item — id + name + optional context for ID resolution."""

    id: str = Field(description="Object ID. Use this in follow-up / write calls.")
    name: Optional[str] = Field(default=None, description="Display name to match against.")
    description: Optional[str] = Field(default=None, description="Description, if present.")


def shape_ref(raw: dict[str, Any]) -> RefItem:
    return RefItem(
        id=str(pick(raw, "id", default="")),
        name=pick(raw, "name"),
        description=pick(raw, "description"),
    )


def resolve_idp_id(client: Any, idp_name: str) -> str:
    """Resolve an IdP display name to its ID (mirrors v1's lookup)."""
    idps, _, err = client.zpa.idp.list_idps(query_params={"search": idp_name})
    if err:
        raise RuntimeError(f"Failed to look up IdP by name: {err}")
    match = next((i for i in (idps or []) if getattr(i, "name", None) == idp_name), None)
    if not match:
        raise RuntimeError(f"No matching IdP found with name '{idp_name}'")
    return str(match.id)
