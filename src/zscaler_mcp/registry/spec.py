"""The internal record a registered tool produces.

This is NOT something a human hand-writes in a central list (that would just be
v1's ``services.py`` catalog with types). It is the record the ``@tool``
decorator (:mod:`zscaler_mcp.registry.decorator`) builds from metadata declared at
the tool's own definition site. Co-locating the declaration with the tool is the
design difference vs v1: there is no second list to keep in sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.shaping import AgentView

# The canonical, fixed Zero Trust verb set (DESIGN.md §2). One tool maps to
# exactly one of these, never multiplexed.
READ = "read"
CREATE = "create"
UPDATE = "update"
DELETE = "delete"

_VALID_ACTIONS = frozenset({READ, CREATE, UPDATE, DELETE})

# Actions that mutate the tenant — used by the filtering layer to enforce
# read-only-by-default (DESIGN.md §2 / §6).
_WRITE_ACTIONS = frozenset({CREATE, UPDATE, DELETE})

__all__ = ["READ", "CREATE", "UPDATE", "DELETE", "ToolSpec"]


@dataclass(frozen=True)
class ToolSpec:
    """Immutable record describing one registered tool.

    Produced by the ``@tool`` decorator from metadata declared at the tool's
    definition site; stored in the central :class:`~zscaler_mcp.registry.registry.Registry`.

    Attributes:
        name: Tool name in ``{service}_{verb}_{resource}`` form.
        action: The single Zero Trust action (DESIGN.md §2). One of
            ``read`` / ``create`` / ``update`` / ``delete`` — never multiplexed.
        fn: The tool implementation. Takes the validated input model instance and
            returns a shaped dict or list of dicts (pre-encoding).
        input_model: Pydantic model for the tool's inputs (the ``inputSchema``).
        output_view: Curated :class:`AgentView` subclass (the ``outputSchema``
            source of truth).
        description: Agent-facing description (defaults to the function docstring).
        service: Owning Zscaler product (``zpa`` / ``zia`` / ...).
        toolset: Toolset id this tool belongs to (catalog-level grouping).
        is_list: True if the tool returns a list of ``output_view`` rows.
        wire_format: Default serialization policy. ``AUTO`` = flat list -> CSV,
            object -> JSON.
    """

    name: str
    action: str
    fn: Callable[[Any], Any]
    input_model: type[BaseModel]
    output_view: type[AgentView]
    description: str
    service: str
    toolset: str
    is_list: bool = False
    wire_format: WireFormat = WireFormat.AUTO

    def __post_init__(self) -> None:
        if self.action not in _VALID_ACTIONS:
            raise ValueError(
                f"ToolSpec '{self.name}': action must be one of "
                f"{sorted(_VALID_ACTIONS)}, got {self.action!r}. "
                "Zero Trust: one tool = one explicit action (DESIGN.md §2)."
            )
        if not self.name:
            raise ValueError("ToolSpec.name must be non-empty")
        if not isinstance(self.output_view, type) or not issubclass(self.output_view, AgentView):
            raise TypeError(
                f"ToolSpec '{self.name}': output_view must be an AgentView subclass, "
                f"got {self.output_view!r}."
            )

    @property
    def is_write(self) -> bool:
        """True if this tool mutates the tenant (create/update/delete)."""
        return self.action in _WRITE_ACTIONS

    # ---- MCP tool-annotation semantics ------------------------------------
    # These three booleans are the domain-level source of truth for the MCP
    # ``ToolAnnotations`` hints (readOnlyHint / destructiveHint / idempotentHint)
    # the bridge advertises. They are DERIVED from the single ``action`` verb —
    # never hand-declared per tool — so the "one tool = one action" invariant
    # (DESIGN.md §2) automatically produces correct, uniform hints. Kept here
    # (not in the bridge) so the semantics are pure domain logic, unit-testable
    # without importing the MCP wire types. See MCP spec ToolAnnotations.

    @property
    def read_only(self) -> bool:
        """True if the tool does not modify the tenant (``readOnlyHint``)."""
        return not self.is_write

    @property
    def destructive(self) -> bool:
        """True if the tool can remove or overwrite existing tenant state.

        Only meaningful when :attr:`read_only` is ``False`` (the MCP spec says
        ``destructiveHint`` is ignored for read-only tools). ``delete`` removes
        resources; ``update`` is PUT-replace (a full overwrite that can drop
        fields — see CLAUDE.md) so it is destructive too. ``create`` only adds a
        new resource, so it is NOT destructive.
        """
        return self.action in (UPDATE, DELETE)

    @property
    def idempotent(self) -> bool:
        """True if repeating the call with the same args yields the same state.

        Only meaningful when :attr:`read_only` is ``False``. ``update``
        (PUT-replace) and ``delete`` converge to the same end state on repeat;
        ``create`` appends a new resource on every call, so it is NOT idempotent.
        """
        return self.action in (UPDATE, DELETE)
