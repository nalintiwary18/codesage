"""OpenAI ChatCompletion backend. Requires OPENAI_API_KEY."""

from typing import Optional

from openai import OpenAI

from src.agents.llm.client import LLMProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """LLMProvider implementation backed by the OpenAI chat/completions API."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        super().__init__(model=model, api_key=api_key)
        # api_key=None causes the SDK to fall back to the OPENAI_API_KEY env var
        self._client = OpenAI(api_key=api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"OpenAI call — model: {self._model}")
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,   # Low temperature for deterministic, consistent output
            max_tokens=4096,
        )
        content = response.choices[0].message.content or ""
        logger.debug(f"OpenAI response: {len(content)} chars")
        return content

    @property
    def provider_name(self) -> str:
        return "openai"
