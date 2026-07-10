"""Wire-encoding implementation — DESIGN.md §5 Pillar D.

The SINGLE place where the "how do we serialize the shaped result for the agent
to read?" decision lives. Centralizing it is what keeps ~300 tools consistent —
no tool re-implements this.

The rule:

    * single object / nested structure  -> JSON   (keeps types + nesting)
    * flat list of flat dicts           -> CSV    (column names stated once)

CSV is purely a wire format: it is the *string the tool returns over the wire*
to the agent. Nothing is written to disk. JSON repeats every key on every row;
CSV states the columns once on a header line, so a long list costs materially
fewer tokens with zero information loss for flat rows.

Safety / correctness rules baked in:

    * A "list" is only CSV-encoded if EVERY row is a flat dict (no nested
      dict/list values). The moment a value is itself a dict or list, we fall
      back to JSON for the whole response — CSV cannot represent nesting and we
      will not silently drop structure.
    * Values are CSV-quoted per RFC 4180 (commas / quotes / newlines handled by
      the stdlib csv module), so a description containing a comma never corrupts
      the row.
    * The union of keys across rows is used for the header (rows may legitimately
      omit an Optional field); missing cells are emitted empty.

Public API is re-exported from ``zscaler_mcp.encoding``; import from there, not from
this module directly.
"""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Any

__all__ = ["WireFormat", "encode"]


class WireFormat(str, Enum):
    """Explicit wire-format selector for a tool response."""

    AUTO = "auto"  # object -> JSON, flat list -> CSV (the default policy)
    JSON = "json"  # force JSON (escape hatch / nested data)
    CSV = "csv"  # force CSV (only honored if the data is a flat list)


def encode(data: Any, *, fmt: WireFormat | str = WireFormat.AUTO) -> str:
    """Serialize a shaped tool result to the wire string the agent reads.

    Args:
        data: the shaped result — a dict (single object) or a list of dicts.
        fmt: ``auto`` (default policy), ``json`` (force), or ``csv`` (force;
            ignored with a JSON fallback if the data is not a flat list).

    Returns:
        A string: pretty JSON for objects/nested data, CSV for flat lists.

    Raises:
        ValueError: if ``fmt`` is not a recognized :class:`WireFormat` value.
    """
    fmt = WireFormat(fmt)

    if fmt is WireFormat.JSON:
        return _to_json(data)

    if fmt is WireFormat.CSV:
        # Honor the request only if the data can actually be CSV; otherwise we
        # must not lose structure -> fall back to JSON.
        return _to_csv(data) if _is_csv_eligible(data) else _to_json(data)

    # AUTO: flat list -> CSV, everything else -> JSON.
    if _is_csv_eligible(data):
        return _to_csv(data)
    return _to_json(data)


# ---------------------------------------------------------------------------
# CSV eligibility
# ---------------------------------------------------------------------------


def _is_flat_scalar(value: Any) -> bool:
    """True for values CSV can represent in a single cell."""
    return value is None or isinstance(value, (str, int, float, bool))


def _is_flat_row(row: Any) -> bool:
    return isinstance(row, dict) and all(_is_flat_scalar(v) for v in row.values())


def _is_csv_eligible(data: Any) -> bool:
    """A response is CSV-eligible iff it's a non-empty list of flat dicts."""
    return isinstance(data, list) and len(data) > 0 and all(_is_flat_row(r) for r in data)


# ---------------------------------------------------------------------------
# CSV rendering
# ---------------------------------------------------------------------------


def _ordered_header(rows: list[dict[str, Any]]) -> list[str]:
    """Union of keys across rows, preserving first-seen order."""
    header: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                header.append(key)
    return header


def _csv_cell(value: Any) -> Any:
    """Render a single cell deterministically; csv handles quoting of strings."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _to_csv(rows: list[dict[str, Any]]) -> str:
    header = _ordered_header(rows)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _csv_cell(row.get(key)) for key in header})
    return buf.getvalue().rstrip("\n")


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------


def _to_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)
