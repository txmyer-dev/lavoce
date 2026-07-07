---
title: "feat: Lavoce — captures-only background dictation app (Windows-first)"
date: 2026-07-07
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
product_contract_source: ce-plan-bootstrap
target_repo: lavoce (new public repo, github.com/txmyer-dev/lavoce)
---

# feat: Lavoce — captures-only background dictation app (Windows-first)

## Product Contract

### Summary
Carve a new standalone desktop app **Lavoce** out of voicebox: an always-on
background **dictation service** (system tray; closing the window never stops
dictation) that does hotkey capture → **Azure STT** → optional **FreeLLMAPI**
refinement → paste, with **no local models**. Strip all TTS/voices/generations/
stories/effects/model-download surfaces. Ship a **Windows `.exe`** via GitHub
Actions. New **public** repo, **zero git history**, secrets never committed.

### Problem Frame
Voicebox is a heavyweight, model-downloading TTS+STT app. The only piece worth
keeping is captures/dictation, and its local-Whisper + local-Qwen defaults make
the app slow and download-bound. We proved Azure STT + FreeLLMAPI are solid and
much faster. Voicebox is also window-bound (floating/minimized/closed) with no
background service — closing the GUI stops dictation. Lavoce fixes both: thin
remote-only backend, and a tray-resident always-on dictation service.

### Requirements
- **R1** Captures pipeline works end-to-end with Azure STT + FreeLLMAPI only.
- **R2** No local models; no torch/transformers/huggingface in the shipped app.
- **R3** Background service: global hotkey dictation works with no window open;
  closing the window hides to tray; quit only via tray menu.
- **R4** Credentials supplied at runtime, never hardcoded: Rust launcher reads
  `%APPDATA%\lavoce\.env` and injects `VOICEBOX_*` env vars into the sidecar.
- **R5** Windows `.exe`/installer produced by GitHub Actions, downloadable.
- **R6** Public repo, zero history, no secrets committed; `.env.example` only.
- **R7** macOS/Linux capture plumbing kept dormant (compiles, not shipped now).

### Scope Boundaries
**In:** captures/dictation, settings for capture+refine, Azure STT backend,
FreeLLMAPI backend, tray/background lifecycle, credential seam, Windows CI.
**Out (removed):** all TTS engines, voice profiles, generations, stories,
effects, local Whisper, local Qwen LLM, model-download/management UI + routes.

#### Deferred to Follow-Up Work
- Option B credentials: in-app Settings UI + Windows Credential Manager.
- Code signing / notarization of the Windows installer.
- macOS/Linux release builds.

---

## Planning Contract

### Key Technical Decisions
- **KTD1 Reuse voicebox's build pipeline.** Adapt existing `build-windows.yml`
  (PyInstaller sidecar → `tauri-action`) rather than authoring CI fresh.
- **KTD2 Minimize internal churn.** Rebrand user-facing surfaces (productName,
  identifier, window/tray titles, data dir → `lavoce`) but keep the internal
  Python package name `backend` and sidecar binary name to reduce build breakage
  overnight. Clean-break is about repo/history/scope, not renaming every symbol.
- **KTD3 Credential seam = Rust spawn env injection.** In `start_server`, read
  `%APPDATA%\lavoce\.env` and pass `VOICEBOX_MICROSOFT_STT_*` / `VOICEBOX_FREELLMAPI_*`
  as `cmd.env(...)`. Python `load_dotenv` uses `setdefault`, so injected wins.
- **KTD4 Strip deps first.** Removing torch/transformers/hf from requirements is
  on the critical path — it shrinks the PyInstaller sidecar and removes the
  hidden-import failure surface that dominates Windows build risk.
- **KTD5 Local-first, then push.** Build lavoce in `/root/dev/lavoce`, get it
  importing/booting on Linux (sanity), then create the public repo and let
  Windows CI produce the `.exe`. I cannot run a Windows binary here.

### Assumptions
- The stripped backend boots without torch once TTS/whisper/qwen imports are gone
  (app.py imports torch at module load — must be removed). **Verify by booting.**
