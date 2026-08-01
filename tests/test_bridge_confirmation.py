"""Bridge-level tests for the destructive-operation confirmation gate.

The unit behaviour of both confirmation paths lives in ``test_elicitation.py``.
What these tests pin is the *wiring*: that a DELETE tool built by the registry
bridge actually reaches the gate before it mutates anything, that the human is
asked over the protocol (SEP-2322) when the client can be prompted, and that it
falls back to the HMAC token exchange when it cannot.

The invariant that matters most: **the tool body must not run unless the gate
returns approval.** Each test asserts on a call-recording body rather than only
on the returned text, so a regression that mutates first and asks later fails
here instead of in production.

Two layers are covered deliberately:

* ``TestResolverWiring`` — the declarative plumbing (what the tool advertises,
  what the resolver decides). Cheap, and catches schema leaks.
* ``TestThroughAClient`` — a real MCP round trip over the in-memory transport,
  which is the only thing that proves the confirmation actually crosses the
  protocol on the negotiated revision. A unit test cannot: mid-call elicitation
  silently stopped working on 2026-07-28, and only a client-level test noticed.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp import Client
from mcp.server.mcpserver import Elicit, MCPServer
from mcp.types import ElicitResult

from zscaler_mcp.registry import DELETE, READ
from zscaler_mcp.registry.fastmcp_bridge import build_function_tool
from zscaler_mcp.registry.spec import ToolSpec
from zscaler_mcp.security import elicitation as el
from zscaler_mcp.shaping import AgentView


class _View(AgentView):
    id: str


class _In(AgentView):
    group_id: str


@pytest.fixture(autouse=True)
def _clean_ledger():
    el._reset_consumed_for_testing()
    yield
    el._reset_consumed_for_testing()


@pytest.fixture(autouse=True)
def _no_skip(monkeypatch):
    """Confirmations must be ON; a stray env var would void every assertion."""
    monkeypatch.delenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", raising=False)


class _Recorder:
    """Tool body that records whether it was allowed to run."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, args):
        self.calls.append(args.model_dump())
        return {"id": "deleted"}

    @property
    def ran(self) -> bool:
        return bool(self.calls)


def _delete_spec(body) -> ToolSpec:
    return ToolSpec(
        name="zpa_delete_segment_group",
        action=DELETE,
        fn=body,
        input_model=_In,
        output_view=_View,
        description="Delete a segment group.",
        service="zpa",
        toolset="zpa_test",
    )


def _text(result) -> str:
    return "".join(getattr(b, "text", "") for b in (result.content or []))


def _server(body, **client_kwargs):
    """A one-tool MCPServer plus a connected in-memory client."""
    srv = MCPServer("test", tools=[build_function_tool(_delete_spec(body))])
    return Client(srv, **client_kwargs)


def _answer(action: str, choice: str | None = None):
    """An elicitation callback that answers the way a human would."""

    async def on_elicit(ctx, params):  # noqa: ARG001 - transport shape
        return ElicitResult(
            action=action, content={"choice": choice} if choice is not None else None
        )

    return on_elicit


