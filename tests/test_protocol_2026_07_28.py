"""Protocol-level tests for the ``2026-07-28`` MCP revision features.

Three things this server adopts from the revision, each pinned here:

* **SEP-2322, stateless input requests.** A destructive tool asks a human for
  approval by returning ``InputRequiredResult``; the client answers and retries,
  echoing back a ``requestState`` blob. There is no server-to-client back-channel
  on this revision, so this is the *only* way to reach a human mid-call.
* **SEP-2322, request-state protection.** ``requestState`` is caller-controlled
  input that decides whether a delete was approved, so it is sealed with
  authenticated encryption and bound to the request and the principal.
* **SEP-2549, cacheable responses.** ``tools/list`` carries a cache hint, so a
  proxy or client can skip re-fetching an inventory that cannot change.

Plus one thing the revision *removed*: ``logging/setLevel``. The handler we keep for
older clients is unreachable here by design, and the tests at the bottom pin that
asymmetry in both directions so it doesn't get "fixed" into a regression.

These are deliberately end-to-end where possible. The failure mode that motivated
this file was invisible to unit tests: mid-call ``ctx.elicit()`` kept passing in
isolation while being unreachable over the negotiated revision, because the
transport had removed the back-channel it depended on. Only a real round trip
distinguishes "the code is correct" from "the code is reachable".
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

import pytest
from mcp import Client
from mcp.server.caching import CacheHint
from mcp.server.mcpserver import MCPServer
from mcp.types import ElicitResult

from zscaler_mcp.registry import DELETE, READ
from zscaler_mcp.registry.fastmcp_bridge import build_function_tool
from zscaler_mcp.registry.spec import ToolSpec
from zscaler_mcp.security import elicitation as el
from zscaler_mcp.server import _TOOL_LIST_CACHE_HINTS, _request_state_security
from zscaler_mcp.shaping import AgentView

#: The revision whose features this module pins. A negotiation below this means
#: the SDK floor regressed and the features silently stop being exercised.
TARGET_REVISION = "2026-07-28"


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
    monkeypatch.delenv("ZSCALER_MCP_SKIP_CONFIRMATIONS", raising=False)


async def _set_level_over_session(revision: str, level: str) -> dict:
    """Drive ``logging/setLevel`` over a session pinned to ``revision``.

    The SDK's ``ClientSession`` always claims the newest revision it knows, so it
    can't be used to test the compatibility path. Hand-rolling the two JSON-RPC
    frames is the only way to make the client claim an older one.

    Returns what the caller needs to judge the outcome: the negotiated revision, any
    JSON-RPC error, and the level of both our logger and the root logger either side
    of the call.
    """
    import mcp.types as types
    from mcp.shared.memory import create_client_server_memory_streams
    from mcp.shared.message import SessionMessage

    from zscaler_mcp.server import build_server

    def request(id_: int, method: str, params: dict) -> SessionMessage:
        return SessionMessage(
            types.JSONRPCRequest(jsonrpc="2.0", id=id_, method=method, params=params)
        )

    low = build_server(
        enabled_toolsets=["zia_url_filtering"], disable_entitlement_filter=True
    )._lowlevel_server

    ours = logging.getLogger("zscaler_mcp")
    root = logging.getLogger()
    original = ours.level
    try:
        ours.setLevel(logging.WARNING)

        async with create_client_server_memory_streams() as (client, server):
            client_read, client_write = client
            server_read, server_write = server

            serving = asyncio.create_task(
                low.run(
                    server_read,
                    server_write,
                    low.create_initialization_options(),
                    raise_exceptions=True,
                )
            )
            try:
                await client_write.send(
                    request(
                        1,
                        "initialize",
                        {
                            "protocolVersion": revision,
                            "capabilities": {},
                            "clientInfo": {"name": "revision-pinned", "version": "0"},
                        },
                    )
                )
                initialized = await client_read.receive()

                await client_write.send(
                    SessionMessage(
                        types.JSONRPCNotification(
                            jsonrpc="2.0", method="notifications/initialized", params={}
                        )
                    )
                )

                root_before = root.level
                await client_write.send(request(2, "logging/setLevel", {"level": level}))
                answer = await client_read.receive()

                return {
                    "negotiated": initialized.message.result["protocolVersion"],
                    "error": getattr(answer.message, "error", None),
                    "ours_after": ours.level,
                    "root_before": root_before,
                    "root_after": root.level,
                }
            finally:
                serving.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await serving
    finally:
        ours.setLevel(original)


class _Recorder:
    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, args):
        self.calls.append(args.model_dump())
        return {"id": "deleted"}

    @property
    def ran(self) -> bool:
        return bool(self.calls)


def _delete_tool(body):
    return build_function_tool(
        ToolSpec(
            name="zpa_delete_segment_group",
            action=DELETE,
            fn=body,
            input_model=_In,
            output_view=_View,
            description="Delete a segment group.",
            service="zpa",
            toolset="zpa_test",
        )
    )


def _read_tool():
    return build_function_tool(
        ToolSpec(
            name="zpa_list_segment_groups",
            action=READ,
            fn=lambda args: [{"id": "1"}],
            input_model=AgentView,
            output_view=_View,
            description="List segment groups.",
            service="zpa",
            toolset="zpa_test",
            is_list=True,
        )
    )


def _approve():
    async def on_elicit(ctx, params):  # noqa: ARG001 - transport shape
        return ElicitResult(action="accept", content={"choice": "delete"})

    return on_elicit


# ---------------------------------------------------------------------------
# Revision negotiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_negotiates_the_target_revision():
    """Everything else in this file is only meaningful at this revision.

    If the negotiated version drops back, the stateless-input tests below would
    still pass — over the old back-channel — and quietly stop testing SEP-2322.
    """
    server = MCPServer("test", tools=[_read_tool()])
    async with Client(server) as client:
        assert client.session.protocol_version == TARGET_REVISION


# ---------------------------------------------------------------------------
# SEP-2322 — stateless input requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStatelessInputRequests:
    async def test_confirmation_travels_over_the_stateless_input_loop(self):
        """The ask must go through ``dispatch_input_request``, not a back-channel.

        This is the distinguishing assertion of the whole migration. Spying on the
        client's dispatcher is the only way to tell the two mechanisms apart from
        the outside: both end with the human being asked, but only one works on
        this revision.
        """
        from mcp.client.session import ClientSession

        dispatched: list[str] = []
        original = ClientSession.dispatch_input_request

        async def spy(self, ctx, req):
            dispatched.append(type(req).__name__)
            return await original(self, ctx, req)

        ClientSession.dispatch_input_request = spy
        try:
            body = _Recorder()
            server = MCPServer("test", tools=[_delete_tool(body)])
            async with Client(server, elicitation_callback=_approve()) as client:
                await client.call_tool("zpa_delete_segment_group", {"group_id": "7429"})
        finally:
            ClientSession.dispatch_input_request = original

        assert dispatched, "confirmation did not use the stateless input-request loop"
        assert body.ran

    async def test_the_approval_slot_is_never_advertised_to_the_model(self):
        """A resolved parameter is filled by the framework, not by the caller.

        If it appeared in the inputSchema, a prompt-injected model could approve
        its own delete and the human would never be asked — which is the entire
        threat this mechanism exists to close.
        """
        server = MCPServer("test", tools=[_delete_tool(_Recorder())])
        async with Client(server) as client:
            listed = {t.name: t for t in (await client.list_tools()).tools}
        schema = listed["zpa_delete_segment_group"].input_schema
        assert "approval" not in (schema.get("properties") or {})
        assert "group_id" in (schema.get("properties") or {})


# ---------------------------------------------------------------------------
# SEP-2322 — request-state protection
# ---------------------------------------------------------------------------


class TestRequestStateProtection:
    def test_state_is_sealed_under_a_per_process_key(self):
        """Two processes must not be able to read each other's state.

        Each call produces an independent key, which is what makes a confirmation
        minted before a restart (or on another replica) undecryptable rather than
        silently honoured.
        """
        first, second = _request_state_security(), _request_state_security()
        assert first is not second

    def test_state_expires(self):
        """An approval must not stay spendable indefinitely."""
        assert _request_state_security().ttl > 0

    def test_state_is_bound_to_the_authenticated_principal(self):
        """One caller's approval must not authorize another caller's delete."""
        assert _request_state_security().bind_principal is not None

    def test_the_boundary_is_installed_on_the_server(self):
        """The policy has to be wired in, not merely constructed.

        Constructing a policy nobody consults is the kind of mistake that reads
        fine and protects nothing, so this asserts on the built server.
        """
        from mcp.server.request_state import RequestStateBoundary

        server = MCPServer(
            "test",
            tools=[_read_tool()],
            request_state_security=_request_state_security(),
        )
        installed = [type(m).__name__ for m in server._lowlevel_server.middleware]
        assert RequestStateBoundary.__name__ in installed


# ---------------------------------------------------------------------------
# SEP-2549 — cacheable tool inventory
# ---------------------------------------------------------------------------


class TestToolListCaching:
    def test_only_the_tool_inventory_is_hinted(self):
        """Hinting anything that reflects tenant state would serve stale data."""
        assert set(_TOOL_LIST_CACHE_HINTS) == {"tools/list"}

    def test_the_hint_is_public_and_bounded(self):
        hint = _TOOL_LIST_CACHE_HINTS["tools/list"]
        assert isinstance(hint, CacheHint)
        assert hint.scope == "public"
        assert 0 < hint.ttl_ms <= 3_600_000

    def test_the_hint_reaches_the_server(self):
        server = MCPServer("test", tools=[_read_tool()], cache_hints=_TOOL_LIST_CACHE_HINTS)
        assert server._lowlevel_server.cache_hints == _TOOL_LIST_CACHE_HINTS

    def test_every_hinted_method_is_one_the_spec_permits_caching(self):
        """The spec allowlists which methods may carry a cache hint.

        Hinting anything else is dead configuration at best — a client is entitled
        to ignore it, and a proxy that honours it would be caching something the
        spec never promised was stable.
        """
        import mcp.server.runner as runner

        for method in _TOOL_LIST_CACHE_HINTS:
            assert method in runner._methods.CACHEABLE_METHODS

    def test_every_hinted_method_exists_in_this_revision(self):
        """`logging/setLevel` is the cautionary example of a method that doesn't."""
        import mcp.server.runner as runner

        for method in _TOOL_LIST_CACHE_HINTS:
            assert (method, TARGET_REVISION) in runner._methods.CLIENT_REQUESTS

    def test_the_inventory_it_claims_to_be_cacheable_is_actually_stable(self):
        """``scope="public"`` and a TTL are a promise about this server's behaviour.

        The promise holds only because every filter — toolsets, write allowlist,
        entitlement downscope — is resolved once at registration and there is no
        runtime registration path. Adding a tool that enables toolsets at runtime
        would make the hint a lie, so this asserts the listing is idempotent.
        """
        server = MCPServer("test", tools=[_read_tool()], cache_hints=_TOOL_LIST_CACHE_HINTS)
        import asyncio

        async def listing():
            return [t.name for t in await server.list_tools()]

        assert asyncio.run(listing()) == asyncio.run(listing())


