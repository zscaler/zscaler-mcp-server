"""The ``@tool`` decorator — declares a tool at its own definition site.

This is the design difference vs v1's central ``services.py`` catalog: a tool
carries its own metadata (action, schemas, toolset, description) right next to
its implementation, and registers itself into :data:`REGISTRY` at import time.
There is no separate list a human must keep in sync, so the v1 failure mode
("added the tool module but forgot the services.py entry") cannot happen.

Usage::

    @tool(action=READ, service="zpa", toolset="zpa_segment_groups",
          input_model=ListSegmentGroupsInput, output_view=SegmentGroupSummary,
          is_list=True)
    def zpa_list_segment_groups(args: ListSegmentGroupsInput) -> list[dict]:
        '''List ZPA segment groups …'''   # docstring becomes the description
        ...
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel

from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry.registry import REGISTRY, Registry
from zscaler_mcp.registry.spec import ToolSpec
from zscaler_mcp.shaping import AgentView

__all__ = ["tool"]


def tool(
    *,
    action: str,
    service: str,
    toolset: str,
    input_model: type[BaseModel],
    output_view: type[AgentView],
    is_list: bool = False,
    name: str | None = None,
    description: str | None = None,
    wire_format: WireFormat = WireFormat.AUTO,
    registry: Registry = REGISTRY,
) -> Callable[[Callable[[Any], Any]], Callable[[Any], Any]]:
    """Register the decorated function as a tool.

    The decorator returns the original function unchanged (so it stays directly
    unit-testable); its side effect is adding a :class:`ToolSpec` to ``registry``.

    Args:
        action: Zero Trust verb — ``READ`` / ``CREATE`` / ``UPDATE`` / ``DELETE``.
        service: Owning Zscaler product (``zpa`` / ``zia`` / ...).
        toolset: Toolset id for catalog-level grouping/filtering.
        input_model: Pydantic input model (the ``inputSchema``).
        output_view: Curated :class:`AgentView` subclass (the ``outputSchema``).
        is_list: True if the tool returns a list of ``output_view`` rows.
        name: Tool name; defaults to the function's ``__name__``.
        description: Agent-facing description; defaults to the function docstring.
        wire_format: Default serialization policy.
        registry: Target registry (defaults to the process-wide one; injectable
            for test isolation).
    """

    def decorate(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
        resolved_name = name or fn.__name__
        resolved_desc = (description or fn.__doc__ or "").strip()
        if not resolved_desc:
            raise ValueError(
                f"Tool '{resolved_name}' has no description (add a docstring or "
                "pass description=...). Agents rely on it for tool selection."
            )
        spec = ToolSpec(
            name=resolved_name,
            action=action,
            fn=fn,
            input_model=input_model,
            output_view=output_view,
            description=resolved_desc,
            service=service,
            toolset=toolset,
            is_list=is_list,
            wire_format=wire_format,
        )
        registry.add(spec)
        return fn

    return decorate