class TestResolverWiring:
    """The declarative half: what is advertised, and what the resolver decides."""

    def test_confirmation_parameter_is_not_advertised(self):
        """The agent must have no slot to approve its own delete.

        This is the property the whole design rests on. If the resolved parameter
        ever leaked into the inputSchema, a prompt-injected model could fill it in
        and the human would never be asked.
        """
        tool = build_function_tool(_delete_spec(_Recorder()))
        assert "approval" not in (tool.parameters.get("properties") or {})
        assert "approval" in tool.resolved_params

    def test_real_inputs_are_still_advertised(self):
        """Hiding the resolved parameter must not hide the tool's actual inputs."""
        tool = build_function_tool(_delete_spec(_Recorder()))
        assert "group_id" in (tool.parameters.get("properties") or {})

    def test_resolver_asks_when_the_client_can_be_prompted(self):
        tool = build_function_tool(_delete_spec(_Recorder()))
        resolver = tool.resolved_params["approval"][0].fn
        request = resolver(group_id="7429", ctx=_capable())
        assert isinstance(request, Elicit)
        assert "7429" in request.message

    def test_resolver_falls_back_when_the_client_cannot_be_prompted(self):
        tool = build_function_tool(_delete_spec(_Recorder()))
        resolver = tool.resolved_params["approval"][0].fn
        assert resolver(group_id="7429", ctx=None) == el.TOKEN_FALLBACK

    def test_only_delete_tools_carry_a_confirmation_channel(self):
        """The gate is DELETE-only, across the whole registry.

        Companion to the description sweep below: this pins the *behaviour* the
        descriptions are allowed to claim, so the two can never be fixed apart.
        """
        from zscaler_mcp.registry.discovery import discover_tools
        from zscaler_mcp.registry.registry import REGISTRY

        discover_tools()
        gated = {
            spec.name
            for spec in REGISTRY
            if "approval" in (build_function_tool(spec).resolved_params or {})
        }
        deletes = {spec.name for spec in REGISTRY if spec.action == DELETE}
        assert gated == deletes

    def test_no_tool_description_claims_a_gate_it_does_not_have(self):
        """A create/update must not tell the agent it will be asked to confirm.

        A docstring becomes the tool ``description`` on the wire, so this is a
        claim made to the model. Sixteen create/update tools inherited "Gated by
        HMAC write-confirmation" from a design that was later narrowed to deletes
        only, and an agent acted on it: it reported that the server had enforced a
        confirmation on a create that in fact executed on the first call. Worse
        than cosmetic — a model told a gate exists has a reason not to ask the
        human itself.

        ``hmac`` is matched as well as ``confirm``, and that is not belt-and-braces.
        The first version of this test searched for ``confirm`` alone, which cleared
        the sixteen tools saying "Gated by HMAC write-confirmation" while leaving
        eighteen more saying "Gated by HMAC + ``--write-tools``" — the identical
        false claim, in a phrasing that happens to contain no such word. They were
        found by a later audit, not by this test. Match the mechanism, not one way
        of spelling it.
        """
        import re

        from zscaler_mcp.registry.discovery import discover_tools
        from zscaler_mcp.registry.registry import REGISTRY

        discover_tools()
        pattern = re.compile(r"confirm|hmac", re.IGNORECASE)
        offenders = sorted(
            spec.name
            for spec in REGISTRY
            if spec.action != DELETE and pattern.search(spec.description or "")
        )
        assert not offenders, (
            f"these tools advertise a confirmation gate that only DELETE tools have: {offenders}"
        )

    def test_every_delete_description_states_the_gate(self):
        """The converse: a delete must not stay silent about it either.

        Three phrasings coexisted here and 37 of 50 deletes said nothing at all, so
        an agent comparing two delete tools could reasonably infer they behaved
        differently. They do not — the gate is derived from the action verb and
        applies to all 50. Silence is the safer failure of the two, but it is still
        an inconsistent security claim on a destructive operation, and inconsistency
        is what produced the false claims this class already guards against.
        """
        import re

        from zscaler_mcp.registry.discovery import discover_tools
        from zscaler_mcp.registry.registry import REGISTRY

        discover_tools()
        pattern = re.compile(r"confirmation required", re.IGNORECASE)
        silent = sorted(
            spec.name
            for spec in REGISTRY
            if spec.action == DELETE and not pattern.search(spec.description or "")
        )
        assert not silent, f"these DELETE tools do not state the confirmation gate: {silent}"

    def test_read_tools_get_no_confirmation_parameter(self):
        read_spec = ToolSpec(
            name="zpa_list_segment_groups",
            action=READ,
            fn=lambda args: [{"id": "1"}],
            input_model=AgentView,
            output_view=_View,
            description="List.",
            service="zpa",
            toolset="zpa_test",
            is_list=True,
        )
        tool = build_function_tool(read_spec)
        assert not tool.resolved_params


def _capable(*, protocol_version="2026-07-28", has_standalone_channel=True):
    from mcp.types import ClientCapabilities, ElicitationCapability

    class _Ctx:
        client_capabilities = ClientCapabilities(elicitation=ElicitationCapability())

    ctx = _Ctx()
    ctx.protocol_version = protocol_version
    ctx.connection = SimpleNamespace(has_standalone_channel=has_standalone_channel)
    return ctx


