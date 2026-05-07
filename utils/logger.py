"""Centralised logger using the rich library."""

import logging
import sys
from rich.logging import RichHandler
from config import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with rich formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        logger.propagate = False
    return logger
