"""Tests for native MCP 2026-07-28 InputRequiredResult elicitation (P3).

Covers the nine test cases enumerated in the P3 section of
``local_dev/mcp-protocol-spec/mcp-2026-07-28-impact-analysis.md``,
plus assertions for cross-instance verification (shared secret),
tamper detection at the bit level, and the dual-mode dispatcher
inside :func:`zscaler_mcp.common.elicitation.check_confirmation`.

The native module is opt-in via ``ZSCALER_MCP_NATIVE_ELICITATION=true``.
Most tests patch that env var on, but a few intentionally leave it off
to exercise the legacy fallback path.
"""

import base64
import importlib
import json
import os
import time
from unittest.mock import patch

import pytest

import zscaler_mcp.common.elicitation as elicitation
import zscaler_mcp.common.elicitation_native as native


# ---------------------------------------------------------------------------
# Module reload helper — the shared secret is captured at import time, so
# tests that simulate "another server replica" need a fresh import.
# ---------------------------------------------------------------------------


def _reload_native(env: dict) -> "object":
    """Reload elicitation_native with a controlled environment.

    Returns the freshly-loaded module so the caller can hold a reference
    to the *other* replica's signing key. Use sparingly — module
    reloads are global state.
    """
    with patch.dict(os.environ, env, clear=False):
        return importlib.reload(native)


@pytest.fixture(autouse=True)
def _reset_native_module():
    """Snap elicitation_native back to a clean per-process state after
    every test so the module-level secret doesn't leak across cases."""
    yield
    # Strip any test-injected env vars that the module captures at import.
    for var in (
        "ZSCALER_MCP_NATIVE_ELICITATION",
        "ZSCALER_MCP_ELICITATION_SECRET",
        "ZSCALER_MCP_SKIP_CONFIRMATIONS",
        "ZSCALER_MCP_CONFIRMATION_TTL",
    ):
        os.environ.pop(var, None)
    importlib.reload(native)


# ===========================================================================
# is_native_elicitation_enabled — opt-in env var
# ===========================================================================


class TestNativeElicitationDetection:
    def test_disabled_by_default(self):
        assert native.is_native_elicitation_enabled() is False

    def test_enabled_when_env_true(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "true"}):
            assert native.is_native_elicitation_enabled() is True

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "TRUE"}):
            assert native.is_native_elicitation_enabled() is True
        with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "True"}):
            assert native.is_native_elicitation_enabled() is True

    def test_other_values_disable(self):
        for v in ("false", "1", "yes", "on", "", "no"):
            with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": v}):
                assert native.is_native_elicitation_enabled() is False, f"value={v!r}"


# ===========================================================================
# T1: test_delete_tool_returns_input_required_result
# Spec shape (SEP-2322).
# ===========================================================================


