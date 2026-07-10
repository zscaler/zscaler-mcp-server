"""The central prompt registry + its visibility query.

Populated by the ``@prompt`` decorator at import time, exactly like the tool
:class:`~zscaler_mcp.registry.registry.Registry`. The server selects which prompts to
advertise by intersecting them with the set of services that survived tool
filtering (entitlement / toolset / disabled patterns), so prompts and tools
stay consistent: a ZDX prompt is only offered when ZDX tools are loaded.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from zscaler_mcp.prompts.spec import PromptSpec

__all__ = ["PromptRegistry", "PROMPT_REGISTRY"]


class PromptRegistry:
    """An ordered, name-unique collection of :class:`PromptSpec` records."""

    def __init__(self) -> None:
        self._specs: dict[str, PromptSpec] = {}

    def add(self, spec: PromptSpec) -> None:
        """Register a spec. Raises on duplicate names so two prompts can never
        silently shadow each other."""
        if spec.name in self._specs:
            raise ValueError(f"Duplicate prompt name registered: {spec.name!r}")
        self._specs[spec.name] = spec

    def __iter__(self) -> Iterator[PromptSpec]:
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, name: str) -> bool:
        return name in self._specs

    def get(self, name: str) -> PromptSpec | None:
        return self._specs.get(name)

    def names(self) -> list[str]:
        return list(self._specs)

    def clear(self) -> None:
        """Reset the registry (used by tests for isolation)."""
        self._specs.clear()

    def select(self, *, visible_services: Iterable[str] | None = None) -> list[PromptSpec]:
        """Return the prompts visible for a given set of services.

        Args:
            visible_services: If given, only prompts whose ``service`` is in this
                set are kept — typically the services that survived tool
                filtering, so prompts track tool visibility. ``None`` keeps all.
        """
        if visible_services is None:
            return list(self._specs.values())
        allowed = set(visible_services)
        return [spec for spec in self._specs.values() if spec.service in allowed]


# The process-wide prompt registry the @prompt decorator writes into.
PROMPT_REGISTRY = PromptRegistry()
