"""
FreeLLMAPI backend implementation.

Delegates LLM inference to a local or remote FreeLLMAPI instance.
Configurable via VOICEBOX_FREELLMAPI_URL and VOICEBOX_FREELLMAPI_MODEL
environment variables.
"""

import os
import httpx
import logging
from typing import Optional

from . import DEFAULT_LLM_MAX_TOKENS, DEFAULT_LLM_TEMPERATURE

logger = logging.getLogger(__name__)


def _build_messages(
    prompt: str,
    system: Optional[str],
    examples: Optional[list[tuple[str, str]]] = None,
) -> list[dict]:
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    if examples:
        for user_text, assistant_text in examples:
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
    messages.append({"role": "user", "content": prompt})
    return messages


class FreeLLMAPIBackend:
    """LLM backend that makes HTTP requests to a FreeLLMAPI endpoint."""

    def __init__(self, model_size: str = "freellmapi-remote"):
        self.model_size = model_size
        self._current_model_size: Optional[str] = None
        
        self.api_url = os.environ.get(
            "VOICEBOX_FREELLMAPI_URL",
            "http://localhost:3001/v1/chat/completions"
        )
        self.api_model = os.environ.get(
            "VOICEBOX_FREELLMAPI_MODEL",
            "auto"
        )
        # FreeLLMAPI gates its /v1 proxy behind a unified bearer token
        # ("freellmapi-…"). Without it the proxy returns 401 and refinement
        # silently fails. Optional so self-hosted, unauthenticated endpoints
        # still work.
        self.api_key = os.environ.get("VOICEBOX_FREELLMAPI_KEY", "").strip()

    def is_loaded(self) -> bool:
        # Remote models are always "loaded" from the client perspective
        return self._current_model_size is not None

    async def load_model(self, model_size: Optional[str] = None) -> None:
        if model_size is None:
            model_size = self.model_size
            
        logger.info(f"Connecting to remote FreeLLMAPI backend at {self.api_url} for model {model_size}")
        self._current_model_size = model_size
        self.model_size = model_size

    def unload_model(self) -> None:
        self._current_model_size = None
        logger.info("FreeLLMAPI backend detached")

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
        temperature: float = DEFAULT_LLM_TEMPERATURE,
        model_size: Optional[str] = None,
        examples: Optional[list[tuple[str, str]]] = None,
    ) -> str:
        await self.load_model(model_size)
        messages = _build_messages(prompt, system, examples)
        
        payload = {
            "model": self.api_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        logger.info(f"Sending LLM request to FreeLLMAPI at {self.api_url}")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.error(f"FreeLLMAPI request failed: {e}")
                raise RuntimeError(f"FreeLLMAPI remote generation failed: {e}")
