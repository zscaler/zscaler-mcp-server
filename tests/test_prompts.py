"""Tests for the MCP Prompts subsystem.

Covers the self-registering registry/decorator, the FastMCP bridge (argument
schema derivation), the concrete ZDX prompt's rendered body, and the server-level
wiring that gates prompts behind the visible services.
"""

from __future__ import annotations

import pytest

from zscaler_mcp.prompts import (
    PromptRegistry,
    build_function_prompt,
    discover_prompts,
    prompt,
)
from zscaler_mcp.prompts.registry import PROMPT_REGISTRY
from zscaler_mcp.server import build_server

# ---------------------------------------------------------------------------
# Registry + decorator
# ---------------------------------------------------------------------------


def test_decorator_registers_into_injected_registry():
    reg = PromptRegistry()

    @prompt(name="zdx_demo", title="Demo", service="zdx", registry=reg)
    def _fn(target: str) -> str:
        """A demo prompt."""
        return f"do {target}"

    spec = reg.get("zdx_demo")
    assert spec is not None
    assert spec.title == "Demo"
    assert spec.service == "zdx"
    assert spec.description == "A demo prompt."
    # The decorator returns the original function unchanged (still callable).
    assert _fn("x") == "do x"


def test_duplicate_prompt_name_raises():
    reg = PromptRegistry()

    @prompt(name="dup", title="A", service="zdx", registry=reg)
    def _a() -> str:
        """A."""
        return "a"

    with pytest.raises(ValueError, match="Duplicate prompt name"):

        @prompt(name="dup", title="B", service="zdx", registry=reg)
        def _b() -> str:
            """B."""
            return "b"


def test_missing_description_raises():
    reg = PromptRegistry()

    with pytest.raises(ValueError, match="no description"):

        @prompt(name="nodesc", title="X", service="zdx", registry=reg)
        def _fn() -> str:
            return "x"


def test_select_filters_by_visible_service():
    reg = PromptRegistry()

    @prompt(name="zdx_p", title="ZDX", service="zdx", registry=reg)
    def _z() -> str:
        """Z."""
        return "z"

    @prompt(name="zia_p", title="ZIA", service="zia", registry=reg)
    def _i() -> str:
        """I."""
        return "i"

    assert {s.name for s in reg.select(visible_services={"zdx"})} == {"zdx_p"}
    assert {s.name for s in reg.select(visible_services=set())} == set()
    # None means "no gating" — every prompt is kept.
    assert {s.name for s in reg.select(visible_services=None)} == {"zdx_p", "zia_p"}


# ---------------------------------------------------------------------------
# Bridge: argument schema derivation
# ---------------------------------------------------------------------------


def test_bridge_derives_required_and_optional_arguments():
    reg = PromptRegistry()

    @prompt(name="zdx_args", title="Args", service="zdx", registry=reg)
    def _fn(user_or_device: str, application: str = "", since_hours: str = "24") -> str:
        """Args demo."""
        return user_or_device

    fp = build_function_prompt(reg.get("zdx_args"))
    assert fp.name == "zdx_args"
    assert fp.title == "Args"
    args = {a.name: a.required for a in fp.arguments}
    assert args == {"user_or_device": True, "application": False, "since_hours": False}


# ---------------------------------------------------------------------------
# The concrete ZDX prompt
# ---------------------------------------------------------------------------


def test_zdx_prompt_is_discovered():
    discover_prompts()
    spec = PROMPT_REGISTRY.get("zdx_troubleshoot_user_experience")
    assert spec is not None
    assert spec.service == "zdx"


@pytest.mark.asyncio
async def test_zdx_prompt_renders_with_inputs():
    discover_prompts()
    fp = build_function_prompt(PROMPT_REGISTRY.get("zdx_troubleshoot_user_experience"))
    result = await fp.render({"user_or_device": "jdoe@acme.com", "since_hours": "48"})
    text = " ".join(m.content.text for m in result.messages)
    # The user and lookback window are interpolated into the playbook body.
    assert "jdoe@acme.com" in text
    assert "48 hours" in text
    # It references the real read-only ZDX tools, not invented ones.
    assert "zdx_list_devices" in text
    assert "since=48" in text


