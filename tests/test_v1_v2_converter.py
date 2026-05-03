"""Regression tests for ``convert_v1_to_v2_response``.

The ZPA Policy Access API returns rule reads (and POST echo-backs) in v1
shape — flat ``{"objectType", "lhs", "rhs"}`` operands, with operands of
the same logical block split into multiple sibling entries inside the
same condition. The MCP server must reshape that into v2 shape so callers
can see the rule the same way they wrote it and round-trip through update.

These tests pin the converter against a real ZPA response captured from
the conditional-access skill (see ``local_dev/response_payload.json``)
and against per-condition aggregation, full type coverage, and edge cases
that previously regressed silently.
"""

import json
from pathlib import Path

import pytest

from zscaler_mcp.utils.utils import (
    convert_v1_to_v2_response,
    normalize_v2_rule_response,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_RESPONSE_FIXTURE = REPO_ROOT / "local_dev" / "response_payload.json"


# ---------------------------------------------------------------------------
# Real-world fixture — the conditional-access rule the skill creates
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_v1_response_conditions():
    if not REAL_RESPONSE_FIXTURE.exists():
        pytest.skip(f"Fixture missing: {REAL_RESPONSE_FIXTURE}")
    payload = json.loads(REAL_RESPONSE_FIXTURE.read_text())
    return payload["conditions"]


class TestRealConditionalAccessResponse:
    """The acceptance test for the asymmetric-API bug.

    The fixture is the actual v1 response the API returned for the
    conditional-access rule (APP, SCIM_GROUP, PLATFORM, POSTURE,
    RISK_FACTOR_TYPE x2, COUNTRY_CODE x2). The converter must rebuild
    the v2 shape the user originally sent.
    """

    def test_preserves_one_v2_condition_per_v1_condition(
        self, real_v1_response_conditions
    ):
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        assert len(v2) == len(real_v1_response_conditions) == 6

    def test_app_condition_uses_values_with_id(self, real_v1_response_conditions):
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        app_cond = next(c for c in v2 if c["operands"][0]["object_type"] == "APP")
        assert app_cond["operator"] == "OR"
        assert app_cond["operands"] == [
            {"object_type": "APP", "values": ["216196257331405442"]}
        ]

    def test_scim_group_condition_uses_entry_values(self, real_v1_response_conditions):
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        scim = next(
            c for c in v2 if c["operands"][0]["object_type"] == "SCIM_GROUP"
        )
        assert scim["operands"][0]["entry_values"] == [
            {"lhs": "216196257331285825", "rhs": "1404704"}
        ]

    def test_platform_condition_keeps_operator(self, real_v1_response_conditions):
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        platform = next(
            c for c in v2 if c["operands"][0]["object_type"] == "PLATFORM"
        )
        # PLATFORM must keep its operator (the previous code stripped it).
        assert "operator" in platform
        assert platform["operator"] == "OR"
        assert platform["operands"][0]["entry_values"] == [
            {"lhs": "windows", "rhs": "true"}
        ]

    def test_posture_condition_uses_udid(self, real_v1_response_conditions):
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        posture = next(
            c for c in v2 if c["operands"][0]["object_type"] == "POSTURE"
        )
        assert posture["operands"][0]["entry_values"] == [
            {"lhs": "13ba3d97-aefb-4acc-9e54-6cc230dee4a5", "rhs": "true"}
        ]

    def test_risk_factor_two_levels_aggregate_within_one_condition(
        self, real_v1_response_conditions
    ):
        """Two RISK_FACTOR_TYPE operands inside one v1 condition (LOW + UNKNOWN)
        must aggregate into a single v2 operand block with both entries."""
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        risk_conds = [
            c
            for c in v2
            if c["operands"][0]["object_type"] == "RISK_FACTOR_TYPE"
        ]
        assert len(risk_conds) == 1
        entries = risk_conds[0]["operands"][0]["entry_values"]
        assert {"lhs": "ZIA", "rhs": "LOW"} in entries
        assert {"lhs": "ZIA", "rhs": "UNKNOWN"} in entries
        assert len(entries) == 2

    def test_country_code_two_countries_aggregate_within_one_condition(
        self, real_v1_response_conditions
    ):
        """US + CA in the same v1 condition must collapse to one v2 operand
        with two entry_values (OR within the block)."""
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        country_conds = [
            c
            for c in v2
            if c["operands"][0]["object_type"] == "COUNTRY_CODE"
        ]
        assert len(country_conds) == 1
        entries = country_conds[0]["operands"][0]["entry_values"]
        assert {"lhs": "US", "rhs": "true"} in entries
        assert {"lhs": "CA", "rhs": "true"} in entries
        assert len(entries) == 2

    def test_no_operand_carries_empty_values_or_entry_values(
        self, real_v1_response_conditions
    ):
        """Regression for the empty-arrays bug observed end-to-end (the
        agent's narration: 'API returned conditions with empty values
        and entry_values arrays')."""
        v2 = convert_v1_to_v2_response(real_v1_response_conditions)
        for cond in v2:
            for operand in cond["operands"]:
                if "values" in operand:
                    assert operand["values"], (
                        f"Empty values list in operand: {operand}"
                    )
                if "entry_values" in operand:
                    assert operand["entry_values"], (
                        f"Empty entry_values list in operand: {operand}"
                    )


# ---------------------------------------------------------------------------
# Per-condition AND/OR semantics — the most dangerous regression
# ---------------------------------------------------------------------------


class TestConditionBoundariesArePreserved:
    """The previous implementation aggregated across all conditions by
    (operator, objectType), which collapsed the AND-vs-OR distinction.

    Two separate POSTURE conditions in v1 = AND between them.
    Two POSTURE operands in one condition = OR within them.
    The converter must NOT merge them.
    """

    def test_two_separate_posture_conditions_remain_separate(self):
        v1 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "objectType": "POSTURE",
                        "lhs": "udid-A",
                        "rhs": "true",
                    }
                ],
            },
            {
                "operator": "OR",
                "operands": [
                    {
                        "objectType": "POSTURE",
                        "lhs": "udid-B",
                        "rhs": "true",
                    }
                ],
            },
        ]
        v2 = convert_v1_to_v2_response(v1)
        assert len(v2) == 2, (
            "Two separate POSTURE conditions must NOT be collapsed; "
            "doing so flips AND into OR."
        )
        assert v2[0]["operands"][0]["entry_values"] == [
            {"lhs": "udid-A", "rhs": "true"}
        ]
        assert v2[1]["operands"][0]["entry_values"] == [
            {"lhs": "udid-B", "rhs": "true"}
        ]

    def test_two_posture_operands_in_one_condition_aggregate_to_one_block(self):
        v1 = [
            {
                "operator": "OR",
                "operands": [
                    {"objectType": "POSTURE", "lhs": "udid-A", "rhs": "true"},
                    {"objectType": "POSTURE", "lhs": "udid-B", "rhs": "true"},
                ],
            }
        ]
        v2 = convert_v1_to_v2_response(v1)
        assert len(v2) == 1
        entries = v2[0]["operands"][0]["entry_values"]
        assert {"lhs": "udid-A", "rhs": "true"} in entries
        assert {"lhs": "udid-B", "rhs": "true"} in entries
        assert len(entries) == 2


