import json
import platform
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

import pycountry


def parse_list(val: Union[str, List, Any]) -> Union[List, Any]:
    """
    Helper function to parse list parameters that can be JSON strings or lists.

    Args:
        val: Either a JSON string representation of a list, or an actual list/other type.

    Returns:
        Parsed list if input was a JSON string, otherwise returns the value as-is.

    Raises:
        ValueError: If the input is a string but not valid JSON.

    Examples:
        >>> parse_list('["item1", "item2"]')
        ['item1', 'item2']
        >>> parse_list(["item1", "item2"])
        ['item1', 'item2']
        >>> parse_list(123)
        123
    """
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON string: {exc}")
    return val


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
    if isinstance(conditions, (list, tuple)) and all(
        isinstance(x, (list, tuple)) for x in conditions
    ):
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

    # ✅ Step 3: Convert v2 dict-shaped conditions to SDK tuple format.
    #
    # The SDK's ``policies._create_conditions_v2`` accepts the simplified
    # tuple shapes documented in the SDK example
    # (``zscaler-sdk-python/local_dev/.../access_rule_v2.py``):
    #
    #   - ``(object_type, [<id>, ...])`` for ID-based types (APP, APP_GROUP,
    #     CLIENT_TYPE, CONSOLE, LOCATION, MACHINE_GRP, USER_PORTAL,
    #     CHROME_POSTURE_PROFILE).
    #   - ``(object_type, [(lhs, rhs), ...])`` or
    #     ``(operator, (object_type, [(lhs, rhs), ...]))`` for attribute-based
    #     types (POSTURE, TRUSTED_NETWORK, COUNTRY_CODE, PLATFORM,
    #     RISK_FACTOR_TYPE, SAML, SCIM, SCIM_GROUP).
    #   - ``(chrome_enterprise, attr, value)`` — flat 3-tuple, scalar lhs/rhs,
    #     no operator wrapper. CHROME_ENTERPRISE is the only type that breaks
    #     the otherwise-uniform list-of-tuples pattern.
    if isinstance(conditions, list) and all(isinstance(x, dict) for x in conditions):
        converted: List[Union[Tuple, List]] = []
        for cond in conditions:
            # SDK defaults missing operators to OR; align with that to avoid
            # silently grouping operands under an unintended AND.
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
                        # SDK expects ``(chrome_enterprise, attr, value)`` —
                        # one flat 3-tuple per attribute. Emit one per entry
                        # to handle multi-attribute inputs correctly.
                        for lhs, rhs in flattened:
                            converted.append((obj_type, lhs, rhs))
                    elif obj_type == "platform":
                        # PLATFORM is the only entry-shaped type the SDK
                        # documents as bare (no operator wrapper).
                        converted.append((obj_type, flattened))
                    else:
                        converted.append((operator, (obj_type, flattened)))
                    continue

                if "lhs" in operand and "rhs" in operand:
                    converted.append((obj_type, operand["lhs"], operand["rhs"]))

        return converted

    raise ValueError(f"Unsupported conditions format: {type(conditions)}")


# Object types whose v1 operands carry the resolved ID in `rhs` (with `lhs="id"`)
# and which should be emitted in v2 as ``{"object_type": X, "values": [<ids>]}``.
# Mirrors ``ConvertV1ResponseToV2Request`` in the Terraform ZPA provider
# (terraform-provider-zpa/zpa/common.go).
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

# Object types whose v1 operands carry semantic ``lhs``/``rhs`` pairs and
# which should be emitted in v2 as ``{"object_type": X, "entry_values": [{"lhs":..,"rhs":..}]}``.
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


