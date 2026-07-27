"""Response-shaping package — the core of the v2 design (DESIGN.md §5).

A *shaper* is a deterministic transform: ``raw SDK dict -> curated view``. It is
where the "what does an AGENT need from this response?" decision lives.

This ``__init__`` only declares the package's public API. Implementations live
in:

- :mod:`zscaler_mcp.shaping.views`   — the :class:`AgentView` base (view contract)
- :mod:`zscaler_mcp.shaping.helpers` — :func:`pick` / :func:`coalesce` /
  :func:`shape_many` (defensive SDK-dict access)

Import from this package::

    from zscaler_mcp.shaping import AgentView, pick, coalesce, shape_many
"""

from zscaler_mcp.shaping.helpers import coalesce, pick, shape_many, shape_one
from zscaler_mcp.shaping.views import AgentView

__all__ = ["AgentView", "pick", "coalesce", "shape_many", "shape_one"]
