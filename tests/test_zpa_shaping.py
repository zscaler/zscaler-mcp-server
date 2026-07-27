"""Shaping tests for the ZPA application-segment, lookup, and LSS tool families
added in the v2 port.

Same contract as the segment-groups reference test: shapers drop SDK noise,
coerce ids to strings, tolerate camel/snake keys, and count relational members.
No SDK / no credentials.
"""

from zscaler_mcp.tools.zpa.lss import (
    Catalog,
)

# =============================================================================
# Standard application segments
# =============================================================================


# =============================================================================
# Browser-access (BA) segments
# =============================================================================


# =============================================================================
# PRA segments
# =============================================================================


# =============================================================================
# Lookups (reference items + segments-by-type)
# =============================================================================


# =============================================================================
# LSS configs + catalog wrapper
# =============================================================================


def test_lss_catalog_passes_payload_through():
    c = Catalog(kind="log_types", items=["a", "b"]).model_dump()
    assert c["kind"] == "log_types" and c["items"] == ["a", "b"]
