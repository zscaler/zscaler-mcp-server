"""ZIA Time Intervals MCP Tools.

Time Intervals are reusable schedule objects (start time, end time, days of
the week) that ZIA policy rules reference via their ``time_windows`` field.
They are the only way to make ZIA Cloud Firewall Filtering, URL Filtering,
Cloud App Control, etc. enforce rules on a recurring time-of-day /
day-of-week schedule (e.g. "only between 8am-5pm M-F"). SSL Inspection
rules do **not** support ``time_windows``.

Each action is exposed as its own MCP tool: ``zia_list_*``, ``zia_get_*``,
``zia_create_*``, ``zia_update_*``, ``zia_delete_*``.

Time-of-day fields (``start_time`` / ``end_time``) are integers expressed in
**minutes from midnight** (0-1439). Examples:

- ``start_time=0,    end_time=1439`` -> the entire day (00:00 - 23:59)
- ``start_time=480,  end_time=1020`` -> 08:00 - 17:00
- ``start_time=120,  end_time=240``  -> 02:00 - 04:00 (maintenance window)

``days_of_week`` accepts the canonical ZIA values: ``EVERYDAY``, ``SUN``,
``MON``, ``TUE``, ``WED``, ``THU``, ``FRI``, ``SAT``.

**Name constraint:** ZIA rejects Time Interval names that contain digits or
special characters. Allowed characters are ASCII letters and spaces only
(e.g. ``Business Hours``, ``After Hours``, ``Weekday Mornings``,
``Weekend All Day``). Names like ``Mon-Fri 08:00-17:00`` or
``Q1 Maintenance`` will be rejected at the API layer with
``Name is not valid``. ``zia_create_time_interval`` and
``zia_update_time_interval`` validate the name client-side and raise
``ValueError`` before the API call so the agent fails fast with a clear
message.

ZIA's TimeInterval update endpoint is a PUT (full replacement). To keep
partial updates safe, ``zia_update_time_interval`` silently backfills
``name``, ``start_time``, ``end_time``, and ``days_of_week`` from the
existing record when the caller does not supply them.
"""

import re
from typing import Annotated, Any, List, Optional, Union

from pydantic import Field

from zscaler_mcp.client import get_zscaler_client
from zscaler_mcp.common.jmespath_utils import apply_jmespath
from zscaler_mcp.utils.utils import parse_list

_VALID_DAYS = {"EVERYDAY", "SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"}

# ZIA rejects Time Interval names containing digits or special characters.
# Allowed: ASCII letters and spaces. Must start with a letter; trailing
# whitespace is stripped before validation.
_TIME_INTERVAL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z ]*$")


def _validate_time_interval_name(name: Optional[str]) -> Optional[str]:
    """Validate a Time Interval name client-side (letters and spaces only).

    Returns the trimmed name when valid, or raises ``ValueError`` with a
    user-facing message that the agent can surface to the admin without
    waiting for the API to reject the call.
    """
    if name is None:
        return None
    trimmed = name.strip()
    if not trimmed:
        raise ValueError("Time Interval name cannot be empty.")
    if not _TIME_INTERVAL_NAME_RE.match(trimmed):
        raise ValueError(
            f"Time Interval name '{name}' is not valid. ZIA rejects names "
            "that contain digits or special characters (hyphens, colons, "
            "em-dashes, slashes, periods, etc.). Use only ASCII letters "
            "and spaces, e.g. 'Business Hours', 'After Hours', "
            "'Weekday Mornings', 'Weekend All Day'."
        )
    return trimmed


def _normalize_days_of_week(
    days_of_week: Optional[Union[List[str], str]],
) -> Optional[List[str]]:
    """Parse, uppercase, and validate the days_of_week argument."""
    if days_of_week is None:
        return None
    parsed = parse_list(days_of_week)
    if not isinstance(parsed, list):
        raise ValueError(
            "days_of_week must be a list of day codes "
            "(EVERYDAY, SUN, MON, TUE, WED, THU, FRI, SAT)."
        )
    normalized = [str(d).strip().upper() for d in parsed if str(d).strip()]
    invalid = [d for d in normalized if d not in _VALID_DAYS]
    if invalid:
        raise ValueError(
            f"Invalid days_of_week value(s): {invalid}. "
            f"Allowed: {sorted(_VALID_DAYS)}."
        )
    return normalized


