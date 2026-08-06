"""The central tool registry + its query interface.

The registry is populated by the ``@tool`` decorator at import time, not by a
hand-maintained list. The filtering layer (toolsets / entitlement / write
allowlist / disabled patterns) is expressed as a :meth:`Registry.select` query
over the registered specs — the same selection logic v1 threads through
``tool_helpers.py``, but operating on rich self-declared records instead of
service-class methods.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable, Iterator

from zscaler_mcp.registry.spec import ToolSpec

__all__ = ["Registry", "REGISTRY"]


class Registry:
    """An ordered, name-unique collection of :class:`ToolSpec` records."""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}

    def add(self, spec: ToolSpec) -> None:
        """Register a spec. Raises on duplicate names so two tools can never
        silently shadow each other (a real risk at hundreds of tools)."""
        if spec.name in self._specs:
            raise ValueError(f"Duplicate tool name registered: {spec.name!r}")
        self._specs[spec.name] = spec

    def __iter__(self) -> Iterator[ToolSpec]:
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, name: str) -> bool:
        return name in self._specs

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def names(self) -> list[str]:
        return list(self._specs)

    def clear(self) -> None:
        """Reset the registry (used by tests for isolation)."""
        self._specs.clear()

    def services(self) -> set[str]:
        """Every distinct ``service`` code across the registered specs.

        Used as the upper bound the OneAPI entitlement filter intersects
        against (it can only ever *remove* services, never invent one).
        """
        return {spec.service for spec in self._specs.values()}

    def toolsets(self) -> set[str]:
        """Every distinct ``toolset`` id across the registered specs.

        Used to validate operator-supplied ``--toolsets`` / ``--disabled-toolsets``
        ids so a typo surfaces as a warning instead of a silently empty server.
        """
        return {spec.toolset for spec in self._specs.values()}

    def select(
        self,
        *,
        enabled_services: Iterable[str] | None = None,
        disabled_services: Iterable[str] | None = None,
        enabled_toolsets: Iterable[str] | None = None,
        disabled_toolsets: Iterable[str] | None = None,
        entitled_services: Iterable[str] | None = None,
        enable_write: bool = False,
        write_allowlist: Iterable[str] | None = None,
        disabled_patterns: Iterable[str] | None = None,
    ) -> list[ToolSpec]:
        """Return the specs visible under a given filter configuration.

        Mirrors v1's precedence (DESIGN.md §6): disabled patterns win, then
        service enable/disable, then OneAPI entitlement downscoping, then
        toolset selection, then the read/write gate.

        Args:
            enabled_services: If given, only tools whose ``service`` is in this
                set are kept — the operator's ``--services`` allowlist. ``None``
                keeps every service.
            disabled_services: If given, tools whose ``service`` is in this set
                are excluded — the operator's ``--disabled-services`` blocklist.
                Applied after ``enabled_services`` (a service can be both enabled
                and then disabled; disable wins).
            enabled_toolsets: If given, only tools in these toolsets are kept —
                the operator's ``--toolsets`` allowlist. ``None`` keeps every
                toolset.
            disabled_toolsets: If given, tools in these toolsets are excluded —
                the operator's ``--disabled-toolsets`` blocklist. Applied after
                ``enabled_toolsets`` so the blocklist wins (a toolset can be both
                selected and then disabled; disable wins), mirroring the
                ``disabled_services`` / ``disabled_patterns`` precedence.
            entitled_services: If given, only tools whose ``service`` is in this
                set are kept — the OneAPI product-entitlement downscope. ``None``
                applies no entitlement filtering (filter skipped/disabled).
            enable_write: If False (default), write tools (create/update/delete)
                are excluded entirely — read-only-by-default (Zero Trust).
            write_allowlist: When ``enable_write`` is True, only write tools whose
                name matches one of these fnmatch patterns are kept. ``None`` with
                ``enable_write=True`` keeps all write tools — this is the filter
                primitive, not the server's policy: :func:`~zscaler_mcp.server.build_server`
                requires an allowlist and registers zero write tools without one.
            disabled_patterns: fnmatch patterns; any tool whose name matches is
                excluded regardless of everything else (highest precedence).
        """
        disabled = list(disabled_patterns or [])
        enabled_svc = set(enabled_services) if enabled_services is not None else None
        disabled_svc = set(disabled_services) if disabled_services is not None else None
        toolsets = set(enabled_toolsets) if enabled_toolsets is not None else None
        disabled_ts = set(disabled_toolsets) if disabled_toolsets is not None else None
        entitled = set(entitled_services) if entitled_services is not None else None
        allow = list(write_allowlist) if write_allowlist is not None else None

        selected: list[ToolSpec] = []
        for spec in self._specs.values():
            if any(fnmatch.fnmatch(spec.name, pat) for pat in disabled):
                continue
            if enabled_svc is not None and spec.service not in enabled_svc:
                continue
            if disabled_svc is not None and spec.service in disabled_svc:
                continue
            if entitled is not None and spec.service not in entitled:
                continue
            if toolsets is not None and spec.toolset not in toolsets:
                continue
            if disabled_ts is not None and spec.toolset in disabled_ts:
                continue
            if spec.is_write:
                if not enable_write:
                    continue
                if allow is not None and not any(fnmatch.fnmatch(spec.name, p) for p in allow):
                    continue
            selected.append(spec)
        return selected


# The process-wide registry the @tool decorator writes into.
REGISTRY = Registry()
