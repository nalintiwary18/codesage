"""
Config loader — merges configuration from multiple sources into one CodesageConfig.

Resolution priority (highest to lowest):
  1. CLI flags (caller-supplied cli_overrides dict)
  2. Environment variables (CODESAGE_* and provider-specific API keys)
  3. .codesage.yml file in the target directory
  4. Hardcoded defaults in config/defaults.py
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

from src.config.defaults import CONFIG_FILE_NAME, DEFAULT_PROVIDER
from src.config.schema import CodesageConfig


def load_config(
    target_path: str = ".",
    cli_overrides: Optional[dict[str, Any]] = None,
) -> CodesageConfig:
    """
    Build and return a validated CodesageConfig by merging all config sources.
    The .env file is loaded first so that environment variables are available
    when reading provider API keys.
    """

    # Load .env so OPENAI_API_KEY etc. are available in os.environ
    load_dotenv()

    # Collect values from .codesage.yml if it exists
    file_config = _load_yaml_config(target_path)

    # Collect values from environment variables
    env_config = _load_env_config()

    # Merge: file < env < CLI
    merged = {**file_config, **env_config}

    if cli_overrides:
        # Only apply non-None overrides — None means "not specified by caller"
        merged.update({k: v for k, v in cli_overrides.items() if v is not None})

    # target_path is always set from the caller, not from config files
    merged["target_path"] = target_path

    return CodesageConfig(**merged)


def _load_yaml_config(target_path: str) -> dict[str, Any]:
    """
    Parse .codesage.yml from the given directory.
    Returns an empty dict if the file doesn't exist or cannot be parsed.
    Errors are silently ignored — the caller falls back to defaults.
    """
    config_path = Path(target_path) / CONFIG_FILE_NAME

    if not config_path.is_file():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except (yaml.YAMLError, OSError):
        return {}


def _load_env_config() -> dict[str, Any]:
    """
    Read config values from environment variables.
    Only CODESAGE_-prefixed variables and provider API keys are considered.
    """
    config: dict[str, Any] = {}

    if provider := os.getenv("CODESAGE_PROVIDER"):
        config["provider"] = provider

    if model := os.getenv("CODESAGE_MODEL"):
        config["model"] = model

    if log_level := os.getenv("CODESAGE_LOG_LEVEL"):
        config["log_level"] = log_level

    # Resolve the API key for whichever provider is configured
    api_key = _get_api_key_from_env(config.get("provider", DEFAULT_PROVIDER))
    if api_key:
        config["api_key"] = api_key

    return config


def _get_api_key_from_env(provider: str) -> Optional[str]:
    """
    Return the API key from the environment variable that matches the provider.
    Ollama runs locally and does not require an API key; returns None for it.
    """
    key_map = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
    }

    env_var = key_map.get(provider)
    return os.getenv(env_var) if env_var else None


def save_config_to_yaml(config: CodesageConfig, target_path: str = ".") -> Path:
    """
    Persist the current config to .codesage.yml in the target directory.
    Sensitive fields (api_key, no_wizard) are excluded from the saved file.
    Called by the `init` command after the wizard completes.
    """
    config_path = Path(target_path) / CONFIG_FILE_NAME
    config_data = config.model_dump(exclude={"api_key", "no_wizard"})

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    return config_path