class TestInputRequiredResultShape:
    """The dict shape returned to the agent must match SEP-2322 exactly."""

    def test_has_required_top_level_fields(self):
        r = native.build_input_required_result(
            "zpa_delete_segment_group", {"group_id": "12345"}
        )
        assert r["resultType"] == "inputRequired"
        assert isinstance(r["inputRequests"], list)
        assert len(r["inputRequests"]) >= 1
        assert isinstance(r["requestState"], str)
        assert r["requestState"]

    def test_input_request_has_confirm_boolean(self):
        r = native.build_input_required_result(
            "zpa_delete_segment_group", {"group_id": "12345"}
        )
        req = r["inputRequests"][0]
        assert req["name"] == "confirm"
        assert req["required"] is True
        assert req["schema"]["type"] == "boolean"
        assert isinstance(req["schema"]["description"], str)
        assert req["schema"]["description"]

    def test_delete_prompt_mentions_resource_and_id(self):
        r = native.build_input_required_result(
            "zpa_delete_segment_group", {"group_id": "12345"}
        )
        desc = r["inputRequests"][0]["schema"]["description"]
        assert "DESTRUCTIVE" in desc
        assert "12345" in desc
        assert "cannot be undone" in desc.lower()

    def test_create_prompt_mentions_name(self):
        r = native.build_input_required_result(
            "zpa_create_segment_group", {"name": "Prod-VPN-Group"}
        )
        desc = r["inputRequests"][0]["schema"]["description"]
        assert "create" in desc.lower()
        assert "Prod-VPN-Group" in desc

    def test_update_prompt_mentions_id(self):
        r = native.build_input_required_result(
            "zpa_update_segment_group", {"id": "98765"}
        )
        desc = r["inputRequests"][0]["schema"]["description"]
        assert "update" in desc.lower()
        assert "98765" in desc

    def test_legacy_message_field_present_for_dual_render(self):
        """The ``_legacy_message`` field is the same text as the schema
        description — clients without native UI can still render it."""
        r = native.build_input_required_result("zpa_delete_segment_group", {"id": "1"})
        assert r["_legacy_message"] == r["inputRequests"][0]["schema"]["description"]

    def test_prompt_override(self):
        r = native.build_input_required_result(
            "zpa_delete_segment_group",
            {"id": "1"},
            prompt="Custom prompt text",
        )
        assert r["inputRequests"][0]["schema"]["description"] == "Custom prompt text"
        assert r["_legacy_message"] == "Custom prompt text"

    def test_prompt_prefix_prepended(self):
        r = native.build_input_required_result(
            "zpa_delete_segment_group",
            {"id": "1"},
            prompt_prefix="Previous request rejected: expired.\n",
        )
        desc = r["inputRequests"][0]["schema"]["description"]
        assert desc.startswith("Previous request rejected: expired.\n")

    def test_request_state_is_url_safe_base64(self):
        r = native.build_input_required_result("zpa_delete_segment_group", {"id": "1"})
        state = r["requestState"]
        # URL-safe base64 alphabet — no `+`, `/`, or `=` (we strip padding).
        for ch in state:
            assert ch.isalnum() or ch in ("-", "_"), f"non-url-safe char: {ch!r}"


# ===========================================================================
# T2: test_delete_tool_confirms_with_input_response — happy path round-trip
# ===========================================================================


class TestRequestStateRoundTrip:
    def test_generate_then_verify_same_params_succeeds(self):
        params = {"group_id": "12345"}
        state = native._build_request_state("zpa_delete_segment_group", params)
        ok, err = native._verify_request_state(state, "zpa_delete_segment_group", params)
        assert ok is True
        assert err is None

    def test_check_input_response_happy_path(self):
        params = {"group_id": "12345"}
        r = native.build_input_required_result("zpa_delete_segment_group", params)
        ok, err = native.check_input_response(
            "zpa_delete_segment_group",
            params,
            input_responses={"confirm": True},
            request_state=r["requestState"],
        )
        assert ok is True
        assert err is None

    def test_check_input_response_rejects_confirm_false(self):
        params = {"group_id": "12345"}
        r = native.build_input_required_result("zpa_delete_segment_group", params)
        ok, err = native.check_input_response(
            "zpa_delete_segment_group",
            params,
            input_responses={"confirm": False},
            request_state=r["requestState"],
        )
        assert ok is False
        assert "did not confirm" in err.lower()

    def test_check_input_response_rejects_missing_input(self):
        params = {"group_id": "12345"}
        r = native.build_input_required_result("zpa_delete_segment_group", params)
        ok, err = native.check_input_response(
            "zpa_delete_segment_group",
            params,
            input_responses=None,
            request_state=r["requestState"],
        )
        assert ok is False
        assert "missing inputresponses" in err.lower()

    def test_check_input_response_rejects_missing_state(self):
        params = {"group_id": "12345"}
        ok, err = native.check_input_response(
            "zpa_delete_segment_group",
            params,
            input_responses={"confirm": True},
            request_state=None,
        )
        assert ok is False
        assert "missing requeststate" in err.lower()


# ===========================================================================
# T3: test_request_state_is_tamper_proof
# ===========================================================================


