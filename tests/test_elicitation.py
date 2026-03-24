"""
Tests for zscaler_mcp.common.elicitation — cryptographic confirmation tokens.

Covers HMAC token generation/validation, canonical payload construction,
legacy confirmed=true handling, token expiry, parameter tampering detection,
and the skip-confirmations escape hatch.
"""

import os
import time
from unittest.mock import patch


from zscaler_mcp.common.elicitation import (
    _canonical_payload,
    _generate_token,
    _validate_token,
    check_confirmation,
    extract_confirmed_from_kwargs,
    generate_confirmation_message,
    should_skip_confirmations,
)


# ---------------------------------------------------------------------------
# _canonical_payload
# ---------------------------------------------------------------------------


class TestCanonicalPayload:
    def test_deterministic_output(self):
        p1 = _canonical_payload("tool_a", {"z": 1, "a": 2})
        p2 = _canonical_payload("tool_a", {"a": 2, "z": 1})
        assert p1 == p2, "Key order must not matter"

    def test_strips_internal_keys(self):
        params = {"name": "foo", "confirmed": True, "confirmation_token": "x", "_internal": 1}
        result = _canonical_payload("t", params)
        assert "confirmed" not in result
        assert "confirmation_token" not in result
        assert "_internal" not in result
        assert "name" in result

    def test_strips_service_and_kwargs(self):
        params = {"name": "foo", "service": "zpa", "kwargs": "{}"}
        result = _canonical_payload("t", params)
        assert "service" not in result
        assert "kwargs" not in result

    def test_strips_use_legacy(self):
        params = {"name": "foo", "use_legacy": True}
        result = _canonical_payload("t", params)
        assert "use_legacy" not in result

    def test_includes_tool_name_prefix(self):
        result = _canonical_payload("zpa_delete_segment", {"id": "123"})
        assert result.startswith("zpa_delete_segment:")

    def test_empty_params(self):
        result = _canonical_payload("tool", {})
        assert result == "tool:{}"


# ---------------------------------------------------------------------------
# _generate_token / _validate_token
# ---------------------------------------------------------------------------


class TestTokenGenerationValidation:
    def test_roundtrip_valid(self):
        params = {"id": "123", "name": "test"}
        token = _generate_token("zpa_delete_segment", params)
        valid, err = _validate_token(token, "zpa_delete_segment", params)
        assert valid is True
        assert err is None

    def test_token_format(self):
        token = _generate_token("t", {"a": 1})
        parts = token.split(":", 1)
        assert len(parts) == 2
        int(parts[0])  # expiry must be an integer
        assert len(parts[1]) == 64  # SHA-256 hex digest

    def test_different_tool_name_fails(self):
        params = {"id": "123"}
        token = _generate_token("zpa_delete_segment", params)
        valid, err = _validate_token(token, "zpa_create_segment", params)
        assert valid is False
        assert "does not match" in err

    def test_modified_params_fails(self):
        original = {"id": "123", "name": "original"}
        token = _generate_token("tool", original)
        tampered = {"id": "123", "name": "TAMPERED"}
        valid, err = _validate_token(token, "tool", tampered)
        assert valid is False
        assert "modified" in err.lower()

    def test_extra_param_fails(self):
        original = {"id": "123"}
        token = _generate_token("tool", original)
        tampered = {"id": "123", "extra": "injected"}
        valid, err = _validate_token(token, "tool", tampered)
        assert valid is False

    def test_removed_param_fails(self):
        original = {"id": "123", "name": "test"}
        token = _generate_token("tool", original)
        tampered = {"id": "123"}
        valid, err = _validate_token(token, "tool", tampered)
        assert valid is False

    def test_expired_token(self):
        params = {"id": "1"}
        token = _generate_token("tool", params)
        expiry, sig = token.split(":", 1)
        expired = f"{int(time.time()) - 10}:{sig}"
        valid, err = _validate_token(expired, "tool", params)
        assert valid is False
        assert "expired" in err.lower()

    def test_malformed_token_no_colon(self):
        valid, err = _validate_token("garbage", "tool", {})
        assert valid is False
        assert "Malformed" in err

    def test_malformed_token_bad_expiry(self):
        valid, err = _validate_token("notanumber:abcdef", "tool", {})
        assert valid is False
        assert "invalid expiry" in err.lower()

    def test_forged_signature_fails(self):
        params = {"id": "1"}
        token = _generate_token("tool", params)
        expiry, _ = token.split(":", 1)
        forged = f"{expiry}:{'a' * 64}"
        valid, err = _validate_token(forged, "tool", params)
        assert valid is False

    def test_internal_keys_ignored_in_validation(self):
        """confirmed/confirmation_token/kwargs/_prefixed keys are stripped
        from canonical payload, so their presence or absence doesn't affect HMAC."""
        params = {"id": "1"}
        token = _generate_token("tool", params)
        params_with_meta = {"id": "1", "confirmed": True, "confirmation_token": token, "_x": 9}
        valid, err = _validate_token(token, "tool", params_with_meta)
        assert valid is True


# ---------------------------------------------------------------------------
# extract_confirmed_from_kwargs
# ---------------------------------------------------------------------------


