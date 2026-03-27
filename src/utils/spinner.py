"""
CLI progress indicators and styled output helpers.
Wraps Rich's Status and Console APIs so the rest of the codebase
doesn't depend on Rich directly for terminal feedback.
"""

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.status import Status


_console = Console(stderr=True)


@contextmanager
def spinner(message: str = "Processing...") -> Generator[Status, None, None]:
    """
    Context manager that displays an animated terminal spinner for the duration
    of the with-block.

    Usage:
        with spinner("Analyzing codebase..."):
            do_heavy_work()
    """
    with _console.status(f"[bold cyan]{message}[/]", spinner="dots") as status:
        yield status


@contextmanager
def step_spinner(step_name: str, step_number: int = 0) -> Generator[Status, None, None]:
    """
    Spinner variant that prefixes the message with a step number.
    Intended for numbered pipeline stages: "[1/5] Loading files..."
    """
    message = f"[{step_number}] {step_name}" if step_number > 0 else step_name
    with _console.status(f"[bold cyan]{message}[/]", spinner="dots") as status:
        yield status


def print_success(message: str) -> None:
    """Print a green success message with a checkmark prefix."""
    _console.print(f"[bold green]✅ {message}[/]")


def print_error(message: str) -> None:
    """Print a red error message with an X prefix."""
    _console.print(f"[bold red]❌ {message}[/]")


def print_warning(message: str) -> None:
    """Print a yellow warning message."""
    _console.print(f"[bold yellow]⚠️  {message}[/]")


def print_info(message: str) -> None:
    """Print a blue informational message."""
    _console.print(f"[bold blue]ℹ️  {message}[/]")


def print_header(title: str) -> None:
    """Print a prominent header line — used for command welcome screens."""
    _console.print()
    _console.print(f"[bold magenta]🚀 {title}[/]")
    _console.print()