def _build_time_interval_payload(
    name: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    days_of_week: Optional[Union[List[str], str]] = None,
) -> dict:
    """Build payload for Time Interval create/update operations.

    The name (if provided) is validated against ZIA's letters-and-spaces-only
    constraint before being added to the payload.
    """
    payload: dict = {}
    validated_name = _validate_time_interval_name(name)
    if validated_name is not None:
        payload["name"] = validated_name
    if start_time is not None:
        payload["start_time"] = start_time
    if end_time is not None:
        payload["end_time"] = end_time
    normalized_days = _normalize_days_of_week(days_of_week)
    if normalized_days is not None:
        payload["days_of_week"] = normalized_days
    return payload


# ============================================================================
# READ OPERATIONS (Read-Only)
# ============================================================================


def zia_list_time_intervals(
    search: Annotated[
        Optional[str],
        Field(description="Optional search filter for listing time intervals by name."),
    ] = None,
    page: Annotated[
        Optional[int], Field(description="Page offset for pagination.")
    ] = None,
    page_size: Annotated[
        Optional[int], Field(description="Page size for pagination.")
    ] = None,
    query: Annotated[
        Optional[str],
        Field(
            description="JMESPath expression for client-side filtering/projection of results."
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> Any:
    """
    Lists ZIA Time Intervals.

    Time Intervals are reusable schedule objects referenced by policy rules
    (Cloud Firewall, URL Filtering, SSL Inspection, Cloud App Control, etc.)
    via their ``time_windows`` field. Read-only. Supports JMESPath
    client-side filtering via the ``query`` parameter.

    Returns:
        list[dict]: Time Interval records with ``id``, ``name``,
        ``start_time``, ``end_time`` (minutes from midnight), and
        ``days_of_week``.
    """
    client = get_zscaler_client(service=service)
    api = client.zia.time_intervals

    query_params: dict = {}
    if search:
        query_params["search"] = search
    if page is not None:
        query_params["page"] = page
    if page_size is not None:
        query_params["page_size"] = page_size

    intervals, _, err = api.list_time_intervals(query_params=query_params)
    if err:
        raise Exception(f"Failed to list Time Intervals: {err}")
    results = [i.as_dict() for i in (intervals or [])]
    return apply_jmespath(results, query)


def zia_get_time_interval(
    interval_id: Annotated[
        Union[int, str], Field(description="The ID of the Time Interval to retrieve.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Gets a specific ZIA Time Interval by ID.

    Returns:
        dict: The Time Interval record.
    """
    if not interval_id:
        raise ValueError("interval_id is required")

    client = get_zscaler_client(service=service)
    api = client.zia.time_intervals

    interval, _, err = api.get_time_intervals(interval_id)
    if err:
        raise Exception(f"Failed to retrieve Time Interval {interval_id}: {err}")
    return interval.as_dict()


# ============================================================================
# WRITE OPERATIONS (Require --enable-write-tools flag)
# ============================================================================


def zia_create_time_interval(
    name: Annotated[
        str,
        Field(
            description=(
                "Time Interval name. ZIA rejects names with digits or "
                "special characters — use ASCII letters and spaces only "
                "(e.g. 'Business Hours', 'After Hours', 'Weekday Mornings', "
                "'Weekend All Day'). Names like 'Mon-Fri 08:00-17:00' or "
                "'Q1 Maintenance' are not valid."
            )
        ),
    ],
    start_time: Annotated[
        int,
        Field(
            description=(
                "Start time in minutes from midnight (0-1439). "
                "Examples: 0 = 00:00, 480 = 08:00, 1020 = 17:00."
            )
        ),
    ],
    end_time: Annotated[
        int,
        Field(
            description=(
                "End time in minutes from midnight (0-1439). "
                "Use 1439 for end-of-day."
            )
        ),
    ],
    days_of_week: Annotated[
        Union[List[str], str],
        Field(
            description=(
                "Days the schedule applies to. Allowed values: EVERYDAY, "
                "SUN, MON, TUE, WED, THU, FRI, SAT. Use [\"EVERYDAY\"] for "
                "every day. Accepts a list or a JSON string."
            )
        ),
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Creates a ZIA Time Interval.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    Once created, the Time Interval ID can be passed to any rule that
    accepts a ``time_windows`` field (Cloud Firewall, URL Filtering, SSL
    Inspection, Cloud App Control, File Type Control, Sandbox, etc.).

    Returns:
        dict: The created Time Interval.
    """
    payload = _build_time_interval_payload(
        name=name,
        start_time=start_time,
        end_time=end_time,
        days_of_week=days_of_week,
    )

    client = get_zscaler_client(service=service)
    api = client.zia.time_intervals

    interval, _, err = api.add_time_intervals(**payload)
    if err:
        raise Exception(f"Failed to create Time Interval: {err}")
    return interval.as_dict()


def zia_update_time_interval(
    interval_id: Annotated[
        Union[int, str], Field(description="The ID of the Time Interval to update.")
    ],
    name: Annotated[
        Optional[str],
        Field(
            description=(
                "Time Interval name. ZIA rejects names with digits or "
                "special characters — use ASCII letters and spaces only."
            )
        ),
    ] = None,
    start_time: Annotated[
        Optional[int],
        Field(description="Start time in minutes from midnight (0-1439)."),
    ] = None,
    end_time: Annotated[
        Optional[int],
        Field(description="End time in minutes from midnight (0-1439)."),
    ] = None,
    days_of_week: Annotated[
        Optional[Union[List[str], str]],
        Field(
            description=(
                "Days the schedule applies to. Allowed values: EVERYDAY, "
                "SUN, MON, TUE, WED, THU, FRI, SAT."
            )
        ),
    ] = None,
    service: Annotated[str, Field(description="The service to use.")] = "zia",
) -> dict:
    """
    Updates a ZIA Time Interval.

    This is a write operation that requires the ``--enable-write-tools`` flag.

    The Time Interval update endpoint is a PUT (full replacement). This
    tool silently backfills ``name``, ``start_time``, ``end_time``, and
    ``days_of_week`` from the existing record when the caller does not
    supply them, so partial updates "just work".

    Returns:
        dict: The updated Time Interval.
    """
    if not interval_id:
        raise ValueError("interval_id is required for update")

    payload = _build_time_interval_payload(
        name=name,
        start_time=start_time,
        end_time=end_time,
        days_of_week=days_of_week,
    )

    client = get_zscaler_client(service=service)
    api = client.zia.time_intervals

    required_fields = ("name", "start_time", "end_time", "days_of_week")
    if any(field not in payload for field in required_fields):
        existing, _, fetch_err = api.get_time_intervals(interval_id)
        if fetch_err:
            raise Exception(
                f"Failed to fetch Time Interval {interval_id} for required-field backfill: {fetch_err}"
            )
        existing_dict = existing.as_dict()
        for field in required_fields:
            if field not in payload and existing_dict.get(field) is not None:
                payload[field] = existing_dict[field]

    updated, _, err = api.update_time_intervals(interval_id, **payload)
    if err:
        raise Exception(f"Failed to update Time Interval {interval_id}: {err}")
    return updated.as_dict()


def zia_delete_time_interval(
    interval_id: Annotated[
        Union[int, str], Field(description="The ID of the Time Interval to delete.")
    ],
    service: Annotated[str, Field(description="The service to use.")] = "zia",
    kwargs: str = "{}",
) -> str:
    """
    Deletes a ZIA Time Interval by ID.

    DESTRUCTIVE OPERATION - Requires double confirmation via HMAC token.
    This action cannot be undone. If the Time Interval is currently
    referenced by any policy rule, the delete will fail at the API layer.

    Returns:
        str: Success message confirming deletion.
    """
    from zscaler_mcp.common.elicitation import (
        check_confirmation,
        extract_confirmed_from_kwargs,
    )

    confirmed = extract_confirmed_from_kwargs(kwargs)
    confirmation_check = check_confirmation(
        "zia_delete_time_interval", confirmed, {"interval_id": str(interval_id)}
    )
    if confirmation_check:
        return confirmation_check

    if not interval_id:
        raise ValueError("interval_id is required for deletion")

    client = get_zscaler_client(service=service)
    api = client.zia.time_intervals

    _, _, err = api.delete_time_intervals(interval_id)
    if err:
        raise Exception(f"Failed to delete Time Interval {interval_id}: {err}")
    return f"Time Interval {interval_id} deleted successfully."