# ---------------------------------------------------------------------------
# logging/setLevel — served for older clients, absent from this revision
# ---------------------------------------------------------------------------


class TestLoggingSetLevel:
    """Pins a deliberate asymmetry that reads like a bug if undocumented.

    A handler IS registered — the `logging-set-level` conformance scenario depends
    on it — but it is unreachable on `2026-07-28`, where SEP-2577's deprecation
    removed the method from the surface. Someone will eventually notice the
    `-32601` on a new-revision client and try to "fix" it. These tests say: the
    registration is correct, the unreachability is upstream and intentional.
    """

    def test_a_handler_is_registered(self):
        """Without it, older clients get -32601 and conformance fails."""
        from zscaler_mcp.server import _install_logging_set_level

        server = MCPServer("test", tools=[_read_tool()])
        assert server._lowlevel_server.get_request_handler("logging/setLevel") is None
        _install_logging_set_level(server)
        assert server._lowlevel_server.get_request_handler("logging/setLevel") is not None

    @pytest.mark.parametrize("revision", ["2025-06-18", "2025-11-25"])
    def test_older_revisions_still_route_the_method(self, revision):
        import mcp.server.runner as runner

        assert ("logging/setLevel", revision) in runner._methods.CLIENT_REQUESTS

    def test_this_revision_dropped_the_method_upstream(self):
        """Not our doing, and not fixable by registering harder.

        The SDK looks the method up in a per-revision surface map during request
        validation, before handler lookup. If this ever starts failing, the method
        came back upstream and the docs claiming otherwise need updating.
        """
        import mcp.server.runner as runner

        assert ("logging/setLevel", TARGET_REVISION) not in runner._methods.CLIENT_REQUESTS

    def test_it_actually_works_over_a_session_on_an_older_revision(self):
        """The claim that matters, exercised the only way that can prove it.

        Registration and surface-map membership are both necessary and neither is
        sufficient — the lesson from mid-call ``ctx.elicit()``, which passed unit
        tests while being unreachable over the wire. So: pin a real session to
        ``2025-11-25``, send the request, and check the logger actually moved.

        Also asserts the root logger did *not* move. Raising it would switch on the
        Zscaler SDK's request logging, which prints credential-bearing headers at
        debug — emphatically not what a client asking for MCP logs is asking for.
        """
        outcome = asyncio.run(_set_level_over_session("2025-11-25", "debug"))

        assert outcome["negotiated"] == "2025-11-25"
        assert outcome["error"] is None, f"handler unreachable: {outcome['error']}"
        assert outcome["ours_after"] == logging.DEBUG
        assert outcome["root_after"] != logging.DEBUG
        assert outcome["root_after"] == outcome["root_before"]

    def test_a_severity_mcp_has_and_python_does_not_still_maps(self):
        """MCP defines eight severities against Python's five.

        ``notice`` is the one with no Python equivalent, so it is the one most
        likely to raise instead of mapping. A client sending a legal level must
        never get an error back.
        """
        outcome = asyncio.run(_set_level_over_session("2025-11-25", "notice"))

        assert outcome["error"] is None
        assert outcome["ours_after"] == logging.INFO


