"""Guard rails on the MCP SDK dependency contract.

Three properties are pinned here, each of which has a concrete failure mode if it
silently changes:

1. **``mcp`` has a floor of 2.0.0.** The ``2026-07-28`` revision — sealed
   ``requestState`` (``RequestStateSecurity``), ``InputRequiredResult``, and
   ``cache_hints`` (SEP-2549) — only exists there. Those are constructor-level
   arguments to ``MCPServer``, so a 1.x resolution does not degrade gracefully; it
   raises at startup.
2. **``mcp`` is capped below 3.** The next major is a landmine a routine
   ``uv sync`` should not pull in silently. Lifting this cap should be a
   deliberate, reviewed act, which is what failing this test forces.
3. **``fastmcp`` is declared nowhere, and nothing needs it.** Every auth mode
   resolves from GA wheels: the OIDC mode is an RFC 9728 resource server, which
   ``mcp`` 2.x implements, verified with ``PyJWT``. The alternative was borrowing
   ``fastmcp``'s ``OIDCProxy``, which would have put a prerelease on the install
   path — ``fastmcp`` 4.x depends on one *transitively*
   (``fastmcp-slim==4.0.0b1``), and ``uv``'s scoped prerelease policies only
   consider direct requirements, so resolving it needs a blanket
   ``prerelease = "allow"``; since ``uv lock`` resolves every extra, that policy
   would govern the whole lockfile, including the automated SDK upgrade job. These
   tests exist to catch it coming back, in either position, and to catch anything
   asking an operator to install a package by hand.
"""

from __future__ import annotations

import re
from pathlib import Path

import tomllib
from packaging.requirements import Requirement

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _data() -> dict:
    return tomllib.loads(_PYPROJECT.read_text())


def _requirement(dist: str, *, extra: str | None = None) -> Requirement:
    data = _data()
    raws = (
        data["project"]["optional-dependencies"][extra]
        if extra
        else data["project"]["dependencies"]
    )
    for raw in raws:
        req = Requirement(raw)
        if req.name == dist:
            return req
    where = f"[project.optional-dependencies.{extra}]" if extra else "[project.dependencies]"
    raise AssertionError(f"{dist!r} not found in {where}")


def test_mcp_floor_includes_the_2026_07_28_features():
    req = _requirement("mcp")
    assert req.specifier.contains("2.0.0"), f"mcp floor excludes the 2026-07-28 SDK — {req}"
    assert not req.specifier.contains("1.28.1"), (
        f"mcp 1.x still resolves, but MCPServer(request_state_security=...) does not "
        f"exist there — {req}"
    )


def test_mcp_is_capped_below_v3():
    req = _requirement("mcp")
    assert not req.specifier.contains("3.0.0"), f"mcp cap lifted — {req}"
    assert not req.specifier.contains("3.0.0b1", prereleases=True), f"mcp cap lifted — {req}"


def test_fastmcp_is_not_a_base_dependency():
    """A prerelease must never be on the default install path."""
    names = {Requirement(raw).name for raw in _data()["project"]["dependencies"]}
    assert "fastmcp" not in names, (
        "fastmcp moved into [project.dependencies]. The release that supports mcp 2.x "
        "is a prerelease, so this forces every consumer to install with "
        "--prerelease=allow. No auth mode needs it: OIDC is an RFC 9728 resource "
        "server, implemented by mcp 2.x."
    )


def test_fastmcp_is_not_an_extra_either():
    """An extra is not a safe home for it while it is a prerelease.

    ``uv lock`` resolves every extra, so a prerelease-bearing extra drags the
    blanket ``--prerelease=allow`` policy onto the whole lockfile — and from there
    onto the automated SDK upgrade job.
    """
    extras = _data()["project"].get("optional-dependencies", {})
    offenders = {
        name
        for name, raws in extras.items()
        if any(Requirement(raw).name == "fastmcp" for raw in raws)
    }
    assert not offenders, (
        f"fastmcp declared in extras {sorted(offenders)}. While fastmcp 4.x is a "
        f"prerelease this makes `uv lock` unsolvable without --prerelease=allow, "
        f"which then governs every other dependency too."
    )


def test_nothing_is_imported_from_fastmcp():
    """The dependency is only truly gone if no code path reaches for it.

    An undeclared import is worse than a declared dependency: it resolves on a
    developer machine that happens to have the package and fails in a clean
    deployment, in whichever auth mode touches it.
    """
    src = Path(__file__).resolve().parent.parent / "src" / "zscaler_mcp"
    # Import statements only. Prose mentions are fine and in places necessary —
    # ``registry/fastmcp_bridge.py`` keeps its name from the FastMCP era, and
    # several comments explain what moved off it and why.
    pattern = re.compile(r"^\s*(?:from|import)\s+fastmcp\b", re.MULTILINE)
    offenders = [
        path.relative_to(src).as_posix()
        for path in src.rglob("*.py")
        if pattern.search(path.read_text())
    ]
    assert not offenders, f"fastmcp imported in {offenders} — it is not a dependency"


def test_no_module_asks_an_operator_to_install_something():
    """No auth mode may be gated behind a manual install.

    This is the property that made the previous design unacceptable: selecting a
    documented, shipped auth mode printed a ``uv pip install --prerelease=allow``
    command and refused to start until the operator ran it.
    """
    src = Path(__file__).resolve().parent.parent / "src" / "zscaler_mcp"
    offenders = [
        path.relative_to(src).as_posix()
        for path in src.rglob("*.py")
        if "--prerelease" in path.read_text()
    ]
    assert not offenders, f"a manual prerelease install is still instructed in {offenders}"


def test_caps_document_their_reason():
    """The pins must carry the rationale comment so the next reader knows they
    are deliberate, not lazy pinning."""
    text = _PYPROJECT.read_text()
    assert "2026-07-28" in text, "pin rationale comment missing from pyproject.toml"
    assert "RFC 9728" in text, (
        "pyproject.toml no longer records why fastmcp is absent. Without the "
        "rationale, the next reader sees a missing dependency rather than a "
        "deliberate choice, and re-adds it."
    )
