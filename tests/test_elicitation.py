"""
Tests for zscaler_mcp.common.elicitation — cryptographic confirmation tokens.

Covers HMAC token generation/validation, canonical payload construction,
legacy confirmed=true handling, token expiry, parameter tampering detection,
the skip-confirmations escape hatch, and CWE-345 resource-binding regression.
"""

import ast
import os
import time
from pathlib import Path
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


# ---------------------------------------------------------------------------
# CWE-345 — HMAC token must be bound to the specific resource ID
# Regression tests to prevent token replay across different resources.
# ---------------------------------------------------------------------------


class TestCWE345TokenReplayPrevention:
    """Verify that HMAC tokens cannot be replayed for different resource IDs.

    Ref: CWE-345 (Insufficient Verification of Data Authenticity).
    All delete operations must bind the resource identifier in the HMAC.
    A token approved for resource A must NOT validate for resource B.
    """

    def test_token_replay_rejected_different_resource_id(self):
        params_a = {"group_id": "decoy_99999"}
        params_b = {"group_id": "PRODUCTION_FW_GROUP"}
        token = _generate_token("zia_delete_ip_destination_group", params_a)
        valid, _ = _validate_token(token, "zia_delete_ip_destination_group", params_b)
        assert valid is False, "Token for resource A must not validate for resource B"

    def test_token_valid_for_same_resource_id(self):
        params = {"group_id": "12345"}
        token = _generate_token("zia_delete_ip_destination_group", params)
        valid, _ = _validate_token(token, "zia_delete_ip_destination_group", params)
        assert valid is True

    def test_empty_params_produces_fungible_token(self):
        """Proves WHY empty {} is dangerous: tokens become interchangeable."""
        token = _generate_token("tool", {})
        valid, _ = _validate_token(token, "tool", {})
        assert valid is True, "Empty params token validates for empty params (fungible)"

    def test_bound_params_prevent_replay(self):
        """Proves the fix: binding resource ID prevents cross-resource replay."""
        token = _generate_token("tool", {"id": "AAA"})
        valid_same, _ = _validate_token(token, "tool", {"id": "AAA"})
        valid_diff, _ = _validate_token(token, "tool", {"id": "BBB"})
        assert valid_same is True, "Token must validate for the same resource"
        assert valid_diff is False, "Token must NOT validate for a different resource"

    def test_replay_rejected_across_all_delete_tool_patterns(self):
        """Exhaustive check: every delete tool pattern rejects cross-resource tokens."""
        tool_params = [
            ("zpa_delete_access_policy_rule", "rule_id"),
            ("zpa_delete_app_connector", "connector_id"),
            ("zpa_delete_app_connector_group", "group_id"),
            ("zpa_delete_application_server", "server_id"),
            ("zpa_delete_application_segment", "segment_id"),
            ("zpa_delete_ba_certificate", "certificate_id"),
            ("zpa_delete_pra_credential", "credential_id"),
            ("zpa_delete_pra_portal", "portal_id"),
            ("zpa_delete_provisioning_key", "key_id"),
            ("zpa_delete_segment_group", "group_id"),
            ("zpa_delete_server_group", "group_id"),
            ("zpa_delete_service_edge_group", "group_id"),
            ("zia_delete_ip_destination_group", "group_id"),
            ("zia_delete_ip_source_group", "group_id"),
            ("zia_delete_location", "location_id"),
            ("zia_delete_static_ip", "static_ip_id"),
            ("zia_delete_vpn_credential", "credential_id"),
            ("zia_delete_url_category", "category_id"),
            ("zia_delete_gre_tunnel", "tunnel_id"),
            ("zia_delete_cloud_firewall_rule", "rule_id"),
            ("zia_delete_cloud_firewall_dns_rule", "rule_id"),
            ("zia_delete_cloud_firewall_ips_rule", "rule_id"),
            ("zia_delete_file_type_control_rule", "rule_id"),
            ("zia_delete_sandbox_rule", "rule_id"),
            ("ztw_delete_ip_destination_group", "group_id"),
            ("ztw_delete_ip_source_group", "group_id"),
            ("ztw_delete_ip_group", "group_id"),
        ]
        for tool_name, param_name in tool_params:
            token = _generate_token(tool_name, {param_name: "DECOY"})
            valid, _ = _validate_token(token, tool_name, {param_name: "TARGET"})
            assert valid is False, (
                f"{tool_name}: token for {param_name}=DECOY must not validate for TARGET"
            )


class TestCWE345SourceCodeRegression:
    """Static analysis: ensure no check_confirmation() call passes empty {}.

    Parses every Python file under zscaler_mcp/tools/ and verifies that
    no call to check_confirmation uses an empty dict literal as the third
    argument. This prevents future regressions of the CWE-345 fix.
    """

    def test_no_empty_params_in_check_confirmation_calls(self):
        tools_dir = Path(__file__).parent.parent / "zscaler_mcp" / "tools"
        assert tools_dir.exists(), f"Tools directory not found: {tools_dir}"

        violations = []
        for py_file in tools_dir.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(), filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name != "check_confirmation":
                    continue
                if len(node.args) >= 3:
                    third_arg = node.args[2]
                    if isinstance(third_arg, ast.Dict) and len(third_arg.keys) == 0:
                        rel = py_file.relative_to(tools_dir.parent.parent)
                        violations.append(f"{rel}:{node.lineno}")

        assert violations == [], (
            f"CWE-345 regression: check_confirmation() called with empty {{}} "
            f"in {len(violations)} location(s):\n" + "\n".join(f"  - {v}" for v in violations)
        )