class TestRequestStateTampering:
    """Any mutation to args, blob, or signature must invalidate."""

    def test_args_swap_rejected(self):
        original = {"group_id": "12345"}
        tampered = {"group_id": "99999"}
        state = native._build_request_state("zpa_delete_segment_group", original)
        ok, err = native._verify_request_state(
            state, "zpa_delete_segment_group", tampered
        )
        assert ok is False
        assert "does not match" in err.lower()

    def test_tool_name_swap_rejected(self):
        params = {"id": "1"}
        state = native._build_request_state("zpa_delete_segment_group", params)
        ok, err = native._verify_request_state(state, "zpa_delete_server_group", params)
        assert ok is False
        assert "does not match" in err.lower()

    def test_extra_arg_added_rejected(self):
        original = {"group_id": "12345"}
        tampered = {"group_id": "12345", "force": True}
        state = native._build_request_state("zpa_delete_segment_group", original)
        ok, err = native._verify_request_state(
            state, "zpa_delete_segment_group", tampered
        )
        assert ok is False
        assert "does not match" in err.lower()

    def test_arg_removed_rejected(self):
        original = {"group_id": "12345", "microtenant_id": "m1"}
        tampered = {"group_id": "12345"}
        state = native._build_request_state("zpa_delete_segment_group", original)
        ok, err = native._verify_request_state(
            state, "zpa_delete_segment_group", tampered
        )
        assert ok is False

    def test_signature_byte_flip_rejected(self):
        """Flip one bit in the decoded blob's signature — must fail."""
        state = native._build_request_state("zpa_delete_segment_group", {"id": "1"})
        decoded = native._b64url_decode(state).decode("utf-8")
        version, expiry, sig = decoded.split(".", 2)
        # Flip the last hex digit of the signature.
        flipped_sig = sig[:-1] + ("0" if sig[-1] != "0" else "1")
        tampered = native._b64url_encode(
            f"{version}.{expiry}.{flipped_sig}".encode("utf-8")
        )
        ok, err = native._verify_request_state(
            tampered, "zpa_delete_segment_group", {"id": "1"}
        )
        assert ok is False
        assert "does not match" in err.lower()

    def test_expiry_extended_rejected(self):
        """Push the expiry forward — the new expiry doesn't appear in the
        signature, so the HMAC won't match."""
        state = native._build_request_state("zpa_delete_segment_group", {"id": "1"})
        decoded = native._b64url_decode(state).decode("utf-8")
        version, expiry, sig = decoded.split(".", 2)
        future_expiry = int(expiry) + 1_000_000
        tampered = native._b64url_encode(
            f"{version}.{future_expiry}.{sig}".encode("utf-8")
        )
        ok, err = native._verify_request_state(
            tampered, "zpa_delete_segment_group", {"id": "1"}
        )
        assert ok is False
        assert "does not match" in err.lower()

    def test_invalid_base64_rejected(self):
        ok, err = native._verify_request_state(
            "not!valid!base64!", "zpa_delete_segment_group", {"id": "1"}
        )
        assert ok is False
        assert "malformed" in err.lower()

    def test_wrong_version_rejected(self):
        decoded = "v999.9999999999.deadbeef"
        bad_state = native._b64url_encode(decoded.encode("utf-8"))
        ok, err = native._verify_request_state(
            bad_state, "zpa_delete_segment_group", {"id": "1"}
        )
        assert ok is False
        assert "version" in err.lower()

    def test_wrong_field_count_rejected(self):
        decoded = "only.two"
        bad_state = native._b64url_encode(decoded.encode("utf-8"))
        ok, err = native._verify_request_state(
            bad_state, "zpa_delete_segment_group", {"id": "1"}
        )
        assert ok is False
        assert "wrong field count" in err.lower()

    def test_empty_state_rejected(self):
        ok, err = native._verify_request_state("", "zpa_delete_segment_group", {"id": "1"})
        assert ok is False
        assert "missing" in err.lower() or "empty" in err.lower()


# ===========================================================================
# T4: test_request_state_ttl_expiry
# ===========================================================================


class TestRequestStateExpiry:
    def test_expired_state_rejected(self):
        """Mock time so the verifier sees the blob as past its expiry."""
        params = {"group_id": "12345"}
        state = native._build_request_state("zpa_delete_segment_group", params)

        # Jump 1 hour forward — well beyond the 5-minute default TTL.
        with patch.object(native.time, "time", return_value=time.time() + 3600):
            ok, err = native._verify_request_state(
                state, "zpa_delete_segment_group", params
            )
        assert ok is False
        assert "expired" in err.lower()

    def test_fresh_state_inside_ttl_accepted(self):
        params = {"group_id": "12345"}
        state = native._build_request_state("zpa_delete_segment_group", params)
        # 30 seconds later — well inside the 5-minute TTL.
        with patch.object(native.time, "time", return_value=time.time() + 30):
            ok, err = native._verify_request_state(
                state, "zpa_delete_segment_group", params
            )
        assert ok is True