def convert_v1_to_v2_response(conditions: List[Dict]) -> List[Dict]:
    """Normalize a ZPA Policy Access v1 GET/POST response into v2 request shape.

    The ZPA Policy Access API is structurally asymmetric: write operations
    accept a v2-shaped body (``operands`` carry ``values: [...]`` for ID-based
    types and ``entry_values: [{lhs, rhs}, ...]`` for attribute-based types),
    but read operations return a v1-shaped body where every operand is a flat
    ``{"objectType": ..., "lhs": ..., "rhs": ...}`` dict and operands of the
    same logical block are split into multiple sibling operand entries inside
    the same condition.

    This function reshapes the v1 response back into the v2 shape so callers
    can round-trip a created/fetched rule through update without re-deriving
    the condition payload by hand. The algorithm mirrors
    ``ConvertV1ResponseToV2Request`` in the Terraform ZPA provider
    (``terraform-provider-zpa/zpa/common.go``). For each input v1 condition it
    preserves the original ``operator``, groups operands by ``objectType`` into
    a VALUE bucket (ID-typed objects: APP, APP_GROUP, MACHINE_GRP, LOCATION,
    CLIENT_TYPE, USER_PORTAL, PRIVILEGE_PORTAL, CONSOLE, CHROME_POSTURE_PROFILE,
    BRANCH_CONNECTOR_GROUP, EDGE_CONNECTOR_GROUP) and an ENTRY bucket
    (attribute-typed objects: PLATFORM, POSTURE, TRUSTED_NETWORK, SAML, SCIM,
    SCIM_GROUP, COUNTRY_CODE, RISK_FACTOR_TYPE, CHROME_ENTERPRISE), then emits
    one v2 operand per ``(objectType, bucket)``. Aggregation never crosses
    condition boundaries — preserving them is critical because the AND/OR
    semantics depend on it (two separate POSTURE conditions = AND, two operands
    within one POSTURE condition = OR). Object types and entry-value pairs are
    sorted for stable output.

    Args:
        conditions: A list of v1-shaped condition dicts as returned by ZPA Policy
            Access GET/POST endpoints. Each condition has an ``operator`` and a
            flat list of ``operands``.

    Returns:
        A list of v2-shaped condition dicts, one per input v1 condition. Each
        emitted condition has the form
        ``{"operator": "AND"|"OR", "operands": [{"object_type": "APP",
        "values": [...]}, {"object_type": "POSTURE", "entry_values":
        [{"lhs": "...", "rhs": "true"}, ...]}]}``. Empty input returns an empty
        list.
    """
    if not conditions:
        return []

    v2_conditions: List[Dict] = []

    # Iteration is intentionally per-condition: aggregation MUST NOT cross
    # condition boundaries (see docstring re. AND vs OR semantics).
    for condition in conditions:
        cond_op = (condition.get("operator") or "OR").upper()
        operands = condition.get("operands") or []

        # Aggregate operands of the same objectType WITHIN this condition only.
        values_by_type: Dict[str, List[str]] = defaultdict(list)
        entries_by_type: Dict[str, List[Dict[str, str]]] = defaultdict(list)

        for operand in operands:
            obj_type = (
                operand.get("objectType") or operand.get("object_type") or ""
            ).upper()
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
                    entries_by_type[obj_type].append(
                        {"lhs": str(lhs), "rhs": str(rhs)}
                    )
            # Unknown object types are ignored (matches Terraform behavior:
            # the switch has no default branch).

        new_operands: List[Dict] = []

        # Emit value-bucket operands in deterministic order.
        for obj_type in sorted(values_by_type.keys()):
            # De-dupe while preserving order, then sort for stable output.
            unique_sorted = sorted(set(values_by_type[obj_type]))
            new_operands.append({"object_type": obj_type, "values": unique_sorted})

        # Emit entry-bucket operands in deterministic order.
        for obj_type in sorted(entries_by_type.keys()):
            entries = sorted(
                entries_by_type[obj_type],
                key=lambda e: (e["lhs"], e["rhs"]),
            )
            new_operands.append({"object_type": obj_type, "entry_values": entries})

        if not new_operands:
            # Drop empty conditions rather than emit an operator with no operands.
            continue

        v2_conditions.append({"operator": cond_op, "operands": new_operands})

    return v2_conditions


def normalize_v2_rule_response(sdk_object: Any, raw_response: Any) -> Dict:
    """Stitch a v2 policy-rule write response into a complete, correct dict.

    Background — the SDK has a known asymmetry in its policy-rule models:

    - The **V1 Operand** model (used by ``policies.get_rule(...)``) reads
      ``objectType``, ``lhs``, and ``rhs`` from the API response. It
      preserves the data the v1-shaped API actually returns.

    - The **V2 Operand** model (used by ``policies.add_*_rule_v2`` and
      ``policies.update_*_rule_v2``) reads only ``objectType``, ``values``,
      and ``entryValues`` — it does **not** read ``lhs`` / ``rhs``. But the
      v2 add/update endpoints receive a **v1-shaped response** from the API
      (operands with flat ``lhs``/``rhs``), which the V2 model then drops on
      deserialization. Result: ``created.as_dict()["conditions"]`` returns
      operands with empty ``values`` and ``entry_values`` arrays even when
      the rule was created perfectly.

    The fix is to bypass the lossy V2 model: read the raw API response body
    (``response.get_body()`` returns the JSON-decoded dict, untouched by any
    SDK model) and run its ``conditions`` through ``convert_v1_to_v2_response``.
    The rest of the rule (id, name, action, etc.) comes from the SDK's
    ``as_dict()`` because the top-level fields ARE preserved correctly there.

    Parameters
    ----------
    sdk_object
        The first element of the SDK tuple — e.g. ``created`` from
        ``created, response, err = api.add_access_rule_v2(...)``. Provides
        the snake_case top-level field set the agent expects.
    raw_response
        The second element of the SDK tuple — the ``ZscalerAPIResponse``
        (or ``None`` if the call failed before a body was received). Used
        only to recover the v1-shaped ``conditions`` block that the SDK's
        V2 model dropped.

    Returns
    -------
    The SDK's ``as_dict()`` with ``conditions`` rebuilt from the raw response.
    Falls back gracefully (returns the SDK dict unchanged) when the raw
    response is missing, has no body, or carries no conditions — so callers
    do not have to check.
    """
    rule_data: Dict = sdk_object.as_dict() if sdk_object is not None else {}

    if raw_response is None:
        return rule_data

    body = None
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


