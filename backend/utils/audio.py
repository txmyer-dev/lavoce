"""Audio utilities — captures-only (soundfile, no librosa/numba)."""

import os
from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf


def load_audio(
    path: str,
    sample_rate: int = 24000,
    mono: bool = True,
) -> Tuple[np.ndarray, int]:
    """Load an audio file for duration/inspection.

    Lavoce sends the original file bytes straight to Azure, so we do NOT
    resample here (that avoids the librosa/numba dependency). We return the
    samples at their native sample rate; callers only use this for duration
    (``len(audio) / sr``), which is invariant to sample rate.
    """
    audio, sr = sf.read(path, dtype="float32", always_2d=False)
    if mono and audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio, sr


def save_audio(audio: np.ndarray, path: str, sample_rate: int = 24000) -> None:
    """Atomically write a WAV file."""
    temp_path = f"{path}.tmp"
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(temp_path, audio, sample_rate, format="WAV")
        os.replace(temp_path, path)
    except Exception as e:
        try:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
        except Exception:
            pass
        raise OSError(f"Failed to save audio to {path}: {e}") from e
