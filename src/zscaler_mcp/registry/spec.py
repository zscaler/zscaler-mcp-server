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
        output_view: Optional :class:`AgentView` subclass describing a SYNTHETIC
            result the server constructs itself (``OperationResult``, a catalog
            wrapper, an aggregate status). ``None`` — the norm — means the tool
            returns a Zscaler API record verbatim and therefore advertises no
            ``outputSchema``: the set of attributes a resource carries is owned
            by the API, not by this server, so enumerating it here would go
            stale the moment engineering ships a new field (issue #88).
        description: Agent-facing description (defaults to the function docstring).
        service: Owning Zscaler product (``zpa`` / ``zia`` / ...).
        toolset: Toolset id this tool belongs to (catalog-level grouping).
        is_list: True if the tool returns a list of records/rows.
        wire_format: Default serialization policy. ``AUTO`` = flat list -> CSV,
            object -> JSON.
        untrusted_content: True if the tool returns content sourced from OUTSIDE
            the customer's trust boundary. The line is the trust boundary, not the
            privilege level: data authored inside the authenticated, customer-managed
            tenant — by an admin OR an IdP-authenticated employee — is ordinary
            tenant data and is NOT flagged (that is the accepted-risk class shared by
            every admin/user-editable free-text field). Only data crossing in from
            outside qualifies: WHOIS registrant fields on an attacker-registered
            domain, or text scraped from an external internet-facing asset. When set,
            the bridge prepends a provenance banner to the text block telling the
            model to treat the values as data, not instructions (defense-in-depth
            against indirect prompt injection, MCP06). Additive and text-only: the
            verbatim record in ``structuredContent`` is never restructured (issue
            #88). Efficacy depends on the client honouring the banner — a hint, not a
            gate.
        untrusted_content_note: Optional tool-specific sentence appended to the
            provenance banner (only meaningful with ``untrusted_content=True``).
            Use it to NAME where the externally-authored content sits in this
            tool's response (e.g. which sections carry sample-derived strings and
            which field carries the vendor's own verdict) — wording only, never a
            schema: the response is still passed through verbatim, so the note
            must not become a field whitelist (issue #88).
    """

    name: str
    action: str
    fn: Callable[[Any], Any]
    input_model: type[BaseModel]
    output_view: type[AgentView] | None
    description: str
    service: str
    toolset: str
    is_list: bool = False
    wire_format: WireFormat = WireFormat.AUTO
    untrusted_content: bool = False
    untrusted_content_note: str | None = None

    def __post_init__(self) -> None:
        if self.action not in _VALID_ACTIONS:
            raise ValueError(
                f"ToolSpec '{self.name}': action must be one of "
                f"{sorted(_VALID_ACTIONS)}, got {self.action!r}. "
                "Zero Trust: one tool = one explicit action (DESIGN.md §2)."
            )
        if not self.name:
            raise ValueError("ToolSpec.name must be non-empty")
        if self.output_view is not None and (
            not isinstance(self.output_view, type) or not issubclass(self.output_view, AgentView)
        ):
            raise TypeError(
                f"ToolSpec '{self.name}': output_view must be an AgentView subclass or None, "
                f"got {self.output_view!r}."
            )

    @property
    def is_write(self) -> bool:
        """True if this tool mutates the tenant (create/update/delete)."""
        return self.action in _WRITE_ACTIONS

    @property
    def supports_query(self) -> bool:
        """True if the bridge should offer this tool a JMESPath ``query`` parameter.

        Filtering/projection is offered on tools that return a COLLECTION, which
        is where it pays for itself: many rows in, only what the caller asked for
        out. That is ``is_list`` tools, plus the handful of ``*_list_*`` reads
        whose SDK call returns a single envelope object wrapping the collection
        (auth-exempt URLs, the ATP denylist, SIM inventory) — v1 offered ``query``
        on those too.

        Excluded: single-object gets (nothing to filter down), writes (the result
        is an acknowledgement, not data), and tools advertising an ``output_view``
        (a synthetic shape the server declares — filtering would contradict the
        schema on the wire).
        """
        if self.output_view is not None or self.is_write:
            return False
        return self.is_list or "_list_" in self.name

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