# ===========================================================================
# T5: test_skip_confirmations_bypasses_elicitation
# ===========================================================================


class TestSkipConfirmationsBypass:
    """``ZSCALER_MCP_SKIP_CONFIRMATIONS=true`` short-circuits both flows."""

    def test_skip_returns_none_in_native_mode(self):
        with patch.dict(
            os.environ,
            {
                "ZSCALER_MCP_NATIVE_ELICITATION": "true",
                "ZSCALER_MCP_SKIP_CONFIRMATIONS": "true",
            },
        ):
            result = elicitation.check_confirmation(
                "zpa_delete_segment_group", None, {"group_id": "12345"}
            )
        assert result is None

    def test_skip_returns_none_in_legacy_mode(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_SKIP_CONFIRMATIONS": "true"}):
            result = elicitation.check_confirmation(
                "zpa_delete_segment_group", None, {"group_id": "12345"}
            )
        assert result is None


# ===========================================================================
# T6: test_hmac_fallback_for_old_clients
# Native mode is enabled but the agent sends a legacy ``confirmation_token``.
# The legacy path must still work — the SEP-2596 deprecation window
# requires 12 months of backward compatibility.
# ===========================================================================


class TestLegacyFallbackStillWorks:
    def test_legacy_token_accepted_in_native_mode(self):
        params = {"group_id": "12345"}
        # First, generate a legacy HMAC token (as the server would on
        # a first call BEFORE native mode was switched on).
        legacy_token = elicitation._generate_token("zpa_delete_segment_group", params)

        # Now flip native mode ON and re-call with the legacy token.
        # This is the scenario where an operator upgrades the server but
        # an older client hasn't migrated yet.
        with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "true"}):
            kwargs_str = json.dumps({"confirmation_token": legacy_token})
            confirmed = elicitation.extract_confirmed_from_kwargs(kwargs_str)
            # The legacy token should NOT be wrapped in the native sentinel.
            assert not confirmed.startswith(elicitation._NATIVE_SENTINEL_PREFIX)
            result = elicitation.check_confirmation(
                "zpa_delete_segment_group", confirmed, params
            )
        assert result is None, "Legacy HMAC token must still work in native mode"

    def test_invalid_legacy_token_in_native_mode_reissues_native(self):
        """A legacy retry that fails should re-prompt the agent in native
        mode (forward migration), not legacy mode."""
        params = {"group_id": "12345"}
        with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "true"}):
            result = elicitation.check_confirmation(
                "zpa_delete_segment_group",
                "1234:obviously-bogus-signature",
                params,
            )
        assert isinstance(result, dict)
        assert result["resultType"] == "inputRequired"
        desc = result["inputRequests"][0]["schema"]["description"]
        assert "rejected" in desc.lower()


# ===========================================================================
# T7: test_input_required_schema_types
# JSON Schema 2020-12 types in inputRequests must be correct.
# ===========================================================================


class TestInputRequestsSchemaTypes:
    def test_confirm_uses_boolean_schema(self):
        r = native.build_input_required_result("zpa_delete_segment_group", {"id": "1"})
        schema = r["inputRequests"][0]["schema"]
        assert schema["type"] == "boolean"
        # The description is REQUIRED by SEP-2322 so the client can render
        # a meaningful prompt.
        assert "description" in schema and schema["description"]

    def test_inputrequests_is_array(self):
        """Even when there's a single input, ``inputRequests`` is an
        array — clients should iterate, not key-access."""
        r = native.build_input_required_result("zpa_delete_segment_group", {"id": "1"})
        assert isinstance(r["inputRequests"], list)

    def test_input_request_has_name_and_required(self):
        r = native.build_input_required_result("zpa_delete_segment_group", {"id": "1"})
        req = r["inputRequests"][0]
        assert "name" in req
        assert "required" in req
        assert isinstance(req["required"], bool)


# ===========================================================================
# T8: test_request_state_stateless_any_instance
# A requestState generated on replica A must verify on replica B when
# the shared secret is configured.
# ===========================================================================


