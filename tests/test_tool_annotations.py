"""Tests for MCP ``ToolAnnotations`` derivation (behavioural hints).

Every registered tool advertises MCP tool-annotation hints
(``readOnlyHint`` / ``destructiveHint`` / ``idempotentHint`` / ``openWorldHint``)
so a client can decide how to present it — e.g. whether to surface a
human-facing confirmation before a destructive call. The hints are DERIVED from
the tool's single action verb (never hand-declared), so they can never disagree
with the tool's real behaviour.

These tests pin three things:

1. The domain properties on :class:`ToolSpec` map each action to the right
   semantics.
2. :func:`_tool_annotations` renders those semantics into the MCP wire type,
   leaving write-only hints unset on read-only tools.
3. Every *real* registered tool satisfies the invariants (reads are never
   destructive, deletes always are, creates are never idempotent, nothing is
   open-world), and every tool actually gets annotations attached when bridged.
"""

from __future__ import annotations

import pytest
from mcp.types import ToolAnnotations

from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE
from zscaler_mcp.registry.discovery import discover_tools
from zscaler_mcp.registry.fastmcp_bridge import _tool_annotations, build_function_tool
from zscaler_mcp.registry.registry import REGISTRY
from zscaler_mcp.registry.spec import ToolSpec
from zscaler_mcp.shaping import AgentView


class _View(AgentView):
    id: str


class _In(AgentView):
    pass


def _spec(action: str, *, name: str = "svc_verb_thing", is_list: bool = False) -> ToolSpec:
    return ToolSpec(
        name=name,
        action=action,
        fn=lambda args: {"id": "1"},
        input_model=_In,
        output_view=_View,
        description="doc",
        service="zpa",
        toolset="zpa_test",
        is_list=is_list,
    )


# ---------------------------------------------------------------------------
# ToolSpec domain properties (pure semantics, no MCP wire type)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "action, read_only, destructive, idempotent",
    [
        (READ, True, False, False),
        (CREATE, False, False, False),
        (UPDATE, False, True, True),
        (DELETE, False, True, True),
    ],
)
def test_spec_annotation_properties(action, read_only, destructive, idempotent):
    spec = _spec(action)
    assert spec.read_only is read_only
    assert spec.destructive is destructive
    assert spec.idempotent is idempotent
    # read_only is the exact inverse of is_write for every action.
    assert spec.read_only is not spec.is_write


# ---------------------------------------------------------------------------
# _tool_annotations — rendering into the MCP ToolAnnotations wire type
# ---------------------------------------------------------------------------


def test_read_annotations_are_read_only_and_omit_write_hints():
    ann = _tool_annotations(_spec(READ))
    assert isinstance(ann, ToolAnnotations)
    assert ann.readOnlyHint is True
    assert ann.openWorldHint is False
    # Write-only hints are meaningless for a read-only tool; leave them unset
    # rather than sending a misleading False.
    assert ann.destructiveHint is None
    assert ann.idempotentHint is None


def test_create_annotations():
    ann = _tool_annotations(_spec(CREATE))
    assert ann.readOnlyHint is False
    assert ann.destructiveHint is False  # additive, never removes/overwrites
    assert ann.idempotentHint is False  # each call appends a new resource
    assert ann.openWorldHint is False


def test_update_annotations():
    ann = _tool_annotations(_spec(UPDATE))
    assert ann.readOnlyHint is False
    assert ann.destructiveHint is True  # PUT-replace can overwrite/drop fields
    assert ann.idempotentHint is True  # same payload -> same end state
    assert ann.openWorldHint is False


def test_delete_annotations():
    ann = _tool_annotations(_spec(DELETE))
    assert ann.readOnlyHint is False
    assert ann.destructiveHint is True
    assert ann.idempotentHint is True  # deleting twice converges to "absent"
    assert ann.openWorldHint is False


# ---------------------------------------------------------------------------
# build_function_tool — the bridge attaches the annotations to the FunctionTool
# ---------------------------------------------------------------------------


def test_bridge_attaches_read_only_annotations():
    ft = build_function_tool(_spec(READ, name="zpa_list_things", is_list=True))
    assert ft.annotations is not None
    assert ft.annotations.readOnlyHint is True


def test_bridge_attaches_destructive_annotations_for_delete():
    ft = build_function_tool(_spec(DELETE, name="zpa_delete_thing"))
    assert ft.annotations is not None
    assert ft.annotations.readOnlyHint is False
    assert ft.annotations.destructiveHint is True


# ---------------------------------------------------------------------------
# Registry-wide invariants — holds for every real tool, no exceptions
# ---------------------------------------------------------------------------


def _all_specs():
    discover_tools()
    specs = list(REGISTRY)
    assert specs, "registry should not be empty after discovery"
    return specs


def test_every_tool_has_consistent_annotations():
    for spec in _all_specs():
        ann = _tool_annotations(spec)
        # Nothing in this server touches an open-ended external world; every
        # tool talks to the single configured Zscaler tenant.
        assert ann.openWorldHint is False, spec.name

        if spec.read_only:
            assert ann.readOnlyHint is True, spec.name
            assert ann.destructiveHint is None, spec.name
            assert ann.idempotentHint is None, spec.name
            continue

        assert ann.readOnlyHint is False, spec.name
        if spec.action == DELETE:
            assert ann.destructiveHint is True, spec.name
            assert ann.idempotentHint is True, spec.name
        elif spec.action == UPDATE:
            assert ann.destructiveHint is True, spec.name
            assert ann.idempotentHint is True, spec.name
        elif spec.action == CREATE:
            assert ann.destructiveHint is False, spec.name
            assert ann.idempotentHint is False, spec.name


def test_every_tool_gets_annotations_when_bridged():
    """Bridging must never drop annotations for any real tool."""
    for spec in _all_specs():
        ft = build_function_tool(spec)
        assert ft.annotations is not None, spec.name
        assert ft.annotations.readOnlyHint is (True if spec.read_only else False), spec.name
