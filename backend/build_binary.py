"""PyInstaller build script for the Lavoce standalone server binary.

Lavoce is a thin remote client (Azure STT + FreeLLMAPI) with no local models,
so this build is small and simple — no torch/transformers/MCP hidden imports,
no CUDA/MLX handling, no runtime hooks.

Usage:
    python build_binary.py     # Build the CPU server binary (voicebox-server)
"""

import PyInstaller.__main__
import argparse
import logging
import os
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

# Kept as "voicebox-server" to match the Tauri sidecar (externalBin) target
# name; the internal binary name is not user-visible.
BINARY_NAME = "voicebox-server"


def build_server() -> None:
    """Build the Python server as a single standalone binary."""
    backend_dir = Path(__file__).parent

    args = [
        "server.py",
        "--onefile",
        "--name",
        BINARY_NAME,
    ]

    # Hide the console window on Windows (Tauri captures logs via the pipe).
    if platform.system() == "Windows":
        args.append("--noconsole")

    # The app is small and mostly statically imported. Name the pieces
    # PyInstaller's static analysis can miss: function-level router/backend
    # imports and uvicorn's dynamically-loaded protocol modules.
    args.extend(
        [
            "--hidden-import", "backend",
            "--hidden-import", "backend.main",
            "--hidden-import", "backend.app",
            "--hidden-import", "backend.config",
            "--hidden-import", "backend.database",
            "--hidden-import", "backend.database.session",
            "--hidden-import", "backend.database.models",
            "--hidden-import", "backend.database.migrations",
            "--hidden-import", "backend.models",
            "--hidden-import", "backend.routes",
            "--hidden-import", "backend.routes.health",
            "--hidden-import", "backend.routes.transcription",
            "--hidden-import", "backend.routes.captures",
            "--hidden-import", "backend.routes.settings",
            "--hidden-import", "backend.routes.tasks",
            "--hidden-import", "backend.services.captures",
            "--hidden-import", "backend.services.refinement",
            "--hidden-import", "backend.services.transcribe",
            "--hidden-import", "backend.services.llm",
            "--hidden-import", "backend.services.settings",
            "--hidden-import", "backend.services.task_queue",
            "--hidden-import", "backend.backends",
            "--hidden-import", "backend.backends.microsoft_stt_backend",
            "--hidden-import", "backend.backends.freellmapi_backend",
            "--hidden-import", "backend.utils.audio",
            "--hidden-import", "backend.utils.platform_detect",
            "--hidden-import", "backend.utils.progress",
            "--hidden-import", "backend.utils.tasks",
            "--hidden-import", "backend.utils.capture_chords",
            "--hidden-import", "fastapi",
            "--hidden-import", "sqlalchemy",
            "--hidden-import", "soundfile",
            "--hidden-import", "httpx",
            "--hidden-import", "multipart",
            "--collect-submodules", "uvicorn",
            # Belt-and-suspenders: never bundle heavy ML libs even if a build
            # environment happens to have them installed.
            "--exclude-module", "torch",
            "--exclude-module", "torchaudio",
            "--exclude-module", "transformers",
            "--exclude-module", "huggingface_hub",
            "--exclude-module", "librosa",
            "--exclude-module", "numba",
            "--exclude-module", "scipy",
            "--exclude-module", "matplotlib",
        ]
    )

    dist_dir = str(backend_dir / "dist")
    build_dir = str(backend_dir / "build")
    args.extend(
        [
            "--distpath", dist_dir,
            "--workpath", build_dir,
            "--noconfirm",
            "--clean",
        ]
    )

    os.chdir(backend_dir)
    PyInstaller.__main__.run(args)
    logger.info("Binary built in %s", backend_dir / "dist" / BINARY_NAME)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Lavoce server binary")
    parser.parse_args()
    build_server()
