"""Tests for the write-confirmation layer (security/elicitation.py).

Two confirmation paths live here and both are covered:

* native elicitation (SEP-2322) — the preferred path, where the client prompts a
  human and the answer arrives as a protocol field;
* the HMAC token exchange — the fallback for callers that cannot be prompted.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from mcp.types import ClientCapabilities, ElicitationCapability

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


def test_resource_identifier_priority_and_fallback():
    # Explicit id/name win over *_id.
    assert el._resource_identifier({"id": "42", "group_id": "9"}) == "42"
    assert el._resource_identifier({"name": "HQ", "rule_id": "9"}) == "HQ"
    # First *_id (sorted) when no id/name.
    assert el._resource_identifier({"group_id": "9"}) == "9 (group_id)"
    assert el._resource_identifier({"segment_id": "7", "rule_id": "3"}) == "3 (rule_id)"
    # Nothing usable.
    assert el._resource_identifier({"enabled": True}) == "unknown"


def test_describe_destructive_operation_names_the_resource():
    out = el.describe_destructive_operation("zpa_delete_segment_group", {"group_id": "7429"})
    assert "DELETE Segment Group" in out
    assert "7429" in out
    # No token leaks into the client-rendered prompt.
    assert "confirmation_token" not in out


# ---------------------------------------------------------------------------
# Native elicitation (SEP-2322)
# ---------------------------------------------------------------------------
#
# The server no longer *sends* the confirmation request: a DELETE tool declares a
# resolved parameter and the framework asks, using whichever transport the
# negotiated revision allows (`InputRequiredResult` on 2026-07-28, a mid-call
# request before it). So the units under test here are the three decisions we
# still own: whether this caller can be asked at all, what question to pose, and
# how to read the answer.

_TOOL = "zpa_delete_segment_group"
_PARAMS = {"group_id": "7429"}


class _FakeContext:
    """Stands in for an MCP ``Context``.

    ``client_capabilities`` is a property so the "no live request" case can raise
    exactly the way the real accessor does — reading it outside a bound request is
    an error, and the gate has to treat that as "nobody can be prompted".
    """

    def __init__(self, *, supports=True, session_raises=False):
        self._supports = supports
        self._session_raises = session_raises

    @property
    def client_capabilities(self):
        if self._session_raises:
            raise RuntimeError("no active request context")
        if self._supports is None:
            return None
        return ClientCapabilities(elicitation=ElicitationCapability() if self._supports else None)


class _Outcome:
    """One member of the ``ElicitationResult`` union."""

    def __init__(self, action: str, data=None):
        self.action = action
        self.data = data


def _accepted(choice: str) -> _Outcome:
    return _Outcome("accept", el.DeleteConfirmation(choice=choice))


def _fallback() -> _Outcome:
    """What the framework hands the body when the resolver declined to ask.

    A resolver's plain return value comes back wrapped in an accepted outcome, so
    the sentinel is only distinguishable by its payload — which is exactly what
    :func:`is_token_fallback` checks.
    """
    return _Outcome("accept", el.TOKEN_FALLBACK)


class TestElicitationAvailability:
    """Every negative answer must route to the token fallback, never to an error."""

    def test_no_context(self):
        assert el.elicitation_available(None) is False

    def test_no_active_session(self):
        assert el.elicitation_available(_FakeContext(session_raises=True)) is False

    def test_no_negotiated_capabilities(self):
        assert el.elicitation_available(_FakeContext(supports=None)) is False

    def test_client_without_capability(self):
        assert el.elicitation_available(_FakeContext(supports=False)) is False

    def test_capable_client(self):
        assert el.elicitation_available(_FakeContext(supports=True)) is True


class TestBuildConfirmationRequest:
    def test_names_the_resource_being_deleted(self):
        req = el.build_confirmation_request(_TOOL, _PARAMS)
        assert "7429" in req.message
        assert "Segment Group" in req.message

    def test_asks_via_a_schema_not_free_text(self):
        """The choices must be structured so the client can render real controls."""
        req = el.build_confirmation_request(_TOOL, _PARAMS)
        assert req.schema is el.DeleteConfirmation
        choices = el.DeleteConfirmation.model_json_schema()["properties"]["choice"]["enum"]
        assert sorted(choices) == ["cancel", "delete"]

    def test_carries_no_token(self):
        """Nothing redeemable may appear in a prompt a human reads."""
        assert "confirmation_token" not in el.build_confirmation_request(_TOOL, _PARAMS).message


class TestIsTokenFallback:
    def test_recognises_the_wrapped_sentinel(self):
        assert el.is_token_fallback(_fallback()) is True

    def test_recognises_the_bare_sentinel(self):
        assert el.is_token_fallback(el.TOKEN_FALLBACK) is True

    def test_a_real_approval_is_not_a_fallback(self):
        """The distinguishing feature is the payload type, not the action."""
        assert el.is_token_fallback(_accepted("delete")) is False

    def test_a_refusal_is_not_a_fallback(self):
        assert el.is_token_fallback(_Outcome("decline")) is False


class TestInterpretConfirmation:
    def test_approval_returns_none(self):
        assert el.interpret_confirmation(_accepted("delete"), _TOOL, _PARAMS) is None

    def test_choosing_cancel_blocks(self):
        out = el.interpret_confirmation(_accepted("cancel"), _TOOL, _PARAMS)
        assert out is not None and "NOT performed" in out

    def test_declined_blocks(self):
        out = el.interpret_confirmation(_Outcome("decline"), _TOOL, _PARAMS)
        assert out is not None and "NOT performed" in out

    def test_cancelled_blocks(self):
        out = el.interpret_confirmation(_Outcome("cancel"), _TOOL, _PARAMS)
        assert out is not None and "NOT performed" in out

    def test_refusal_names_the_resource(self):
        """The caller has to be able to tell WHICH delete did not happen."""
        out = el.interpret_confirmation(_Outcome("decline"), _TOOL, _PARAMS)
        assert "7429" in out

    def test_refusal_leaks_no_token(self):
        out = el.interpret_confirmation(_Outcome("decline"), _TOOL, _PARAMS)
        assert "confirmation_token" not in out

    @pytest.mark.parametrize(
        "outcome",
        [None, _Outcome("something-new"), _Outcome(None), object()],
        ids=["none", "unknown-action", "null-action", "not-an-outcome"],
    )
    def test_unrecognised_outcomes_fail_closed(self, outcome):
        """Anything we cannot read must be a refusal.

        This is the load-bearing default: a future protocol revision could add an
        outcome we do not know, and the wrong answer here silently approves
        deletions nobody confirmed.
        """
        out = el.interpret_confirmation(outcome, _TOOL, _PARAMS)
        assert out is not None and "NOT performed" in out


class TestGateDestructiveOperation:
    """The single entry point the bridge calls."""

    def test_approval_allows_the_operation(self):
        # No token supplied, yet the operation is allowed: proof the native answer
        # was honoured instead of the HMAC exchange.
        assert el.gate_destructive_operation(_accepted("delete"), _TOOL, _PARAMS, None) is None

    def test_refusal_blocks_without_issuing_a_token(self):
        out = el.gate_destructive_operation(_Outcome("decline"), _TOOL, _PARAMS, None)
        assert out is not None
        assert "confirmation_token" not in out

    def test_fallback_sentinel_routes_to_the_token_exchange(self):
        out = el.gate_destructive_operation(_fallback(), _TOOL, _PARAMS, None)
        assert out is not None
        assert "CONFIRMATION REQUIRED" in out
        # And the issued token still completes the fallback handshake.
        assert el.gate_destructive_operation(_fallback(), _TOOL, _PARAMS, _token_from(out)) is None

    def test_a_token_cannot_stand_in_for_a_refusal(self):
        """A supplied token must not override a human's "no".

        The two gates are alternatives, not a sequence: once a human has been asked
        and declined, a token the agent happens to hold is irrelevant.
        """
        out = el.gate_destructive_operation(_Outcome("decline"), _TOOL, _PARAMS, "any-token-at-all")
        assert out is not None and "NOT performed" in out

    def test_skip_env_bypasses_both_paths(self, monkeypatch):
        monkeypatch.setenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", "true")
        assert el.gate_destructive_operation(_Outcome("decline"), _TOOL, _PARAMS, None) is None


# =============================================================================
# Server-authoritative resource name in the confirmation prompt
# =============================================================================


class TestResourceNameInPrompt:
    """The prompt names the resource, and the lookup can never break the gate.

    A human approving `DELETE Segment Group — 999999991` cannot verify that is
    the right group; two ids differing by one digit look identical. The name has
    to come from the API (Zscaler deletes answer 204, so it is unavailable
    afterwards) — but fetching it costs a round trip inside a security gate, so
    the failure behaviour matters more than the happy path.
    """

    def test_name_is_shown_with_the_bare_id(self):
        from zscaler_mcp.security.elicitation import describe_destructive_operation

        out = describe_destructive_operation(
            "zpa_delete_segment_group", {"group_id": "7205"}, "Corp Apps"
        )
        # the id stays — it is the durable audit key — but without the noisy
        # "(group_id)" annotation that only exists to give a bare id context
        assert out == 'DELETE Segment Group — "Corp Apps" (7205)'

    def test_without_a_name_the_prompt_is_unchanged(self):
        from zscaler_mcp.security.elicitation import describe_destructive_operation

        assert describe_destructive_operation(
            "zpa_delete_segment_group", {"group_id": "7205"}
        ) == "DELETE Segment Group — 7205 (group_id)"

    def test_lookup_is_not_called_when_a_valid_token_lets_the_call_through(self):
        """The extra API call must never touch the happy path."""
        from zscaler_mcp.security import elicitation as e

        e._reset_consumed_for_testing()
        params = {"group_id": "7205"}
        token = e._generate_token("zpa_delete_segment_group", params)
        calls = []

        result = e.check_confirmation(
            "zpa_delete_segment_group", token, params, lambda: calls.append(1) or "X"
        )
        assert result is None
        assert calls == []

    def test_lookup_is_not_called_when_confirmations_are_skipped(self, monkeypatch):
        from zscaler_mcp.security import elicitation as e

        monkeypatch.setenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", "true")
        calls = []
        assert (
            e.check_confirmation(
                "zpa_delete_segment_group", None, {"group_id": "1"}, lambda: calls.append(1) or "X"
            )
            is None
        )
        assert calls == []

    def test_lookup_is_used_when_a_prompt_is_rendered(self):
        from zscaler_mcp.security import elicitation as e

        e._reset_consumed_for_testing()
        message = e.check_confirmation(
            "zpa_delete_segment_group", None, {"group_id": "7205"}, lambda: "Corp Apps"
        )
        assert message is not None
        assert '"Corp Apps" (7205)' in message

    def test_a_failing_lookup_degrades_to_the_id_and_never_raises(self):
        """Cosmetic lookup; the gate must survive a 404 / 403 / timeout."""
        from zscaler_mcp.registry.fastmcp_bridge import _resolve_resource_name
        from zscaler_mcp.registry.registry import REGISTRY
        from zscaler_mcp.server import build_server

        build_server(enable_write=True, write_allowlist=["*"])
        spec = REGISTRY.get("zpa_delete_segment_group")

        def exploding_client(*_a, **_kw):
            raise RuntimeError("403 forbidden")

        with patch(
            "zscaler_mcp.tools.zpa.segment_groups.get_zscaler_client", exploding_client
        ):
            assert _resolve_resource_name(spec, {"group_id": "7205"}) is None

    def test_delete_tools_without_a_get_counterpart_return_none(self):
        from zscaler_mcp.registry.fastmcp_bridge import _resolve_resource_name
        from zscaler_mcp.registry.registry import REGISTRY
        from zscaler_mcp.server import build_server

        build_server(enable_write=True, write_allowlist=["*"])
        # bulk deletes, URL-list deletes and ZTW's list-only resources have no
        # single-resource read; they keep the id-only prompt by design
        for name in ("zpa_bulk_delete_app_connectors", "zia_delete_auth_exempt_urls"):
            assert _resolve_resource_name(REGISTRY.get(name), {}) is None
