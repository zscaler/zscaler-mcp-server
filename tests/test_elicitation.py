"""Tests for the HMAC write-confirmation layer (security/elicitation.py)."""

from __future__ import annotations

import time

import pytest

from zscaler_mcp.security import elicitation as el


@pytest.fixture(autouse=True)
def _clean_single_use_ledger():
    """Isolate the single-use ledger between tests.

    The ledger is process-global by design, so without this a token minted in
    one test could collide with another's (and ordering would matter).
    """
    el._reset_consumed_for_testing()
    yield
    el._reset_consumed_for_testing()


def _token_from(msg: str) -> str:
    """Pull the confirmation token out of a confirmation message."""
    return msg.split('"confirmation_token": "', 1)[1].split('"', 1)[0]


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


class TestSingleUse:
    """A confirmation authorizes exactly one execution.

    Regression guard: three user-facing docs claimed tokens were single-use
    while no ledger existed in any released version — a valid token was
    replayable for the whole TTL window.
    """

    def test_token_cannot_be_redeemed_twice(self):
        params = {"group_id": "216196257331405654"}
        token = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))

        assert el.check_confirmation("zpa_delete_segment_group", token, params) is None

        replayed = el.check_confirmation("zpa_delete_segment_group", token, params)
        assert replayed is not None
        assert "already been used" in replayed
        # The rejection still hands back a fresh token so the user can re-approve.
        assert "confirmation_token" in replayed

    def test_replacement_token_works_after_replay_rejection(self):
        params = {"group_id": "42"}
        first = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))
        assert el.check_confirmation("zpa_delete_segment_group", first, params) is None

        rejected = el.check_confirmation("zpa_delete_segment_group", first, params)
        second = _token_from(rejected)
        assert second != first
        assert el.check_confirmation("zpa_delete_segment_group", second, params) is None

    def test_tokens_are_unique_per_issue(self):
        """Each issued token must be distinct even for identical inputs.

        Tokens used to be a pure function of (tool, params, expiry-second). Once
        single-use tracking exists that is a bug: a re-issued token would be
        born already spent. A nonce makes every issue unique.
        """
        params = {"group_id": "42"}
        a = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))
        b = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))
        assert a != b

    def test_same_operation_can_be_performed_twice_in_one_ttl_window(self):
        """Single-use must not become 'once per TTL per operation'."""
        params = {"group_id": "42"}
        for _ in range(2):
            token = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))
            assert el.check_confirmation("zpa_delete_segment_group", token, params) is None

    def test_failed_verification_does_not_spend_the_token(self):
        """A wrong-params attempt must not burn the real token.

        Otherwise anyone able to submit a guess could deny a legitimate
        approval by forcing it to be consumed.
        """
        params = {"group_id": "42"}
        token = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))

        assert el.check_confirmation("zpa_delete_segment_group", token, {"group_id": "99"})
        # The genuine redemption still succeeds.
        assert el.check_confirmation("zpa_delete_segment_group", token, params) is None

    def test_expired_entries_are_swept(self, monkeypatch):
        params = {"group_id": "42"}
        token = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))
        assert el.check_confirmation("zpa_delete_segment_group", token, params) is None
        assert el._consumed_signatures

        real_time = time.time
        monkeypatch.setattr(
            el.time, "time", lambda: real_time() + el.CONFIRMATION_TOKEN_TTL_SECONDS + 10
        )
        # Any later write sweeps entries that are past their expiry.
        el._consume_signature("unrelated", real_time() + 999)
        assert len(el._consumed_signatures) == 1