# ---------------------------------------------------------------------------
# Object-type coverage — types previously dropped
# ---------------------------------------------------------------------------


class TestExtendedObjectTypeCoverage:
    """The original VALUE/ENTRY sets were missing 8 object types that the
    Terraform provider handles. Operands of those types were silently
    dropped. These tests pin the full Terraform-equivalent coverage.
    """

    @pytest.mark.parametrize(
        "object_type",
        [
            "CONSOLE",
            "CHROME_POSTURE_PROFILE",
            "LOCATION",
            "BRANCH_CONNECTOR_GROUP",
            "EDGE_CONNECTOR_GROUP",
            "USER_PORTAL",
            "PRIVILEGE_PORTAL",
        ],
    )
    def test_value_type_round_trips(self, object_type):
        v1 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "objectType": object_type,
                        "lhs": "id",
                        "rhs": "the-id-123",
                    }
                ],
            }
        ]
        v2 = convert_v1_to_v2_response(v1)
        assert v2 == [
            {
                "operator": "OR",
                "operands": [
                    {"object_type": object_type, "values": ["the-id-123"]}
                ],
            }
        ]

    def test_chrome_enterprise_entry_type_round_trips(self):
        v1 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "objectType": "CHROME_ENTERPRISE",
                        "lhs": "managed",
                        "rhs": "true",
                    }
                ],
            }
        ]
        v2 = convert_v1_to_v2_response(v1)
        assert v2 == [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "CHROME_ENTERPRISE",
                        "entry_values": [{"lhs": "managed", "rhs": "true"}],
                    }
                ],
            }
        ]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_conditions_returns_empty_list(self):
        assert convert_v1_to_v2_response([]) == []
        assert convert_v1_to_v2_response(None) == []

    def test_unknown_object_type_is_dropped(self):
        v1 = [
            {
                "operator": "OR",
                "operands": [
                    {"objectType": "UNRECOGNIZED_TYPE", "lhs": "x", "rhs": "y"}
                ],
            }
        ]
        # Unknown types are dropped; if that leaves the condition empty,
        # the condition itself is dropped to avoid emitting bare operators.
        assert convert_v1_to_v2_response(v1) == []

    def test_mixed_value_and_entry_in_same_condition_emits_both(self):
        v1 = [
            {
                "operator": "OR",
                "operands": [
                    {"objectType": "APP", "lhs": "id", "rhs": "app-1"},
                    {"objectType": "POSTURE", "lhs": "udid-x", "rhs": "true"},
                ],
            }
        ]
        v2 = convert_v1_to_v2_response(v1)
        assert len(v2) == 1
        operands = v2[0]["operands"]
        assert {"object_type": "APP", "values": ["app-1"]} in operands
        assert {
            "object_type": "POSTURE",
            "entry_values": [{"lhs": "udid-x", "rhs": "true"}],
        } in operands

    def test_duplicate_value_ids_within_condition_dedupe_and_sort(self):
        v1 = [
            {
                "operator": "OR",
                "operands": [
                    {"objectType": "APP", "lhs": "id", "rhs": "z-id"},
                    {"objectType": "APP", "lhs": "id", "rhs": "a-id"},
                    {"objectType": "APP", "lhs": "id", "rhs": "z-id"},
                ],
            }
        ]
        v2 = convert_v1_to_v2_response(v1)
        assert v2[0]["operands"][0]["values"] == ["a-id", "z-id"]

    def test_default_operator_is_or_when_missing(self):
        v1 = [
            {
                "operands": [
                    {"objectType": "APP", "lhs": "id", "rhs": "app-1"}
                ]
            }
        ]
        v2 = convert_v1_to_v2_response(v1)
        assert v2[0]["operator"] == "OR"

    def test_object_type_matches_camelcase_or_snakecase(self):
        v1 = [
            {
                "operator": "OR",
                "operands": [{"object_type": "APP", "lhs": "id", "rhs": "x"}],
            }
        ]
        assert convert_v1_to_v2_response(v1) == [
            {
                "operator": "OR",
                "operands": [{"object_type": "APP", "values": ["x"]}],
            }
        ]