@pytest.mark.asyncio
class TestThroughAClient:
    """Full MCP round trips. These are the tests that catch transport regressions."""

    async def test_delete_runs_when_human_approves(self):
        body = _Recorder()
        async with _server(body, elicitation_callback=_answer("accept", "delete")) as c:
            result = await c.call_tool("zpa_delete_segment_group", {"group_id": "7429"})

        assert body.ran, "approved delete should have executed"
        assert body.calls[0]["group_id"] == "7429"
        assert not result.is_error
        assert "CONFIRMATION REQUIRED" not in _text(result)

    async def test_the_human_sees_which_resource_is_being_deleted(self):
        """A prompt that cannot name its target is not a meaningful confirmation."""
        seen: list[str] = []

        async def on_elicit(ctx, params):  # noqa: ARG001 - transport shape
            seen.append(params.message)
            return ElicitResult(action="accept", content={"choice": "delete"})

        async with _server(_Recorder(), elicitation_callback=on_elicit) as c:
            await c.call_tool("zpa_delete_segment_group", {"group_id": "7429"})

        assert seen and "7429" in seen[0]
        assert "Segment Group" in seen[0]

    @pytest.mark.parametrize(
        "action, choice",
        [("accept", "cancel"), ("decline", None), ("cancel", None)],
        ids=["chose-cancel", "declined", "dismissed"],
    )
    async def test_delete_blocked_when_human_refuses(self, action, choice):
        body = _Recorder()
        async with _server(body, elicitation_callback=_answer(action, choice)) as c:
            result = await c.call_tool("zpa_delete_segment_group", {"group_id": "7429"})

        assert not body.ran, "refused delete must not touch the SDK"
        assert "NOT performed" in _text(result)

    async def test_delete_not_executed_when_the_client_cannot_answer(self):
        """A client that advertises elicitation but then fails must not mutate.

        This is the client-side timeout / dropped-answer case, which a user hit in
        practice: the confirmation prompt appeared, the client's own timeout fired
        before it was answered, and the call died. The important half is what did
        *not* happen. Because the resolver runs before the tool body, an
        unanswered question means the body is never reached — the failure mode is
        a failed call, never a silent deletion.
        """
        body = _Recorder()

        async def explode(ctx, params):  # noqa: ARG001 - transport shape
            raise RuntimeError("client gave up")

        with pytest.raises(BaseException):  # noqa: B017 - shape is transport-defined
            async with _server(body, elicitation_callback=explode) as c:
                await c.call_tool("zpa_delete_segment_group", {"group_id": "7429"})

        assert not body.ran, "an unanswered confirmation must not mutate anything"

    async def test_falls_back_to_token_when_client_cannot_be_prompted(self):
        """A client with no elicitation capability still gets the HMAC handshake."""
        body = _Recorder()
        async with _server(body) as c:
            first = await c.call_tool("zpa_delete_segment_group", {"group_id": "7429"})
            assert not body.ran, "first call must only ask, never mutate"
            text = _text(first)
            assert "CONFIRMATION REQUIRED" in text

            token = text.split('"confirmation_token": "', 1)[1].split('"', 1)[0]
            await c.call_tool(
                "zpa_delete_segment_group",
                {"group_id": "7429", "kwargs": f'{{"confirmation_token": "{token}"}}'},
            )
        assert body.ran, "the token handshake should complete the delete"

    async def test_a_valid_token_cannot_override_a_human_refusal(self):
        """The `kwargs` token must be inert whenever a human can be asked.

        This is the invariant behind the claim that an agent cannot approve its own
        delete. The `kwargs` channel cannot simply be removed — clients without
        elicitation support depend on it — so the protection rests entirely on the
        gate consulting it *only* on the fallback path. Asserted with a genuine,
        unredeemed token rather than a forged one, because a forgery would be
        rejected by the signature check and would pass this test for the wrong
        reason.
        """
        async with _server(_Recorder()) as c:
            minted = _text(await c.call_tool("zpa_delete_segment_group", {"group_id": "7429"}))
        token = minted.split('"confirmation_token": "', 1)[1].split('"', 1)[0]

        body = _Recorder()
        async with _server(body, elicitation_callback=_answer("accept", "cancel")) as c:
            result = await c.call_tool(
                "zpa_delete_segment_group",
                {"group_id": "7429", "kwargs": f'{{"confirmation_token": "{token}"}}'},
            )

        assert not body.ran, "a valid token must not override a human's refusal"
        assert "NOT performed" in _text(result)

        # The refusal must not spend the token either: it was never consulted, so it
        # is still the one approval a fallback client is entitled to redeem.
        fallback_body = _Recorder()
        async with _server(fallback_body) as c:
            await c.call_tool(
                "zpa_delete_segment_group",
                {"group_id": "7429", "kwargs": f'{{"confirmation_token": "{token}"}}'},
            )
        assert fallback_body.ran, "an unconsulted token should not have been burned"

    async def test_no_environment_variable_can_skip_the_prompt(self, monkeypatch):
        """End-to-end counterpart to the unit test: the bypass is gone from the wire.

        Asserted through a real tool call rather than against the gate directly,
        because the env var used to be read on two separate paths and a partial
        removal would still pass a unit test of either one.
        """
        monkeypatch.setenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", "true")
        body = _Recorder()
        async with _server(body) as c:
            result = await c.call_tool("zpa_delete_segment_group", {"group_id": "7429"})
        assert not body.ran, "the delete ran without any confirmation"
        assert "CONFIRMATION REQUIRED" in _text(result)
