"""Integration tests: the server build + bridge wire the security layer correctly.

These assert the end-to-end guarantees an operator cares about:
* write tools are hidden unless explicitly enabled (read-only by default);
* the write allowlist narrows which write tools surface;
* a write call without a confirmation token returns the HMAC prompt (no mutation);
* tool input schemas are FLAT (no nested ``args`` wrapper);
* list tools advertise the wrapped-array output schema, objects advertise plain.
"""

from __future__ import annotations

import pytest

from zscaler_mcp.server import build_server


async def _names(server):
    return {t.name for t in await server.list_tools()}


@pytest.mark.asyncio
async def test_read_only_by_default():
    server = build_server()
    names = await _names(server)
    assert "zpa_list_segment_groups" in names
    assert "zpa_get_segment_group" in names
    # Write tool must NOT appear without --write-tools.
    assert "zpa_create_segment_group" not in names


@pytest.mark.asyncio
async def test_write_enabled_surfaces_write_tool():
    server = build_server(enable_write=True, write_allowlist=["zpa_create_*"])
    assert "zpa_create_segment_group" in await _names(server)


@pytest.mark.asyncio
async def test_write_allowlist_excludes_non_matching():
    server = build_server(enable_write=True, write_allowlist=["zpa_delete_*"])
    # create doesn't match the delete-only allowlist.
    assert "zpa_create_segment_group" not in await _names(server)


@pytest.mark.asyncio
async def test_disabled_pattern_wins():
    server = build_server(disabled_patterns=["zpa_list_*"])
    assert "zpa_list_segment_groups" not in await _names(server)


@pytest.mark.asyncio
async def test_toolset_filter():
    # A non-existent toolset selection yields no service tools.
    server = build_server(enabled_toolsets=["does_not_exist"])
    assert await _names(server) == set()


@pytest.mark.asyncio
async def test_input_schema_is_flat():
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    props = tools["zpa_list_segment_groups"].input_schema.get("properties", {})
    # Flat fields, NOT a nested {"args": {...}} wrapper.
    assert "args" not in props
    assert "search" in props
    assert "microtenant_id" in props


@pytest.mark.asyncio
async def test_record_tools_advertise_no_output_schema():
    # Tools returning a Zscaler API record declare NO outputSchema. The set of
    # attributes a resource carries belongs to the API, so any schema we wrote
    # here would be a snapshot that silently goes stale the moment engineering
    # ships a new field — the failure mode behind issue #88. The SDK documents
    # reads the same way: query params are enumerated, the response is just
    # `record.as_dict()`.
    server = build_server(enable_write=True, write_allowlist=["zpa_*"])
    tools = {t.name: t for t in await server.list_tools()}
    for name in (
        "zpa_list_segment_groups",
        "zpa_get_segment_group",
        "zpa_create_segment_group",
        "zpa_update_segment_group",
        "zpa_delete_segment_group",
    ):
        assert tools[name].output_schema is None, f"{name} should not declare an outputSchema"


@pytest.mark.asyncio
async def test_synthetic_result_tools_keep_their_schema():
    # The exception: results the SERVER constructs (catalogs, status envelopes)
    # really are our shape, so they still advertise it. The Catalog wrapper is
    # itself a passthrough — the ZPA payload rides untouched under `items`.
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    out = tools["zpa_list_lss_log_types"].output_schema
    assert out is not None
    assert out["type"] == "object"
    assert set(out["properties"]) == {"kind", "items"}


@pytest.mark.asyncio
async def test_delete_call_without_token_returns_confirmation_no_mutation(monkeypatch):
    # DELETE is confirmation-gated: the first call (no token) must return the HMAC
    # confirmation prompt and perform NO mutation. If the SDK were ever reached,
    # this would explode — proving no mutation.
    import zscaler_mcp.tools.zpa.segment_groups as sg

    def explode(*a, **k):
        raise AssertionError("SDK must not be called before confirmation")

    monkeypatch.setattr(sg, "get_zscaler_client", explode)

    server = build_server(enable_write=True, write_allowlist=["zpa_delete_*"])
    result = await server.call_tool("zpa_delete_segment_group", {"group_id": "123"})
    # result is a (content, structured) tuple or CallToolResult-like; pull text.
    content = result[0] if isinstance(result, tuple) else getattr(result, "content", result)
    text = content[0].text
    assert "CONFIRMATION REQUIRED" in text
    assert "confirmation_token" in text


@pytest.mark.asyncio
async def test_create_call_executes_without_confirmation(monkeypatch):
    # v1 parity: create/update are NOT confirmation-gated. With write-tools
    # enabled, a create call goes straight to the SDK and returns the shaped
    # resource — no HMAC confirmation envelope, no second round-trip.
    import zscaler_mcp.tools.zpa.segment_groups as sg

    class _Result:
        def as_dict(self):
            return {"id": "999", "name": "My Group", "enabled": True, "applications": []}

    class _SG:
        def add_group(self, **kwargs):
            return _Result(), None, None

    class _Client:
        class zpa:
            segment_groups = _SG()

    monkeypatch.setattr(sg, "get_zscaler_client", lambda **k: _Client())

    server = build_server(enable_write=True, write_allowlist=["zpa_create_*"])
    result = await server.call_tool(
        "zpa_create_segment_group", {"name": "My Group", "enabled": True}
    )
    content = result[0] if isinstance(result, tuple) else getattr(result, "content", result)
    text = content[0].text
    assert "CONFIRMATION REQUIRED" not in text
    # The created resource (id 999) is returned directly.
    assert "999" in text


