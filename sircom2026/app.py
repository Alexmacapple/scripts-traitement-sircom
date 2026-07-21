from __future__ import annotations

import asyncio
import logging
import shutil
import sqlite3
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sircom2026 import __version__
from sircom2026.api.artifacts import router as artifacts_router
from sircom2026.api.errors import ApiError, register_error_handlers
from sircom2026.api.storage import router as storage_router
from sircom2026.api.security import (
    AccessAction,
    AccessPolicy,
    ActorContext,
    LocalAccessPolicy,
    require_action,
)
from sircom2026.api.lots import router as lots_router
from sircom2026.artifacts import ArtifactStore
from sircom2026.config import ConfigError, Settings, load_settings
from sircom2026.csv_preview import CsvPreviewError, get_csv_preview_payload
from sircom2026.database import Database, SchemaVersionError, connect_sqlite
from sircom2026.image_matching import ImageMatchingNotReady, get_persisted_image_matching
from sircom2026.images import ImageInspectionNotReady, get_persisted_image_inspection
from sircom2026.lots import get_lot_detail, list_lots
from sircom2026.mapping import MappingError, get_mapping_payload
from sircom2026.package import PackageNotReady, get_persisted_package
from sircom2026.purge import (
    purge_expired_lots,
    purge_expired_lots_for_settings,
    storage_summary,
)
from sircom2026.reports import ReportsNotReady, get_persisted_reports
from sircom2026.sorting import SortDecisionError, get_sort_payload


TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
DSFR_VERSION = "1.14.4"
DSFR_ASSETS_PATH = f"/static/dsfr/{DSFR_VERSION}"
LOGGER = logging.getLogger(__name__)

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

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        reconcile_artifacts_at_startup(settings, settings_error)
        purge_task: asyncio.Task[None] | None = None
        if settings_error is None:
            purge_task = asyncio.create_task(periodic_purge_loop(settings))
        try:
            yield
        finally:
            if purge_task is not None:
                purge_task.cancel()
                with suppress(asyncio.CancelledError):
                    await purge_task

    app = FastAPI(
        title="Sircom 2026",
        version=__version__,
        description="Socle local de l'application Sircom 2026.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.settings_error = settings_error
    app.state.access_policy = access_policy or LocalAccessPolicy(settings.bind_host)
    register_error_handlers(app)
    app.include_router(artifacts_router)
    app.include_router(lots_router)
    app.include_router(storage_router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def index(
        request: Request,
        _actor: ActorContext = Depends(require_action(AccessAction.LOT_READ)),
    ):
        lot_id = request.query_params.get("lot_id")
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": "Sircom 2026",
                "app_version": __version__,
                "dsfr_assets_path": DSFR_ASSETS_PATH,
                "dsfr_version": DSFR_VERSION,
                "limits": app.state.settings.public_limits(),
                **load_index_context(app.state.settings, app.state.settings_error, lot_id),
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


def reconcile_artifacts_at_startup(
    settings: Settings,
    settings_error: ConfigError | None,
) -> None:
    if settings_error is not None:
        return

    database = Database(
        settings.sqlite_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    try:
        database.migrate()
        with database.transaction() as repositories:
            expired_jobs = repositories.jobs.expire_stale_leases()
            report = store.reconcile(repositories)
            purge_outcomes = purge_expired_lots(repositories, settings=settings)
    except (OSError, SchemaVersionError, sqlite3.Error, ValueError):
        LOGGER.warning("technical_event=artifact_reconciliation_startup_failed", exc_info=True)
        return

    report_counts = report.to_dict()
    if expired_jobs or any(report_counts.values()) or purge_outcomes:
        LOGGER.info(
            "technical_event=artifact_reconciliation_startup counts=%s expired_jobs=%s purged=%s",
            report_counts,
            expired_jobs,
            len(purge_outcomes),
        )


async def periodic_purge_loop(settings: Settings) -> None:
    while True:
        await asyncio.sleep(settings.purge_interval_seconds)
        try:
            await asyncio.to_thread(purge_expired_lots_for_settings, settings)
        except (OSError, SchemaVersionError, sqlite3.Error, ValueError):
            LOGGER.warning("technical_event=periodic_purge_failed", exc_info=True)


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


def load_index_context(
    settings: Settings,
    settings_error: ConfigError | None,
    lot_id: str | None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "lots": [],
        "selected_lot": None,
        "storage": None,
        "ui_error": None,
    }
    if settings_error is not None:
        context["ui_error"] = ui_error(
            "Configuration invalide",
            "La configuration locale ne peut pas etre chargee.",
            "Corriger les variables SIRCOM_* puis relancer l'application.",
        )
        return context

    database = Database(
        settings.sqlite_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    try:
        database.migrate()
        with database.session() as repositories:
            storage = storage_summary(repositories, settings=settings)
            context["storage"] = storage
            storage_by_lot_id = {item["id"]: item for item in storage["lots"]}
            context["lots"] = list_lots(repositories, limit=20, offset=0)["items"]
            for lot_item in context["lots"]:
                lot_item["storage"] = storage_by_lot_id.get(lot_item["id"])
            if lot_id:
                try:
                    selected_lot = get_lot_detail(repositories, lot_id)
                    selected_lot["storage"] = storage_by_lot_id.get(lot_id)
                    try:
                        selected_lot["mapping"] = get_mapping_payload(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                    except MappingError as exc:
                        selected_lot["mapping"] = None
                        if exc.code != "SIRCOM_MAPPING_DIAGNOSTIC_NOT_READY":
                            selected_lot["mapping_error"] = mapping_ui_error(exc)
                    try:
                        selected_lot["sort"] = get_sort_payload(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                    except SortDecisionError:
                        selected_lot["sort"] = None
                    try:
                        selected_lot["csv_preview"] = get_csv_preview_payload(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                    except CsvPreviewError:
                        selected_lot["csv_preview"] = None
                    try:
                        selected_lot["image_inspection"] = get_persisted_image_inspection(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        ).inspection
                    except ImageInspectionNotReady:
                        selected_lot["image_inspection"] = None
                    try:
                        image_matching = get_persisted_image_matching(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                        selected_lot["image_matching"] = {
                            "matching": image_matching.matching,
                            "artifact": image_matching.artifact,
                            "processed_images_artifact": (
                                {
                                    **image_matching.processed_images_artifact,
                                    "download_url": (
                                        f"/api/lots/{lot_id}/downloads/"
                                        f"{image_matching.processed_images_artifact['id']}"
                                    ),
                                }
                                if image_matching.processed_images_artifact
                                else None
                            ),
                        }
                    except ImageMatchingNotReady:
                        selected_lot["image_matching"] = None
                    try:
                        reports = get_persisted_reports(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                        selected_lot["reports"] = {
                            "business_report_artifact": {
                                **reports.business_artifact,
                                "download_url": (
                                    f"/api/lots/{lot_id}/downloads/"
                                    f"{reports.business_artifact['id']}"
                                ),
                            },
                            "technical_report_artifact": {
                                **reports.technical_artifact,
                                "download_url": (
                                    f"/api/lots/{lot_id}/downloads/"
                                    f"{reports.technical_artifact['id']}"
                                ),
                            },
                        }
                    except ReportsNotReady:
                        selected_lot["reports"] = None
                    try:
                        package = get_persisted_package(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )
                        selected_lot["package"] = {
                            "artifact": {
                                **package.artifact,
                                "download_url": (
                                    f"/api/lots/{lot_id}/downloads/"
                                    f"{package.artifact['id']}"
                                ),
                            },
                        }
                    except PackageNotReady:
                        selected_lot["package"] = None
                    context["selected_lot"] = selected_lot
                except KeyError:
                    context["ui_error"] = ui_error(
                        "Lot introuvable",
                        "Le lot demande n'existe pas ou a ete retire.",
                        "Selectionner un lot actif dans la liste.",
                    )
    except (OSError, SchemaVersionError, sqlite3.Error):
        context["ui_error"] = ui_error(
            "Base locale indisponible",
            "SQLite ne peut pas etre ouvert ou migre.",
            "Verifier le dossier de donnees puis relancer l'application.",
        )
    return context


def ui_error(title: str, cause: str, action: str) -> dict[str, str]:
    return {
        "title": title,
        "cause": cause,
        "action": action,
    }


def mapping_ui_error(exc: MappingError) -> dict[str, str]:
    if exc.code == "SIRCOM_MAPPING_SOURCE_HEADERS_MISSING":
        action = (
            "Relancer le diagnostic Excel ou redéposer l'Excel pour reconstruire "
            "les métadonnées de colonnes."
        )
    elif exc.code == "SIRCOM_MAPPING_DIAGNOSTIC_BLOCKED":
        action = "Corriger l'Excel bloquant puis redéposer le fichier."
    else:
        action = "Relancer l'étape précédente ou redéposer l'Excel."
    return {
        "title": "Mapping indisponible",
        "cause": exc.message,
        "action": action,
        "code": exc.code,
    }


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
