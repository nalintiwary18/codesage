"""
CodesageConfig — central configuration schema for the entire tool.
Validated by Pydantic at construction time so invalid configs fail early.

Config values are resolved in priority order:
  CLI flags > environment variables > .codesage.yml file > defaults
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Enumeration of supported LLM backend providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"


class Severity(str, Enum):
    """Issue severity levels from most to least critical."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CodesageConfig(BaseModel):
    """
    Single source of truth for all runtime configuration.
    Constructed once at startup and passed through the pipeline read-only.
    """

    # Path to the directory to be analyzed
    target_path: str = Field(
        default=".",
        description="Project directory to analyze",
    )

    # Primary language of the codebase — used for parser selection
    language: str = Field(
        default="python",
        description="Primary programming language of the codebase",
    )

    # Which LLM backend to use for analysis
    provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="LLM provider (openai / gemini / anthropic / groq / ollama)",
    )

    # Model identifier passed to the provider API
    model: str = Field(
        default="gpt-4o-mini",
        description="Model name to use for analysis",
    )

    # API key — required for cloud providers, unused for Ollama
    api_key: Optional[str] = Field(
        default=None,
        description="Provider API key — read from env if not set explicitly",
    )

    # Upper bound on chunks sent to the LLM in a single run
    max_chunks: int = Field(
        default=50,
        description="Maximum number of chunks to analyze per run",
        ge=1,
        le=500,
    )

    # Directory where generated reports are written
    output_dir: str = Field(
        default="./reports",
        description="Directory to write generated Markdown reports",
    )

    # Filename for the generated report
    output_filename: str = Field(
        default="report.md",
        description="Output report filename",
    )

    # Skip re-analysis of chunks whose content hash is already cached
    cache_enabled: bool = Field(
        default=True,
        description="Enable hash-based caching to skip unchanged chunks",
    )

    # Issues below this confidence threshold are filtered before the report
    min_confidence: float = Field(
        default=0.5,
        description="Minimum issue confidence required for inclusion in report",
        ge=0.0,
        le=1.0,
    )

    # Python logging level
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity level",
    )

    # When True, skip the interactive setup questionnaire
    no_wizard: bool = Field(
        default=False,
        description="Skip the interactive wizard if True",
    )

    model_config = {"use_enum_values": True}
