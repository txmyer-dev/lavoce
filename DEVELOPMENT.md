# Lavoce — Development (Windows-first)

Lavoce is a Tauri v2 desktop app (Rust) that bundles a small Python **sidecar**
(FastAPI) as an `externalBin`. The sidecar talks to **Azure AI Speech** (STT) and
**FreeLLMAPI** (refinement). There are no local ML models.

## Prerequisites (Windows)

- **Rust** (stable) + MSVC build tools — https://rustup.rs
- **Bun** — https://bun.sh
- **Python 3.12** (on PATH)
- **WebView2** runtime (usually already present on Windows 11)

## Layout

- `backend/` — Python FastAPI sidecar (entry: `backend/server.py`; app: `backend/main.py`)
- `tauri/` — Tauri app; Rust in `tauri/src-tauri/src/main.rs`; frontend build in `tauri/`
- `app/` — React frontend source (still contains legacy voice tabs; see #U3)
- `.github/workflows/build-windows.yml` — CI that builds the installer

## Build the Python sidecar

```powershell
cd backend
python -m pip install --upgrade pip
pip install pyinstaller
pip install -r requirements.txt
python build_binary.py            # -> backend/dist/voicebox-server.exe

# Tauri expects the sidecar named with the Rust host triple:
$triple = (rustc --print host-tuple)   # x86_64-pc-windows-msvc
mkdir ..\tauri\src-tauri\binaries -Force
copy dist\voicebox-server.exe ..\tauri\src-tauri\binaries\voicebox-server-$triple.exe
```

## Run the app (dev)

```powershell
bun install
bun run dev          # tauri dev (spawns the sidecar; hot-reloads the frontend)
```

To run the sidecar standalone (e.g. to hit the API directly):

```powershell
uvicorn backend.main:app --port 17493
```

## Build the installer (local)

```powershell
bun install
cd tauri
bun run tauri build  # -> tauri/src-tauri/target/release/bundle/{nsis,msi}/
```

CI does the same on `windows-latest` and uploads the installer artifact.

## Credentials

Runtime only — never committed. The Rust launcher reads `%APPDATA%\lavoce\.env`
and injects `VOICEBOX_*` vars into the sidecar (writes a template on first run).
See [`.env.example`](.env.example). Note: `VOICEBOX_FREELLMAPI_URL` must be an
endpoint reachable **from the Windows machine** (not `host.docker.internal`).
