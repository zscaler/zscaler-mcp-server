import pytest
from zscaler_mcp.common.zpa_helpers import convert_v1_to_v2_response

def test_v1_input_standard_types():
    """Verify standard v1 payload aggregation works as it originally did."""
    v1_input = [{
        "operator": "OR",
        "operands": [
            {"object_type": "APP", "rhs": "123"},
            {"object_type": "APP", "rhs": "456"},
            {"object_type": "SAML", "lhs": "idp1", "rhs": "grp1"}
        ]
    }]
    expected = [{
        "operator": "OR",
        "operands": [
            {"object_type": "APP", "values": ["123", "456"]},
            {"object_type": "SAML", "entry_values": [{"lhs": "idp1", "rhs": "grp1"}]}
        ]
    }]
    assert convert_v1_to_v2_response(v1_input) == expected

def test_v2_input_passthrough():
    """Bug 1: Verify already-v2 payloads are passed through without modification."""
    v2_input = [{
        "operator": "AND",
        "operands": [
            {"object_type": "APP", "values": ["72058304855090128"]},
            {"object_type": "SCIM_GROUP", "entry_values": [{"lhs": "idp-1", "rhs": "grp-1"}]}
        ]
    }]
    # Should return identical output, not an empty list
    assert convert_v1_to_v2_response(v2_input) == v2_input

def test_unknown_object_types():
        """Bug 2: Verify unlisted object types are preserved based on lhs/rhs presence."""
        unknown_input = [{
            "operator": "OR",
            "operands": [
                {"object_type": "UNKNOWN_VALUE_TYPE", "rhs": "999"},
                {"object_type": "UNKNOWN_ENTRY_TYPE", "lhs": "custom-lhs", "rhs": "custom-rhs"}
            ]
        }]
        expected = [{
            "operator": "OR",
            "operands": [
                {"object_type": "UNKNOWN_VALUE_TYPE", "values": ["999"]},
                {"object_type": "UNKNOWN_ENTRY_TYPE", "entry_values": [{"lhs": "custom-lhs", "rhs": "custom-rhs"}]}
            ]
        }]
        assert convert_v1_to_v2_response(unknown_input) == expected

def test_mixed_v1_and_v2_inputs():
    """Verify a mix of v1 and v2 operands in the same condition are handled correctly."""
    mixed_input = [{
        "operator": "OR",
        "operands": [
            {"object_type": "APP", "values": ["111"]},  # v2
            {"object_type": "APP", "rhs": "222"},       # v1
        ]
    }]
    expected = [{
        "operator": "OR",
        "operands": [
            {"object_type": "APP", "values": ["111"]},
            {"object_type": "APP", "values": ["222"]}
        ]
    }]
    assert convert_v1_to_v2_response(mixed_input) == expected

def test_empty_and_invalid_operands():
    """Verify empty conditions and operands missing object_types are handled safely."""
    invalid_input = [{
        "operator": "OR",
        "operands": [
            {}, 
            {"rhs": "missing-type"}
        ]
    }]
    assert convert_v1_to_v2_response([]) == []
    assert convert_v1_to_v2_response(invalid_input) == []