class TestSigningKey:
    """The signing key must be shareable so multi-replica deployments work."""

    def test_defaults_to_ephemeral(self, monkeypatch):
        monkeypatch.delenv(el.SECRET_ENV_VAR, raising=False)
        assert el.uses_shared_secret() is False
        assert el._server_secret() == el._EPHEMERAL_SECRET

    def test_shared_secret_is_used_when_set(self, monkeypatch):
        monkeypatch.setenv(el.SECRET_ENV_VAR, "shared-key")
        assert el.uses_shared_secret() is True
        assert el._server_secret() != el._EPHEMERAL_SECRET

    def test_blank_secret_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv(el.SECRET_ENV_VAR, "   ")
        assert el.uses_shared_secret() is False

    def test_token_validates_across_processes_with_shared_secret(self, monkeypatch):
        """The multi-replica fix: mint under one process, verify under another.

        A different process is simulated by swapping the module's ephemeral key,
        which is exactly what differs between two replicas. With a shared secret
        configured, the ephemeral key is not consulted, so the token still
        verifies — this is the case that previously failed.
        """
        monkeypatch.setenv(el.SECRET_ENV_VAR, "shared-across-replicas")
        params = {"group_id": "42"}
        token = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))

        monkeypatch.setattr(el, "_EPHEMERAL_SECRET", b"a-different-process-key" * 2)
        assert el.check_confirmation("zpa_delete_segment_group", token, params) is None

    def test_token_does_not_validate_across_processes_without_shared_secret(self, monkeypatch):
        """Documents the default limitation the startup warning calls out."""
        monkeypatch.delenv(el.SECRET_ENV_VAR, raising=False)
        params = {"group_id": "42"}
        token = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))

        monkeypatch.setattr(el, "_EPHEMERAL_SECRET", b"a-different-process-key" * 2)
        out = el.check_confirmation("zpa_delete_segment_group", token, params)
        assert out is not None
        assert "does not match" in out

    def test_rotating_the_shared_secret_invalidates_old_tokens(self, monkeypatch):
        monkeypatch.setenv(el.SECRET_ENV_VAR, "key-v1")
        params = {"group_id": "42"}
        token = _token_from(el.check_confirmation("zpa_delete_segment_group", None, params))

        monkeypatch.setenv(el.SECRET_ENV_VAR, "key-v2")
        out = el.check_confirmation("zpa_delete_segment_group", token, params)
        assert out is not None
        assert "does not match" in out


class TestPostureLogging:
    """Operators must be told when the posture has a caveat."""

    def test_warns_on_http_without_shared_secret(self, monkeypatch, caplog):
        monkeypatch.delenv(el.SECRET_ENV_VAR, raising=False)
        monkeypatch.delenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", raising=False)
        with caplog.at_level("WARNING"):
            el.log_confirmation_posture("streamable-http")
        assert el.SECRET_ENV_VAR in caplog.text
        assert "EPHEMERAL" in caplog.text

    def test_no_warning_on_stdio(self, monkeypatch, caplog):
        monkeypatch.delenv(el.SECRET_ENV_VAR, raising=False)
        monkeypatch.delenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", raising=False)
        with caplog.at_level("WARNING"):
            el.log_confirmation_posture("stdio")
        assert "EPHEMERAL" not in caplog.text

    def test_no_warning_on_http_with_shared_secret(self, monkeypatch, caplog):
        monkeypatch.setenv(el.SECRET_ENV_VAR, "shared")
        monkeypatch.delenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", raising=False)
        with caplog.at_level("WARNING"):
            el.log_confirmation_posture("streamable-http")
        assert "EPHEMERAL" not in caplog.text

    def test_warns_loudly_when_confirmations_are_skipped(self, monkeypatch, caplog):
        monkeypatch.setenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", "true")
        with caplog.at_level("WARNING"):
            el.log_confirmation_posture("stdio")
        assert "DISABLED" in caplog.text


def test_resource_identifier_priority_and_fallback():
    # Explicit id/name win over *_id.
    assert el._resource_identifier({"id": "42", "group_id": "9"}) == "42"
    assert el._resource_identifier({"name": "HQ", "rule_id": "9"}) == "HQ"
    # First *_id (sorted) when no id/name.
    assert el._resource_identifier({"group_id": "9"}) == "9 (group_id)"
    assert el._resource_identifier({"segment_id": "7", "rule_id": "3"}) == "3 (rule_id)"
    # Nothing usable.
    assert el._resource_identifier({"enabled": True}) == "unknown"
