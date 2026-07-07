"""
Microsoft Speech to Text backend implementation.

Delegates STT to Azure AI Speech fast transcription. Configure with either:

- VOICEBOX_MICROSOFT_STT_ENDPOINT / VOICEBOX_MICROSOFT_STT_KEY
- VOICEBOX_AZURE_SPEECH_ENDPOINT / VOICEBOX_AZURE_SPEECH_KEY
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

API_VERSION = "2025-10-15"
DEFAULT_TIMEOUT_S = 120.0

LANGUAGE_TO_LOCALE = {
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "ja": "ja-JP",
    "zh": "zh-CN",
    "hi": "hi-IN",
    "it": "it-IT",
    "ko": "ko-KR",
    "pt": "pt-BR",
}


class MicrosoftSTTBackend:
    """STT backend that sends audio files to Azure AI Speech."""

    def __init__(self, model_size: str = "microsoft-stt"):
        self.model_size = model_size
        self.endpoint = (
            os.environ.get("VOICEBOX_MICROSOFT_STT_ENDPOINT")
            or os.environ.get("VOICEBOX_AZURE_SPEECH_ENDPOINT")
            or ""
        ).strip()
        self.api_key = (
            os.environ.get("VOICEBOX_MICROSOFT_STT_KEY")
            or os.environ.get("VOICEBOX_AZURE_SPEECH_KEY")
            or ""
        ).strip()
        self.default_locale = (
            os.environ.get("VOICEBOX_MICROSOFT_STT_LOCALE")
            or os.environ.get("VOICEBOX_AZURE_SPEECH_LOCALE")
            or "en-US"
        ).strip()
        self.profanity_filter_mode = (
            os.environ.get("VOICEBOX_MICROSOFT_STT_PROFANITY")
            or os.environ.get("VOICEBOX_AZURE_SPEECH_PROFANITY")
            or "None"
        ).strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    async def load_model(self, model_size: str) -> None:
        self.model_size = model_size
        if not self.is_configured:
            raise RuntimeError(
                "Microsoft STT requires VOICEBOX_MICROSOFT_STT_ENDPOINT "
                "and VOICEBOX_MICROSOFT_STT_KEY"
            )
        logger.info("Microsoft STT backend configured for %s", self.endpoint)

    def unload_model(self) -> None:
        logger.info("Microsoft STT backend detached")

    def is_loaded(self) -> bool:
        return self.is_configured

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        model_size: Optional[str] = None,
    ) -> str:
        if model_size:
            self.model_size = model_size
        if not self.is_configured:
            raise RuntimeError(
                "Microsoft STT requires VOICEBOX_MICROSOFT_STT_ENDPOINT "
                "and VOICEBOX_MICROSOFT_STT_KEY"
            )

        path = Path(audio_path)
        locale = self._resolve_locale(language)
        definition = {
            "locales": [locale],
            "profanityFilterMode": self.profanity_filter_mode,
        }
        url = self._transcribe_url()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

        logger.info("Sending STT request to Microsoft Speech at %s for locale %s", url, locale)

        with path.open("rb") as audio_file:
            files = {
                "audio": (path.name, audio_file, content_type),
                "definition": (None, json.dumps(definition), "application/json"),
            }
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
                response = await client.post(url, headers=headers, files=files)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text[:1000]
            raise RuntimeError(
                f"Microsoft STT failed with HTTP {response.status_code}: {detail}"
            ) from exc

        payload = response.json()
        transcript = self._extract_transcript(payload)
        if not transcript:
            raise RuntimeError("Microsoft STT returned no transcript text")
        return transcript.strip()

    def _transcribe_url(self) -> str:
        endpoint = self.endpoint.rstrip("/")
        return f"{endpoint}/speechtotext/transcriptions:transcribe?api-version={API_VERSION}"

    def _resolve_locale(self, language: Optional[str]) -> str:
        raw = (language or self.default_locale or "en-US").strip()
        if not raw or raw == "auto":
            return self.default_locale or "en-US"
        return LANGUAGE_TO_LOCALE.get(raw.lower(), raw)

    def _extract_transcript(self, payload: dict[str, Any]) -> str:
        combined = payload.get("combinedPhrases") or payload.get("combined_phrases")
        if isinstance(combined, list):
            texts = [
                item.get("text", "").strip()
                for item in combined
                if isinstance(item, dict) and item.get("text")
            ]
            if texts:
                return "\n".join(texts)

        phrases = payload.get("phrases")
        if isinstance(phrases, list):
            texts: list[str] = []
            for item in phrases:
                if not isinstance(item, dict):
                    continue
                best = item.get("nBest") or item.get("n_best")
                if isinstance(best, list) and best:
                    first = best[0]
                    if isinstance(first, dict):
                        text = first.get("display") or first.get("displayText") or first.get("text")
                        if text:
                            texts.append(str(text).strip())
                            continue
                text = item.get("text") or item.get("displayText")
                if text:
                    texts.append(str(text).strip())
            if texts:
                return " ".join(texts)

        text = payload.get("text") or payload.get("displayText") or payload.get("DisplayText")
        return str(text).strip() if text else ""
