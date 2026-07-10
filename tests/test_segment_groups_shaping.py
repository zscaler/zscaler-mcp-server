"""Tests for the segment-groups shaping layer.

These exercise the *design work* (the shaper) directly, with no SDK or live
credentials — proving the curated-view pattern in isolation. The shaper takes a
raw SDK-style dict and returns the lean / full agent view.
"""

from zscaler_mcp.tools.zpa.segment_groups import (
    GetSegmentGroupInput,
    ListSegmentGroupsInput,
    SegmentGroupDetail,
    SegmentGroupSummary,
    shape_detail,
    shape_summary,
)

# A deliberately VERBOSE raw SDK object — the kind v1 would forward verbatim.
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


def test_summary_drops_provenance_and_transport_fields():
    view = shape_summary(RAW_SDK_GROUP)
    assert isinstance(view, SegmentGroupSummary)
    dumped = view.model_dump()
    # Curated identifying/decision/relational/explanatory fields are kept.
    assert dumped["id"] == "72058304855015425"
    assert dumped["name"] == "Corp Apps"
    assert dumped["enabled"] is True
    assert dumped["description"] == "Internal corporate applications"
    assert dumped["application_segment_count"] == 2
    # Provenance + transport noise is GONE from the agent-facing surface.
    for leaked in ("creationTime", "modifiedBy", "configSpace", "href", "applications"):
        assert leaked not in dumped


def test_detail_surfaces_relations_and_provenance_explicitly():
    view = shape_detail(RAW_SDK_GROUP)
    assert isinstance(view, SegmentGroupDetail)
    dumped = view.model_dump()
    assert dumped["application_segment_ids"] == ["111", "222"]
    assert dumped["microtenant_id"] == "0"
    assert dumped["created_time"] == "1700000000"
    assert dumped["modified_time"] == "1700000500"
    # Still no raw blob leakage.
    assert "applications" not in dumped
    assert "href" not in dumped


def test_shaper_is_resilient_to_missing_and_camel_or_snake_fields():
    # Sparse object, snake_case relational key, numeric id.
    sparse = {"id": 999, "name": "x", "app_segments": [{"id": 5}]}
    view = shape_detail(sparse)
    dumped = view.model_dump()
    assert dumped["id"] == "999"  # coerced to string
    assert dumped["enabled"] is False  # missing -> safe default
    assert dumped["application_segment_count"] == 1
    assert dumped["application_segment_ids"] == ["5"]


def test_view_rejects_uncurated_fields():
    # The AgentView base forbids extras, so a shaper that tries to leak an
    # un-curated SDK field fails loudly instead of silently widening the surface.
    import pytest

    with pytest.raises(Exception):
        SegmentGroupSummary(
            id="1", name="n", enabled=True, application_segment_count=0, href="leaked"
        )


def test_output_schema_is_derived_from_the_view():
    schema = SegmentGroupSummary.output_schema()
    assert schema["type"] == "object"
    props = schema["properties"]
    # Exactly the curated fields are advertised.
    assert set(props) == {
        "id",
        "name",
        "enabled",
        "description",
        "application_segment_count",
    }


def test_input_defaults_are_agent_first():
    # List defaults to the lean summary; get defaults to full.
    assert ListSegmentGroupsInput().detail == "summary"
    assert GetSegmentGroupInput(group_id="1").detail == "full"
