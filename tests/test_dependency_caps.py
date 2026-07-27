"""Guard rails on the MCP SDK dependency caps.

The MCP ``2026-07-28`` spec ships in ``mcp`` 2.x and ``fastmcp`` 4.x — a
stateless-core rewrite (CallToolResult/InputRequiredResult return types,
ServerRunner, native multi-round-trip elicitation). Adopting those majors is a
planned, staged migration, NOT something a routine ``uvx zscaler-mcp`` /
``uv sync`` should pull in silently the day they GA.

``pyproject.toml`` therefore pins upper bounds (``mcp<2`` / ``fastmcp<4``). This
test fails loudly if either cap is dropped or weakened, so nobody removes the
landmine guard by accident. When we intentionally do the migration, this test
gets updated in the same PR — that is the point: lifting the cap becomes a
deliberate, reviewed act.
"""

from __future__ import annotations

from pathlib import Path

import tomllib
from packaging.requirements import Requirement

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _requirement(dist: str) -> Requirement:
    data = tomllib.loads(_PYPROJECT.read_text())
    for raw in data["project"]["dependencies"]:
        req = Requirement(raw)
        if req.name == dist:
            return req
    raise AssertionError(f"{dist!r} not found in [project.dependencies]")


def test_mcp_is_capped_below_v2():
    req = _requirement("mcp")
    # Behavioural check: the current GA line resolves, the breaking major does not.
    assert req.specifier.contains("1.28.1"), req
    assert not req.specifier.contains("2.0.0"), f"mcp cap lifted — {req}"
    assert not req.specifier.contains("2.0.0b2", prereleases=True), f"mcp cap lifted — {req}"


def test_fastmcp_is_capped_below_v4():
    req = _requirement("fastmcp")
    assert req.specifier.contains("3.4.4"), req
    assert not req.specifier.contains("4.0.0"), f"fastmcp cap lifted — {req}"
    assert not req.specifier.contains("4.0.0a1", prereleases=True), f"fastmcp cap lifted — {req}"


def test_caps_document_their_reason():
    """The caps must carry the rationale comment so the next reader knows they
    are deliberate, not lazy pinning."""
    text = _PYPROJECT.read_text()
    assert "2026-07-28" in text, "cap rationale comment missing from pyproject.toml"
