"""ZPA-specific helpers (product-scoped; see CLAUDE.md helper-file convention).

Only ZPA tools import from here. Append new ZPA helpers as sections in this file
rather than fragmenting into per-feature modules.

Country-code normalization (ISO alpha-2)
========================================
App Connector / Service Edge groups take a ``country_code`` in ISO 3166-1
alpha-2 form. v1 used ``pycountry`` fuzzy matching; v2 keeps its dependency
footprint lean (see ``ztw_helpers``) and accepts a bare alpha-2 code, uppercased.
Full country names are rejected with an actionable error.

Enrollment-certificate resolution
==================================
:func:`resolve_enrollment_cert_id` mirrors v1's connector-group cert resolution:
use an explicit id if given, else look the certificate up by name (default
"Connector"), raising if it can't be found.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Optional, Union

__all__ = [
    "normalize_iso_country_code",
    "resolve_enrollment_cert_id",
    "convert_v2_to_sdk_format",
    "convert_v1_to_v2_response",
    "normalize_v2_rule_response",
]

DEFAULT_ENROLLMENT_CERT_NAME = "Connector"


def normalize_iso_country_code(value: str) -> str:
    """Normalize a country input to ISO 3166-1 alpha-2 (uppercase).

    Accepts a 2-letter code only (e.g. 'ca', 'US'). Rejects full names with an
    actionable error telling the caller to use the alpha-2 code.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("country_code must be a non-empty string")
    code = value.strip().upper()
    if len(code) != 2 or not code.isalpha():
        raise ValueError(
            f"Invalid country_code '{value}'. Pass an ISO 3166-1 alpha-2 code "
            f"(e.g. 'CA', 'US', 'GB'), not a full country name."
        )
    return code


def resolve_enrollment_cert_id(
    client,
    *,
    enrollment_cert_id: Optional[str],
    enrollment_cert_name: Optional[str],
    default_name: str = DEFAULT_ENROLLMENT_CERT_NAME,
) -> Optional[str]:
    """Resolve the enrollment_cert_id for an App Connector / Service Edge group.

    1. Explicit ``enrollment_cert_id`` wins.
    2. Otherwise look up by name (``enrollment_cert_name`` or ``default_name``),
       raising ``ValueError`` if no exact (case-insensitive) match exists.
    """
    if enrollment_cert_id:
        return enrollment_cert_id

    name = enrollment_cert_name or default_name
    certs, _, err = client.zpa.enrollment_certificates.list_enrolment(query_params={"search": name})
    if err:
        raise RuntimeError(f"Failed to look up enrollment certificate '{name}': {err}")
    matches = [
        c for c in (certs or []) if getattr(c, "name", None) and c.name.lower() == name.lower()
    ]
    if not matches:
        raise ValueError(
            f"Enrollment certificate '{name}' not found in this tenant. "
            f"Pass enrollment_cert_id=<id> explicitly or create the certificate first."
        )
    return matches[0].id


# =============================================================================
# Policy-rule condition translation (ZPA Policy Access v1 <-> v2)
# =============================================================================
#
# These three functions are ported verbatim from v1's utils.py. They are the
# load-bearing translators that let the policy-rule tools accept the simplified
# v2 condition shape, convert it to the SDK tuple format on write, and reshape
# the v1-shaped API response back into v2 on read. They are pure (no pycountry).


def convert_v2_to_sdk_format(conditions: Any) -> list[Union[tuple, list]]:
    """Convert various condition formats to the SDK's expected v2 tuple format.

    Handles SDK-native tuples/lists, JSON strings, and v2 dict-shaped conditions
    (operands/operator). Flattens malformed entryValues, never drops entries.
    """
    if not conditions:
        return []

    if isinstance(conditions, str):
        try:
            conditions = json.loads(conditions)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for conditions: {e}")

    if isinstance(conditions, (list, tuple)) and all(
        isinstance(x, (list, tuple)) for x in conditions
    ):
        normalized_conditions: list[Union[tuple, list]] = []
        for cond in conditions:
            if len(cond) == 2 and cond[0] in ("AND", "OR"):
                op, inner = cond
                if isinstance(inner, (list, tuple)) and len(inner) == 2:
                    obj_type, values = inner
                    obj_type_lower = str(obj_type).lower()
                    if (
                        obj_type_lower == "platform"
                        and isinstance(values, list)
                        and all(isinstance(t, (list, tuple)) and len(t) == 2 for t in values)
                    ):
                        normalized_conditions.append((obj_type, values))
                        continue
                    if (
                        isinstance(values, list)
                        and len(values) == 1
                        and isinstance(values[0], list)
                        and all(isinstance(t, (list, tuple)) and len(t) == 2 for t in values[0])
                    ):
                        values = values[0]
                    normalized_conditions.append((op, (obj_type, values)))
                    continue
            elif len(cond) == 2:
                obj_type, values = cond
                if (
                    isinstance(values, list)
                    and len(values) == 1
                    and isinstance(values[0], list)
                    and all(isinstance(t, (list, tuple)) and len(t) == 2 for t in values[0])
                ):
                    values = values[0]
                normalized_conditions.append((obj_type, values))
                continue
            normalized_conditions.append(cond)
        return normalized_conditions

    if isinstance(conditions, list) and all(isinstance(x, dict) for x in conditions):
        converted: list[Union[tuple, list]] = []
        for cond in conditions:
            operator = cond.get("operator", "OR").upper()
            operands = cond.get("operands", [])
            for operand in operands:
                obj_type = (operand.get("objectType") or operand.get("object_type") or "").lower()
                values = operand.get("values", [])
                entry_values = operand.get("entryValues", operand.get("entry_values", []))
                if not obj_type:
                    continue
                if values:
                    converted.append((obj_type, values if isinstance(values, list) else [values]))
                    continue
                if entry_values:
                    if isinstance(entry_values, dict):
                        entry_values = [entry_values]
                    flattened = [
                        (ev["lhs"], ev["rhs"]) for ev in entry_values if "lhs" in ev and "rhs" in ev
                    ]
                    if obj_type == "chrome_enterprise":
                        for lhs, rhs in flattened:
                            converted.append((obj_type, lhs, rhs))
                    elif obj_type == "platform":
                        converted.append((obj_type, flattened))
                    else:
                        converted.append((operator, (obj_type, flattened)))
                    continue
                if "lhs" in operand and "rhs" in operand:
                    converted.append((obj_type, operand["lhs"], operand["rhs"]))
        return converted

    raise ValueError(f"Unsupported conditions format: {type(conditions)}")