# ---------------------------------------------------------------------------
# OneAPI entitlement downscoping at server build time
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_entitlement_filter_downscopes_tools(monkeypatch):
    # Simulate a token entitled to a single product (zia). Every tool from a
    # non-entitled product (e.g. zpa_*) must be stripped from the surface,
    # while the entitled product's tools remain.
    import zscaler_mcp.server as server_mod

    monkeypatch.setattr(
        server_mod,
        "apply_entitlement_filter",
        lambda available, **kw: ({"zia"}, "entitlement filter applied: kept zia"),
    )
    server = build_server()
    names = await _names(server)
    assert not any(n.startswith("zpa_") for n in names)
    assert any(n.startswith("zia_") for n in names)


@pytest.mark.asyncio
async def test_entitlement_filter_keeps_entitled_service(monkeypatch):
    import zscaler_mcp.server as server_mod

    monkeypatch.setattr(
        server_mod,
        "apply_entitlement_filter",
        lambda available, **kw: ({"zpa"}, "entitlement filter applied: kept zpa"),
    )
    server = build_server()
    assert "zpa_list_segment_groups" in await _names(server)


@pytest.mark.asyncio
async def test_entitlement_filter_skipped_keeps_all(monkeypatch):
    # When the filter returns None (skip), no downscoping is applied.
    import zscaler_mcp.server as server_mod

    monkeypatch.setattr(
        server_mod,
        "apply_entitlement_filter",
        lambda available, **kw: (None, "entitlement filter skipped (no token)"),
    )
    server = build_server()
    assert "zpa_list_segment_groups" in await _names(server)


@pytest.mark.asyncio
async def test_no_entitlement_filter_flag_skips_resolution(monkeypatch):
    # disable_entitlement_filter=True must not even call apply_entitlement_filter.
    import zscaler_mcp.server as server_mod

    def boom(*a, **k):
        raise AssertionError("entitlement filter must not run when disabled")

    monkeypatch.setattr(server_mod, "apply_entitlement_filter", boom)
    server = build_server(disable_entitlement_filter=True)
    assert "zpa_list_segment_groups" in await _names(server)


# --- Write tools need BOTH knobs (v1 parity) --------------------------------
#
# v1 gated registration on the master switch AND treated the allowlist as
# mandatory (``register_write_tools``: ``if not enable_write_tools: return 0``
# followed by ``if not write_tools: ... return 0``). Neither knob grants
# anything alone. v2 briefly resolved them with an OR, which silently turned
# "switch on, allowlist blank" into all 148 write tools including every delete.


@pytest.mark.asyncio
async def test_write_switch_alone_registers_no_write_tools(caplog):
    # Master switch on, no allowlist -> zero write tools, and say why.
    with caplog.at_level("WARNING"):
        server = build_server(enable_write=True)
    names = await _names(server)
    assert not any(n.startswith(("zpa_create_", "zpa_delete_", "zia_update_")) for n in names)
    assert "zpa_list_segment_groups" in names  # reads are unaffected
    assert "no allowlist" in caplog.text


@pytest.mark.asyncio
async def test_write_allowlist_alone_registers_no_write_tools(caplog):
    # An allowlist without the master switch must not enable anything: this is
    # the shape of an env file carrying ZSCALER_MCP_WRITE_TOOLS with the switch
    # off (or absent), which must stay read-only. Releases 0.13.0-0.14.0 enabled
    # writes here, so on upgrade the tools vanish — say why rather than go quiet.
    with caplog.at_level("WARNING"):
        server = build_server(enable_write=False, write_allowlist=["zpa_create_*", "zpa_delete_*"])
    names = await _names(server)
    assert "zpa_create_segment_group" not in names
    assert "zpa_list_segment_groups" in names
    assert "write tools are disabled" in caplog.text


@pytest.mark.asyncio
async def test_write_requires_both_knobs_together():
    server = build_server(enable_write=True, write_allowlist=["zpa_create_*"])
    names = await _names(server)
    assert "zpa_create_segment_group" in names
    # The allowlist still scopes: a delete outside the patterns stays hidden.
    assert "zpa_delete_segment_group" not in names


@pytest.mark.asyncio
async def test_empty_write_allowlist_registers_no_write_tools():
    # ZSCALER_MCP_WRITE_TOOLS="" parses to an empty selection, which must be
    # read as "permit nothing", never as "permit everything".
    server = build_server(enable_write=True, write_allowlist=[])
    assert "zpa_create_segment_group" not in await _names(server)


@pytest.mark.asyncio
async def test_entitlement_filter_outranks_write_allowlist(monkeypatch):
    # A token scoped to ZIA must not yield ZPA write tools, however broad the
    # operator's allowlist is. Entitlement is checked per-spec before the
    # read/write gate, so it downscopes writes and reads alike.
    import zscaler_mcp.server as server_mod

    monkeypatch.setattr(
        server_mod,
        "apply_entitlement_filter",
        lambda available, **kw: ({"zia"}, "entitlement filter applied: kept zia"),
    )
    server = build_server(enable_write=True, write_allowlist=["*"])
    names = await _names(server)
    assert not any(n.startswith("zpa_") for n in names)
    assert any(n.startswith("zia_") for n in names)
