"""Wire-encoding package — the single JSON/CSV decision point (DESIGN.md §5 Pillar D).

This ``__init__`` only declares the package's public API. The implementation
lives in :mod:`zscaler_mcp.encoding.encoder`. Import from this package:

    from zscaler_mcp.encoding import WireFormat, encode
"""

from zscaler_mcp.encoding.encoder import WireFormat, encode

__all__ = ["WireFormat", "encode"]