def validate_and_convert_country_code(country_input: str) -> str:
    """
    Validates and converts country input to Zscaler's COUNTRY_XX format.

    Args:
        country_input (str): Country name, ISO code, or existing COUNTRY_XX format

    Returns:
        str: Validated country code in COUNTRY_XX format (e.g., COUNTRY_CA, COUNTRY_US)

    Raises:
        ValueError: If country cannot be found or is invalid

    Examples:
        >>> validate_and_convert_country_code("Canada")
        'COUNTRY_CA'
        >>> validate_and_convert_country_code("CA")
        'COUNTRY_CA'
        >>> validate_and_convert_country_code("COUNTRY_CA")
        'COUNTRY_CA'
        >>> validate_and_convert_country_code("United States")
        'COUNTRY_US'
    """
    if not country_input or not isinstance(country_input, str):
        raise ValueError("Country input must be a non-empty string")

    country_input = country_input.strip().upper()

    # If already in COUNTRY_XX format, validate the country code
    if country_input.startswith("COUNTRY_"):
        country_code = country_input[8:]  # Remove "COUNTRY_" prefix
        try:
            country = pycountry.countries.get(alpha_2=country_code)
            if country:
                return country_input
            else:
                raise ValueError(f"Invalid country code: {country_code}")
        except Exception:
            raise ValueError(f"Invalid country code: {country_code}")

    # Try to find by ISO alpha-2 code
    try:
        country = pycountry.countries.get(alpha_2=country_input)
        if country:
            return f"COUNTRY_{country.alpha_2}"
    except Exception:
        pass

    # Try to find by ISO alpha-3 code
    try:
        country = pycountry.countries.get(alpha_3=country_input)
        if country:
            return f"COUNTRY_{country.alpha_2}"
    except Exception:
        pass

    # Try to find by country name
    try:
        country = pycountry.countries.get(name=country_input)
        if country:
            return f"COUNTRY_{country.alpha_2}"
    except Exception:
        pass

    # Try to find by common name
    try:
        country = pycountry.countries.get(common_name=country_input)
        if country:
            return f"COUNTRY_{country.alpha_2}"
    except Exception:
        pass

    # Try to find by official name
    try:
        country = pycountry.countries.get(official_name=country_input)
        if country:
            return f"COUNTRY_{country.alpha_2}"
    except Exception:
        pass

    # Try fuzzy search for country names
    try:
        countries = pycountry.countries.search_fuzzy(country_input)
        if countries:
            return f"COUNTRY_{countries[0].alpha_2}"
    except Exception:
        pass

    raise ValueError(f"Could not find country: {country_input}")


def validate_and_convert_country_codes(country_inputs: Union[List[str], str]) -> List[str]:
    """
    Validates and converts multiple country inputs to Zscaler's COUNTRY_XX format.

    Args:
        country_inputs: List of country names/codes or JSON string of countries

    Returns:
        List[str]: List of validated country codes in COUNTRY_XX format

    Raises:
        ValueError: If any country cannot be found or is invalid

    Examples:
        >>> validate_and_convert_country_codes(["Canada", "US", "COUNTRY_GB"])
        ['COUNTRY_CA', 'COUNTRY_US', 'COUNTRY_GB']
        >>> validate_and_convert_country_codes('["Canada", "US"]')
        ['COUNTRY_CA', 'COUNTRY_US']
    """
    if isinstance(country_inputs, str):
        try:
            country_inputs = json.loads(country_inputs)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for countries: {e}")

    if not isinstance(country_inputs, list):
        raise ValueError("Country inputs must be a list or JSON string of countries")

    converted_countries = []
    for country_input in country_inputs:
        converted_country = validate_and_convert_country_code(country_input)
        converted_countries.append(converted_country)

    return converted_countries


