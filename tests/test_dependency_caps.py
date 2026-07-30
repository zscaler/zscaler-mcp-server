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
3. **``fastmcp`` is declared nowhere — not even as an extra.** It is needed only
   for the ``oidcproxy`` auth mode, and the release that runs on ``mcp`` 2.x is
   still a prerelease whose own dependency pins a prerelease *transitively*. That
   detail is what rules out an extra: ``uv``'s scoped prerelease policies only
   consider direct requirements, so resolving it needs a blanket
   ``prerelease = "allow"``, and since ``uv lock`` resolves every extra, the
   blanket policy would govern the entire lockfile — including the automated SDK
   upgrade job, which would then be free to pull prerelease builds of
   ``zscaler-sdk-python`` and ``pydantic``. Operators of that one auth mode install
   ``fastmcp`` themselves; ``security/auth.py`` raises an ``ImportError`` with the
   command. This test exists to catch it being re-declared.
"""

from __future__ import annotations

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
        "--prerelease=allow. It is only needed for the oidcproxy auth mode."
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
        f"which then governs every other dependency too. Promote it to an extra "
        f"once fastmcp 4.x reaches GA."
    )


def test_pyproject_documents_how_to_get_fastmcp():
    """Undeclared is only acceptable if the operator is told what to install."""
    text = _PYPROJECT.read_text()
    assert "fastmcp>=4.0.0b1" in text, (
        "pyproject.toml no longer records the fastmcp version the oidcproxy auth "
        "mode needs. An undeclared dependency with no documented install command is "
        "just a broken auth mode."
    )


def test_the_error_message_names_the_install_command():
    """The ImportError is the only place most operators will ever look."""
    from zscaler_mcp.security import auth

    source = Path(auth.__file__).read_text()
    assert "--prerelease=allow" in source
    assert "fastmcp>=4.0.0b1" in source


def test_caps_document_their_reason():
    """The pins must carry the rationale comment so the next reader knows they
    are deliberate, not lazy pinning."""
    text = _PYPROJECT.read_text()
    assert "2026-07-28" in text, "pin rationale comment missing from pyproject.toml"
    assert "oidcproxy" in text, "oidcproxy rationale missing from pyproject.toml"
