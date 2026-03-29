"""
Ollama backend for locally hosted models. No API key required.
Requires Ollama to be running locally: https://ollama.ai
"""

from typing import Optional

import ollama as ollama_client

from src.agents.llm.client import LLMProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """
    LLMProvider implementation that talks to a locally running Ollama server.
    api_key is accepted for interface compatibility but always ignored.
    """

    def __init__(self, model: str, api_key: Optional[str] = None):
        # api_key is intentionally discarded — Ollama has no authentication
        super().__init__(model=model, api_key=None)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # System prompt is prepended inline since Ollama's generate() API
        # does not have a dedicated system_prompt parameter
        full_prompt = f"{system_prompt}\n\n---\n\n{prompt}" if system_prompt else prompt

        logger.debug(f"Ollama call — model: {self._model}")
        try:
            response = ollama_client.generate(
                model=self._model,
                prompt=full_prompt,
                options={"temperature": 0.2},
            )
            content = response.get("response", "")
            logger.debug(f"Ollama response: {len(content)} chars")
            return content
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            logger.error("Ensure Ollama is running. Start it with: ollama serve")
            raise

    @property
    def provider_name(self) -> str:
        return "ollama"

    @staticmethod
    def is_available() -> bool:
        """
        Return True if the Ollama server responds to a list request.
        Used by the doctor command for environment diagnostics.
        """
        try:
            ollama_client.list()
            return True
        except Exception:
            return False