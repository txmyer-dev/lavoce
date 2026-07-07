"""STT (Speech-to-Text) module — delegates to the remote Microsoft backend."""

from typing import Optional

from ..backends import STTBackend, get_stt_backend_for_engine, get_stt_model_configs


def get_stt_model(model_size: Optional[str] = None) -> STTBackend:
    """Get the STT backend that owns ``model_size`` (Microsoft Speech only)."""
    if not model_size:
        model_size = "microsoft-stt"

    cfg = next((c for c in get_stt_model_configs() if c.model_size == model_size), None)
    if cfg is None:
        valid = ", ".join(c.model_size for c in get_stt_model_configs())
        raise ValueError(f"Invalid STT model '{model_size}'. Must be one of: {valid}")

    return get_stt_backend_for_engine(cfg.engine)


def unload_whisper_model() -> None:
    """No-op: Lavoce has no local Whisper model to unload."""
    return None
