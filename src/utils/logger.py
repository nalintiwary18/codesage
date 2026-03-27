"""
Logger setup for the entire application.
Uses Rich's RichHandler for colored, readable console output.
Call setup_logger() once at startup; use get_logger(__name__) everywhere else.
"""

import logging

from rich.console import Console
from rich.logging import RichHandler


# Shared console instance — stderr so it doesn't pollute piped output
console = Console(stderr=True)


def setup_logger(level: str = "INFO") -> logging.Logger:
    """
    Configure the root logger with a Rich handler.
    Should be called once, at application entry, before any logging occurs.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                show_time=True,
                show_path=False,
                markup=True,
                rich_tracebacks=True,
            )
        ],
        force=True,  # Replace any handlers that may have been set earlier
    )

    logger = logging.getLogger("codesage")
    logger.setLevel(log_level)
    return logger


def get_logger(name: str = "codesage") -> logging.Logger:
    """
    Retrieve a named logger for use within a module.
    Convention: get_logger(__name__) at the top of each file.
    """
    return logging.getLogger(name)
