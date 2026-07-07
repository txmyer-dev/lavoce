"""Lightweight root .env loader for local Voicebox configuration."""

from __future__ import annotations

import os
from pathlib import Path

_LOADED = False


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv(path: str | Path | None = None) -> None:
    """Load KEY=value pairs from the repo/runtime root .env file.

    Existing environment variables win, so Docker/Dokploy/shell-provided
    secrets are not overwritten by a local file.
    """
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    env_path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, _strip_quotes(value.strip()))