class TestSharedSecretAcrossInstances:
    SHARED = "test-shared-secret-32-bytes-min-padding-xx"

    def test_state_from_replica_a_verifies_on_replica_b(self):
        """Two server instances with the same shared secret — issuance
        on one, verification on the other."""
        # Replica A boots with the shared secret and issues a state.
        replica_a = _reload_native({"ZSCALER_MCP_ELICITATION_SECRET": self.SHARED})
        params = {"group_id": "12345"}
        state = replica_a._build_request_state("zpa_delete_segment_group", params)

        # Replica B (same secret) verifies — must succeed.
        replica_b = _reload_native({"ZSCALER_MCP_ELICITATION_SECRET": self.SHARED})
        ok, err = replica_b._verify_request_state(
            state, "zpa_delete_segment_group", params
        )
        assert ok is True, f"Cross-instance verify failed: {err}"

    def test_state_does_not_verify_on_different_secret(self):
        """Two replicas with *different* secrets must NOT cross-verify."""
        replica_a = _reload_native({"ZSCALER_MCP_ELICITATION_SECRET": self.SHARED})
        params = {"group_id": "12345"}
        state = replica_a._build_request_state("zpa_delete_segment_group", params)

        replica_b = _reload_native(
            {"ZSCALER_MCP_ELICITATION_SECRET": "a-completely-different-secret"}
        )
        ok, err = replica_b._verify_request_state(
            state, "zpa_delete_segment_group", params
        )
        assert ok is False
        assert "does not match" in err.lower()

    def test_state_does_not_verify_when_only_one_has_secret(self):
        """Replica A has the shared secret, replica B does not — verify
        must fail (B has its own per-process random key)."""
        replica_a = _reload_native({"ZSCALER_MCP_ELICITATION_SECRET": self.SHARED})
        params = {"group_id": "12345"}
        state = replica_a._build_request_state("zpa_delete_segment_group", params)

        # Replica B without shared secret — gets a per-process random key.
        replica_b = _reload_native({})  # no ZSCALER_MCP_ELICITATION_SECRET
        ok, _ = replica_b._verify_request_state(
            state, "zpa_delete_segment_group", params
        )
        assert ok is False


# ===========================================================================
# T9: test_all_delete_tools_use_native_elicitation
# When native mode is on, any tool currently using check_confirmation
# returns an InputRequiredResult dict on first call.
# ===========================================================================


class TestAllDestructiveToolsUseNative:
    """Spot-check: native mode is on, every common destructive-tool call
    pattern should yield an InputRequiredResult dict, not a string."""

    @pytest.fixture(autouse=True)
    def _enable_native(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "true"}):
            yield

    @pytest.mark.parametrize(
        "tool_name,params",
        [
            ("zpa_delete_segment_group", {"group_id": "1"}),
            ("zpa_delete_server_group", {"group_id": "1"}),
            ("zpa_delete_app_connector", {"connector_id": "1"}),
            ("zpa_delete_application_segment", {"segment_id": "1"}),
            ("zia_delete_url_filtering_rule", {"rule_id": "1"}),
            ("zia_delete_cloud_firewall_rule", {"rule_id": "1"}),
            ("zia_delete_ssl_inspection_rule", {"rule_id": "1"}),
            ("zia_delete_location", {"location_id": "1"}),
            ("zia_delete_static_ip", {"ip_id": "1"}),
        ],
    )
    def test_first_call_returns_input_required_result(self, tool_name, params):
        result = elicitation.check_confirmation(tool_name, None, params)
        assert isinstance(result, dict)
        assert result["resultType"] == "inputRequired"
        assert result["requestState"]
        assert result["inputRequests"][0]["name"] == "confirm"

    @pytest.mark.parametrize(
        "tool_name,params",
        [
            ("zpa_create_segment_group", {"name": "Prod-Group"}),
            ("zia_create_url_filtering_rule", {"name": "Block-Gambling"}),
        ],
    )
    def test_create_tools_also_use_native(self, tool_name, params):
        result = elicitation.check_confirmation(tool_name, None, params)
        assert isinstance(result, dict)
        assert result["resultType"] == "inputRequired"


# ===========================================================================
# End-to-end dispatch through check_confirmation
# Covers the full agent <-> server round-trip via the kwargs transport.
# ===========================================================================