def validate_and_convert_country_code_iso(country_input: str) -> str:
    """
    Validates and converts country input to standard ISO 3166-1 alpha-2 format.

    Args:
        country_input (str): Country name, ISO code, or existing ISO format

    Returns:
        str: Validated country code in ISO alpha-2 format (e.g., CA, US, GB)

    Raises:
        ValueError: If country cannot be found or is invalid

    Examples:
        >>> validate_and_convert_country_code_iso("Canada")
        'CA'
        >>> validate_and_convert_country_code_iso("US")
        'US'
        >>> validate_and_convert_country_code_iso("CA")
        'CA'
        >>> validate_and_convert_country_code_iso("United States")
        'US'
    """
    if not country_input or not isinstance(country_input, str):
        raise ValueError("Country input must be a non-empty string")

    country_input = country_input.strip()

    # If already in ISO alpha-2 format, validate it
    if len(country_input) == 2 and country_input.isalpha():
        try:
            country = pycountry.countries.get(alpha_2=country_input.upper())
            if country:
                return country.alpha_2
            else:
                raise ValueError(f"Invalid country code: {country_input}")
        except Exception:
            raise ValueError(f"Invalid country code: {country_input}")

    # Try to find by ISO alpha-2 code (case insensitive)
    try:
        country = pycountry.countries.get(alpha_2=country_input.upper())
        if country:
            return country.alpha_2
    except Exception:
        pass

    # Try to find by ISO alpha-3 code
    try:
        country = pycountry.countries.get(alpha_3=country_input.upper())
        if country:
            return country.alpha_2
    except Exception:
        pass

    # Try to find by country name
    try:
        country = pycountry.countries.get(name=country_input)
        if country:
            return country.alpha_2
    except Exception:
        pass

    # Try to find by common name
    try:
        country = pycountry.countries.get(common_name=country_input)
        if country:
            return country.alpha_2
    except Exception:
        pass

    # Try to find by official name
    try:
        country = pycountry.countries.get(official_name=country_input)
        if country:
            return country.alpha_2
    except Exception:
        pass

    # Try fuzzy search for country names
    try:
        countries = pycountry.countries.search_fuzzy(country_input)
        if countries:
            return countries[0].alpha_2
    except Exception:
        pass

    raise ValueError(f"Could not find country: {country_input}")


def get_mcp_user_agent() -> str:
    """
    Generate a formatted user-agent string for the Zscaler Integrations MCP Server.

    Returns:
        str: Formatted user-agent string in the format:
             zscaler-mcp-server/<version>/<OS_Architecture>

    Examples:
        >>> get_mcp_user_agent()
        'zscaler-mcp-server/0.2.0/Darwin-24.6.0-x86_64'
    """
    import importlib.metadata

    try:
        # Get the version from the package metadata
        version = importlib.metadata.version("zscaler-mcp")
    except importlib.metadata.PackageNotFoundError:
        # Fallback to reading from pyproject.toml if package not installed
        version = "0.2.0"  # Default version

    # Get system information
    system = platform.system()
    release = platform.release()
    machine = platform.machine()

    # Format: OS-Release-Architecture
    os_arch = f"{system}-{release}-{machine}"

    return f"zscaler-mcp-server/{version}/{os_arch}"


def get_combined_user_agent(user_agent_comment: Optional[str] = None) -> str:
    """
    Generate a user-agent string for the Zscaler MCP Server.

    Args:
        user_agent_comment: Optional additional information to append to the user-agent
                          (e.g., "Claude Desktop 1.2024.10.23")

    Returns:
        str: User-agent string in the format:
             zscaler-mcp-server/<version> python/<python_version> <os>/<arch> [comment]

    Examples:
        >>> get_combined_user_agent()
        'zscaler-mcp-server/0.3.1 python/3.11.8 darwin/arm64'
        >>> get_combined_user_agent("Claude Desktop 1.2024.10.23")
        'zscaler-mcp-server/0.3.1 python/3.11.8 darwin/arm64 Claude Desktop 1.2024.10.23'
    """
    import importlib.metadata

    # Get MCP server version
    try:
        version = importlib.metadata.version("zscaler-mcp")
    except importlib.metadata.PackageNotFoundError:
        version = "0.3.1"  # Default version from pyproject.toml

    # Get Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Get OS and architecture
    system = platform.system().lower()  # e.g., 'darwin', 'linux', 'windows'
    machine = platform.machine().lower()  # e.g., 'arm64', 'x86_64', 'amd64'

    # Build the base user-agent string
    user_agent = f"zscaler-mcp-server/{version} python/{python_version} {system}/{machine}"

    # Append optional comment if provided
    if user_agent_comment:
        user_agent += f" {user_agent_comment}"

    return user_agent
