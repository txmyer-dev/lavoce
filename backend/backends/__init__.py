"""Lean backend registry for Lavoce.

Only remote providers: Microsoft Speech (STT) and FreeLLMAPI (LLM refinement).
No local models, no torch/transformers/huggingface. The heavy voicebox backend
factory (TTS engines, local Whisper, local Qwen) has been removed.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional, Protocol

from typing_extensions import runtime_checkable

DEFAULT_LLM_MAX_TOKENS = 512
DEFAULT_LLM_TEMPERATURE = 0.7


@dataclass
class ModelConfig:
    """Declarative config for a model variant (remote-only in Lavoce)."""

    model_name: str
    display_name: str
    engine: str
    hf_repo_id: str
    model_size: str = "default"
    size_mb: int = 0
    needs_trim: bool = False
    supports_instruct: bool = False
    languages: list[str] = field(default_factory=lambda: ["en"])


@runtime_checkable
class STTBackend(Protocol):
    """Protocol for STT backend implementations."""

    async def load_model(self, model_size: str) -> None: ...

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        model_size: Optional[str] = None,
    ) -> str: ...

    def unload_model(self) -> None: ...

    def is_loaded(self) -> bool: ...


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM (chat/completion) backend implementations."""

    async def load_model(self, model_size: str) -> None: ...

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
        temperature: float = DEFAULT_LLM_TEMPERATURE,
        model_size: Optional[str] = None,
        examples: Optional[list[tuple[str, str]]] = None,
    ) -> str: ...

    def unload_model(self) -> None: ...

    def is_loaded(self) -> bool: ...


STT_ENGINES = {"microsoft_stt": "Microsoft Speech to Text"}
LLM_ENGINES = {"freellmapi": "Remote FreeLLMAPI"}
TTS_ENGINES: dict[str, str] = {}

_stt_backends: dict[str, STTBackend] = {}
_llm_backends: dict[str, LLMBackend] = {}
_lock = threading.Lock()


def _microsoft_stt_configs() -> list[ModelConfig]:
    return [
        ModelConfig(
            model_name="microsoft-stt",
            display_name="Microsoft Speech to Text",
            engine="microsoft_stt",
            hf_repo_id="remote/microsoft-stt",
            model_size="microsoft-stt",
            size_mb=0,
            languages=["en", "zh", "ja", "ko", "de", "fr", "pt", "es", "it", "hi"],
        )
    ]


def _freellmapi_configs() -> list[ModelConfig]:
    return [
        ModelConfig(
            model_name="freellmapi-remote",
            display_name="FreeLLMAPI (local/remote)",
            engine="freellmapi",
            hf_repo_id="remote/freellmapi",
            model_size="freellmapi-remote",
            size_mb=0,
            languages=["en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"],
        )
    ]


def get_stt_model_configs() -> list[ModelConfig]:
    return _microsoft_stt_configs()


def get_llm_model_configs() -> list[ModelConfig]:
    return _freellmapi_configs()


def get_tts_model_configs() -> list[ModelConfig]:
    return []


def get_all_model_configs() -> list[ModelConfig]:
    return _microsoft_stt_configs() + _freellmapi_configs()


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    for cfg in get_all_model_configs():
        if cfg.model_name == model_name:
            return cfg
    return None


def get_stt_backend_for_engine(engine: str) -> STTBackend:
    if engine != "microsoft_stt":
        raise ValueError(f"Unsupported STT engine: {engine}. Only 'microsoft_stt'.")
    with _lock:
        if "microsoft_stt" not in _stt_backends:
            from .microsoft_stt_backend import MicrosoftSTTBackend

            _stt_backends["microsoft_stt"] = MicrosoftSTTBackend()
        return _stt_backends["microsoft_stt"]


def get_llm_backend_for_engine(engine: str) -> LLMBackend:
    if engine != "freellmapi":
        raise ValueError(f"Unsupported LLM engine: {engine}. Only 'freellmapi'.")
    with _lock:
        if "freellmapi" not in _llm_backends:
            from .freellmapi_backend import FreeLLMAPIBackend

            _llm_backends["freellmapi"] = FreeLLMAPIBackend()
        return _llm_backends["freellmapi"]


def get_llm_backend() -> LLMBackend:
    return get_llm_backend_for_engine("freellmapi")


def reset_backends() -> None:
    _stt_backends.clear()
    _llm_backends.clear()
