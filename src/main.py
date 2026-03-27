"""
Application entry point.
Defines the root Click command group and registers all subcommands.
This module is invoked via `python -m src.main` or the `codesage` console script.
"""

import click

from src.cli.commands.run import run_command
from src.cli.commands.init import init_command
from src.cli.commands.doctor import doctor_command


@click.group()
@click.version_option(version="0.1.0", prog_name="codesage")
def cli() -> None:
    """
    CodeSage — AI-powered codebase analyzer.

    Analyzes a codebase and generates a structured Markdown report
    with line-referenced issues verified against real source files.
    """
    pass


cli.add_command(run_command)
cli.add_command(init_command)
cli.add_command(doctor_command)


if __name__ == "__main__":
    cli()
