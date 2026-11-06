"""Small provider interface with Gemini and Anthropic implementations."""

import os
from pathlib import Path
from typing import Protocol

from anthropic import Anthropic
from dotenv import load_dotenv
from google import genai


class CompletionClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return one text completion for the supplied prompt."""


class AnthropicCompletionClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )


class GeminiCompletionClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return response.text or ""


def create_llm_client() -> CompletionClient:
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY must be set to make a model call")
        model = os.getenv("LLM_MODEL", "gemini-3.8-flash")
        return GeminiCompletionClient(api_key=api_key, model=model)

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set to make a model call")
        model = os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929")
        return AnthropicCompletionClient(api_key=api_key, model=model)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")