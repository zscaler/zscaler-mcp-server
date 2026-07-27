"""Shared IdP resolver for the ZPA ``get_zpa_*`` reference-data lookup tools.

The reference-data lookups (profiles, identity attributes, trusted networks)
return objects that other ZPA configs reference *by ID*, so the agent uses them
to resolve a human name -> the ID a write tool expects. The records themselves
are returned verbatim; only this name->ID resolver is shared. Registers no tools
itself.
"""

from __future__ import annotations

from typing import Any

__all__ = ["resolve_idp_id"]


def resolve_idp_id(client: Any, idp_name: str) -> str:
    """Resolve an IdP display name to its ID (mirrors v1's lookup)."""
    idps, _, err = client.zpa.idp.list_idps(query_params={"search": idp_name})
    if err:
        raise RuntimeError(f"Failed to look up IdP by name: {err}")
    match = next((i for i in (idps or []) if getattr(i, "name", None) == idp_name), None)
    if not match:
        raise RuntimeError(f"No matching IdP found with name '{idp_name}'")
    return str(match.id)
