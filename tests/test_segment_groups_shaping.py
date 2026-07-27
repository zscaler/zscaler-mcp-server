"""Tool-level contract tests for the ZPA segment-groups family.

Segment groups are the reference tool family, so they carry the worked example
of the post-#88 contract: the tool hands back the Zscaler API record verbatim,
and its inputs carry no verbosity knob. The registry-wide version of this
invariant lives in ``tests/test_shaping_helpers.py``.
"""

from zscaler_mcp.shaping import shape_many, shape_one
from zscaler_mcp.tools.zpa.segment_groups import (
    GetSegmentGroupInput,
    ListSegmentGroupsInput,
)

# A deliberately VERBOSE raw SDK object — every field of it must survive.
RAW_SDK_GROUP = {
    "id": "72058304855015425",
    "name": "Corp Apps",
    "enabled": True,
    "description": "Internal corporate applications",
    "creationTime": "1700000000",
    "modifiedTime": "1700000500",
    "modifiedBy": "72058304855015007",
    "configSpace": "DEFAULT",
    "microtenantId": "0",
    "href": "/mgmtconfig/v1/admin/customers/123/segmentGroup/72058304855015425",
    "applications": [
        {"id": "111", "name": "jira", "enabled": True, "domainNames": ["jira.corp"]},
        {"id": "222", "name": "wiki", "enabled": True, "domainNames": ["wiki.corp"]},
    ],
}


def test_get_returns_the_record_verbatim():
    assert shape_one(RAW_SDK_GROUP) == RAW_SDK_GROUP


def test_list_returns_every_row_verbatim():
    rows = [RAW_SDK_GROUP, {"id": "2", "name": "Other", "someFutureField": "kept"}]
    out = shape_many(rows)
    assert out == rows
    # A field this server has never heard of reaches the agent untouched — that
    # is the whole point: a new API attribute needs no code change here.
    assert out[1]["someFutureField"] == "kept"


def test_nested_members_are_not_flattened_or_counted_away():
    out = shape_one(RAW_SDK_GROUP)
    assert out["applications"] == RAW_SDK_GROUP["applications"]
    assert out["href"] == RAW_SDK_GROUP["href"]
    assert out["configSpace"] == "DEFAULT"


def test_inputs_carry_no_verbosity_knob():
    # There is no detail='summary'|'full' switch: tools always return the full
    # record, so the knob would only misrepresent what the caller gets.
    assert "detail" not in ListSegmentGroupsInput.model_fields
    assert "detail" not in GetSegmentGroupInput.model_fields


def test_inputs_still_declare_query_parameters():
    # The asymmetry the SDK models: query params ARE enumerated (the caller
    # cannot discover them otherwise); response attributes are not.
    assert {"search", "microtenant_id", "page", "page_size"} <= set(
        ListSegmentGroupsInput.model_fields
    )
