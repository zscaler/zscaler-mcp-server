import json
import platform
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

import pycountry


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
                        and all(
                            isinstance(t, (list, tuple)) and len(t) == 2 for t in values
                        )
                    ):
                        normalized_conditions.append((obj_type, values))  # no op
                        continue

                    # ✅ Flatten [[("lhs", "rhs")]] → [("lhs", "rhs")]
                    if (
                        isinstance(values, list)
                        and len(values) == 1
                        and isinstance(values[0], list)
                        and all(
                            isinstance(t, (list, tuple)) and len(t) == 2
                            for t in values[0]
                        )
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
                    and all(
                        isinstance(t, (list, tuple)) and len(t) == 2 for t in values[0]
                    )
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
                obj_type = (
                    operand.get("objectType") or operand.get("object_type") or ""
                ).lower()
                values = operand.get("values", [])
                entry_values = operand.get(
                    "entryValues", operand.get("entry_values", [])
                )

                if not obj_type:
                    continue

                if values:
                    converted.append(
                        (obj_type, values if isinstance(values, list) else [values])
                    )

                elif entry_values:
                    if isinstance(entry_values, dict):
                        entry_values = [entry_values]
                    flattened = [
                        (ev["lhs"], ev["rhs"])
                        for ev in entry_values
                        if "lhs" in ev and "rhs" in ev
                    ]
                    (
                        converted.append((obj_type, flattened))
                        if obj_type == "platform"
                        else converted.append((operator, (obj_type, flattened)))
                    )

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
    ENTRY_TYPES = {
        "COUNTRY_CODE",
        "POSTURE",
        "TRUSTED_NETWORK",
        "SAML",
        "SCIM",
        "SCIM_GROUP",
        "PLATFORM",
    }

    grouped_values = defaultdict(list)
    grouped_entries = defaultdict(list)
    v2_conditions = []

    for condition in conditions:
        cond_op = (condition.get("operator") or "OR").upper()

        for operand in condition.get("operands", []):
            obj_type = (
                operand.get("objectType") or operand.get("object_type") or ""
            ).upper()
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
                    grouped_entries[(cond_op, obj_type)].append(
                        {"lhs": lhs, "rhs": rhs}
                    )

    # Group value-based conditions
    for (op, obj_type), values in grouped_values.items():
        v2_conditions.append(
            {
                "operator": op,
                "operands": [
                    {"object_type": obj_type, "values": sorted(list(set(values)))}
                ],
            }
        )

    # Group entry-value-based conditions
    for (op, obj_type), entries in grouped_entries.items():
        v2_conditions.append(
            {
                "operands": [{"object_type": obj_type, "entry_values": entries}],
                **(
                    {"operator": op} if obj_type != "PLATFORM" else {}
                ),  # ✅ no operator for platform
            }
        )

    return v2_conditions


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
