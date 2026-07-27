"""Tests for the HMAC write-confirmation layer (security/elicitation.py)."""

from __future__ import annotations

import time

import pytest

from zscaler_mcp.security import elicitation as el


def test_first_call_returns_confirmation_message():
    msg = el.check_confirmation("zpa_create_segment_group", None, {"name": "HQ"})
    assert msg is not None
    assert "CONFIRMATION REQUIRED" in msg
    assert "confirmation_token" in msg


def test_valid_token_round_trips():
    params = {"name": "HQ", "enabled": True}
    msg = el.check_confirmation("zpa_create_segment_group", None, params)
    # Extract the token from the message.
    token = msg.split('"confirmation_token": "', 1)[1].split('"', 1)[0]
    # Re-submitting with the same params + token proceeds (returns None).
    assert el.check_confirmation("zpa_create_segment_group", token, params) is None


def test_token_rejected_when_params_change():
    params = {"name": "HQ"}
    msg = el.check_confirmation("zpa_delete_segment_group", None, params)
    token = msg.split('"confirmation_token": "', 1)[1].split('"', 1)[0]
    # Tampered params must NOT validate — the HMAC binds tool+params.
    tampered = el.check_confirmation("zpa_delete_segment_group", token, {"name": "EVIL"})
    assert tampered is not None
    assert "does not match" in tampered


def test_token_bound_to_tool_name():
    params = {"name": "HQ"}
    msg = el.check_confirmation("zpa_create_segment_group", None, params)
    token = msg.split('"confirmation_token": "', 1)[1].split('"', 1)[0]
    # Same token, different tool -> rejected.
    other = el.check_confirmation("zpa_delete_segment_group", token, params)
    assert other is not None
    assert "does not match" in other


def test_expired_token_rejected(monkeypatch):
    params = {"name": "HQ"}
    msg = el.check_confirmation("zpa_create_segment_group", None, params)
    token = msg.split('"confirmation_token": "', 1)[1].split('"', 1)[0]
    # Jump past the TTL.
    real_time = time.time
    monkeypatch.setattr(
        el.time, "time", lambda: real_time() + el.CONFIRMATION_TOKEN_TTL_SECONDS + 10
    )
    out = el.check_confirmation("zpa_create_segment_group", token, params)
    assert out is not None
    assert "expired" in out.lower()


def test_skip_confirmations_env(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", "true")
    assert el.check_confirmation("zpa_delete_segment_group", None, {"id": "1"}) is None


def test_extract_confirmed_from_kwargs():
    assert el.extract_confirmed_from_kwargs('{"confirmation_token": "abc"}') == "abc"
    assert el.extract_confirmed_from_kwargs({"confirmation_token": "abc"}) == "abc"
    assert el.extract_confirmed_from_kwargs("") is None
    assert el.extract_confirmed_from_kwargs("{}") is None
    assert el.extract_confirmed_from_kwargs({"confirmed": True}) == "__deprecated_bool_confirmed__"


@pytest.mark.parametrize(
    "tool_name,expected",
    [
        ("zpa_delete_segment_group", "DELETE"),
        ("zpa_create_segment_group", "CREATE"),
        ("zpa_update_segment_group", "UPDATE"),
        ("some_other_write", "WRITE OPERATION"),
    ],
)
def test_message_shape_per_verb(tool_name, expected):
    msg = el.check_confirmation(tool_name, None, {"name": "X", "id": "1"})
    assert expected in msg


def test_delete_message_names_resource_via_suffixed_id():
    """The confirmation prompt must name the resource even when the primary-key
    param isn't literally ``id``/``name`` (e.g. ZPA's ``group_id``)."""
    msg = el.check_confirmation(
        "zpa_delete_segment_group", None, {"group_id": "216196257331405654"}
    )
    assert "216196257331405654" in msg
    assert "group_id" in msg
    assert "unknown" not in msg


def test_resource_identifier_priority_and_fallback():
    # Explicit id/name win over *_id.
    assert el._resource_identifier({"id": "42", "group_id": "9"}) == "42"
    assert el._resource_identifier({"name": "HQ", "rule_id": "9"}) == "HQ"
    # First *_id (sorted) when no id/name.
    assert el._resource_identifier({"group_id": "9"}) == "9 (group_id)"
    assert el._resource_identifier({"segment_id": "7", "rule_id": "3"}) == "3 (rule_id)"
    # Nothing usable.
    assert el._resource_identifier({"enabled": True}) == "unknown"