# ---------------------------------------------------------------------------
# Pre-2026-07-28 clients — the population that regressed
# ---------------------------------------------------------------------------


async def _legacy_delete_exchange(revision: str, *, capabilities: dict) -> dict:
    """Call a delete as a pre-2026-07-28 client and report which path answered.

    Hand-rolled frames for the same reason as ``_set_level_over_session``: the SDK's
    ``ClientSession`` always claims the newest revision it knows, so it cannot
    impersonate the clients that most users are actually running today.

    The memory streams are a persistent bidirectional pair, which is the transport
    shape of stdio and of a session-bearing streamable-http connection — i.e. one
    where a server-to-client prompt *can* be delivered. Returns the first frame the
    server sends after the call so the caller can tell an ask from a token.
    """
    import mcp.types as types
    from mcp.shared.memory import create_client_server_memory_streams
    from mcp.shared.message import SessionMessage

    body = _Recorder()
    low = MCPServer("test", tools=[_delete_tool(body)])._lowlevel_server
    out: dict = {"pushed_method": None, "text": "", "ran": False}

    async with create_client_server_memory_streams() as (client, server):
        client_read, client_write = client
        server_read, server_write = server

        serving = asyncio.create_task(
            low.run(
                server_read,
                server_write,
                low.create_initialization_options(),
                raise_exceptions=True,
            )
        )
        try:
            await client_write.send(
                SessionMessage(
                    types.JSONRPCRequest(
                        jsonrpc="2.0",
                        id=1,
                        method="initialize",
                        params={
                            "protocolVersion": revision,
                            "capabilities": capabilities,
                            "clientInfo": {"name": "legacy", "version": "0"},
                        },
                    )
                )
            )
            handshake = await client_read.receive()
            out["negotiated"] = handshake.message.result.get("protocolVersion")

            await client_write.send(
                SessionMessage(
                    types.JSONRPCNotification(
                        jsonrpc="2.0", method="notifications/initialized", params={}
                    )
                )
            )
            await client_write.send(
                SessionMessage(
                    types.JSONRPCRequest(
                        jsonrpc="2.0",
                        id=2,
                        method="tools/call",
                        params={
                            "name": "zpa_delete_segment_group",
                            "arguments": {"group_id": "7429"},
                        },
                    )
                )
            )

            frame = await asyncio.wait_for(client_read.receive(), timeout=10)
            msg = frame.message
            method = getattr(msg, "method", None)
            if method:
                # A server-initiated request: the human is being asked.
                out["pushed_method"] = method
            else:
                out["text"] = str(getattr(msg, "result", "") or getattr(msg, "error", ""))
        finally:
            serving.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await serving

    out["ran"] = body.ran
    return out


