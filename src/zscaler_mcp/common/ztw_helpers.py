"""ZTW-specific helpers (v2).

Per the helper-file convention, product-specific helpers live in a single
``common/{service}_helpers.py`` rather than fragmented per-feature modules.

Currently this holds the country-name/ISO-code → Zscaler ``COUNTRY_XX``
converter used by ZTW IP-destination groups of type ``DSTN_OTHER`` (and, later,
by any ZIA tool that takes countries). Ported verbatim in behaviour from v1's
``zscaler_mcp/utils/utils.py`` so the resolution order is identical.
"""

from __future__ import annotations

import json
from typing import List, Union

import pycountry

__all__ = ["validate_and_convert_country_code", "validate_and_convert_country_codes"]


def validate_and_convert_country_code(country_input: str) -> str:
    """Convert a country name / ISO code / ``COUNTRY_XX`` to ``COUNTRY_XX``.

    Resolution order (first match wins): existing ``COUNTRY_XX`` validation →
    alpha-2 → alpha-3 → name → common name → official name → fuzzy search.
    Raises ``ValueError`` if nothing matches.

    >>> validate_and_convert_country_code("Canada")
    'COUNTRY_CA'
    >>> validate_and_convert_country_code("CA")
    'COUNTRY_CA'
    >>> validate_and_convert_country_code("COUNTRY_CA")
    'COUNTRY_CA'
    """
    if not country_input or not isinstance(country_input, str):
        raise ValueError("Country input must be a non-empty string")

    country_input = country_input.strip().upper()

    if country_input.startswith("COUNTRY_"):
        country_code = country_input[8:]
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            return country_input
        raise ValueError(f"Invalid country code: {country_code}")

    for getter in ("alpha_2", "alpha_3", "name", "common_name", "official_name"):
        try:
            country = pycountry.countries.get(**{getter: country_input})
        except Exception:  # pragma: no cover - defensive against pycountry quirks
            country = None
        if country:
            return f"COUNTRY_{country.alpha_2}"

    try:
        countries = pycountry.countries.search_fuzzy(country_input)
    except Exception:  # pragma: no cover - fuzzy search can raise on no match
        countries = None
    if countries:
        return f"COUNTRY_{countries[0].alpha_2}"

    raise ValueError(f"Could not find country: {country_input}")


def validate_and_convert_country_codes(country_inputs: Union[List[str], str]) -> List[str]:
    """Convert a list (or JSON-string list) of countries to ``COUNTRY_XX`` codes.

    >>> validate_and_convert_country_codes(["Canada", "US", "COUNTRY_GB"])
    ['COUNTRY_CA', 'COUNTRY_US', 'COUNTRY_GB']
    """
    if isinstance(country_inputs, str):
        try:
            country_inputs = json.loads(country_inputs)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON string for countries: {exc}") from exc

    if not isinstance(country_inputs, list):
        raise ValueError("Country inputs must be a list or JSON string of countries")

    return [validate_and_convert_country_code(c) for c in country_inputs]
