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


def test_audit_logs_the_positional_input_model_the_bridge_passes(caplog):
    """The registry bridge calls tools as `fn(model)` — no keyword arguments.

    Reading `kwargs` alone logged `args: {}` for every call in the running
    server, so the audit line recorded nothing about what was asked for. That
    blind spot cost a debugging session: an agent's filtered listing came back
    empty and the log could not say what it had filtered on.
    """
    from pydantic import BaseModel

    class _Input(BaseModel):
        search: str | None = None
        custom_only: bool | None = None
        page_size: int | None = None

    def fn(args):
        return [{"id": "1"}]

    audit.enable_tool_call_logging()
    try:
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.audit"):
            audit.wrap_tool(fn, "zia_list_url_categories")(_Input(custom_only=True))
        text = "\n".join(r.message for r in caplog.records)
        assert "custom_only" in text and "True" in text
        # Unset optionals stay out, so a 30-field model still logs the one field
        # that was actually passed.
        assert "page_size" not in text
    finally:
        audit.disable_tool_call_logging()


def test_audit_redacts_sensitive_fields_inside_the_input_model(caplog):
    """Redaction must survive the model unpacking, not just top-level kwargs."""
    from pydantic import BaseModel

    class _Input(BaseModel):
        client_secret: str | None = None

    audit.enable_tool_call_logging()
    try:
        with caplog.at_level(logging.INFO, logger="zscaler_mcp.audit"):
            audit.wrap_tool(lambda args: {}, "zia_x")(_Input(client_secret="supersecret"))
        text = "\n".join(r.message for r in caplog.records)
        assert "supersecret" not in text
        assert "***REDACTED***" in text
    finally:
        audit.disable_tool_call_logging()
