"""Tests for the shared wire-encoding layer (DESIGN.md §5 Pillar D).

The encoder is the SINGLE decision point for JSON-vs-CSV across all tools, so
its correctness + safety rules are tested directly.
"""

import csv
import io
import json

import pytest

from zscaler_mcp.encoding import WireFormat, encode

FLAT_ROWS = [
    {"id": "1", "name": "Corp Apps", "enabled": True, "count": 12},
    {"id": "2", "name": "Dev Tools", "enabled": False, "count": 3},
]


def _parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_auto_uses_csv_for_flat_list():
    out = encode(FLAT_ROWS, fmt=WireFormat.AUTO)
    assert out.splitlines()[0] == "id,name,enabled,count"  # header once
    parsed = _parse_csv(out)
    assert parsed[0]["name"] == "Corp Apps"
    assert parsed[1]["enabled"] == "false"


def test_auto_uses_json_for_single_object():
    out = encode({"id": "1", "name": "x", "enabled": True}, fmt=WireFormat.AUTO)
    assert json.loads(out)["name"] == "x"  # round-trips as JSON


def test_auto_falls_back_to_json_when_rows_have_nested_values():
    # A list whose rows contain a nested list/dict must NOT be CSV-encoded —
    # CSV cannot represent nesting and we refuse to drop structure.
    nested = [{"id": "1", "apps": [{"id": "a"}]}]
    out = encode(nested, fmt=WireFormat.AUTO)
    assert json.loads(out)[0]["apps"][0]["id"] == "a"


def test_forced_csv_falls_back_to_json_for_nested_data():
    nested = [{"id": "1", "apps": [{"id": "a"}]}]
    out = encode(nested, fmt=WireFormat.CSV)
    assert json.loads(out)[0]["apps"] == [{"id": "a"}]  # fell back, no loss


def test_forced_json_never_uses_csv_even_for_flat_list():
    out = encode(FLAT_ROWS, fmt=WireFormat.JSON)
    assert json.loads(out)[0]["id"] == "1"


def test_csv_quotes_values_containing_commas_and_quotes():
    rows = [{"id": "1", "name": 'Apps, Inc. "HQ"'}]
    out = encode(rows, fmt=WireFormat.AUTO)
    # Round-trips cleanly despite the comma + embedded quotes.
    assert _parse_csv(out)[0]["name"] == 'Apps, Inc. "HQ"'


def test_csv_handles_rows_with_missing_optional_fields():
    rows = [{"id": "1", "name": "a", "desc": "hi"}, {"id": "2", "name": "b"}]
    out = encode(rows, fmt=WireFormat.AUTO)
    parsed = _parse_csv(out)
    assert parsed[1]["desc"] == ""  # missing cell emitted empty, not dropped


def test_empty_list_encodes_as_json_not_an_empty_csv():
    out = encode([], fmt=WireFormat.AUTO)
    assert json.loads(out) == []


def test_none_values_render_as_empty_csv_cell():
    rows = [{"id": "1", "description": None}]
    out = encode(rows, fmt=WireFormat.AUTO)
    assert _parse_csv(out)[0]["description"] == ""


def test_invalid_format_string_raises():
    with pytest.raises(ValueError):
        encode(FLAT_ROWS, fmt="yaml")