@pytest.mark.asyncio
async def test_zdx_prompt_requires_user_or_device():
    discover_prompts()
    fp = build_function_prompt(PROMPT_REGISTRY.get("zdx_troubleshoot_user_experience"))
    with pytest.raises(ValueError, match="Missing required arguments"):
        await fp.render({"since_hours": "24"})


# ---------------------------------------------------------------------------
# Server wiring: prompts track visible services
# ---------------------------------------------------------------------------


async def _prompt_names(server):
    return {p.name for p in await server.list_prompts()}


@pytest.mark.asyncio
async def test_server_registers_zdx_prompt_by_default():
    server = build_server()
    assert "zdx_troubleshoot_user_experience" in await _prompt_names(server)


@pytest.mark.asyncio
async def test_prompt_hidden_when_service_filtered_out():
    # Disabling every zdx tool removes zdx from the visible-services set, so the
    # ZDX prompt must not be advertised either (no tools to back the playbook).
    server = build_server(disabled_patterns=["zdx_*"])
    assert "zdx_troubleshoot_user_experience" not in await _prompt_names(server)


# ---------------------------------------------------------------------------
# The concrete ZCell prompts
# ---------------------------------------------------------------------------

_ZCELL_PROMPTS = {
    "zcell_investigate_sim",
    "zcell_audit_data_usage",
    "zcell_review_anomaly_policies",
}


def test_zcell_prompts_are_discovered():
    discover_prompts()
    for name in _ZCELL_PROMPTS:
        spec = PROMPT_REGISTRY.get(name)
        assert spec is not None, f"{name} not discovered"
        assert spec.service == "zcell"


def test_zcell_investigate_sim_argument_schema():
    discover_prompts()
    fp = build_function_prompt(PROMPT_REGISTRY.get("zcell_investigate_sim"))
    args = {a.name: a.required for a in fp.arguments}
    # iccid is required; the lookback window is optional (defaulted).
    assert args == {"iccid": True, "since_days": False}


@pytest.mark.asyncio
async def test_zcell_investigate_sim_renders_with_inputs():
    discover_prompts()
    fp = build_function_prompt(PROMPT_REGISTRY.get("zcell_investigate_sim"))
    result = await fp.render({"iccid": "8944500912345678", "since_days": "14"})
    text = " ".join(m.content.text for m in result.messages)
    # Inputs are interpolated into the playbook body.
    assert "8944500912345678" in text
    assert "14 days" in text
    # It references real read-only ZCell tools and the days lookback knob.
    assert "zcell_get_sim_details" in text
    assert "zcell_list_network_events" in text
    assert "days=14" in text


@pytest.mark.asyncio
async def test_zcell_investigate_sim_requires_iccid():
    discover_prompts()
    fp = build_function_prompt(PROMPT_REGISTRY.get("zcell_investigate_sim"))
    with pytest.raises(ValueError, match="Missing required arguments"):
        await fp.render({"since_days": "7"})


@pytest.mark.asyncio
async def test_zcell_usage_and_anomaly_prompts_render_default_window():
    discover_prompts()
    usage = build_function_prompt(PROMPT_REGISTRY.get("zcell_audit_data_usage"))
    usage_text = " ".join(m.content.text for m in (await usage.render({})).messages)
    assert "zcell_list_sim_usage_by_country" in usage_text
    assert "30 days" in usage_text  # default since_days

    anomaly = build_function_prompt(PROMPT_REGISTRY.get("zcell_review_anomaly_policies"))
    anomaly_text = " ".join(m.content.text for m in (await anomaly.render({})).messages)
    assert "zcell_list_anomaly_policies" in anomaly_text
    assert "zcell_get_sim_location_group" in anomaly_text


# ---------------------------------------------------------------------------
# Server wiring: ZCell prompts track visible services
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_registers_zcell_prompts_by_default():
    names = await _prompt_names(build_server())
    assert _ZCELL_PROMPTS <= names


@pytest.mark.asyncio
async def test_zcell_prompts_hidden_when_service_filtered_out():
    server = build_server(disabled_patterns=["zcell_*"])
    names = await _prompt_names(server)
    assert not (_ZCELL_PROMPTS & names)