# ---------------------------------------------------------------------------
# Behavioral regression: every new ZIA delete tool enforces HMAC confirmation
# ---------------------------------------------------------------------------


class TestNewZIADeleteToolsConfirmation:
    """End-to-end verification that the four new ZIA rule-delete tools
    (cloud_firewall_dns, cloud_firewall_ips, file_type_control, sandbox)
    refuse to call the SDK without a valid, resource-bound confirmation token.

    The static analyzer above guarantees we don't pass empty {} to
    check_confirmation; this suite proves the wiring actually fires at
    runtime so a future refactor that drops the call will fail loudly.
    """

    DELETE_TOOLS = [
        (
            "zscaler_mcp.tools.zia.cloud_firewall_dns_rules",
            "zia_delete_cloud_firewall_dns_rule",
            "cloud_firewall_dns",
        ),
        (
            "zscaler_mcp.tools.zia.cloud_firewall_ips_rules",
            "zia_delete_cloud_firewall_ips_rule",
            "cloud_firewall_ips",
        ),
        (
            "zscaler_mcp.tools.zia.file_type_control_rules",
            "zia_delete_file_type_control_rule",
            "file_type_control_rule",
        ),
        (
            "zscaler_mcp.tools.zia.sandbox_rules",
            "zia_delete_sandbox_rule",
            "sandbox_rules",
        ),
    ]

    @staticmethod
    def _patched_client(sdk_attr):
        """Return a MagicMock client + the inner delete_rule mock, wired so
        ``client.zia.<sdk_attr>.delete_rule(rule_id)`` returns ``(None, None, None)``.
        """
        from unittest.mock import MagicMock

        delete_rule = MagicMock(return_value=(None, None, None))
        sdk_resource = MagicMock(delete_rule=delete_rule)
        client = MagicMock()
        setattr(client.zia, sdk_attr, sdk_resource)
        return client, delete_rule

    def test_all_new_delete_tools_block_without_confirmation(self):
        """No confirmation token => returns confirmation prompt, never calls SDK."""
        import importlib

        for module_path, fn_name, sdk_attr in self.DELETE_TOOLS:
            mod = importlib.import_module(module_path)
            fn = getattr(mod, fn_name)
            client, delete_rule = self._patched_client(sdk_attr)

            with patch.dict(os.environ, {}, clear=False), patch(
                f"{module_path}.get_zscaler_client", return_value=client
            ):
                result = fn(rule_id="42")

            assert isinstance(result, str), f"{fn_name} must return a string prompt"
            assert "confirm" in result.lower(), (
                f"{fn_name} prompt must mention confirmation; got: {result[:120]}"
            )
            delete_rule.assert_not_called(), (
                f"{fn_name} called SDK delete_rule() without a confirmation token!"
            )

    def test_all_new_delete_tools_reject_token_for_different_rule_id(self):
        """Token bound to rule X must NOT authorize deletion of rule Y (CWE-345)."""
        import importlib
        import json

        for module_path, fn_name, sdk_attr in self.DELETE_TOOLS:
            mod = importlib.import_module(module_path)
            fn = getattr(mod, fn_name)
            client, delete_rule = self._patched_client(sdk_attr)

            decoy_token = _generate_token(fn_name, {"rule_id": "DECOY"})

            with patch(f"{module_path}.get_zscaler_client", return_value=client):
                result = fn(
                    rule_id="TARGET",
                    kwargs=json.dumps({"confirmation_token": decoy_token}),
                )

            assert isinstance(result, str)
            assert "rejected" in result.lower() or "confirm" in result.lower(), (
                f"{fn_name} must reject decoy token; got: {result[:120]}"
            )
            delete_rule.assert_not_called(), (
                f"{fn_name} called SDK delete_rule() with a cross-resource token!"
            )

    def test_all_new_delete_tools_proceed_with_valid_token(self):
        """Valid resource-bound token => SDK delete_rule is invoked exactly once."""
        import importlib
        import json

        for module_path, fn_name, sdk_attr in self.DELETE_TOOLS:
            mod = importlib.import_module(module_path)
            fn = getattr(mod, fn_name)
            client, delete_rule = self._patched_client(sdk_attr)

            valid_token = _generate_token(fn_name, {"rule_id": "42"})

            with patch(f"{module_path}.get_zscaler_client", return_value=client):
                result = fn(
                    rule_id="42",
                    kwargs=json.dumps({"confirmation_token": valid_token}),
                )

            assert "deleted successfully" in result, (
                f"{fn_name} should return success message; got: {result[:120]}"
            )
            delete_rule.assert_called_once_with("42")
