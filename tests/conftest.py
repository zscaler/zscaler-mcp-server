"""Shared pytest fixtures.

The OneAPI entitlement filter is network-touching by nature (it exchanges
credentials for a bearer token). To keep the suite hermetic and fast, we
neutralize it by default for every test via an autouse fixture, so a developer
with live ``ZSCALER_*`` creds in their shell doesn't trigger real ``/token``
calls during ``build_server()``. Tests that exercise the filter directly inject
their own ``token_provider`` stub into ``apply_entitlement_filter`` and don't go
through this path.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _neutralize_entitlement_filter(monkeypatch, request):
    """Make the server-startup entitlement filter a no-op (skip) in tests.

    Opt out per-test with ``@pytest.mark.real_entitlement`` if a test needs the
    genuine codepath (none currently do — the unit tests target the function
    directly with a stub provider).
    """
    if request.node.get_closest_marker("real_entitlement"):
        return

    import zscaler_mcp.server as server_mod

    monkeypatch.setattr(
        server_mod,
        "apply_entitlement_filter",
        lambda available, **kw: (None, "entitlement filter skipped (neutralized in tests)"),
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "real_entitlement: run the genuine entitlement-filter startup path",
    )
