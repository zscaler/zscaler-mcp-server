"""Prompt discovery — imports the ``prompts/catalog/`` tree so ``@prompt`` fires.

Mirrors tool discovery (:mod:`zscaler_mcp.registry.discovery`): prompts register
themselves as a side effect of being imported. Discovery walks the
``zscaler_mcp.prompts.catalog`` package only (NOT the infra modules in
``zscaler_mcp.prompts`` itself), so importing the registry/decorator/bridge does not
get triggered as part of the walk. Adding a new prompt module under
``catalog/<service>/`` is enough for it to be found.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

from zscaler_mcp.prompts.registry import PROMPT_REGISTRY, PromptRegistry

__all__ = ["discover_prompts"]


def discover_prompts(
    package_name: str = "zscaler_mcp.prompts.catalog",
    registry: PromptRegistry = PROMPT_REGISTRY,
) -> PromptRegistry:
    """Import every module under ``package_name`` so decorated prompts register.

    Returns the populated registry. Idempotent: importing an already-imported
    module is a no-op, and the registry rejects duplicate names, so calling this
    twice does not double-register.
    """
    package: ModuleType = importlib.import_module(package_name)
    for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
        importlib.import_module(module_info.name)
    return registry
