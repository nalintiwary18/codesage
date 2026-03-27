"""Google Gemini backend via google-generativeai. Requires GEMINI_API_KEY."""

from typing import Optional

import google.generativeai as genai

from src.agents.llm.client import LLMProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """LLMProvider implementation backed by the Google Generative AI SDK."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        super().__init__(model=model, api_key=api_key)
        if api_key:
            genai.configure(api_key=api_key)
        self._model_instance = genai.GenerativeModel(model)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Gemini's SDK does not expose a dedicated system-prompt field at this level,
        # so the system prompt is prepended directly to the user prompt.
        full_prompt = f"{system_prompt}\n\n---\n\n{prompt}" if system_prompt else prompt

        logger.debug(f"Gemini call — model: {self._model}")
        response = self._model_instance.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=4096,
            ),
        )
        content = response.text or ""
        logger.debug(f"Gemini response: {len(content)} chars")
        return content

    @property
    def provider_name(self) -> str:
        return "gemini"
