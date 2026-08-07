"""Tests for JMESPath client-side filtering on list tools.

Two layers: the pure helper (``apply_jmespath``) and the central wiring in
``registry/fastmcp_bridge`` that gives EVERY list tool the ``query`` parameter
without the tool module opting in.

This is the caller-side counterpart to the verbatim-record contract in
``test_shaping_helpers.py``: the server never decides which attributes matter,
but the agent can project exactly what it wants.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest

from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.server import build_server

RECORDS = [
    {"id": "1", "name": "hq", "enabled": True, "policyName": "SGIOLab"},
    {"id": "2", "name": "branch", "enabled": False, "policyName": "Default"},
]


# =============================================================================
# The helper
# =============================================================================


def test_no_expression_returns_data_unchanged():
    assert apply_jmespath(RECORDS, None) is RECORDS
    assert apply_jmespath(RECORDS, "") is RECORDS


def test_filter_expression():
    assert apply_jmespath(RECORDS, "[?enabled==`true`]") == [RECORDS[0]]


def test_projection_expression():
    assert apply_jmespath(RECORDS, "[*].{name: name, id: id}") == [
        {"name": "hq", "id": "1"},
        {"name": "branch", "id": "2"},
    ]


def test_scalar_result_is_wrapped_so_list_tools_stay_lists():
    # length(@)/sum(...) produce a scalar; a list tool must still return a list.
    assert apply_jmespath(RECORDS, "length(@)") == [2]


def test_no_match_returns_empty_list():
    assert apply_jmespath(RECORDS, "[?name=='nope']") == []
    assert apply_jmespath(RECORDS, "missingField") == []


def test_invalid_expression_returns_error_record_not_raise():
    out = apply_jmespath(RECORDS, "[?bad ==")
    assert isinstance(out, list) and len(out) == 1
    assert "Invalid JMESPath expression" in out[0]["error"]


def test_camelcase_field_names_work():
    # Records pass through verbatim, so expressions use the API's own spelling.
    assert apply_jmespath(RECORDS, "[?policyName=='SGIOLab'].id") == ["1"]


# =============================================================================
# The central wiring
# =============================================================================


@pytest.mark.asyncio
async def test_every_collection_tool_exposes_query():
    """The wiring is central, so no tool can be missing it or opt out by accident."""
    from zscaler_mcp.registry.registry import REGISTRY

    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    wrong = []
    for name, tool in tools.items():
        expected = REGISTRY.get(name).supports_query
        actual = "query" in (tool.input_schema.get("properties") or {})
        if expected != actual:
            wrong.append(f"{name}: supports_query={expected} but query-param={actual}")
    assert not wrong, "\n".join(wrong)


@pytest.mark.asyncio
async def test_envelope_returning_list_tools_also_get_query():
    # v1 parity: these return one object wrapping the collection rather than a
    # row list, but they are still "list" surfaces the caller may want to filter.
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    for name in ("zia_list_auth_exempt_urls", "zia_list_atp_malicious_urls", "zcell_list_sims"):
        assert "query" in (tools[name].input_schema.get("properties") or {}), name


@pytest.mark.asyncio
async def test_query_parameter_is_documented_for_the_agent():
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    q = tools["zcc_list_devices"].input_schema["properties"]["query"]
    assert "JMESPath" in q["description"]
    assert q["default"] is None  # omitting it is the default path


@pytest.mark.asyncio
async def test_query_description_warns_that_field_names_are_snake_case():
    """The description used to claim the keys are "exactly what the API returns".

    They are not: the SDK's ``as_dict()`` snake_cases them, so a record the API
    documents as ``customCategory`` arrives as ``custom_category``. An agent
    trusting the old wording filtered on the camelCase spelling, got ``[]``, and
    had no way to tell that from a genuinely empty result.
    """
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    desc = tools["zia_list_url_categories"].input_schema["properties"]["query"]["description"]
    assert "snake_case" in desc
    assert "exactly what the Zscaler API returns" not in desc


@pytest.mark.asyncio
async def test_a_query_that_matches_nothing_is_logged_with_both_row_counts(caplog):
    """`query` never reaches the tool, so [TOOL CALL] cannot record it.

    Without this line an empty response is indistinguishable in the log from an
    empty tenant — which is exactly the ambiguity that made the regression above
    expensive to diagnose.
    """
    from zscaler_mcp.security import audit

    server = build_server()
    target = "zscaler_mcp.tools.zcc.list_devices.get_zscaler_client"
    audit.enable_tool_call_logging()
    try:
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.audit"):
            with patch(target, return_value=_fake_client(RECORDS)):
                await server.call_tool("zcc_list_devices", {"query": "[?noSuchField]"})
    finally:
        audit.disable_tool_call_logging()
    text = "\n".join(r.message for r in caplog.records)
    assert "[QUERY]" in text
    assert "noSuchField" in text
    assert "2 -> 0 rows" in text


@pytest.mark.asyncio
async def test_non_list_tools_have_no_query_parameter():
    # A single-object get has nothing to filter; the parameter would be noise.
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    assert "query" not in (tools["zpa_get_segment_group"].input_schema.get("properties") or {})


class _FakeDevice:
    def __init__(self, data: dict) -> None:
        self._data = data

    def as_dict(self) -> dict:
        return dict(self._data)


def _fake_client(records):
    class _Client:
        class zcc:
            class devices:
                @staticmethod
                def list_devices(query_params=None):
                    return ([_FakeDevice(r) for r in records], None, None)

    return _Client


@pytest.mark.asyncio
async def test_query_is_applied_end_to_end_through_the_tool():
    server = build_server()
    target = "zscaler_mcp.tools.zcc.list_devices.get_zscaler_client"
    with patch(target, return_value=_fake_client(RECORDS)):
        full = await server.call_tool("zcc_list_devices", {})
        projected = await server.call_tool("zcc_list_devices", {"query": "[*].{name: name}"})
    # Unfiltered: the whole record, verbatim.
    assert "policyName" in full.content[0].text
    # Projected: only what the caller asked for.
    text = projected.content[0].text
    assert "policyName" not in text
    assert "hq" in text and "branch" in text


@pytest.mark.asyncio
async def test_query_does_not_leak_into_the_input_model():
    # `query` is a bridge-owned channel; the tool's own input model never sees
    # it, so validation must not reject the call.
    server = build_server()
    target = "zscaler_mcp.tools.zcc.list_devices.get_zscaler_client"
    with patch(target, return_value=_fake_client(RECORDS)):
        result = await server.call_tool("zcc_list_devices", {"query": "length(@)"})
    assert json.loads(result.content[0].text) == [2]


# =============================================================================
# Operator-input validation (regression: a typo must not silently empty the server)
# =============================================================================


def test_unknown_toolset_id_warns_instead_of_silently_emptying_the_server(caplog):
    """A typo'd `--toolsets` id matches nothing and yields ZERO tools.

    Failing silently there is the worst case for an operator, so the boot logs a
    warning naming the bad id and listing the known ones. Documented contract is
    warn-and-continue, not fail-fast.
    """
    import logging

    with caplog.at_level(logging.WARNING, logger="zscaler_mcp"):
        build_server(enabled_toolsets=["zia_ssl_inspction"])  # deliberate typo
    warnings = [r.getMessage() for r in caplog.records if "unknown toolset id" in r.getMessage()]
    assert warnings, "no warning logged for an unknown --toolsets id"
    assert "zia_ssl_inspction" in warnings[0]


def test_unknown_disabled_toolset_id_also_warns(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="zscaler_mcp"):
        build_server(disabled_toolsets=["nope_not_a_toolset"])
    assert any("nope_not_a_toolset" in r.getMessage() for r in caplog.records)


def test_valid_toolset_ids_produce_no_warning(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="zscaler_mcp"):
        build_server(enabled_toolsets=["zcc_devices"], disabled_toolsets=["zia_ssl_inspection"])
    assert not [r for r in caplog.records if "unknown toolset id" in r.getMessage()]
