"""Logging configuration for the v2 MCP server.

Carried forward from v1 (``zscaler_mcp/common/logging.py``) verbatim in spirit:
a stderr-friendly configurator (so stdio transport never corrupts the MCP
protocol stream on stdout) plus the shared security-warning banner used by the
auth layer.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


def configure_logging(
    debug: bool = False, name: str = "zscaler_mcp", use_stderr: bool = False
) -> logging.Logger:
    """Configure root logging for the server.

    Args:
        debug: Enable DEBUG-level logging.
        name: Logger name to return.
        use_stderr: Route logs to stderr (recommended for stdio transport so
            log lines never collide with the JSON-RPC stream on stdout).
    """
    log_level = logging.DEBUG if debug else logging.INFO
    stream = sys.stderr if use_stderr else sys.stdout

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(stream)],
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a named logger (defaults to the ``zscaler_mcp`` root)."""
    return logging.getLogger(name if name else "zscaler_mcp")


def log_security_warning(title: str, details: list[str]) -> None:
    """Log a prominent, standardized security-warning banner.

    Used by the auth layer when a protective feature is disabled (e.g. MCP
    client authentication turned off, plaintext HTTP on a non-localhost bind).
    """
    _logger = get_logger("zscaler_mcp.security")
    _logger.warning("=" * 72)
    _logger.warning("  SECURITY WARNING: %s", title)
    _logger.warning("")
    for line in details:
        _logger.warning("  %s", line)
    _logger.warning("=" * 72)