- `tauri-plugin-shell` sidecar + global-hotkey plugin already work on Windows in
  voicebox (release.yml ships Windows), so tray + hotkey are incremental.

---

## Implementation Units

### U1. Create lavoce working copy with zero history
**Goal:** Fresh tree in `/root/dev/lavoce`, no `.git`, secrets excluded.
**Files:** (new tree) copy of repo minus `.git`, `.env`, `node_modules`,
`target`, `__pycache__`, `dist`, `output`, model caches.
**Approach:** rsync with excludes; `git init`; confirm `.env` gitignored and
absent. Sanitize `.env.example` (already placeholders). Clean `docs/plans` of
voicebox-specific docs.
**Verification:** `git status` clean-ish; no `.env`; `git log` empty until first commit.

### U2. Strip backend to captures + remote backends only
**Goal:** Remove all TTS/local-STT/local-LLM code and routes; backend boots
without torch.
**Files:** delete `backend/backends/{mlx,pytorch,luxtts,chatterbox,chatterbox_turbo,hume,kokoro,qwen_custom_voice,qwen_llm}_backend.py`; trim `backend/backends/__init__.py` (keep `microsoft_stt`, `freellmapi`, drop TTS/whisper/qwen registries + config lists); delete routes `generations,profiles,stories,effects,speak,audio,llm,models,cuda`; trim `backend/routes/__init__.py` register_routers; remove `import torch` from `backend/app.py`; strip `backend/requirements.txt` to fastapi/uvicorn/sqlalchemy/httpx (+soundfile/librosa if capture decode needs them — verify).
**Approach:** Follow the import graph; remove `hf_offline_patch` import if it pulls transformers. Keep `models.py` capture models; drop TTS/generation pydantic models only if unreferenced.
**Test scenarios:** backend imports and `/health` responds; `/capture/readiness` returns stt=microsoft-stt ready; POST `/captures` transcribes via Azure (reuse this session's proven path). Covers R1, R2.
**Verification:** `python -m backend.main` boots on Linux with no torch installed; captures smoke test passes.

### U3. Strip frontend to Captures + trimmed Settings
**Goal:** Remove non-capture tabs/components; app builds.
**Files:** delete `app/src/components/{VoicesTab,VoiceProfiles,StoriesTab,Generation,AudioStudio,AudioTab,EffectsTab,Effects,ModelsTab,MainEditor,AudioPlayer}`; trim `Sidebar`, routing, and `ServerSettings` to capture-relevant; drop dead imports/i18n keys.
**Approach:** Keep `CapturesTab, CapturePill, DictateWindow, ChordPicker, DictationReadinessChecklist, AccessibilityGate, InputMonitoringGate, AudioBars`. Fix router/nav so default view is Captures.
**Test scenarios:** `bun run build:web` (or vite build) succeeds; `bun run typecheck` passes or errors are pre-existing/removed. Covers R1.
**Verification:** frontend builds clean.

### U4. Rebrand to Lavoce (user-facing + data dir)
**Goal:** Product identity + `%APPDATA%\lavoce` data/config dir.
**Files:** `tauri/src-tauri/tauri.conf.json` (productName "Lavoce", identifier e.g. `app.felaniam.lavoce`, window title, tray tooltip); app title/branding strings; backend data-dir/app-name so config lands under `lavoce`; `package.json` names.
**Approach:** Keep icons for now (swap later). Ensure the credential path and data dir both resolve to `lavoce`.
**Test scenarios:** none — cosmetic/config; covered by U6/U7 build. Test expectation: none -- rebrand strings/config.
**Verification:** grep shows productName/identifier/data-dir = lavoce.

### U5. Background dictation service (tray + window lifecycle)
**Goal:** Tray-resident service; close hides to tray; dictation runs windowless; quit only via tray.
**Files:** `tauri/src-tauri/src/main.rs` (+ `lib.rs`): tray icon + menu (Show/Hide, Quit), intercept window close → hide, keep sidecar + hotkey monitor alive; ensure global hotkey works with no focused window; wire `runInBackground`/`keepServerRunningOnClose` defaults on.
**Approach:** Use Tauri v2 tray API; on window close-requested, prevent default + hide. Hotkey monitor (`hotkey_monitor.rs`) already global — verify it fires without a window. Quit path stops sidecar cleanly.
**Test scenarios:** (manual/Windows) closing window keeps process + tray; hotkey triggers capture with no window; tray Quit exits and stops sidecar. Covers R3.
**Verification:** code paths correct; user validates on Windows.

### U6. Credential seam — Rust reads %APPDATA%\lavoce\.env, injects env
**Goal:** Sidecar gets Azure + FreeLLMAPI creds without a bundled file.
**Files:** `tauri/src-tauri/src/main.rs` `start_server`: locate `%APPDATA%\lavoce\.env` (create dir + template on first run if missing), parse KEY=VALUE, set `cmd.env(k, v)` for `VOICEBOX_*`; keep existing `VOICEBOX_MODELS_DIR` injection.
**Approach:** Minimal dotenv parse in Rust (or a small crate). On missing file, write `.env.example`-style template and surface a friendly "add your keys" state via readiness.
**Test scenarios:** with keys present, sidecar `is_configured` true and captures work; with keys absent, readiness shows configure-needed (no crash). Covers R4.
**Verification:** (Windows) app picks up keys from `%APPDATA%\lavoce\.env`.

### U7. Windows CI → downloadable .exe
**Goal:** GH Actions builds and uploads the Windows installer.
**Files:** adapt `.github/workflows/build-windows.yml`: strip torch steps, build sidecar via `build_binary.py` (fast now), copy to `tauri/src-tauri/binaries/`, `tauri-action` build, upload `.msi`/`.exe` as artifact (and draft release on tag). Remove `docker-publish.yml`, `release.yml` (voicebox-specific) or trim. `ci.yml` keep as typecheck/build gate.
**Approach:** Keep signing off (unsigned installer fine for now). Ensure `externalBin` triple-naming matches the copied binary. Trigger on push to main.
**Test scenarios:** none (CI); success = green run + downloadable installer artifact. Covers R5.
**Verification:** green `build-windows` run; installer artifact downloads.

### U8. Create public repo, push, iterate CI to green
**Goal:** Public `txmyer-dev/lavoce` with a green Windows build + installer.
**Files:** repo-level (gh repo create, initial commit, README).
**Approach:** `gh repo create lavoce --public`; push; watch `build-windows`; fix
failures (PyInstaller hidden imports, tauri config, missing assets) and re-push
until green. Poll CI on a cadence overnight.
**Test scenarios:** none. Covers R5, R6.
**Verification:** installer artifact available on the latest green run.

---

## Verification Contract
- **Linux sanity (me):** stripped backend boots without torch; captures POST
  transcribes via Azure; frontend builds; tauri config/rust compiles as far as
  a Linux `cargo check` allows.
- **Windows CI (me):** `build-windows` green; installer artifact produced.
- **Windows runtime (user, morning):** install `.exe`; drop keys in
  `%APPDATA%\lavoce\.env`; hotkey-dictate with window closed; text pastes.

## Definition of Done
Public `lavoce` repo exists with zero history and no secrets; a green Windows
CI run has a downloadable installer; backend is torch-free and captures-only;
tray/background lifecycle + credential seam implemented; a morning test
checklist is left for the user. Runtime confirmation on Windows is the user's.

## Risks
- **PyInstaller hidden-imports** (fastapi/uvicorn/pydantic/sqlalchemy) on Windows
  — mitigate with `--collect-all`/hidden-import flags; iterate in CI.
- **torch removal breaks shared imports** — trace `app.py`/`backends/__init__`;
  boot-test on Linux before pushing.
- **Tauri v2 tray API drift** — follow existing plugin usage; keep changes small.
- **Can't runtime-test Windows here** — leave a precise user checklist; keep the
  wiring provably correct via the Linux captures smoke test.
