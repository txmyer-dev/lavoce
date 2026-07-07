# Lavoce

An always-on **background dictation service** for the desktop. Press a hotkey,
speak, and your words are transcribed and pasted — anywhere, with no window open.

Lavoce is a thin, fast client: speech-to-text runs on **Azure AI Speech** (fast
transcription) and optional cleanup runs on a **FreeLLMAPI** endpoint. There are
**no local models to download** — it starts instantly and stays small.

> Lavoce began as a captures-only carve-out of a larger voice toolkit, stripped
> down to the one thing worth keeping: dictation.

## Status

Early. Windows-first. The desktop app (Tauri) bundles a small Python sidecar
that talks to your Azure + FreeLLMAPI endpoints.

## Configuration

Lavoce reads credentials at runtime from `%APPDATA%\lavoce\.env` (never baked
into the binary). See [`.env.example`](.env.example) for the keys:

```
VOICEBOX_MICROSOFT_STT_ENDPOINT=...
VOICEBOX_MICROSOFT_STT_KEY=...
VOICEBOX_FREELLMAPI_URL=...
VOICEBOX_FREELLMAPI_KEY=...
```

## Building

Windows installers are built in CI (GitHub Actions → **Build Windows**). The
artifact is a downloadable installer under each workflow run.

Local backend dev:

```
pip install -r backend/requirements.txt
uvicorn backend.main:app --port 17493
```

## License

See [LICENSE](LICENSE).
