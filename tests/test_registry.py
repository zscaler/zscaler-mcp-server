"""Tests for the declarative registration layer (DESIGN.md §2 + §6).

Covers the three things that make this design correct rather than a typed copy
of v1's central catalog:

1. Tools self-register via @tool at import time (no manual list).
2. The Zero Trust action boundary is enforced at decoration time.
3. The filtering layer is a query over the registry (Registry.select).
"""

import pytest

from zscaler_mcp.encoding import WireFormat
from zscaler_mcp.registry import CREATE, DELETE, READ, UPDATE, Registry, tool
from zscaler_mcp.registry.spec import ToolSpec
from zscaler_mcp.shaping import AgentView


class _View(AgentView):
    id: str


class _In(AgentView):  # reuse a pydantic model as a stand-in input model
    pass


def _make_registry_with(action=READ, **tool_kwargs):
    """Decorate a throwaway fn into an isolated registry and return (reg, fn)."""
    reg = Registry()

    @tool(
        action=action,
        service="zpa",
        toolset="zpa_test",
        input_model=_In,
        output_view=_View,
        registry=reg,
        **tool_kwargs,
    )
    def some_tool(args):
        """A tool docstring so the description is non-empty."""
        return {"id": "1"}

    return reg, some_tool


def test_decorator_registers_tool_at_import_time():
    reg, fn = _make_registry_with(name="zpa_read_thing")
    assert "zpa_read_thing" in reg
    assert reg.get("zpa_read_thing").action == READ


def test_decorator_returns_original_function_unchanged():
    reg, fn = _make_registry_with(name="zpa_read_thing")
    # The decorated fn is still directly callable (stays unit-testable).
    assert fn({}) == {"id": "1"}


def test_description_defaults_to_docstring():
    reg, fn = _make_registry_with(name="zpa_read_thing")
    assert (
        reg.get("zpa_read_thing").description == "A tool docstring so the description is non-empty."
    )


def test_missing_description_is_rejected():
    reg = Registry()
    with pytest.raises(ValueError):

        @tool(
            action=READ,
            service="zpa",
            toolset="t",
            input_model=_In,
            output_view=_View,
            registry=reg,
        )
        def no_doc(args):  # no docstring, no description=
            return {}


def test_invalid_action_rejected_at_decoration():
    reg = Registry()
    for bad in ("read_write", "rw", "list", ""):
        with pytest.raises(ValueError):

            @tool(
                action=bad,
                service="zpa",
                toolset="t",
                input_model=_In,
                output_view=_View,
                registry=reg,
            )
            def t(args):
                """doc"""
                return {}


def test_duplicate_name_rejected():
    reg, _ = _make_registry_with(name="dupe")
    with pytest.raises(ValueError):
        _make_registry_into(reg, name="dupe")


def _make_registry_into(reg, *, name, action=READ):
    @tool(
        action=action,
        service="zpa",
        toolset="t",
        input_model=_In,
        output_view=_View,
        registry=reg,
        name=name,
    )
    def another(args):
        """doc"""
        return {}

    return another


def test_output_view_must_be_agentview():
    reg = Registry()
    with pytest.raises(TypeError):

        @tool(
            action=READ,
            service="zpa",
            toolset="t",
            input_model=_In,
            output_view=dict,
            registry=reg,  # not an AgentView
        )
        def bad(args):
            """doc"""
            return {}


# ---------------------------------------------------------------------------
# Registry.select — the filtering layer as a query (DESIGN.md §6)
# ---------------------------------------------------------------------------


def _populated_registry() -> Registry:
    reg = Registry()
    for name, action, toolset in [
        ("zpa_list_groups", READ, "zpa_groups"),
        ("zpa_create_group", CREATE, "zpa_groups"),
        ("zpa_delete_group", DELETE, "zpa_groups"),
        ("zia_list_rules", READ, "zia_fw"),
        ("zia_update_rule", UPDATE, "zia_fw"),
    ]:

        @tool(
            action=action,
            service=name.split("_")[0],
            toolset=toolset,
            input_model=_In,
            output_view=_View,
            registry=reg,
            name=name,
        )
        def _fn(args):
            """doc"""
            return {}

    return reg


