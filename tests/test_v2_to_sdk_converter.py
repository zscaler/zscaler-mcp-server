"""Regression tests for ``convert_v2_to_sdk_format``.

These tests pin the output shape the MCP tool sends into the Zscaler SDK's
``policies._create_conditions_v2``. The SDK accepts a *simplified tuple
format* (see ``zscaler-sdk-python/local_dev/OneAPI/zpa_dev/policy_access/
access_rule_v2.py``) with a few non-uniform shapes:

- ``(object_type, [<id>, ...])`` for ID-typed objects
  (APP, APP_GROUP, CLIENT_TYPE, CHROME_POSTURE_PROFILE, MACHINE_GRP,
   CONSOLE, LOCATION, USER_PORTAL).

- ``(object_type, [(lhs, rhs), ...])`` (bare) for PLATFORM only.

- ``(operator, (object_type, [(lhs, rhs), ...]))`` (operator-wrapped) for
  POSTURE, TRUSTED_NETWORK, COUNTRY_CODE, RISK_FACTOR_TYPE, SAML, SCIM,
  SCIM_GROUP. The SDK aggregates these by ``(operator, object_type)``.

- ``(chrome_enterprise, attribute, value)`` — *flat 3-tuple, scalar values,
  no operator wrapper*. Only chrome_enterprise breaks the list-of-tuples
  pattern.

Agents send conditions as v2 dicts (``{"operator", "operands": [...]}``);
the converter must translate each operand into the matching SDK tuple
shape so the SDK's ``_create_conditions_v2`` produces the correct request
body to ZPA.
"""

import pytest

from zscaler_mcp.utils.utils import convert_v2_to_sdk_format

# ---------------------------------------------------------------------------
# ID-typed objects → bare 2-tuple, list of IDs
# ---------------------------------------------------------------------------


class TestIdTypedObjectsProduceBareTwoTuple:
    @pytest.mark.parametrize(
        "object_type",
        [
            "APP",
            "APP_GROUP",
            "CLIENT_TYPE",
            "CHROME_POSTURE_PROFILE",
            "MACHINE_GRP",
            "CONSOLE",
            "LOCATION",
            "USER_PORTAL",
        ],
    )
    def test_single_id_emits_bare_2_tuple(self, object_type):
        v2 = [
            {
                "operator": "OR",
                "operands": [{"object_type": object_type, "values": ["id-1"]}],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            (object_type.lower(), ["id-1"])
        ]

    def test_multiple_ids_preserve_order(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {"object_type": "MACHINE_GRP", "values": ["mg-1", "mg-2", "mg-3"]}
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("machine_grp", ["mg-1", "mg-2", "mg-3"])
        ]

    def test_app_and_app_group_emit_separately_for_sdk_to_group(self):
        # The SDK groups APP + APP_GROUP into one operands block; the
        # converter just emits one tuple per agent operand and lets the SDK
        # aggregate. Verify both tuples land in the output list.
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {"object_type": "APP", "values": ["app-1"]},
                    {"object_type": "APP_GROUP", "values": ["ag-1"]},
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("app", ["app-1"]),
            ("app_group", ["ag-1"]),
        ]


# ---------------------------------------------------------------------------
# Attribute-typed objects with operator wrapper
# ---------------------------------------------------------------------------