class TestEndToEndDispatch:
    """The dispatcher inside elicitation.check_confirmation glues the
    new kwargs-shape extractor to the native verifier. Exercise both
    legs of the round-trip with the actual public surface."""

    @pytest.fixture(autouse=True)
    def _enable_native(self):
        with patch.dict(os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "true"}):
            yield

    def test_first_call_then_confirmed_retry(self):
        params = {"group_id": "12345"}

        # Leg 1: first call, no confirmation in kwargs → InputRequiredResult.
        first = elicitation.check_confirmation("zpa_delete_segment_group", None, params)
        assert isinstance(first, dict)
        request_state = first["requestState"]

        # Leg 2: agent re-calls with the answers + echoed requestState.
        retry_kwargs = json.dumps(
            {"inputResponses": {"confirm": True}, "requestState": request_state}
        )
        confirmed = elicitation.extract_confirmed_from_kwargs(retry_kwargs)
        assert confirmed.startswith(elicitation._NATIVE_SENTINEL_PREFIX)

        second = elicitation.check_confirmation(
            "zpa_delete_segment_group", confirmed, params
        )
        assert second is None, "Retry with valid native confirmation must let the call proceed"

    def test_first_call_then_unconfirmed_retry(self):
        params = {"group_id": "12345"}
        first = elicitation.check_confirmation("zpa_delete_segment_group", None, params)
        request_state = first["requestState"]

        # Agent re-calls with confirm=False — must be rejected.
        kwargs = json.dumps(
            {"inputResponses": {"confirm": False}, "requestState": request_state}
        )
        confirmed = elicitation.extract_confirmed_from_kwargs(kwargs)
        second = elicitation.check_confirmation(
            "zpa_delete_segment_group", confirmed, params
        )
        assert isinstance(second, dict), "Unconfirmed retry must re-prompt"
        assert second["resultType"] == "inputRequired"
        desc = second["inputRequests"][0]["schema"]["description"]
        assert "rejected" in desc.lower()

    def test_first_call_then_tampered_args_retry(self):
        """Agent issues retry with different args than the original
        request — requestState HMAC won't match."""
        original_params = {"group_id": "12345"}
        first = elicitation.check_confirmation(
            "zpa_delete_segment_group", None, original_params
        )
        request_state = first["requestState"]

        kwargs = json.dumps(
            {"inputResponses": {"confirm": True}, "requestState": request_state}
        )
        confirmed = elicitation.extract_confirmed_from_kwargs(kwargs)

        # Note the SWAPPED group_id.
        tampered_params = {"group_id": "99999"}
        second = elicitation.check_confirmation(
            "zpa_delete_segment_group", confirmed, tampered_params
        )
        assert isinstance(second, dict)
        desc = second["inputRequests"][0]["schema"]["description"]
        assert "rejected" in desc.lower()
        assert "does not match" in desc.lower() or "parameters" in desc.lower()

    def test_first_call_then_missing_request_state(self):
        """Agent sends inputResponses without echoing requestState."""
        params = {"group_id": "12345"}
        elicitation.check_confirmation("zpa_delete_segment_group", None, params)

        kwargs = json.dumps({"inputResponses": {"confirm": True}})  # no requestState
        confirmed = elicitation.extract_confirmed_from_kwargs(kwargs)
        second = elicitation.check_confirmation(
            "zpa_delete_segment_group", confirmed, params
        )
        assert isinstance(second, dict)
        desc = second["inputRequests"][0]["schema"]["description"]
        assert "rejected" in desc.lower()

    def test_legacy_mode_still_returns_string(self):
        """With native mode OFF, the first-call response is the legacy
        prose message — proving the dispatcher honors the opt-in."""
        with patch.dict(
            os.environ, {"ZSCALER_MCP_NATIVE_ELICITATION": "false"}, clear=False
        ):
            result = elicitation.check_confirmation(
                "zpa_delete_segment_group", None, {"group_id": "12345"}
            )
        assert isinstance(result, str)
        assert "DESTRUCTIVE" in result.upper() or "DELETE" in result.upper()


# ===========================================================================
# Native kwargs-shape parser
# ===========================================================================


