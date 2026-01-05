"""
Logging configuration for CallMate API.
"""

import logging
import sys
from typing import Optional

from app.core.config import settings


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               Defaults to DEBUG in development, INFO in production.

    Returns:
        Configured logger instance
    """
    # Determine log level
    if level is None:
        level = "DEBUG" if settings.DEBUG else "INFO"

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Create app logger
    app_logger = logging.getLogger("callmate")
    app_logger.setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    app_logger.info(f"Logging initialized | level={level} | env={settings.ENVIRONMENT}")

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance

    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Processing request")
    """
    return logging.getLogger(f"callmate.{name}")


# Initialize on import
logger = setup_logging()
