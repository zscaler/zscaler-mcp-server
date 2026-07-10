"""Tests for the sanitize + audit execution wrapper (security/audit.py)."""

from __future__ import annotations

import logging

from zscaler_mcp.security import audit


def test_wrap_tool_sanitizes_result_when_enabled():
    def fn(args):
        return [{"name": "ok\u200b", "desc": "<b>x</b>"}]

    wrapped = audit.wrap_tool(fn, "zpa_list_x")
    out = wrapped(None)
    assert out == [{"name": "ok", "desc": "x"}]


def test_wrap_tool_passes_through_when_sanitization_disabled():
    from zscaler_mcp.security import sanitize

    def fn(args):
        return {"name": "ok\u200b"}

    sanitize.disable_sanitization()
    try:
        out = audit.wrap_tool(fn, "zpa_get_x")(None)
        assert out == {"name": "ok\u200b"}
    finally:
        sanitize.enable_sanitization()


def test_audit_logging_emits_when_enabled(caplog):
    def fn(args=None, **kw):
        return [{"id": "1"}]

    audit.enable_tool_call_logging()
    try:
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.audit"):
            audit.wrap_tool(fn, "zpa_list_x")(None, search="HQ")
        text = "\n".join(r.message for r in caplog.records)
        assert "[TOOL CALL] zpa_list_x" in text
        assert "[TOOL OK]   zpa_list_x" in text
    finally:
        audit.disable_tool_call_logging()


def test_audit_redacts_sensitive_args(caplog):
    def fn(args, **kw):
        return {}

    audit.enable_tool_call_logging()
    try:
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.audit"):
            audit.wrap_tool(fn, "zia_login")(None, client_secret="supersecret", search="ok")
        text = "\n".join(r.message for r in caplog.records)
        assert "supersecret" not in text
        assert "***REDACTED***" in text
        assert "ok" in text
    finally:
        audit.disable_tool_call_logging()


def test_no_audit_logging_when_disabled(caplog):
    def fn(args):
        return {}

    audit.disable_tool_call_logging()
    with caplog.at_level(logging.INFO, logger="zscaler_mcp.audit"):
        audit.wrap_tool(fn, "zpa_get_x")(None)
    assert all("[TOOL" not in r.message for r in caplog.records)


def test_refresh_tool_call_logging(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_LOG_TOOL_CALLS", "true")
    audit.refresh_tool_call_logging()
    assert audit.is_tool_call_logging_enabled() is True
    monkeypatch.setenv("ZSCALER_MCP_LOG_TOOL_CALLS", "false")
    audit.refresh_tool_call_logging()
    assert audit.is_tool_call_logging_enabled() is False