# ---------------------------------------------------------------------------
# normalize_v2_rule_response — bypass the lossy SDK V2 Operand model
# ---------------------------------------------------------------------------


class _FakeSDKObject:
    """Stand-in for the rule object returned by ``add_*_rule_v2``.

    Mirrors the bug exactly: top-level fields survive ``as_dict()`` but
    ``conditions`` operands lose their ``lhs``/``rhs`` data because the
    V2 ``Operand`` model only reads ``values``/``entryValues`` from the
    v1-shaped API response.
    """

    def __init__(self, snake_dict):
        self._dict = snake_dict

    def as_dict(self):
        return dict(self._dict)


class _FakeRawResponse:
    """Stand-in for ``ZscalerAPIResponse``. Returns the raw v1 body."""

    def __init__(self, body):
        self._body = body

    def get_body(self):
        return self._body


class TestNormalizeV2RuleResponseBypass:
    """Pin the workaround for the SDK's lossy V2 ``Operand`` model.

    The acceptance scenario:

    1. The MCP tool POSTs a v2 rule.
    2. ZPA echoes it back v1-shaped (operands carry ``lhs``/``rhs``).
    3. The SDK's V2 ``Operand`` model deserializes that response, drops
       ``lhs``/``rhs``, and ``created.as_dict()["conditions"]`` ends up
       with empty operand bodies.
    4. ``normalize_v2_rule_response`` reads the raw body via
       ``response.get_body()`` and rebuilds the conditions in v2 shape.
    """

    def test_recovers_conditions_when_sdk_dict_is_empty(self):
        sdk_dict = {
            "id": "rule-123",
            "name": "DataCenter Switches SSH",
            "action": "ALLOW",
            "conditions": [],  # ← the lossy SDK output
        }
        raw_body = {
            "id": "rule-123",
            "conditions": [
                {
                    "operator": "OR",
                    "operands": [
                        {"objectType": "APP", "lhs": "id", "rhs": "app-1"}
                    ],
                },
                {
                    "operator": "OR",
                    "operands": [
                        {"objectType": "POSTURE", "lhs": "udid-x", "rhs": "true"}
                    ],
                },
            ],
        }

        result = normalize_v2_rule_response(
            _FakeSDKObject(sdk_dict), _FakeRawResponse(raw_body)
        )

        assert result["id"] == "rule-123"
        assert result["name"] == "DataCenter Switches SSH"
        assert result["action"] == "ALLOW"
        assert result["conditions"] == [
            {
                "operator": "OR",
                "operands": [{"object_type": "APP", "values": ["app-1"]}],
            },
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "POSTURE",
                        "entry_values": [{"lhs": "udid-x", "rhs": "true"}],
                    }
                ],
            },
        ]

    def test_recovers_full_real_world_response(self, real_v1_response_conditions):
        """End-to-end: the SDK dict is empty; the raw body has the full v1
        conditional-access response. Result must match the converter's
        output for the same conditions."""
        sdk_dict = {
            "id": "rule-456",
            "name": "DataCenter Switches SSH - Conditional Access",
            "conditions": [],
        }
        raw_body = {"conditions": real_v1_response_conditions}

        result = normalize_v2_rule_response(
            _FakeSDKObject(sdk_dict), _FakeRawResponse(raw_body)
        )

        assert result["conditions"] == convert_v1_to_v2_response(
            real_v1_response_conditions
        )
        assert len(result["conditions"]) == len(real_v1_response_conditions)

    def test_preserves_top_level_fields_unchanged(self):
        sdk_dict = {
            "id": "x",
            "name": "n",
            "action": "ALLOW",
            "rule_order": "1",
            "policy_type": "1",
            "operator": "AND",
            "conditions": [],
        }
        raw_body = {
            "conditions": [
                {
                    "operator": "OR",
                    "operands": [
                        {"objectType": "APP", "lhs": "id", "rhs": "a"}
                    ],
                }
            ]
        }
        result = normalize_v2_rule_response(
            _FakeSDKObject(sdk_dict), _FakeRawResponse(raw_body)
        )
        assert result["id"] == "x"
        assert result["name"] == "n"
        assert result["action"] == "ALLOW"
        assert result["rule_order"] == "1"
        assert result["policy_type"] == "1"
        assert result["operator"] == "AND"

    def test_no_raw_response_falls_back_to_sdk_dict(self):
        sdk_dict = {"id": "x", "conditions": []}
        result = normalize_v2_rule_response(_FakeSDKObject(sdk_dict), None)
        assert result == {"id": "x", "conditions": []}

    def test_raw_response_without_get_body_falls_back(self):
        class NoGetBody:
            pass

        sdk_dict = {"id": "x", "conditions": []}
        result = normalize_v2_rule_response(_FakeSDKObject(sdk_dict), NoGetBody())
        assert result == {"id": "x", "conditions": []}

    def test_raw_body_not_a_dict_falls_back(self):
        sdk_dict = {"id": "x", "conditions": []}
        result = normalize_v2_rule_response(
            _FakeSDKObject(sdk_dict), _FakeRawResponse("plain text body")
        )
        assert result == {"id": "x", "conditions": []}

    def test_raw_body_without_conditions_key_falls_back(self):
        sdk_dict = {"id": "x", "conditions": []}
        result = normalize_v2_rule_response(
            _FakeSDKObject(sdk_dict), _FakeRawResponse({"id": "x"})
        )
        assert result == {"id": "x", "conditions": []}

    def test_none_sdk_object_returns_dict_with_recovered_conditions(self):
        raw_body = {
            "conditions": [
                {
                    "operator": "OR",
                    "operands": [
                        {"objectType": "APP", "lhs": "id", "rhs": "a"}
                    ],
                }
            ]
        }
        result = normalize_v2_rule_response(None, _FakeRawResponse(raw_body))
        assert result == {
            "conditions": [
                {
                    "operator": "OR",
                    "operands": [{"object_type": "APP", "values": ["a"]}],
                }
            ]
        }
