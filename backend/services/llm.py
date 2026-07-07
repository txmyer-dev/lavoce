"""
LLM inference module - delegates to backend abstraction layer.
"""

from ..backends import get_llm_backend, LLMBackend


def get_llm_model(model_size: str = None) -> LLMBackend:
    """Get LLM backend instance (MLX, PyTorch, or FreeLLMAPI)."""
    if model_size == "freellmapi-remote":
        from ..backends import get_llm_backend_for_engine
        return get_llm_backend_for_engine("freellmapi")
    return get_llm_backend()


def unload_llm_model(model_size: str = None) -> None:
    """Unload LLM model to free memory."""
    get_llm_model(model_size).unload_model()
