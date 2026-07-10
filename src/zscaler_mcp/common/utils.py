"""Low-level, product-agnostic utilities (v2 equivalent of v1 ``utils/utils.py``).

This is the v2 home for small helpers that are *not* tied to any one Zscaler
product — the kind of thing v1 kept in ``zscaler_mcp/utils/utils.py``. Following
the helper-file convention (don't fragment), append new product-agnostic helpers
here rather than creating per-feature modules. Product-specific helpers belong in
a ``common/{service}_helpers.py`` file instead.

Ported subset (the genuinely cross-cutting ones):

* :func:`parse_list` — tolerant list parsing (JSON-string or already-a-list).
* :func:`get_mcp_user_agent` / :func:`get_combined_user_agent` — User-Agent
  string construction for the SDK's outbound calls.

The ZIA-specific converters from v1 (``convert_v2_to_sdk_format``, country-code
validators, …) are intentionally NOT ported yet — v2 has no tool that needs
them. Add them to a ``common/zia_helpers.py`` when the first ZIA tool lands.
"""

from __future__ import annotations

import json
import platform
from typing import Any, Optional, Union

__all__ = [
    "parse_list",
    "get_mcp_user_agent",
    "get_combined_user_agent",
]


def parse_list(val: Union[str, list, Any]) -> Union[list, Any]:
    """Parse a list parameter that may arrive as a JSON string or a real list.

    Returns the parsed list when ``val`` is a JSON string, otherwise returns
    ``val`` unchanged. Raises ``ValueError`` if ``val`` is a string but not
    valid JSON.

    >>> parse_list('["a", "b"]')
    ['a', 'b']
    >>> parse_list(["a", "b"])
    ['a', 'b']
    >>> parse_list(123)
    123
    """
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON string: {exc}") from exc
    return val


def _get_package_version() -> str:
    """Best-effort resolution of the installed/declared package version.

    Order: installed dist metadata → in-source ``__version__`` → ``0.0.0``
    sentinel (intentionally invalid so a regression is loud, not silent).
    """
    import importlib.metadata

    for dist in ("zscaler-mcp-server", "zscaler-mcp"):
        try:
            return importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            continue

    try:
        from zscaler_mcp import __version__ as pkg_version
    except ImportError:
        return "0.0.0"

    return pkg_version or "0.0.0"


def get_mcp_user_agent() -> str:
    """Return ``zscaler-mcp/<version>/<OS-Release-Arch>`` for outbound calls."""
    version = _get_package_version()
    os_arch = f"{platform.system()}-{platform.release()}-{platform.machine()}"
    return f"zscaler-mcp/{version}/{os_arch}"


def get_combined_user_agent(user_agent_comment: Optional[str] = None) -> str:
    """Append an optional operator comment to the base User-Agent string."""
    base = get_mcp_user_agent()
    comment = (user_agent_comment or "").strip()
    return f"{base} ({comment})" if comment else base
