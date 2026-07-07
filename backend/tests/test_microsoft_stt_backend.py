"""Regression coverage for Microsoft STT configuration and response parsing."""

from backend.backends import get_stt_model_configs
from backend.backends.microsoft_stt_backend import MicrosoftSTTBackend


def test_microsoft_stt_config_matches_capture_setting():
    cfg = next(c for c in get_stt_model_configs() if c.model_name == "microsoft-stt")

    assert cfg.model_size == "microsoft-stt"
    assert cfg.engine == "microsoft_stt"
    assert cfg.hf_repo_id == "remote/microsoft-stt"


def test_microsoft_stt_backend_reads_azure_env_aliases(monkeypatch):
    monkeypatch.delenv("VOICEBOX_MICROSOFT_STT_ENDPOINT", raising=False)
    monkeypatch.delenv("VOICEBOX_MICROSOFT_STT_KEY", raising=False)
    monkeypatch.setenv("VOICEBOX_AZURE_SPEECH_ENDPOINT", "https://voicebox-test.cognitiveservices.azure.com/")
    monkeypatch.setenv("VOICEBOX_AZURE_SPEECH_KEY", "test-key")

    backend = MicrosoftSTTBackend()

    assert backend.is_configured
    assert backend._transcribe_url() == (
        "https://voicebox-test.cognitiveservices.azure.com"
        "/speechtotext/transcriptions:transcribe?api-version=2025-10-15"
    )


def test_microsoft_stt_language_codes_become_azure_locales():
    backend = MicrosoftSTTBackend()

    assert backend._resolve_locale("en") == "en-US"
    assert backend._resolve_locale("ja") == "ja-JP"
    assert backend._resolve_locale("en-GB") == "en-GB"


def test_microsoft_stt_extracts_combined_phrases():
    backend = MicrosoftSTTBackend()

    transcript = backend._extract_transcript(
        {
            "combinedPhrases": [
                {"text": "First sentence."},
                {"text": "Second sentence."},
            ]
        }
    )

    assert transcript == "First sentence.\nSecond sentence."


def test_microsoft_stt_extracts_phrase_fallback():
    backend = MicrosoftSTTBackend()

    transcript = backend._extract_transcript(
        {
            "phrases": [
                {"nBest": [{"display": "Fallback sentence."}]},
            ]
        }
    )

    assert transcript == "Fallback sentence."
