from __future__ import annotations

from collections.abc import Callable, Mapping

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sircom2026 import __version__
from sircom2026.api.artifacts import router as artifacts_router
from sircom2026.api.errors import register_error_handlers
from sircom2026.api.lots import router as lots_router
from sircom2026.api.security import AccessPolicy, LocalAccessPolicy
from sircom2026.api.storage import router as storage_router
from sircom2026.app_lifecycle import build_lifespan
from sircom2026.config import ConfigError, Settings, load_settings
from sircom2026.web_constants import STATIC_DIR
from sircom2026.web_routes import register_web_routes

LoadSettings = Callable[[Mapping[str, str] | None], Settings]


def create_app(
    settings: Settings | None = None,
    *,
    access_policy: AccessPolicy | None = None,
    load_settings_func: LoadSettings = load_settings,
) -> FastAPI:
    settings_error: ConfigError | None = None
    if settings is None:
        try:
            settings = load_settings_func(None)
        except ConfigError as exc:
            settings_error = exc
            settings = load_settings_func({})

    app = FastAPI(
        title="Sircom 2026",
        version=__version__,
        description="Socle local de l'application Sircom 2026.",
        lifespan=build_lifespan(settings, settings_error),
    )
    app.state.settings = settings
    app.state.settings_error = settings_error
    app.state.access_policy = access_policy or LocalAccessPolicy(settings.bind_host)
    app.state.database_migrated = False
    register_error_handlers(app)
    app.include_router(artifacts_router)
    app.include_router(lots_router)
    app.include_router(storage_router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    register_web_routes(app)
    return app
