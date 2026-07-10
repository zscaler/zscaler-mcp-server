"""MCP Prompts subsystem — declarative, co-located, self-registering.

Prompts are the *user-controlled* MCP capability: the client lists them in a
menu, the user picks one and fills a small argument form, and the server renders
a templated, parameterized playbook that seeds the conversation. This package
mirrors the tool registry design (``@tool`` → ``zscaler_mcp.registry``): a prompt
declares itself at its own definition site via ``@prompt`` and registers into a
central :class:`PromptRegistry` at import time.

Layout (mirrors tools = infra-vs-catalog split):

* infra lives here — ``spec`` / ``registry`` / ``decorator`` / ``discovery`` /
  ``bridge``;
* concrete prompts live under :mod:`zscaler_mcp.prompts.catalog` (one module per
  prompt, grouped by service), which is the only tree ``discover_prompts`` walks.

    from zscaler_mcp.prompts import prompt, discover_prompts, build_function_prompt
"""

from zscaler_mcp.prompts.bridge import build_function_prompt
from zscaler_mcp.prompts.decorator import prompt
from zscaler_mcp.prompts.discovery import discover_prompts
from zscaler_mcp.prompts.registry import PROMPT_REGISTRY, PromptRegistry
from zscaler_mcp.prompts.spec import PromptSpec

__all__ = [
    "prompt",
    "discover_prompts",
    "build_function_prompt",
    "PROMPT_REGISTRY",
    "PromptRegistry",
    "PromptSpec",
]