class TestLegacyClientConfirmation:
    """A pre-2026-07-28 client on a real session must be ASKED, not handed a token.

    This is the test whose absence let a real regression ship. ``elicitation_available``
    briefly consulted ``ctx.connection.has_standalone_channel`` — an attribute `mcp`
    2.0.0's ``Context`` does not have — so every legacy caller raised
    ``AttributeError`` into a broad ``except`` and was routed to the HMAC token. The
    unit tests passed throughout, because they faked that attribute into existence.

    Why the distinction matters more than it sounds: the token can be redeemed by the
    agent in the same turn it was issued, so the fallback path means no human
    necessarily approves the delete. Losing the prompt is a safety regression, not a
    cosmetic one, and it is invisible unless a test drives a real client.
    """

    @pytest.mark.parametrize("revision", ["2025-11-25", "2025-06-18"])
    def test_a_capable_legacy_client_gets_a_pushed_prompt(self, revision):
        outcome = asyncio.run(_legacy_delete_exchange(revision, capabilities={"elicitation": {}}))

        assert outcome["pushed_method"] == "elicitation/create", (
            "a legacy client that advertised elicitation was not asked; it got "
            f"{outcome['text'][:200]!r}"
        )
        assert "CONFIRMATION REQUIRED" not in outcome["text"]
        assert not outcome["ran"], "the delete ran before anyone approved it"

    def test_a_legacy_client_without_the_capability_still_gets_the_token(self):
        """The fallback must survive: it is the only gate such a client can use."""
        outcome = asyncio.run(_legacy_delete_exchange("2025-11-25", capabilities={}))

        assert outcome["pushed_method"] is None
        assert "CONFIRMATION REQUIRED" in outcome["text"]
        assert not outcome["ran"]
