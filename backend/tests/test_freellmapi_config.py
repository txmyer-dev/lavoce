"""Regression coverage for the FreeLLMAPI capture/refinement integration."""

from backend.backends import get_llm_model_configs
from backend.backends.freellmapi_backend import FreeLLMAPIBackend


def test_freellmapi_config_matches_capture_setting():
    cfg = next(
        c for c in get_llm_model_configs() if c.model_name == "freellmapi-remote"
    )

    assert cfg.model_size == "freellmapi-remote"
    assert cfg.hf_repo_id == "remote/freellmapi"


def test_freellmapi_backend_defaults_to_router_auto_model(monkeypatch):
    monkeypatch.delenv("VOICEBOX_FREELLMAPI_MODEL", raising=False)

    backend = FreeLLMAPIBackend()

    assert backend.model_size == "freellmapi-remote"
    assert backend.api_model == "auto"