class TestExtractConfirmedFromKwargs:
    def test_dict_with_token(self):
        result = extract_confirmed_from_kwargs({"confirmation_token": "abc"})
        assert result == "abc"

    def test_json_string_with_token(self):
        result = extract_confirmed_from_kwargs('{"confirmation_token": "xyz"}')
        assert result == "xyz"

    def test_legacy_confirmed_true_dict(self):
        result = extract_confirmed_from_kwargs({"confirmed": True})
        assert result == "__legacy_confirmed__"

    def test_legacy_confirm_true_dict(self):
        result = extract_confirmed_from_kwargs({"confirm": True})
        assert result == "__legacy_confirmed__"

    def test_legacy_confirmed_json_string(self):
        result = extract_confirmed_from_kwargs('{"confirmed": true}')
        assert result == "__legacy_confirmed__"

    def test_empty_string(self):
        assert extract_confirmed_from_kwargs("") is None

    def test_empty_dict_string(self):
        assert extract_confirmed_from_kwargs("{}") is None

    def test_empty_dict(self):
        assert extract_confirmed_from_kwargs({}) is None

    def test_none(self):
        assert extract_confirmed_from_kwargs(None) is None

    def test_invalid_json_string(self):
        assert extract_confirmed_from_kwargs("not json") is None

    def test_integer_value(self):
        assert extract_confirmed_from_kwargs(42) is None

    def test_token_takes_precedence_over_confirmed(self):
        data = {"confirmation_token": "tok", "confirmed": True}
        assert extract_confirmed_from_kwargs(data) == "tok"


# ---------------------------------------------------------------------------
# should_skip_confirmations
# ---------------------------------------------------------------------------


class TestShouldSkipConfirmations:
    def test_not_set(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ZSCALER_MCP_SKIP_CONFIRMATIONS", None)
            assert should_skip_confirmations() is False

    def test_set_true(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "true"}):
            assert should_skip_confirmations() is True

    def test_set_TRUE_uppercase(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "TRUE"}):
            assert should_skip_confirmations() is True

    def test_set_false(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "false"}):
            assert should_skip_confirmations() is False


# ---------------------------------------------------------------------------
# generate_confirmation_message
# ---------------------------------------------------------------------------


class TestGenerateConfirmationMessage:
    def test_delete_operation(self):
        msg = generate_confirmation_message("zpa_delete_segment", {"id": "42"}, "tok")
        assert "DESTRUCTIVE OPERATION" in msg
        assert "DELETE" in msg
        assert "confirmation_token" in msg
        assert "tok" in msg

    def test_create_operation(self):
        msg = generate_confirmation_message(
            "zpa_create_segment", {"name": "web-app", "domain": "example.com"}, "tok"
        )
        assert "CREATE OPERATION" in msg
        assert "web-app" in msg
        assert "confirmation_token" in msg

    def test_update_operation(self):
        msg = generate_confirmation_message(
            "zpa_update_segment", {"id": "1", "name": "updated"}, "tok"
        )
        assert "UPDATE OPERATION" in msg
        assert "confirmation_token" in msg

    def test_generic_write_operation(self):
        msg = generate_confirmation_message("zpa_reorder_rules", {"policy_type": "access"}, "tok")
        assert "WRITE OPERATION" in msg
        assert "confirmation_token" in msg

    def test_bulk_delete(self):
        msg = generate_confirmation_message("zpa_bulk_delete_segments", {"ids": [1, 2]}, "tok")
        assert "DESTRUCTIVE OPERATION" in msg
        assert "DELETE" in msg

    def test_display_params_strip_internal(self):
        msg = generate_confirmation_message(
            "zpa_create_segment",
            {"name": "x", "confirmed": True, "service": "zpa", "_meta": "y"},
            "tok",
        )
        assert "confirmed" not in msg.split("confirmation_token")[0]
        assert "service" not in msg.split("confirmation_token")[0]


# ---------------------------------------------------------------------------
# check_confirmation (integration)
# ---------------------------------------------------------------------------


class TestCheckConfirmation:
    def test_no_confirmation_returns_message(self):
        result = check_confirmation("tool", None, {"id": "1"})
        assert result is not None
        assert "confirmation_token" in result

    def test_false_confirmation_returns_message(self):
        result = check_confirmation("tool", False, {"id": "1"})
        assert result is not None

    def test_legacy_confirmed_reprompts(self):
        result = check_confirmation("tool", "__legacy_confirmed__", {"id": "1"})
        assert result is not None
        assert "confirmation_token" in result

    def test_valid_token_returns_none(self):
        params = {"id": "1", "name": "test"}
        token = _generate_token("tool", params)
        result = check_confirmation("tool", token, params)
        assert result is None

    def test_invalid_token_reprompts(self):
        result = check_confirmation("tool", "fake:token", {"id": "1"})
        assert result is not None
        assert "rejected" in result.lower() or "Confirmation" in result

    def test_expired_token_reprompts(self):
        params = {"id": "1"}
        token = _generate_token("tool", params)
        expiry, sig = token.split(":", 1)
        expired = f"{int(time.time()) - 10}:{sig}"
        result = check_confirmation("tool", expired, params)
        assert result is not None
        assert "expired" in result.lower()

    def test_tampered_params_reprompts(self):
        original = {"id": "1", "name": "original"}
        token = _generate_token("tool", original)
        tampered = {"id": "1", "name": "HACKED"}
        result = check_confirmation("tool", token, tampered)
        assert result is not None
        assert "modified" in result.lower() or "does not match" in result.lower()

    def test_skip_confirmations_bypasses(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "true"}):
            result = check_confirmation("tool", None, {"id": "1"})
            assert result is None
