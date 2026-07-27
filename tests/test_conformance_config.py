"""Guards on the MCP conformance CI wiring.

The conformance run itself is a Node tool executed in CI (see
``.github/workflows/mcp-conformance.yml``); it can't run inside the Python test
suite. What these tests DO guard is that the config the CI run depends on stays
coherent and honest:

* the baseline is valid YAML shaped the way the runner expects;
* the workflow pins the runner and targets the PUBLISHED protocol baseline
  (never ``draft`` / ``latest``) — so a conformance *claim* can't drift silently;
* the baseline and the workflow agree on the same spec version.
"""

from __future__ import annotations

from pathlib import Path

import tomllib  # noqa: F401  (kept for parity with sibling config tests)
import yaml

_REPO = Path(__file__).resolve().parent.parent
_BASELINE = _REPO / ".github" / "conformance-baseline.yml"
_WORKFLOW = _REPO / ".github" / "workflows" / "mcp-conformance.yml"

_PUBLISHED_SPEC = "2025-11-25"


def test_baseline_is_valid_and_well_shaped():
    data = yaml.safe_load(_BASELINE.read_text())
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
