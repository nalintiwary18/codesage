"""Anthropic Claude backend. Requires ANTHROPIC_API_KEY."""

from typing import Optional

from anthropic import Anthropic

from src.agents.llm.client import LLMProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """LLMProvider implementation backed by the Anthropic Messages API."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        super().__init__(model=model, api_key=api_key)
        self._client = Anthropic(api_key=api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        logger.debug(f"Anthropic call — model: {self._model}")

        kwargs = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Anthropic's API takes the system prompt as a top-level field, not in messages
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._client.messages.create(**kwargs)
        content = response.content[0].text if response.content else ""
        logger.debug(f"Anthropic response: {len(content)} chars")
        return content

    @property
    def provider_name(self) -> str:
        return "anthropic"
