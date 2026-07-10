"""The ``@prompt`` decorator — declares an MCP prompt at its definition site.

Mirrors the ``@tool`` decorator: the prompt carries its own metadata next to its
render function and self-registers into :data:`PROMPT_REGISTRY` at import time.
The render function's typed parameters become the prompt's arguments (FastMCP
derives the argument schema from the signature in the bridge).

Usage::

    @prompt(
        name="zdx_troubleshoot_user_experience",
        title="ZDX: Troubleshoot User Experience",
        service="zdx",
    )
    def troubleshoot_user_experience(user_or_device: str, since_hours: str = "24") -> str:
        '''Investigate a user's ZDX digital experience …'''  # docstring → description
        return f"..."
"""

from __future__ import annotations

from typing import Any, Callable

from zscaler_mcp.prompts.registry import PROMPT_REGISTRY, PromptRegistry
from zscaler_mcp.prompts.spec import PromptSpec

__all__ = ["prompt"]


def prompt(
    *,
    name: str,
    title: str,
    service: str,
    description: str | None = None,
    registry: PromptRegistry = PROMPT_REGISTRY,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register the decorated function as an MCP prompt.

    The decorator returns the original function unchanged (so it stays directly
    unit-testable); its side effect is adding a :class:`PromptSpec` to ``registry``.

    Args:
        name: Stable prompt id surfaced as the menu entry.
        title: Human-friendly label shown in the client's prompt picker.
        service: Owning Zscaler product; gates the prompt behind that service's
            visibility.
        description: Shown under the title; defaults to the function docstring.
        registry: Target registry (defaults to the process-wide one; injectable
            for test isolation).
    """

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        resolved_desc = (description or fn.__doc__ or "").strip()
        if not resolved_desc:
            raise ValueError(
                f"Prompt '{name}' has no description (add a docstring or pass "
                "description=...). The user reads it in the prompt picker."
            )
        registry.add(
            PromptSpec(
                name=name,
                title=title,
                description=resolved_desc,
                fn=fn,
                service=service,
            )
        )
        return fn

    return decorate
