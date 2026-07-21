from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sircom2026 import __version__
from sircom2026.api.errors import ApiError, register_error_handlers
from sircom2026.api.security import (
    AccessAction,
    AccessPolicy,
    ActorContext,
    LocalAccessPolicy,
    require_action,
)
from sircom2026.config import ConfigError, Settings, load_settings
from sircom2026.database import connect_sqlite


TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
DSFR_VERSION = "1.14.4"
DSFR_ASSETS_PATH = f"/static/dsfr/{DSFR_VERSION}"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    ok: bool
    code: str
    details: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"name": self.name, "ok": self.ok, "code": self.code}
        if self.details:
            payload["details"] = self.details
        return payload


def create_app(
    settings: Settings | None = None,
    *,
    access_policy: AccessPolicy | None = None,
) -> FastAPI:
    settings_error: ConfigError | None = None
    if settings is None:
        try:
            settings = load_settings()
        except ConfigError as exc:
            settings_error = exc
            settings = load_settings({})

    app = FastAPI(
        title="Sircom 2026",
        version=__version__,
        description="Socle local de l'application Sircom 2026.",
    )
    app.state.settings = settings
    app.state.settings_error = settings_error
    app.state.access_policy = access_policy or LocalAccessPolicy()
    register_error_handlers(app)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def index(request: Request):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": "Sircom 2026",
                "app_version": __version__,
                "dsfr_assets_path": DSFR_ASSETS_PATH,
                "dsfr_version": DSFR_VERSION,
            },
        )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "sircom2026", "version": __version__}

    @app.get("/health/ready", tags=["health"])
    async def health_ready() -> JSONResponse:
        payload = check_readiness(app.state.settings, app.state.settings_error)
        return JSONResponse(
            status_code=200 if payload["ready"] else 503,
            content=payload,
        )

    @app.get("/api/config/limits", tags=["config"])
    async def config_limits(
        _actor: ActorContext = Depends(require_action(AccessAction.CONFIG_READ)),
    ) -> dict[str, object]:
        if app.state.settings_error is not None:
            raise ApiError(
                500,
                "SIRCOM_CONFIG_INVALID",
                "Configuration invalide.",
            )
        return {"limits": app.state.settings.public_limits()}

    return app


def check_readiness(
    settings: Settings,
    settings_error: ConfigError | None = None,
) -> dict[str, object]:
    checks: list[ReadinessCheck] = []

    if settings_error is not None:
        checks.append(ReadinessCheck("config", False, "SIRCOM_CONFIG_INVALID"))
        return _readiness_payload(checks)

    checks.append(ReadinessCheck("config", True, "SIRCOM_CONFIG_OK"))
    checks.append(_check_data_dir(settings))
    if checks[-1].ok:
        checks.append(_check_sqlite(settings))
        checks.append(_check_disk(settings))

    return _readiness_payload(checks)


def _readiness_payload(checks: list[ReadinessCheck]) -> dict[str, object]:
    ready = all(check.ok for check in checks)
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "code": "SIRCOM_READY" if ready else "SIRCOM_NOT_READY",
        "checks": [check.to_dict() for check in checks],
    }


def _check_data_dir(settings: Settings) -> ReadinessCheck:
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        if not settings.data_dir.is_dir():
            return ReadinessCheck("data_dir", False, "SIRCOM_DATA_DIR_NOT_DIRECTORY")
        probe = settings.data_dir / ".sircom-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        return ReadinessCheck("data_dir", False, "SIRCOM_DATA_DIR_NOT_WRITABLE")
    return ReadinessCheck("data_dir", True, "SIRCOM_DATA_DIR_OK")


def _check_sqlite(settings: Settings) -> ReadinessCheck:
    connection = None
    try:
        connection = connect_sqlite(
            settings.sqlite_path,
            busy_timeout_ms=settings.sqlite_busy_timeout_ms,
        )
        connection.execute("SELECT 1")
    except Exception:
        return ReadinessCheck("sqlite", False, "SIRCOM_SQLITE_UNAVAILABLE")
    finally:
        if connection is not None:
            connection.close()
    return ReadinessCheck("sqlite", True, "SIRCOM_SQLITE_OK")


def _check_disk(settings: Settings) -> ReadinessCheck:
    try:
        usage = shutil.disk_usage(settings.data_dir)
    except OSError:
        return ReadinessCheck("disk", False, "SIRCOM_DISK_UNAVAILABLE")

    free_mb = usage.free // (1024 * 1024)
    details = {"free_mb": free_mb, "required_mb": settings.disk_free_min_mb}
    if free_mb < settings.disk_free_min_mb:
        return ReadinessCheck("disk", False, "SIRCOM_DISK_FREE_LOW", details)
    return ReadinessCheck("disk", True, "SIRCOM_DISK_OK", details)


app = create_app()
