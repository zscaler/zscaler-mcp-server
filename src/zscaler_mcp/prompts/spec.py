"""The internal record a registered MCP prompt produces.

Prompts are the third MCP capability (alongside tools and resources). Unlike
tools, they are *user-controlled*: the client lists them in a menu and the user
explicitly invokes one, filling a small form for the prompt's arguments. The
server then renders a templated message sequence that seeds the conversation —
a reusable, parameterized playbook.

This mirrors the tool side (:mod:`zscaler_mcp.registry.spec`): a prompt declares its
metadata at its own definition site via the ``@prompt`` decorator, and the
record lands in the central :class:`~zscaler_mcp.prompts.registry.PromptRegistry`.
The render function's own parameters become the prompt's arguments (FastMCP
derives the argument schema from the signature), so there is no second list to
keep in sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

__all__ = ["PromptSpec"]


@dataclass(frozen=True)
class PromptSpec:
    """Immutable record describing one registered MCP prompt.

    Attributes:
        name: Stable prompt id (``{service}_{verb}_{resource}`` style, e.g.
            ``zdx_troubleshoot_user_experience``). Surfaced as the menu entry.
        title: Human-friendly label shown in the client's prompt picker.
        description: One-line explanation of what the playbook does. Shown under
            the title in the wizard.
        fn: The render function. Its typed parameters become the prompt's
            arguments; it returns the templated instruction text (a ``str``, a
            list of messages, or a FastMCP ``PromptResult``).
        service: Owning Zscaler product (``zdx`` / ``zia`` / ...). Used to gate
            the prompt behind the same service visibility the tools resolve to,
            so a ZDX prompt never appears when ZDX is disabled/unentitled.
    """

    name: str
    title: str
    description: str
    fn: Callable[..., Any]
    service: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("PromptSpec.name must be non-empty")
        if not self.description:
            raise ValueError(
                f"PromptSpec '{self.name}': description must be non-empty "
                "(the user reads it in the prompt picker)."
            )
        if not callable(self.fn):
            raise TypeError(f"PromptSpec '{self.name}': fn must be callable.")
