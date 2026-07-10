"""Token-comparison harness — proves the shaping + encoding claims with numbers.

Relocated from the top-level ``scripts/`` folder into ``common/`` so it lives
with the other reusable cross-cutting utilities (and shares the exact tokenizer
the runtime token-usage metrics use, via :func:`zscaler_mcp.common.count_tokens`).

Measures, on a realistic ZPA segment-group list response, the token cost of:

    1. v1 baseline      — raw SDK as_dict() returned verbatim, JSON
    2. v2 curated JSON  — Pillar A (curated view), still JSON encoded
    3. v2 curated CSV   — Pillar A + Pillar D (curated view + CSV wire format)

Run:  python -m zscaler_mcp.common.token_comparison [N_ROWS]
  or:  zscaler-mcp-tokens [N_ROWS]   (console-script entry point)
"""

from __future__ import annotations

import json
import sys

from zscaler_mcp.common.token_metrics import count_tokens as _count_tokens
from zscaler_mcp.encoding import WireFormat, encode
from zscaler_mcp.tools.zpa.segment_groups import shape_summary


def count_tokens(text: str) -> int:
    """Token count for ``text`` (exact when tiktoken is installed)."""
    tokens, _exact = _count_tokens(text)
    return tokens


def make_raw_segment_group(i: int) -> dict:
    """A realistic, VERBOSE raw SDK ``as_dict()`` segment group.

    Modeled on what zscaler-sdk-python returns: ~20 top-level fields plus a
    nested ``applications`` array — exactly the object v1 forwards verbatim.
    """
    return {
        "id": f"7205830485501{5000 + i}",
        "name": f"Segment Group {i}",
        "description": f"Auto-managed segment group number {i} for the corp environment",
        "enabled": True,
        "configSpace": "DEFAULT",
        "creationTime": "1700000000",
        "modifiedBy": "72058304855015007",
        "modifiedTime": str(1700000000 + i),
        "policyMigrated": True,
        "tcpKeepAliveEnabled": "1",
        "microtenantId": "0",
        "microtenantName": "Default",
        "href": f"/mgmtconfig/v1/admin/customers/123456/segmentGroup/7205830485501{5000 + i}",
        "applications": [
            {
                "id": f"8805830485501{j}",
                "name": f"app-{i}-{j}",
                "enabled": True,
                "domainNames": [f"app{i}{j}.corp.example.com"],
                "applicationGroupId": f"99058304855015{i}",
                "creationTime": "1700000000",
                "modifiedTime": "1700000100",
                "bypassType": "NEVER",
            }
            for j in range(3)
        ],
    }


def main() -> None:
    n_rows = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    raw_rows = [make_raw_segment_group(i) for i in range(n_rows)]
    curated_rows = [shape_summary(r).model_dump() for r in raw_rows]

    v1_json = json.dumps(raw_rows, separators=(",", ":"), default=str)
    v2_curated_json = encode(curated_rows, fmt=WireFormat.JSON)
    v2_curated_csv = encode(curated_rows, fmt=WireFormat.AUTO)

    rows = [
        ("1. v1 baseline (raw as_dict, JSON minified)", v1_json),
        ("2. v2 curated view (JSON pretty)", v2_curated_json),
        ("3. v2 curated view (CSV, AUTO)", v2_curated_csv),
    ]

    base_tokens = count_tokens(v1_json)

    print(f"\nZPA segment-group list — {n_rows} rows\n" + "=" * 64)
    print(f"{'representation':<46}{'bytes':>8}{'tokens':>9}")
    print("-" * 64)
    for label, text in rows:
        b = len(text.encode("utf-8"))
        t = count_tokens(text)
        print(f"{label:<46}{b:>8}{t:>9}")
    print("-" * 64)

    v2j = count_tokens(v2_curated_json)
    v2c = count_tokens(v2_curated_csv)
    print(f"\nReductions vs v1 baseline ({base_tokens} tokens):")
    print(
        f"  curated JSON : {base_tokens - v2j:>6} fewer tokens "
        f"({100 * (base_tokens - v2j) / base_tokens:.1f}% smaller)"
    )
    print(
        f"  curated CSV  : {base_tokens - v2c:>6} fewer tokens "
        f"({100 * (base_tokens - v2c) / base_tokens:.1f}% smaller)"
    )
    if v2j:
        print(
            f"  CSV vs curated-JSON only: "
            f"{100 * (v2j - v2c) / v2j:.1f}% additional reduction from the encoder"
        )
    print(
        f"\n  per-row cost: v1={base_tokens / n_rows:.1f}  "
        f"curatedJSON={v2j / n_rows:.1f}  curatedCSV={v2c / n_rows:.1f} tokens/row\n"
    )

    print("Sample of v2 CSV output (first 4 lines):")
    print("\n".join(v2_curated_csv.splitlines()[:4]))
    print()


if __name__ == "__main__":
    main()
