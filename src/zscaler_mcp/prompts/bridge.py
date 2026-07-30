"""Bridge a :class:`PromptSpec` onto an MCP ``Prompt``.

This is the single adapter between v2's self-declared prompt records and the MCP
framework, analogous to :mod:`zscaler_mcp.registry.fastmcp_bridge` for tools. The
framework derives the prompt's argument schema (the wizard fields the client
renders) from the render function's signature, so all this layer does is attach
the declared name / title / description.
"""

from __future__ import annotations

from mcp.server.mcpserver.prompts.base import Prompt

from zscaler_mcp.prompts.spec import PromptSpec

__all__ = ["build_function_prompt"]


def build_function_prompt(spec: PromptSpec) -> Prompt:
    """Construct the MCP ``Prompt`` for a spec.

    The render function's typed parameters become MCP ``PromptArgument`` entries
    (name + description from the docstring + required flag from the schema), which
    the client turns into the "Enter prompt inputs" form.
    """
    return Prompt.from_function(
        spec.fn,
        name=spec.name,
        title=spec.title,
        description=spec.description,
    )