def test_select_read_only_by_default_excludes_writes():
    reg = _populated_registry()
    names = {s.name for s in reg.select()}
    assert names == {"zpa_list_groups", "zia_list_rules"}  # only reads


def test_select_enable_write_includes_writes():
    reg = _populated_registry()
    names = {s.name for s in reg.select(enable_write=True)}
    assert "zpa_create_group" in names and "zia_update_rule" in names


def test_select_write_allowlist_narrows_writes():
    reg = _populated_registry()
    names = {s.name for s in reg.select(enable_write=True, write_allowlist=["zpa_create_*"])}
    assert "zpa_create_group" in names
    assert "zpa_delete_group" not in names  # not in allowlist
    assert "zia_update_rule" not in names
    assert "zpa_list_groups" in names  # reads always pass


def test_select_toolset_filter():
    reg = _populated_registry()
    names = {s.name for s in reg.select(enabled_toolsets=["zia_fw"])}
    assert names == {"zia_list_rules"}  # reads in zia_fw only (writes off)


def test_select_disabled_toolsets_blocklist():
    reg = _populated_registry()
    names = {s.name for s in reg.select(disabled_toolsets=["zia_fw"])}
    assert names == {"zpa_list_groups"}  # zia_fw gone, zpa reads remain


def test_select_disabled_toolset_wins_over_enabled_toolset():
    reg = _populated_registry()
    # A toolset both selected and disabled → disable wins (mirrors services).
    names = {s.name for s in reg.select(enabled_toolsets=["zia_fw"], disabled_toolsets=["zia_fw"])}
    assert names == set()


def test_select_disabled_toolsets_none_keeps_all():
    reg = _populated_registry()
    # None (the default) applies no blocklist — same as omitting it.
    assert {s.name for s in reg.select(disabled_toolsets=None)} == {s.name for s in reg.select()}


def test_select_enabled_services_allowlist():
    reg = _populated_registry()
    names = {s.name for s in reg.select(enabled_services=["zia"])}
    assert names == {"zia_list_rules"}  # only zia reads, zpa excluded


def test_select_disabled_services_blocklist():
    reg = _populated_registry()
    names = {s.name for s in reg.select(disabled_services=["zia"])}
    assert names == {"zpa_list_groups"}  # zia gone, zpa reads remain


def test_select_disabled_service_wins_over_enabled():
    reg = _populated_registry()
    # A service both enabled and disabled → disable wins (defensive).
    names = {s.name for s in reg.select(enabled_services=["zia"], disabled_services=["zia"])}
    assert names == set()


def test_select_enabled_services_none_keeps_all_reads():
    reg = _populated_registry()
    names = {s.name for s in reg.select(enabled_services=None)}
    assert names == {"zpa_list_groups", "zia_list_rules"}


def test_select_disabled_pattern_wins_over_everything():
    reg = _populated_registry()
    names = {s.name for s in reg.select(enable_write=True, disabled_patterns=["*_delete_*"])}
    assert "zpa_delete_group" not in names


def test_is_write_property():
    reg = _populated_registry()
    assert reg.get("zpa_create_group").is_write is True
    assert reg.get("zpa_list_groups").is_write is False


def test_spec_is_immutable():
    reg, _ = _make_registry_with(name="frozen_tool")
    spec: ToolSpec = reg.get("frozen_tool")
    with pytest.raises(Exception):
        spec.action = UPDATE  # type: ignore[misc]


def test_wire_format_defaults_to_auto():
    reg, _ = _make_registry_with(name="fmt_tool")
    assert reg.get("fmt_tool").wire_format is WireFormat.AUTO
