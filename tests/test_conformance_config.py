"""Guards on the MCP conformance CI wiring.

The conformance run itself is a Node tool executed in CI (see
``.github/workflows/mcp-conformance.yml``); it can't run inside the Python test
suite. What these tests DO guard is that the config the CI run depends on stays
coherent and honest:

* both baselines are valid YAML shaped the way the runner expects;
* the workflow pins the runner and targets the PUBLISHED protocol baseline
  (never ``draft`` / ``latest``) — so a conformance *claim* can't drift silently;
* the baseline and the workflow agree on the same spec version;
* the newer-revision baseline stays OUT of CI while its runner is a prerelease.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import tomllib  # noqa: F401  (kept for parity with sibling config tests)
import yaml

_REPO = Path(__file__).resolve().parent.parent
_BASELINE = _REPO / ".github" / "conformance-baseline.yml"
_NEXT_BASELINE = _REPO / ".github" / "conformance-baseline-next.yml"
_WORKFLOW = _REPO / ".github" / "workflows" / "mcp-conformance.yml"
_MAKEFILE = _REPO / "Makefile"

_PUBLISHED_SPEC = "2025-11-25"
#: The revision this server negotiates. Exercised by `make conformance-next`.
_NEXT_SPEC = "2026-07-28"


@pytest.mark.parametrize("path", [_BASELINE, _NEXT_BASELINE], ids=["published", "next"])
def test_baseline_is_valid_and_well_shaped(path):
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict), "baseline must be a mapping"
    assert "server" in data, "baseline must have a 'server' key"
    entries = data["server"]
    assert isinstance(entries, list) and entries, "server baseline must be a non-empty list"
    assert all(isinstance(e, str) and e for e in entries), "every entry must be a scenario name"
    # No accidental duplicates (a duplicate would mask a second, real failure).
    assert len(entries) == len(set(entries)), "duplicate scenario in baseline"


def test_baseline_explains_why_each_group_is_excused():
    """The baseline must document the two legitimate reasons (missing reference
    test fixtures + capabilities we don't advertise), so nobody mistakes it for a
    dumping ground that hides real regressions."""
    text = _BASELINE.read_text()
    assert "fixture" in text.lower()
    assert "capabilit" in text.lower()


def test_workflow_pins_runner_and_targets_published_spec():
    text = _WORKFLOW.read_text()
    lower = text.lower()
    # Runner must be version-pinned, not "latest".
    assert "@modelcontextprotocol/conformance@" in text
    assert "conformance@latest" not in lower
    # Must target the PUBLISHED baseline explicitly...
    assert _PUBLISHED_SPEC in text
    assert "--spec-version" in text
    assert "--suite active" in text
    # ...and never actually RUN against the moving draft (as a suite or spec
    # value). The word "draft" may appear in explanatory prose; what must not
    # appear is a draft *invocation*.
    assert "--suite draft" not in lower
    assert "spec-version draft" not in lower
    assert 'spec-version "draft"' not in lower


def test_workflow_uses_the_committed_baseline():
    text = _WORKFLOW.read_text()
    assert ".github/conformance-baseline.yml" in text


# ---------------------------------------------------------------------------
# The 2026-07-28 target — reachable, but deliberately not a CI gate
# ---------------------------------------------------------------------------


def test_the_newer_revision_is_actually_exercised_somewhere():
    """Negotiating a revision we never conformance-test would be an empty claim."""
    text = _MAKEFILE.read_text()
    assert "conformance-next:" in text, "no target runs the 2026-07-28 scenarios"
    assert _NEXT_SPEC in text
    assert ".github/conformance-baseline-next.yml" in text


def test_the_prerelease_runner_does_not_gate_ci():
    """CI must stay on the pinned stable runner.

    An alpha runner can add, rename or reinterpret scenarios between builds, which
    would turn upstream churn into red builds on this repo. Guarding the workflow
    text is how that stays true after someone copies the make target into CI.
    """
    workflow = _WORKFLOW.read_text()
    assert "alpha" not in workflow.lower(), "CI is gating on a prerelease runner"
    assert "conformance-baseline-next.yml" not in workflow
    assert _NEXT_SPEC not in workflow, (
        "the CI gate moved to 2026-07-28. That is fine once the runner is GA — "
        "at which point fold conformance-next into the gate and delete this test."
    )


def test_the_next_baseline_says_why_it_is_not_gating():
    """A second baseline with no stated reason reads like an oversight."""
    text = _NEXT_BASELINE.read_text().lower()
    assert "not gating" in text or "not gate" in text
    assert "alpha" in text or "prerelease" in text
