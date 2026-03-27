"""
LLM client ABC and provider factory.

All LLM interactions in the system go through LLMProvider.generate().
New providers are added by:
  1. Subclassing LLMProvider in agents/llm/providers/
  2. Adding a branch in create_client()

The rest of the codebase only imports create_client() — never provider classes directly.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract base class that all LLM backends must implement."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send prompt to the LLM and return the generated text.
        Implementations must raise on API errors — do not return empty strings silently.
        """
        ...

    @property
    def model_name(self) -> str:
        return self._model

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Canonical provider identifier: "openai", "gemini", "anthropic", etc."""
        ...


def create_client(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
) -> LLMProvider:
    """
    Factory function: instantiates the correct LLMProvider for the given provider name.
    Imports are deferred to avoid loading all SDK libraries at startup.
    Raises ValueError for unknown provider names.
    """
    provider_lower = provider.lower()

    if provider_lower == "openai":
        from src.agents.llm.providers.openai import OpenAIProvider
        return OpenAIProvider(model=model, api_key=api_key)

    elif provider_lower == "gemini":
        from src.agents.llm.providers.gemini import GeminiProvider
        return GeminiProvider(model=model, api_key=api_key)

    elif provider_lower == "anthropic":
        from src.agents.llm.providers.anthropic import AnthropicProvider
        return AnthropicProvider(model=model, api_key=api_key)

    elif provider_lower == "groq":
        from src.agents.llm.providers.groq import GroqProvider
        return GroqProvider(model=model, api_key=api_key)

    elif provider_lower == "ollama":
        from src.agents.llm.providers.ollama import OllamaProvider
        return OllamaProvider(model=model, api_key=api_key)

    else:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Supported: openai, gemini, anthropic, groq, ollama"
        )
