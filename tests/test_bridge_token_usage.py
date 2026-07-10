"""Tests for the opt-in per-response token-usage reporting in the bridge.

When ``ZSCALER_MCP_REPORT_TOKENS`` is set, ``_to_tool_result`` must attach a
``token_usage`` block to the structured content and a one-line footer to the
text; when unset it must do neither (zero overhead, no output pollution).
"""

from __future__ import annotations

from zscaler_mcp.registry import READ, Registry, tool
from zscaler_mcp.registry.fastmcp_bridge import _to_tool_result
from zscaler_mcp.shaping import AgentView


class _Row(AgentView):
    id: str
    name: str


class _In(AgentView):
    pass


def _list_spec():
    reg = Registry()

    @tool(
        action=READ,
        service="zpa",
        toolset="zpa_test",
        input_model=_In,
        output_view=_Row,
        registry=reg,
        name="zpa_read_rows",
        is_list=True,
    )
    def _fn(args):  # pragma: no cover - not invoked here
        """List rows."""
        return []

    return reg.get("zpa_read_rows")


def test_agent_echo_absent_when_flag_unset(monkeypatch):
    # Without the flag, the agent-facing echo is suppressed (it would cost the
    # model response tokens) — but the server-side log line is unconditional.
    monkeypatch.delenv("ZSCALER_MCP_REPORT_TOKENS", raising=False)
    spec = _list_spec()
    rows = [_Row(id="1", name="HQ"), _Row(id="2", name="Branch")]
    res = _to_tool_result(spec, rows)

    assert "token_usage" not in res.structured_content
    assert "# token_usage:" not in res.content[0].text


def test_server_side_token_log_always_emitted(monkeypatch, caplog):
    # No flag set: the [TOKENS] audit line must still appear (native telemetry).
    monkeypatch.delenv("ZSCALER_MCP_REPORT_TOKENS", raising=False)
    spec = _list_spec()
    rows = [_Row(id="1", name="HQ"), _Row(id="2", name="Branch")]
    with caplog.at_level("INFO", logger="zscaler_mcp.audit"):
        _to_tool_result(spec, rows)
    assert any("[TOKENS]" in rec.message for rec in caplog.records)
    assert any("zpa_read_rows" in rec.message for rec in caplog.records)


def test_empty_list_result_does_not_crash(monkeypatch, caplog):
    # Regression: a list tool returning 0 rows must not raise KeyError. The
    # token block omits `tokens_per_row` for empty results (no divide-by-zero),
    # and the audit formatter must tolerate that and still log "0 rows".
    monkeypatch.delenv("ZSCALER_MCP_REPORT_TOKENS", raising=False)
    spec = _list_spec()
    with caplog.at_level("INFO", logger="zscaler_mcp.audit"):
        res = _to_tool_result(spec, [])
    assert res.structured_content == {"result": []}
    assert any("0 rows" in rec.message for rec in caplog.records)
    assert not any("tok/row" in rec.message for rec in caplog.records)


def test_agent_echo_attached_when_flag_set(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_REPORT_TOKENS", "true")
    spec = _list_spec()
    rows = [_Row(id="1", name="HQ"), _Row(id="2", name="Branch")]
    res = _to_tool_result(spec, rows)

    usage = res.structured_content["token_usage"]
    assert usage["response_tokens"] > 0
    assert usage["rows"] == 2
    assert "# token_usage:" in res.content[0].text
    # list tools still wrap the payload under "result"
    assert "result" in res.structured_content