_V1_TO_V2_VALUE_TYPES = {
    "APP",
    "APP_GROUP",
    "CONSOLE",
    "CHROME_POSTURE_PROFILE",
    "MACHINE_GRP",
    "LOCATION",
    "BRANCH_CONNECTOR_GROUP",
    "EDGE_CONNECTOR_GROUP",
    "CLIENT_TYPE",
    "USER_PORTAL",
    "PRIVILEGE_PORTAL",
}

_V1_TO_V2_ENTRY_TYPES = {
    "PLATFORM",
    "POSTURE",
    "TRUSTED_NETWORK",
    "SAML",
    "SCIM",
    "SCIM_GROUP",
    "COUNTRY_CODE",
    "RISK_FACTOR_TYPE",
    "CHROME_ENTERPRISE",
}


def convert_v1_to_v2_response(conditions: list[dict]) -> list[dict]:
    """Normalize a ZPA Policy Access v1 GET/POST response into v2 request shape.

    Mirrors ``ConvertV1ResponseToV2Request`` in the Terraform ZPA provider.
    Aggregation never crosses condition boundaries (AND/OR semantics depend on
    it). Object types and entry-value pairs are sorted for stable output.
    """
    if not conditions:
        return []

    v2_conditions: list[dict] = []
    for condition in conditions:
        cond_op = (condition.get("operator") or "OR").upper()
        operands = condition.get("operands") or []
        values_by_type: dict[str, list[str]] = defaultdict(list)
        entries_by_type: dict[str, list[dict[str, str]]] = defaultdict(list)

        for operand in operands:
            obj_type = (operand.get("objectType") or operand.get("object_type") or "").upper()
            if not obj_type:
                continue
            if obj_type in _V1_TO_V2_VALUE_TYPES:
                rhs = operand.get("rhs")
                if rhs is not None and str(rhs) != "":
                    values_by_type[obj_type].append(str(rhs))
            elif obj_type in _V1_TO_V2_ENTRY_TYPES:
                lhs = operand.get("lhs")
                rhs = operand.get("rhs")
                if lhs is not None and rhs is not None:
                    entries_by_type[obj_type].append({"lhs": str(lhs), "rhs": str(rhs)})

        new_operands: list[dict] = []
        for obj_type in sorted(values_by_type.keys()):
            unique_sorted = sorted(set(values_by_type[obj_type]))
            new_operands.append({"object_type": obj_type, "values": unique_sorted})
        for obj_type in sorted(entries_by_type.keys()):
            entries = sorted(entries_by_type[obj_type], key=lambda e: (e["lhs"], e["rhs"]))
            new_operands.append({"object_type": obj_type, "entry_values": entries})

        if not new_operands:
            continue
        v2_conditions.append({"operator": cond_op, "operands": new_operands})

    return v2_conditions


def normalize_v2_rule_response(sdk_object: Any, raw_response: Any) -> dict:
    """Stitch a v2 policy-rule write response into a complete, correct dict.

    The SDK's V2 Operand model drops the v1-shaped ``lhs``/``rhs`` the write
    endpoints return, so ``created.as_dict()["conditions"]`` loses its operand
    values. This recovers ``conditions`` from the raw response body and runs it
    through :func:`convert_v1_to_v2_response`. Falls back to the SDK dict when
    the raw response is missing/empty.
    """
    rule_data: dict = sdk_object.as_dict() if sdk_object is not None else {}
    if raw_response is None:
        return rule_data
    try:
        body = raw_response.get_body()
    except AttributeError:
        return rule_data
    if not isinstance(body, dict):
        return rule_data
    raw_conditions = body.get("conditions")
    if raw_conditions is None:
        return rule_data
    rule_data["conditions"] = convert_v1_to_v2_response(raw_conditions)
    return rule_data
