"""
Logging configuration for Zscaler Integrations MCP Server

This module provides logging utilities for the Zscaler Integrations MCP Server.
"""

import logging
import sys
from typing import Optional


def configure_logging(
    debug: bool = False, name: str = "zscaler_mcp", use_stderr: bool = False
) -> logging.Logger:
    """Configure logging for the Zscaler Integrations MCP Server.

    Args:
        debug: Enable debug logging
        name: Logger name
        use_stderr: Use stderr for logging (recommended for stdio transport)

    Returns:
        logging.Logger: Configured logger
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Use stderr for logging to avoid interfering with MCP protocol on stdout
    stream = sys.stderr if use_stderr else sys.stdout

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(stream)],
    )

    # Set third-party loggers to a higher level to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Get and return the logger for this application
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Logger name (defaults to "zscaler_mcp")

    Returns:
        logging.Logger: Logger instance
    """
    logger_name = name if name else "zscaler_mcp"
    return logging.getLogger(logger_name)
