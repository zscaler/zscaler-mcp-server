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
    props = tools["zpa_list_segment_groups"].parameters.get("properties", {})
    # Flat fields, NOT a nested {"args": {...}} wrapper.
    assert "args" not in props
    assert "search" in props
    assert "detail" in props


@pytest.mark.asyncio
async def test_list_output_schema_wrapped_object():
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    out = tools["zpa_list_segment_groups"].output_schema
    assert out["type"] == "object"
    assert out.get("x-fastmcp-wrap-result") is True
    assert out["properties"]["result"]["type"] == "array"


@pytest.mark.asyncio
async def test_object_output_schema_plain():
    server = build_server()
    tools = {t.name: t for t in await server.list_tools()}
    out = tools["zpa_get_segment_group"].output_schema
    assert out["type"] == "object"
    assert "x-fastmcp-wrap-result" not in out


@pytest.mark.asyncio
async def test_only_delete_tool_has_no_output_schema():
    # Only DELETE is polymorphic (HMAC confirmation prompt on the first call,
    # OperationResult on the confirmed call). Declaring a strict outputSchema
    # makes the MCP server reject the confirmation envelope with "outputSchema
    # defined but no structured output returned", so DELETE registers WITHOUT an
    # outputSchema. create/update are NOT confirmation-gated (v1 parity: only
    # destructive ops confirm) — they always return their shaped resource, so
    # they keep a strict outputSchema exactly like reads.
    server = build_server(enable_write=True, write_allowlist=["zpa_*"])
    tools = {t.name: t for t in await server.list_tools()}
    assert tools["zpa_delete_segment_group"].output_schema is None
    # create/update and reads all keep their strict schema.
    assert tools["zpa_create_segment_group"].output_schema is not None
    assert tools["zpa_update_segment_group"].output_schema is not None
    assert tools["zpa_list_segment_groups"].output_schema is not None


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
    result = await server._call_tool_mcp("zpa_delete_segment_group", {"group_id": "123"})
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
    result = await server._call_tool_mcp(
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
