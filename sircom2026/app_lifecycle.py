from __future__ import annotations

import asyncio
import logging
import shutil
import sqlite3
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass

from fastapi import FastAPI

from sircom2026.artifacts import ArtifactStore
from sircom2026.config import ConfigError, Settings
from sircom2026.database import Database, SchemaVersionError, connect_sqlite
from sircom2026.purge import purge_expired_lots, purge_expired_lots_for_settings
from sircom2026.worker_runner import run_worker_once

LOGGER = logging.getLogger(__name__)

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


def build_lifespan(settings: Settings, settings_error: ConfigError | None):
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        reconcile_artifacts_at_startup(settings, settings_error)
        purge_task: asyncio.Task[None] | None = None
        worker_task: asyncio.Task[None] | None = None
        if settings_error is None:
            purge_task = asyncio.create_task(periodic_purge_loop(settings))
            if settings.worker_enabled:
                worker_task = asyncio.create_task(periodic_worker_loop(settings))
        try:
            yield
        finally:
            for task in (purge_task, worker_task):
                if task is not None:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task

    return lifespan


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


async def periodic_worker_loop(settings: Settings) -> None:
    while True:
        try:
            result = await asyncio.to_thread(run_worker_once, settings=settings)
        except (OSError, SchemaVersionError, sqlite3.Error, ValueError):
            LOGGER.warning("technical_event=periodic_worker_failed", exc_info=True)
            await asyncio.sleep(settings.worker_poll_seconds)
            continue
        await asyncio.sleep(0 if result.processed else settings.worker_poll_seconds)


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
