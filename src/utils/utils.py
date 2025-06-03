from typing import Union, List, Dict, Any, Tuple
from collections import defaultdict
import json

# def convert_v2_to_sdk_format(conditions: Any) -> List[Union[Tuple, List]]:
#     """
#     Convert various condition formats to the SDK's expected v2 format.
#     Handles:
#     - SDK-native tuple/list format
#     - JSON string (parsed into list)
#     - API v1-style dicts (operands/operator)
#     Also flattens malformed entryValues and ensures nothing is dropped.
#     """
#     if not conditions:
#         return []

#     # ✅ Step 1: Parse JSON string if passed
#     if isinstance(conditions, str):
#         try:
#             conditions = json.loads(conditions)
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Invalid JSON string for conditions: {e}")

#     # ✅ Step 2: Normalize SDK-style tuples/lists
#     if isinstance(conditions, (list, tuple)) and all(isinstance(x, (list, tuple)) for x in conditions):
#         normalized_conditions = []

#         for cond in conditions:
#             if len(cond) == 2 and cond[0] in ("AND", "OR"):
#                 op, inner = cond
#                 if isinstance(inner, (list, tuple)) and len(inner) == 2:
#                     obj_type, values = inner

#                     # ✅ Flatten [[("lhs", "rhs")]] to [("lhs", "rhs")]
#                     if (
#                         isinstance(values, list)
#                         and len(values) == 1
#                         and isinstance(values[0], list)
#                         and all(isinstance(t, (list, tuple)) and len(t) == 2 for t in values[0])
#                     ):
#                         values = values[0]

#                     normalized_conditions.append((op, (obj_type, values)))

#             elif len(cond) == 2:
#                 obj_type, values = cond

#                 # ✅ Flatten [[("lhs", "rhs")]] to [("lhs", "rhs")]
#                 if (
#                     isinstance(values, list)
#                     and len(values) == 1
#                     and isinstance(values[0], list)
#                     and all(isinstance(t, (list, tuple)) and len(t) == 2 for t in values[0])
#                 ):
#                     values = values[0]

#                 normalized_conditions.append((obj_type, values))

#             else:
#                 normalized_conditions.append(cond)

#         return normalized_conditions

#     # ✅ Step 3: Convert API v1-style response (dicts)
#     if isinstance(conditions, list) and all(isinstance(x, dict) for x in conditions):
#         converted = []
#         for cond in conditions:
#             operator = cond.get("operator", "AND").upper()
#             operands = cond.get("operands", [])

#             for operand in operands:
#                 obj_type = (operand.get("objectType") or operand.get("object_type") or "").lower()
#                 values = operand.get("values", [])
#                 entry_values = operand.get("entryValues", operand.get("entry_values", []))

#                 if not obj_type:
#                     continue

#                 if values:
#                     converted.append((obj_type, values if isinstance(values, list) else [values]))

#                 elif entry_values:
#                     if isinstance(entry_values, dict):
#                         entry_values = [entry_values]
#                     flattened = [(ev["lhs"], ev["rhs"]) for ev in entry_values if "lhs" in ev and "rhs" in ev]
#                     converted.append((operator, (obj_type, flattened)))

#                 elif "lhs" in operand and "rhs" in operand:
#                     converted.append((obj_type, operand["lhs"], operand["rhs"]))

#         return converted

#     raise ValueError(f"Unsupported conditions format: {type(conditions)}")

import json
from typing import Any, List, Union, Tuple, Dict
from collections import defaultdict

