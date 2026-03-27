"""
`codesage doctor` — environment diagnostics command.

Checks:
  - Python version (requires 3.11+)
  - Core library availability (click, pydantic, pathspec, etc.)
  - LLM SDK availability and API key presence per provider
  - Ollama server reachability (if the SDK is installed)
  - Project config files (.env, .codesage.yml)

Exits with a summary indicating whether the environment is ready for analysis.
"""

import os
import sys
from importlib.metadata import version, PackageNotFoundError

import click

from src.utils.spinner import print_success, print_error, print_warning, print_header, print_info


@click.command("doctor")
def doctor_command() -> None:
    """
    Run environment diagnostics and report the health of the setup.
    """
    print_header("CodeSage Doctor — Environment Diagnostics")

    all_ok = True

    # Python version check — 3.11+ required for union type hints and other features
    py = sys.version_info
    if py >= (3, 11):
        print_success(f"Python {py.major}.{py.minor}.{py.micro}")
    else:
        print_error(f"Python {py.major}.{py.minor} detected — 3.11+ required")
        all_ok = False

    # Core runtime dependencies
    for dep in ["click", "pydantic", "pathspec", "rich", "questionary", "pyyaml"]:
        try:
            print_success(f"{dep} v{version(dep)}")
        except PackageNotFoundError:
            print_error(f"{dep} not installed — run: pip install {dep}")
            all_ok = False

    # LLM provider SDKs and their corresponding API keys
    print_info("\nLLM Provider SDKs:")
    llm_deps = {
        "openai": "OPENAI_API_KEY",
        "google-generativeai": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "ollama": None,
    }

    for dep, env_var in llm_deps.items():
        try:
            sdk_label = f"{dep} v{version(dep)}"
        except PackageNotFoundError:
            sdk_label = f"{dep} (not installed)"

        if env_var:
            key = os.getenv(env_var, "")
            if key and len(key) > 5:
                print_success(f"{sdk_label} (API key: set)")
            else:
                print_warning(f"{sdk_label} (API key: {env_var} not set)")
        else:
            # For Ollama, check if the local server is reachable
            try:
                from src.agents.llm.providers.ollama import OllamaProvider
                if OllamaProvider.is_available():
                    print_success(f"{sdk_label} (server: running)")
                else:
                    print_warning(f"{sdk_label} (server: not reachable — run: ollama serve)")
            except Exception:
                print_warning(f"{sdk_label} (server check failed)")

    # Config file presence
    print_info("\nConfiguration:")
    from pathlib import Path
    if Path(".env").is_file():
        print_success(".env file found")
    else:
        print_warning(".env file not found — copy from .env.example")

    if Path(".codesage.yml").is_file():
        print_success(".codesage.yml found")
    else:
        print_info(".codesage.yml not found — run: codesage init")

    print()
    if all_ok:
        print_success("Environment is ready!")
    else:
        print_error("Some checks failed — see above for details")
