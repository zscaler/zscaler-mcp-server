"""Contract tests for the shaping chokepoints (``shape_many`` / ``shape_one``).

These lock in the post-#88 design. Tools returning a Zscaler API record hand it
through VERBATIM: the server does not enumerate, rename, or trim the attributes
of a resource, because that attribute set belongs to the API and any list kept
here would silently go stale when engineering ships a new field. The helpers
remain as the coercion point (SDK model object -> plain dict).

The merge form (``shape_one(raw, shaper)``) is retained for the handful of
SYNTHETIC results the server genuinely constructs, and even there it can only
ADD to the record, never restrict it.

Token efficiency comes from toolset selection + the CSV wire format, never from
dropping fields.
"""

from __future__ import annotations

from typing import Optional

from zscaler_mcp.shaping import AgentView, shape_many, shape_one


class _Highlight(AgentView):
    """Minimal view: normalizes ``id`` to str, exposes one computed field."""

    id: Optional[str] = None
    kind: Optional[str] = None


def _shaper(raw: dict) -> _Highlight:
    return _Highlight(id=str(raw.get("id")) if raw.get("id") is not None else None, kind="device")


class _Obj:
    """Stand-in for an SDK model object exposing ``as_dict()``."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def as_dict(self) -> dict:
        return dict(self._data)


def test_shape_one_merges_full_record_with_highlights():
    raw = {"id": 7, "name": "hq", "nested": {"a": 1}, "extra_flag": True}
    out = shape_one(raw, _shaper)
    # Full record preserved (nothing stripped) ...
    assert out["name"] == "hq"
    assert out["nested"] == {"a": 1}
    assert out["extra_flag"] is True
    # ... with the shaper's normalization overlaid.
    assert out["id"] == "7"  # coerced to string by the shaper
    assert out["kind"] == "device"  # computed field added


def test_shape_one_none_shaper_is_plain_passthrough():
    raw = {"id": 1, "keep": "everything"}
    assert shape_one(raw) == {"id": 1, "keep": "everything"}


def test_shape_one_accepts_sdk_object_not_just_dict():
    # Settings singletons call shape_one(sdk_object, to_view); it must coerce.
    out = shape_one(_Obj({"id": 9, "policy_blob": {"x": 1}}), _shaper)
    assert out["id"] == "9"
    assert out["policy_blob"] == {"x": 1}


def test_shape_many_preserves_every_field_per_row():
    rows = [
        {"id": 1, "a": "x", "deep": [1, 2]},
        {"id": 2, "b": "y"},
    ]
    out = shape_many(rows, _shaper)
    assert out[0]["a"] == "x" and out[0]["deep"] == [1, 2] and out[0]["id"] == "1"
    assert out[1]["b"] == "y" and out[1]["id"] == "2"


def test_shape_many_without_shaper_returns_full_records():
    rows = [{"id": 1, "everything": "kept"}]
    assert shape_many(rows) == [{"id": 1, "everything": "kept"}]


def test_view_schema_is_permissive():
    schema = _Highlight.output_schema()
    # Declared fields are documented ...
    assert "id" in schema["properties"] and "kind" in schema["properties"]
    # ... but the record may carry anything else (full passthrough contract).
    assert schema["additionalProperties"] is True


# =============================================================================
# Registry-wide invariant — the guard against re-introducing enumeration
# =============================================================================


def test_record_returning_tools_declare_no_output_view():
    """No tool may enumerate the attributes of a Zscaler API record.

    A resource's attribute set is owned by the API, not by this server. If a
    tool declares an ``output_view`` for a record, that view becomes a snapshot
    which goes stale the moment engineering adds a field — and, before #88, a
    whitelist that actively deleted the fields it didn't know about.

    Only results the SERVER constructs may declare a view. Adding a name to
    ``SYNTHETIC`` is a deliberate act: it asserts "this shape is ours, not the
    API's".
    """
    from zscaler_mcp.registry.registry import REGISTRY
    from zscaler_mcp.server import build_server

    SYNTHETIC = {
        "OperationResult",  # delete/bulk-op acknowledgement
        "Catalog",  # metadata catalogs (payload rides under `items`)
        "AggregateStatus",  # ZMS protection-status envelope
        "AnalysisStatus",  # ZDX analysis status envelope
        "DiscoverySettings",  # ZTW discovery settings envelope
        "NonceDetail",  # ZMS nonce envelope
        "StartedAnalysis",  # ZDX start-analysis acknowledgement
        "StartedTrace",  # ZDX start-trace acknowledgement
        "TotpSecrets",  # ZMS TOTP secrets envelope
    }

    build_server()  # importing the tool packages is what populates the registry
    offenders = sorted(
        f"{name} -> {spec.output_view.__name__}"
        for name in REGISTRY.names()
        if (spec := REGISTRY.get(name)).output_view is not None
        and spec.output_view.__name__ not in SYNTHETIC
    )
    assert not offenders, (
        "These tools enumerate an API record's attributes via output_view. "
        "Return the record verbatim instead (issue #88):\n  " + "\n  ".join(offenders)
    )