def convert_v2_to_sdk_format(conditions: Any) -> List[Union[Tuple, List]]:
    """
    Convert various condition formats to the SDK's expected v2 format.
    Handles:
    - SDK-native tuple/list format
    - JSON string (parsed into list)
    - API v1-style dicts (operands/operator)
    Also flattens malformed entryValues and ensures nothing is dropped.
    """
    if not conditions:
        return []

    # ✅ Step 1: Parse JSON string if passed
    if isinstance(conditions, str):
        try:
            conditions = json.loads(conditions)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for conditions: {e}")

    # ✅ Step 2: Normalize SDK-style tuples/lists
    if isinstance(conditions, (list, tuple)) and all(isinstance(x, (list, tuple)) for x in conditions):
        normalized_conditions = []

        for cond in conditions:
            if len(cond) == 2 and cond[0] in ("AND", "OR"):
                op, inner = cond
                if isinstance(inner, (list, tuple)) and len(inner) == 2:
                    obj_type, values = inner
                    obj_type_lower = str(obj_type).lower()

                    # ✅ Platform condition — never operator wrapped
                    if (
                        obj_type_lower == "platform"
                        and isinstance(values, list)
                        and all(isinstance(t, (list, tuple)) and len(t) == 2 for t in values)
                    ):
                        normalized_conditions.append((obj_type, values))  # no op
                        continue

                    # ✅ Flatten [[("lhs", "rhs")]] → [("lhs", "rhs")]
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

                # ✅ Flatten [[("lhs", "rhs")]] → [("lhs", "rhs")]
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

    # ✅ Step 3: Convert API v1-style response (dicts)
    if isinstance(conditions, list) and all(isinstance(x, dict) for x in conditions):
        converted = []
        for cond in conditions:
            operator = cond.get("operator", "AND").upper()
            operands = cond.get("operands", [])

            for operand in operands:
                obj_type = (operand.get("objectType") or operand.get("object_type") or "").lower()
                values = operand.get("values", [])
                entry_values = operand.get("entryValues", operand.get("entry_values", []))

                if not obj_type:
                    continue

                if values:
                    converted.append((obj_type, values if isinstance(values, list) else [values]))

                elif entry_values:
                    if isinstance(entry_values, dict):
                        entry_values = [entry_values]
                    flattened = [(ev["lhs"], ev["rhs"]) for ev in entry_values if "lhs" in ev and "rhs" in ev]
                    converted.append((obj_type, flattened)) if obj_type == "platform" else converted.append((operator, (obj_type, flattened)))

                elif "lhs" in operand and "rhs" in operand:
                    converted.append((obj_type, operand["lhs"], operand["rhs"]))

        return converted

    raise ValueError(f"Unsupported conditions format: {type(conditions)}")

def convert_v1_to_v2_response(conditions: List[Dict]) -> List[Dict]:
    """
    Convert the API's v1 response format to a standardized v2 format
    that maintains operator grouping and simplifies the structure.
    """
    if not conditions:
        return []

    VALUE_TYPES = {"APP", "APP_GROUP", "CLIENT_TYPE", "MACHINE_GRP"}
    ENTRY_TYPES = {"COUNTRY_CODE", "POSTURE", "TRUSTED_NETWORK", "SAML", "SCIM", "SCIM_GROUP", "PLATFORM"}

    grouped_values = defaultdict(list)
    grouped_entries = defaultdict(list)
    v2_conditions = []

    for condition in conditions:
        cond_op = (condition.get("operator") or "OR").upper()

        for operand in condition.get("operands", []):
            obj_type = (operand.get("objectType") or operand.get("object_type") or "").upper()
            if not obj_type:
                continue

            if obj_type in VALUE_TYPES:
                rhs = str(operand.get("rhs", ""))
                if rhs:
                    grouped_values[(cond_op, obj_type)].append(rhs)

            elif obj_type in ENTRY_TYPES:
                lhs = str(operand.get("lhs", ""))
                rhs = str(operand.get("rhs", ""))
                if lhs and rhs:
                    grouped_entries[(cond_op, obj_type)].append({"lhs": lhs, "rhs": rhs})

    # Group value-based conditions
    for (op, obj_type), values in grouped_values.items():
        v2_conditions.append({
            "operator": op,
            "operands": [{
                "object_type": obj_type,
                "values": sorted(list(set(values)))
            }]
        })

    # Group entry-value-based conditions
    for (op, obj_type), entries in grouped_entries.items():
        v2_conditions.append({
            "operands": [{
                "object_type": obj_type,
                "entry_values": entries
            }],
            **({"operator": op} if obj_type != "PLATFORM" else {})  # ✅ no operator for platform
        })

    return v2_conditions
