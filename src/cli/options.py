"""
Shared CLI flag definitions, applied as a decorator to any Click command.

Defining options here instead of per-command avoids duplication and ensures
consistent flag names and defaults across the `run` and `init` commands.
"""

import click
from functools import wraps
from typing import Any, Callable


def common_options(func: Callable) -> Callable:
    """
    Click decorator that attaches the standard CodeSage flags to a command.
    Apply this decorator after @click.command() on any command that shares
    the standard provider/model/output configuration flags.
    """

    @click.option(
        "--provider", "-p",
        type=click.Choice(["openai", "gemini", "anthropic", "groq", "ollama"]),
        default=None,
        help="LLM provider to use",
    )
    @click.option(
        "--model", "-m",
        type=str,
        default=None,
        help="Model name to use",
    )
    @click.option(
        "--output", "-o",
        type=str,
        default=None,
        help="Report output file name",
    )
    @click.option(
        "--verbose", "-v",
        is_flag=True,
        default=False,
        help="Enable DEBUG-level logging",
    )
    @click.option(
        "--no-cache",
        is_flag=True,
        default=False,
        help="Disable caching — force a fresh analysis of all chunks",
    )
    @click.option(
        "--no-wizard",
        is_flag=True,
        default=False,
        help="Skip the interactive setup wizard",
    )
    @click.option(
        "--max-chunks",
        type=int,
        default=None,
        help="Maximum number of chunks to analyze",
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper
