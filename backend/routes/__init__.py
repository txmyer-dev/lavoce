"""Route registration for the Lavoce API (captures-only)."""

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """Include the captures/dictation routers on the application."""
    from .health import router as health_router
    from .transcription import router as transcription_router
    from .captures import router as captures_router
    from .settings import router as settings_router
    from .tasks import router as tasks_router

    app.include_router(health_router)
    app.include_router(transcription_router)
    app.include_router(captures_router)
    app.include_router(settings_router)
    app.include_router(tasks_router)
