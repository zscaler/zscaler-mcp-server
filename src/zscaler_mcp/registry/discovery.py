"""Tool discovery — imports the ``tools/`` package tree so ``@tool`` fires.

Tools register themselves as a side effect of being imported (the ``@tool``
decorator runs at import time). Discovery just walks the ``zscaler_mcp.tools``
package and imports every module, which populates :data:`REGISTRY`. No central
list to maintain — adding a new tool module is enough for it to be found.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

from zscaler_mcp.registry.registry import REGISTRY, Registry

__all__ = ["discover_tools"]


def discover_tools(
    package_name: str = "zscaler_mcp.tools", registry: Registry = REGISTRY
) -> Registry:
    """Import every module under ``package_name`` so decorated tools register.

    Returns the populated registry. Idempotent: importing an already-imported
    module is a no-op, and the registry rejects duplicate names, so calling this
    twice does not double-register.
    """
    package: ModuleType = importlib.import_module(package_name)
    for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
        # Skip package __init__ entries themselves; walk_packages yields them as
        # ispkg=True. Importing the package is harmless but the tool modules are
        # what carry the decorators.
        importlib.import_module(module_info.name)
    return registry
