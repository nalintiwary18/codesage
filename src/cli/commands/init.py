"""
`codesage init` — creates a .codesage.yml config file via an interactive wizard.

Does not run any analysis — only collects user preferences and persists them
to eliminate the need for wizard prompts on subsequent `codesage run` invocations.
"""

import click
import questionary

from src.config.defaults import PROVIDER_MODELS, SUPPORTED_LANGUAGES
from src.config.loader import load_config, save_config_to_yaml
from src.utils.spinner import print_success, print_error, print_header, print_info


@click.command("init")
@click.argument("target", default=".", type=click.Path(exists=True))
def init_command(target: str) -> None:
    """
    Initialise CodeSage config for a project directory.
    Creates .codesage.yml in TARGET (defaults to current directory).
    """
    print_header("CodeSage Init — Setup Configuration")

    try:
        answers = _collect_settings()
        config = load_config(target_path=target, cli_overrides=answers)
        saved = save_config_to_yaml(config, target)
        print()
        print_success(f"Config saved: {saved}")
        print_info("Run `codesage run .` to start analysis.")
    except click.Abort:
        print_error("Init cancelled.")


def _collect_settings() -> dict:
    """Prompt the user for essential configuration and return as a dict."""
    print_info("A few questions to set up your project:\n")
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
        choices=["OpenAI", "Gemini", "Anthropic", "Groq", "Ollama (local)"],
    ).ask()
    if provider is None:
        raise click.Abort()
    provider_key = provider.lower().split("(")[0].strip()
    answers["provider"] = provider_key

    available_models = PROVIDER_MODELS.get(provider_key, ["default"])
    model = questionary.select(
        "Select model:",
        choices=[*available_models, "custom"],
    ).ask()
    if model is None:
        raise click.Abort()
    if model == "custom":
        model = questionary.text("Enter custom model name:").ask()
        if model is None:
            raise click.Abort()
    answers["model"] = model

    output = questionary.text("Output file name?", default="report.md").ask()
    if output is None:
        raise click.Abort()
    answers["output_filename"] = output.strip()

    return answers
