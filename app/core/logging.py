"""
Centralized logging configuration.

Called exactly once, at application startup (from main.py), to configure
the root logger. Every other module should just do:

    import logging
    logger = logging.getLogger(__name__)

and use it — never call logging.basicConfig() anywhere else.
"""

import logging
import sys


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """
    Configure the root logger for the whole application.

    Args:
        level: One of "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging() is ever called twice
    # (e.g. in tests or with reload=True during development).
    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root_logger.addHandler(handler)

    # Third-party libraries tend to be very verbose at INFO/DEBUG level.
    # Keep them quieter unless we're explicitly debugging the app.
    if numeric_level > logging.DEBUG:
        for noisy_logger in ("httpx", "httpcore", "urllib3", "sqlalchemy.engine"):
            logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging configured at level %s", level.upper())