class TestAttributeTypedObjectsAreOperatorWrapped:
    @pytest.mark.parametrize(
        "object_type",
        [
            "POSTURE",
            "TRUSTED_NETWORK",
            "COUNTRY_CODE",
            "RISK_FACTOR_TYPE",
            "SAML",
            "SCIM",
            "SCIM_GROUP",
        ],
    )
    def test_single_entry_pair_emits_operator_wrapped_tuple(self, object_type):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": object_type,
                        "entry_values": [{"lhs": "L", "rhs": "R"}],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("OR", (object_type.lower(), [("L", "R")]))
        ]

    def test_and_operator_is_preserved(self):
        v2 = [
            {
                "operator": "AND",
                "operands": [
                    {
                        "object_type": "SCIM_GROUP",
                        "entry_values": [{"lhs": "idp", "rhs": "gid"}],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("AND", ("scim_group", [("idp", "gid")]))
        ]

    def test_default_operator_is_or_when_missing(self):
        # The SDK defaults missing operators to "OR" — match that so we
        # don't silently emit AND when the agent omits the operator.
        v2 = [
            {
                "operands": [
                    {
                        "object_type": "POSTURE",
                        "entry_values": [{"lhs": "u", "rhs": "true"}],
                    }
                ]
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("OR", ("posture", [("u", "true")]))
        ]

    def test_multiple_entry_pairs_aggregate_into_one_tuple(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "RISK_FACTOR_TYPE",
                        "entry_values": [
                            {"lhs": "ZIA", "rhs": "LOW"},
                            {"lhs": "ZIA", "rhs": "UNKNOWN"},
                        ],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            (
                "OR",
                (
                    "risk_factor_type",
                    [("ZIA", "LOW"), ("ZIA", "UNKNOWN")],
                ),
            )
        ]


# ---------------------------------------------------------------------------
# PLATFORM is bare (no operator wrapper) — special per SDK contract
# ---------------------------------------------------------------------------


class TestPlatformIsBare:
    def test_single_platform_emits_bare_tuple(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "PLATFORM",
                        "entry_values": [{"lhs": "windows", "rhs": "true"}],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("platform", [("windows", "true")])
        ]

    def test_multiple_platforms_aggregate_into_one_bare_tuple(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "PLATFORM",
                        "entry_values": [
                            {"lhs": "windows", "rhs": "true"},
                            {"lhs": "mac", "rhs": "true"},
                            {"lhs": "linux", "rhs": "true"},
                        ],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            (
                "platform",
                [("windows", "true"), ("mac", "true"), ("linux", "true")],
            )
        ]


# ---------------------------------------------------------------------------
# CHROME_ENTERPRISE — flat 3-tuple, no operator wrapper, scalar values
# ---------------------------------------------------------------------------


class TestChromeEnterpriseEmitsFlat3Tuple:
    """The SDK contract for CHROME_ENTERPRISE is the only non-uniform shape:

    ``("chrome_enterprise", attribute, value)`` — bare 3-tuple, scalar
    lhs/rhs, NO operator wrapper. Emitting the usual operator-wrapped
    list-of-tuples shape causes the SDK to put a list in the ``lhs`` field
    of the request body (broken JSON output).
    """

    def test_single_attribute_emits_flat_3_tuple(self):
        v2 = [
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
        assert convert_v2_to_sdk_format(v2) == [
            ("chrome_enterprise", "managed", "true")
        ]

    def test_no_operator_wrapper_even_with_explicit_and(self):
        v2 = [
            {
                "operator": "AND",
                "operands": [
                    {
                        "object_type": "CHROME_ENTERPRISE",
                        "entry_values": [{"lhs": "managed", "rhs": "true"}],
                    }
                ],
            }
        ]
        # Even though the agent specified AND, the SDK contract for
        # chrome_enterprise is a flat 3-tuple with no operator wrapper.
        assert convert_v2_to_sdk_format(v2) == [
            ("chrome_enterprise", "managed", "true")
        ]

    def test_multiple_attributes_emit_one_flat_3_tuple_each(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "CHROME_ENTERPRISE",
                        "entry_values": [
                            {"lhs": "managed", "rhs": "true"},
                            {"lhs": "device_serial_number", "rhs": "ABC123"},
                        ],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("chrome_enterprise", "managed", "true"),
            ("chrome_enterprise", "device_serial_number", "ABC123"),
        ]

    def test_v1_style_lhs_rhs_also_emits_flat_3_tuple(self):
        # If the agent sends an operand as flat lhs/rhs (instead of
        # entry_values), the existing v1-style path emits the same shape.
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "CHROME_ENTERPRISE",
                        "lhs": "managed",
                        "rhs": "true",
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("chrome_enterprise", "managed", "true")
        ]


# ---------------------------------------------------------------------------
# Real-world conditional-access rule (the user's actual rule)
# ---------------------------------------------------------------------------


class TestRealWorldConditionalAccessRule:
    """The exact 6-condition payload from ``local_dev/request_payload.json``.

    Mirrors the conditional-access rule the agent actually creates:
    APP + SCIM_GROUP + PLATFORM + POSTURE + RISK_FACTOR_TYPE + COUNTRY_CODE.
    """

    def test_all_six_conditions_translate_to_expected_sdk_tuples(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {"object_type": "APP", "values": ["216196257331405446"]}
                ],
            },
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "SCIM_GROUP",
                        "entry_values": [
                            {"lhs": "216196257331285825", "rhs": "1404704"}
                        ],
                    }
                ],
            },
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "PLATFORM",
                        "entry_values": [{"lhs": "windows", "rhs": "true"}],
                    }
                ],
            },
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "POSTURE",
                        "entry_values": [
                            {
                                "lhs": "13ba3d97-aefb-4acc-9e54-6cc230dee4a5",
                                "rhs": "true",
                            }
                        ],
                    }
                ],
            },
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "RISK_FACTOR_TYPE",
                        "entry_values": [
                            {"lhs": "ZIA", "rhs": "LOW"},
                            {"lhs": "ZIA", "rhs": "UNKNOWN"},
                        ],
                    }
                ],
            },
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "COUNTRY_CODE",
                        "entry_values": [
                            {"lhs": "US", "rhs": "true"},
                            {"lhs": "CA", "rhs": "true"},
                        ],
                    }
                ],
            },
        ]

        assert convert_v2_to_sdk_format(v2) == [
            ("app", ["216196257331405446"]),
            ("OR", ("scim_group", [("216196257331285825", "1404704")])),
            ("platform", [("windows", "true")]),
            (
                "OR",
                ("posture", [("13ba3d97-aefb-4acc-9e54-6cc230dee4a5", "true")]),
            ),
            (
                "OR",
                (
                    "risk_factor_type",
                    [("ZIA", "LOW"), ("ZIA", "UNKNOWN")],
                ),
            ),
            (
                "OR",
                (
                    "country_code",
                    [("US", "true"), ("CA", "true")],
                ),
            ),
        ]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_input_returns_empty_list(self):
        assert convert_v2_to_sdk_format(None) == []
        assert convert_v2_to_sdk_format([]) == []

    def test_missing_object_type_skips_operand(self):
        v2 = [{"operator": "OR", "operands": [{"values": ["x"]}]}]
        assert convert_v2_to_sdk_format(v2) == []

    def test_camelcase_object_type_is_accepted(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [{"objectType": "APP", "values": ["id"]}],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [("app", ["id"])]

    def test_camelcase_entry_values_is_accepted(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "objectType": "POSTURE",
                        "entryValues": [{"lhs": "u", "rhs": "true"}],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [
            ("OR", ("posture", [("u", "true")]))
        ]

    def test_values_takes_precedence_over_entry_values(self):
        # If both are accidentally populated the converter prefers values
        # because the ID-shape wins for ID-typed objects. This pins the
        # behavior to avoid silent surprises.
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {
                        "object_type": "APP",
                        "values": ["id-1"],
                        "entry_values": [{"lhs": "ignored", "rhs": "ignored"}],
                    }
                ],
            }
        ]
        assert convert_v2_to_sdk_format(v2) == [("app", ["id-1"])]

    def test_v1_style_lhs_rhs_falls_back_for_attribute_types(self):
        v2 = [
            {
                "operator": "OR",
                "operands": [
                    {"object_type": "POSTURE", "lhs": "udid", "rhs": "true"}
                ],
            }
        ]
        # Bare 3-tuple — the SDK still routes this correctly because
        # ``len(values)==2 and not isinstance(values[0], list)``.
        assert convert_v2_to_sdk_format(v2) == [
            ("posture", "udid", "true")
        ]

    def test_already_sdk_tuple_format_passes_through(self):
        # The converter is forgiving of pre-shaped SDK input (used by
        # callers that build the format directly).
        sdk_input = [
            ("app", ["id-1"]),
            ("OR", ("posture", [("u", "true")])),
        ]
        assert convert_v2_to_sdk_format(sdk_input) == [
            ("app", ["id-1"]),
            ("OR", ("posture", [("u", "true")])),
        ]
