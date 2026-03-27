"""Groq LPU backend. Requires GROQ_API_KEY. OpenAI-compatible API."""

from typing import Optional

from groq import Groq

from src.agents.llm.client import LLMProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GroqProvider(LLMProvider):
    """
    LLMProvider implementation backed by the Groq API.
    Groq uses an OpenAI-compatible chat completion format
    over a dedicated LPU (Language Processing Unit) backend.
    """

    def __init__(self, model: str, api_key: Optional[str] = None):
        super().__init__(model=model, api_key=api_key)
        self._client = Groq(api_key=api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Groq call — model: {self._model}")
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
        )
        content = response.choices[0].message.content or ""
        logger.debug(f"Groq response: {len(content)} chars")
        return content

    @property
    def provider_name(self) -> str:
        return "groq"