class TestExtractNativeInputsFromKwargs:
    def test_extracts_both_fields(self):
        kwargs = json.dumps({"inputResponses": {"confirm": True}, "requestState": "abc"})
        ir, rs = native.extract_native_inputs_from_kwargs(kwargs)
        assert ir == {"confirm": True}
        assert rs == "abc"

    def test_handles_dict_input(self):
        kwargs = {"inputResponses": {"confirm": True}, "requestState": "abc"}
        ir, rs = native.extract_native_inputs_from_kwargs(kwargs)
        assert ir == {"confirm": True}
        assert rs == "abc"

    def test_returns_none_pair_for_empty(self):
        assert native.extract_native_inputs_from_kwargs("") == (None, None)
        assert native.extract_native_inputs_from_kwargs("{}") == (None, None)
        assert native.extract_native_inputs_from_kwargs(None) == (None, None)

    def test_malformed_input_responses_dropped(self):
        kwargs = json.dumps({"inputResponses": "not-a-dict", "requestState": "abc"})
        ir, rs = native.extract_native_inputs_from_kwargs(kwargs)
        assert ir is None  # dropped
        assert rs == "abc"

    def test_malformed_request_state_dropped(self):
        kwargs = json.dumps({"inputResponses": {"confirm": True}, "requestState": 12345})
        ir, rs = native.extract_native_inputs_from_kwargs(kwargs)
        assert ir == {"confirm": True}
        assert rs is None

    def test_invalid_json_returns_none(self):
        ir, rs = native.extract_native_inputs_from_kwargs("not{valid:json")
        assert ir is None and rs is None


# ===========================================================================
# Legacy elicitation.extract_confirmed_from_kwargs precedence
# Native shape MUST win when both are present (agent is migrating).
# ===========================================================================


class TestExtractKwargsPrecedence:
    def test_native_wins_when_both_shapes_present(self):
        """If kwargs has BOTH inputResponses AND confirmation_token, the
        agent is mid-migration. The native shape takes precedence."""
        kwargs = json.dumps(
            {
                "inputResponses": {"confirm": True},
                "requestState": "xyz",
                "confirmation_token": "legacy-token",
            }
        )
        confirmed = elicitation.extract_confirmed_from_kwargs(kwargs)
        assert confirmed.startswith(elicitation._NATIVE_SENTINEL_PREFIX)

    def test_native_sentinel_is_decodable(self):
        kwargs = json.dumps(
            {"inputResponses": {"confirm": True}, "requestState": "xyz"}
        )
        confirmed = elicitation.extract_confirmed_from_kwargs(kwargs)
        encoded = confirmed[len(elicitation._NATIVE_SENTINEL_PREFIX):]
        padding = "=" * (-len(encoded) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(encoded + padding).decode("utf-8"))
        assert decoded == {"inputResponses": {"confirm": True}, "requestState": "xyz"}

    def test_native_shape_with_only_request_state(self):
        """Even with only requestState (no inputResponses), the agent
        is clearly using the native protocol."""
        kwargs = json.dumps({"requestState": "xyz"})
        confirmed = elicitation.extract_confirmed_from_kwargs(kwargs)
        assert confirmed.startswith(elicitation._NATIVE_SENTINEL_PREFIX)


# ===========================================================================
# Canonical-args symmetry — native vs legacy must bind the same surface.
# ===========================================================================


class TestCanonicalArgsSymmetry:
    """Both flows must canonicalize args the same way, or migration
    between them would silently invalidate tokens issued before the
    upgrade."""

    def test_excluded_keys_match(self):
        params = {
            "group_id": "1",
            "name": "foo",
            "confirmed": True,
            "confirmation_token": "x",
            "service": "zpa",
            "kwargs": "{}",
            "_internal": "hidden",
            "inputResponses": {"confirm": True},  # native field
            "requestState": "blob",  # native field
        }
        legacy = elicitation._canonical_payload("tool", params)
        new = native._canonical_args("tool", params)

        # The native canonicalizer should also drop confirmed/confirmation_token/
        # service/kwargs/underscore-keys. The new fields (inputResponses,
        # requestState) are NOT yet in the excluded set in either module —
        # they're intentionally part of the surface because the request
        # itself binds them via the HMAC blob, not the args dict.
        assert legacy == new, "Canonical args must match across flows"
        assert "confirmed" not in new
        assert "service" not in new
        assert "_internal" not in new

    def test_key_order_independent(self):
        params_a = {"z": 1, "a": 2, "m": 3}
        params_b = {"m": 3, "a": 2, "z": 1}
        assert native._canonical_args("tool", params_a) == native._canonical_args(
            "tool", params_b
        )

    def test_includes_tool_name_prefix(self):
        result = native._canonical_args("zpa_delete_segment_group", {"id": "1"})
        assert result.startswith("zpa_delete_segment_group:")
