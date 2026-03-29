"""
`codesage run` command — executes the full analysis pipeline.

The 10-step pipeline:
  1. Load files (respecting .gitignore and binary/size exclusions)
  2. Chunk code (AST for Python, regex for others; large blocks split)
  3. Build index and select top-N chunks by importance score
  4. Connect to LLM provider
  5. Generate codebase understanding (context for detection)
  6. Detect issues (chunk_id + relative lines only)
  7. Review/filter detected issues (false-positive removal)
  8. Polish issue text (descriptions and fixes)
  9. Structural + semantic validation (resolve lines, reject hallucinations)
  10. Generate and save Markdown report
Wizard questions are presented before the pipeline when --no-wizard is not set.
"""

import click
import questionary
from pathlib import Path
from src.cli.options import common_options
from src.config.defaults import PROVIDER_MODELS, SUPPORTED_LANGUAGES
from src.config.loader import load_config
from src.config.schema import CodesageConfig
from src.graph.builder import build_graph
from src.utils.logger import setup_logger, get_logger
from src.utils.spinner import spinner, print_success, print_error, print_header, print_info

@click.command("run")
@click.argument("target", default=".", type=click.Path(exists=True))
@common_options
def run_command(
    target: str,
    provider: str | None,
    model: str | None,
    output: str | None,
    verbose: bool,
    no_cache: bool,
    no_wizard: bool,
    max_chunks: int | None,
) -> None:
    """
    Analyze a codebase and write a Markdown report.
    TARGET is the path to the project directory (defaults to current directory).
    """
    setup_logger("DEBUG" if verbose else "INFO")

    print_header("Welcome to CodeSage!")

    # Collect CLI overrides — omit None values so defaults are not overwritten
    cli_overrides: dict = {k: v for k, v in {
        "provider": provider,
        "model": model,
        "output_filename": output,
        "cache_enabled": False if no_cache else None,
        "max_chunks": max_chunks,
        "no_wizard": no_wizard or False,
    }.items() if v is not None}

    config = load_config(target_path=target, cli_overrides=cli_overrides)

    if not config.no_wizard:
        wizard_answers = _run_wizard(config)
        config = load_config(target_path=target, cli_overrides={**cli_overrides, **wizard_answers})

    try:
        _execute_pipeline(config, target)
    except Exception as e:
        print_error(f"Analysis failed: {e}")
        get_logger(__name__).exception("Pipeline error")
        raise click.Abort()


def _run_wizard(config: CodesageConfig) -> dict:
    """
    Prompt the user for configuration choices interactively.
    Raises click.Abort if the user presses Ctrl+C at any prompt.
    """
    print_info("Quick setup — answer a few questions to get started.\n")
    answers: dict = {}

    language = questionary.select(
        "Which language is your codebase?",
        choices=SUPPORTED_LANGUAGES,
        default="Python",
    ).ask()
    if language is None:
        raise click.Abort()
    answers["language"] = language.lower().split("/")[0].strip()

    provider = questionary.select(
        "Which LLM provider?",
        choices=[
            questionary.Choice("OpenAI", value="openai"),
            questionary.Choice("Gemini", value="gemini"),
            questionary.Choice("Anthropic", value="anthropic"),
            questionary.Choice("Groq", value="groq"),
            questionary.Choice("Ollama (local)", value="ollama"),
        ],
        default="openai",
    ).ask()
    if provider is None:
        raise click.Abort()
    answers["provider"] = provider

    if provider != "ollama":
        api_key = questionary.password("Enter your API key:").ask()
        if api_key is None:
            raise click.Abort()
        if api_key.strip():
            answers["api_key"] = api_key.strip()

    available_models = PROVIDER_MODELS.get(provider, ["default"])
    model = questionary.select(
        "Select model:",
        choices=[*available_models, "custom"],
        default=available_models[0],
    ).ask()
    if model is None:
        raise click.Abort()
    if model == "custom":
        model = questionary.text("Enter custom model name:").ask()
        if model is None:
            raise click.Abort()
    answers["model"] = model

    output_name = questionary.text("Output file name?", default="report.md").ask()
    if output_name is None:
        raise click.Abort()
    answers["output_filename"] = output_name.strip()

    print()
    print_success("Setup complete! Starting analysis...")
    print()

    return answers


def _execute_pipeline(config, target):
    graph = build_graph()
    initial_state = {
        "config": config,
        "target": str(target),
        "files": [],
        "all_chunks": [],
        "index": None,
        "selected": [],
        "llm": None,
        "understanding": {},
        "raw_issues": [],
        "reviewed": [],
        "polished": [],
        "validated": [],
        "saved_path": None,
    }
    result = graph.invoke(initial_state)
    print()
    if result.get("saved_path"):
        print_success(f"Report saved: {result['saved_path']}")
        print_info(f"Total issues: {len(result.get('validated', []))}")
    else:
        print_info("No report generated — nothing to report.")
