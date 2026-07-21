from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 4
LOGGER = logging.getLogger(__name__)

LOT_STATUSES = (
    "brouillon",
    "en_cours",
    "action_requise",
    "bloque",
    "termine",
    "termine_avec_alertes",
    "echoue",
    "annule",
    "supprime",
    "purge",
)
STEP_STATUSES = (
    "non_demarre",
    "pret",
    "en_cours",
    "action_requise",
    "bloque",
    "termine",
    "termine_avec_alertes",
    "echoue",
    "ignore",
    "annule",
    "invalide",
)
JOB_STATUSES = ("queued", "leased", "running", "succeeded", "failed", "canceled", "expired")
ARTIFACT_STATUSES = ("pending", "committed", "obsolete", "deleted", "quarantined")
PROBLEM_SEVERITIES = ("bloquant", "alerte", "information")
PROBLEM_STATUSES = ("open", "resolved", "obsolete")
EVENT_LEVELS = ("info", "warning", "error")
LOT_WRITE_BLOCKED_STATUSES = ("annule", "supprime", "purge")
MANAGED_TABLES = ("lots", "etapes", "jobs", "artefacts", "evenements", "problemes")
EXPECTED_TABLE_COLUMNS = {
    "lots": {
        "id",
        "created_at",
        "updated_at",
        "status",
        "title",
        "idempotency_key",
        "active_run_id",
        "cancel_requested_at",
        "delete_requested_at",
        "deleted_at",
        "purge_requested_at",
        "bytes_uploaded",
        "bytes_artifacts",
        "artifacts_count",
        "problems_open_count",
    },
    "etapes": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "status",
        "current_run_id",
        "input_fingerprint",
        "output_fingerprint",
        "progress_current",
        "progress_total",
        "started_at",
        "finished_at",
        "invalidated_at",
        "summary_json",
    },
    "jobs": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "status",
        "run_id",
        "idempotency_key",
        "lease_owner",
        "lease_version",
        "lease_until",
        "heartbeat_at",
        "attempt",
        "cancel_requested_at",
        "started_at",
        "finished_at",
        "error_code",
        "error_message",
    },
    "artefacts": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "run_id",
        "status",
        "kind",
        "role",
        "relative_path",
        "sha256",
        "size_bytes",
        "schema_version",
        "mime_type",
        "metadata_json",
        "committed_at",
        "obsoleted_at",
        "deleted_at",
        "quarantined_at",
    },
    "evenements": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "run_id",
        "level",
        "event_type",
        "payload_json",
    },
    "problemes": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "run_id",
        "severity",
        "code",
        "title",
        "cause",
        "message",
        "action",
        "location_json",
        "technical_json",
        "status",
        "resolved_at",
    },
}
EXPECTED_INDEXES = {
    "idx_lots_idempotency_key",
    "idx_etapes_lot_status",
    "idx_jobs_status_lease",
    "idx_jobs_lot_step",
    "idx_jobs_active_lot_step",
    "idx_artefacts_lot_status",
    "idx_artefacts_lot_step_run",
    "idx_evenements_lot_created",
    "idx_problemes_lot_status",
}
EXPECTED_FOREIGN_KEY_GROUPS = {
    "etapes": {("lot_id",)},
    "jobs": {("lot_id",), ("lot_id", "step_key")},
    "artefacts": {("lot_id",), ("lot_id", "step_key")},
    "evenements": {("lot_id",), ("lot_id", "step_key")},
    "problemes": {("lot_id",), ("lot_id", "step_key")},
}
TECHNICAL_EVENT_PAYLOAD_KEYS = {
    "artifact_id",
    "artifacts_count",
    "ambiguous_count",
    "code",
    "columns_count",
    "conversion_failed_count",
    "duration_ms",
    "error_code",
    "free_mb",
    "job_id",
    "level",
    "lot_id",
    "missing_count",
    "required_mb",
    "run_id",
    "rows_count",
    "rows_removed",
    "size_bytes",
    "status",
    "step_key",
    "steps_total",
    "tolerant_count",
    "warning_code",
    "active_jobs",
    "attempt",
    "input_fingerprint",
    "invalidated_steps_count",
    "lease_version",
    "manual_resolutions_count",
    "obsolete_artifacts_count",
    "output_fingerprint",
    "progress_current",
    "progress_total",
    "processed_images_count",
    "reason",
    "source_step_key",
    "unreferenced_count",
    "worker_id",
}
ACTIVE_JOB_STATUSES = ("queued", "leased", "running")
COMMITTABLE_JOB_STATUSES = ("leased", "running")


class SchemaVersionError(RuntimeError):
    """Raised when the SQLite schema version cannot be migrated safely."""


@dataclass(frozen=True)
class Database:
    path: Path
    busy_timeout_ms: int = 5000

    def connect(self) -> sqlite3.Connection:
        return connect_sqlite(self.path, busy_timeout_ms=self.busy_timeout_ms)

    def migrate(self) -> None:
        migrate_database(self.path, busy_timeout_ms=self.busy_timeout_ms)

    @contextmanager
    def session(self) -> Iterator[Repositories]:
        connection = self.connect()
        try:
            yield Repositories(connection)
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[Repositories]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield Repositories(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def connect_sqlite(
    path: Path,
    *,
    busy_timeout_ms: int = 5000,
    warning_handler: Callable[[str, str], None] | None = None,
) -> sqlite3.Connection:
    busy_timeout = int(busy_timeout_ms)
    if busy_timeout < 0:
        raise ValueError("busy_timeout_ms must be greater than or equal to 0.")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {busy_timeout}")
    try:
        connection.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error as exc:
        if warning_handler is not None:
            warning_handler("SIRCOM_SQLITE_WAL_UNAVAILABLE", exc.__class__.__name__)
        LOGGER.warning(
            "SQLite WAL unavailable; default journal mode retained: %s",
            exc.__class__.__name__,
        )
    return connection


def migrate_database(path: Path, *, busy_timeout_ms: int = 5000) -> None:
    connection = connect_sqlite(path, busy_timeout_ms=busy_timeout_ms)
    try:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_schema_migrations_table(connection)
        current_version = _current_schema_version(connection)
        if current_version > SCHEMA_VERSION:
            raise SchemaVersionError(
                f"SQLite schema version {current_version} is newer than "
                f"supported version {SCHEMA_VERSION}."
            )
        if current_version < 1:
            _refuse_partial_unversioned_schema(connection)
            _apply_schema_v1(connection)
        if current_version < 2:
            _apply_schema_v2(connection)
        if current_version < 3:
            _apply_schema_v3(connection)
        if current_version < 4:
            _apply_schema_v4(connection)
        _validate_schema(connection)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@dataclass(frozen=True)
class Repositories:
    connection: sqlite3.Connection

    @property
    def lots(self) -> LotsRepository:
        return LotsRepository(self.connection)

    @property
    def steps(self) -> StepsRepository:
        return StepsRepository(self.connection)

    @property
    def jobs(self) -> JobsRepository:
        return JobsRepository(self.connection)

    @property
    def artifacts(self) -> ArtifactsRepository:
        return ArtifactsRepository(self.connection)

    @property
    def events(self) -> EventsRepository:
        return EventsRepository(self.connection)

    @property
    def problems(self) -> ProblemsRepository:
        return ProblemsRepository(self.connection)


class LotsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        title: str | None = None,
        status: str = "brouillon",
        lot_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("lot status", status, LOT_STATUSES)
        now = _now()
        row_id = lot_id or _new_id("lot")
        self.connection.execute(
            """
            INSERT INTO lots (id, created_at, updated_at, status, title, idempotency_key)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row_id, now, now, status, title, idempotency_key),
        )
        return self.get_required(row_id)

    def get(self, lot_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM lots WHERE id = ?", (lot_id,))

    def get_required(self, lot_id: str) -> dict[str, Any]:
        row = self.get(lot_id)
        if row is None:
            raise KeyError(lot_id)
        return row

    def get_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM lots WHERE idempotency_key = ?",
            (idempotency_key,),
        )

    def list(
        self,
        *,
        include_deleted: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where = "" if include_deleted else "WHERE status NOT IN ('supprime', 'purge')"
        rows = self.connection.execute(
            f"""
            SELECT * FROM lots
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self, *, include_deleted: bool = False) -> int:
        where = "" if include_deleted else "WHERE status NOT IN ('supprime', 'purge')"
        row = self.connection.execute(f"SELECT COUNT(*) FROM lots {where}").fetchone()
        return int(row[0])

    def update_status(self, lot_id: str, status: str) -> dict[str, Any]:
        _validate_choice("lot status", status, LOT_STATUSES)
        self.connection.execute(
            "UPDATE lots SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), lot_id),
        )
        return self.get_required(lot_id)

    def request_cancel(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        self.connection.execute(
            """
            UPDATE lots
            SET cancel_requested_at = COALESCE(cancel_requested_at, ?), updated_at = ?
            WHERE id = ?
            """,
            (now, now, lot_id),
        )
        return self.get_required(lot_id)

    def mark_deleted(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        self.connection.execute(
            """
            UPDATE lots
            SET
                status = 'supprime',
                delete_requested_at = COALESCE(delete_requested_at, ?),
                deleted_at = COALESCE(deleted_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, now, lot_id),
        )
        return self.get_required(lot_id)

    def refresh_artifact_counters(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS artifacts_count, COALESCE(SUM(size_bytes), 0) AS size_bytes
            FROM artefacts
            WHERE lot_id = ? AND status = 'committed'
            """,
            (lot_id,),
        ).fetchone()
        self.connection.execute(
            """
            UPDATE lots
            SET artifacts_count = ?, bytes_artifacts = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                int(row["artifacts_count"]),
                int(row["size_bytes"]),
                now,
                lot_id,
            ),
        )
        return self.get_required(lot_id)

    def refresh_problem_counters(self, lot_id: str) -> dict[str, Any]:
        now = _now()
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS problems_open_count
            FROM problemes
            WHERE lot_id = ? AND status = 'open'
            """,
            (lot_id,),
        ).fetchone()
        self.connection.execute(
            """
            UPDATE lots
            SET problems_open_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (int(row["problems_open_count"]), now, lot_id),
        )
        return self.get_required(lot_id)


class StepsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        status: str = "non_demarre",
        step_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("step status", status, STEP_STATUSES)
        now = _now()
        row_id = step_id or _new_id("step")
        self.connection.execute(
            """
            INSERT INTO etapes (id, created_at, updated_at, lot_id, step_key, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row_id, now, now, lot_id, step_key, status),
        )
        return self.get_required(row_id)

    def get(self, step_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM etapes WHERE id = ?", (step_id,))

    def get_required(self, step_id: str) -> dict[str, Any]:
        row = self.get(step_id)
        if row is None:
            raise KeyError(step_id)
        return row

    def list_for_lot(self, lot_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM etapes
            WHERE lot_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (lot_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_by_lot_key(self, lot_id: str, step_key: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM etapes WHERE lot_id = ? AND step_key = ?",
            (lot_id, step_key),
        )

    def update_status(
        self,
        step_id: str,
        status: str,
        *,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("step status", status, STEP_STATUSES)
        step = self.get_required(step_id)
        lot_status = LotsRepository(self.connection).get_required(step["lot_id"])["status"]
        if lot_status in {"supprime", "purge"} or (
            lot_status == "annule" and status != "annule"
        ):
            raise ValueError("Cannot update a step for a canceled or deleted lot.")
        if status == "termine":
            open_alerts = self.connection.execute(
                """
                SELECT COUNT(*) FROM problemes
                WHERE lot_id = ?
                  AND step_key = ?
                  AND severity = 'alerte'
                  AND status = 'open'
                """,
                (step["lot_id"], step["step_key"]),
            ).fetchone()[0]
            if int(open_alerts):
                raise ValueError(
                    "A step with an open warning must be marked termine_avec_alertes."
                )
        now = _now()
        is_started = 1 if status == "en_cours" else 0
        is_finished = 1 if status in {
            "termine",
            "termine_avec_alertes",
            "echoue",
            "ignore",
            "annule",
        } else 0
        self.connection.execute(
            """
            UPDATE etapes
            SET
                status = ?,
                current_run_id = COALESCE(?, current_run_id),
                updated_at = ?,
                started_at = CASE
                    WHEN ? THEN COALESCE(started_at, ?)
                    ELSE started_at
                END,
                finished_at = CASE
                    WHEN ? THEN COALESCE(finished_at, ?)
                    ELSE finished_at
                END
            WHERE id = ?
            """,
            (status, run_id, now, is_started, now, is_finished, now, step_id),
        )
        return self.get_required(step_id)

    def prepare_run(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        input_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot prepare a run for a canceled or deleted lot.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET
                status = 'pret',
                current_run_id = ?,
                input_fingerprint = ?,
                output_fingerprint = NULL,
                progress_current = 0,
                progress_total = 0,
                started_at = NULL,
                finished_at = NULL,
                invalidated_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (run_id, input_fingerprint, now, step["id"]),
        )
        return self.get_required(step["id"])

    def mark_invalidated(
        self,
        *,
        lot_id: str,
        step_key: str,
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot invalidate a step for a canceled or deleted lot.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET
                status = 'invalide',
                current_run_id = NULL,
                input_fingerprint = NULL,
                output_fingerprint = NULL,
                progress_current = 0,
                progress_total = 0,
                started_at = NULL,
                finished_at = NULL,
                invalidated_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, step["id"]),
        )
        return self.get_required(step["id"])

    def set_output_fingerprint(
        self,
        *,
        lot_id: str,
        step_key: str,
        output_fingerprint: str,
        input_fingerprint: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot update a fingerprint for a canceled or deleted lot.")
        current_run_id = step["current_run_id"]
        if run_id is not None and current_run_id is not None and current_run_id != run_id:
            raise ValueError("Fingerprint run_id does not match the current step run_id.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET
                current_run_id = COALESCE(?, current_run_id),
                input_fingerprint = COALESCE(?, input_fingerprint),
                output_fingerprint = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (run_id, input_fingerprint, output_fingerprint, now, step["id"]),
        )
        return self.get_required(step["id"])

    def set_summary(
        self,
        *,
        lot_id: str,
        step_key: str,
        summary: Mapping[str, Any],
    ) -> dict[str, Any]:
        step = self.get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        lot_status = LotsRepository(self.connection).get_required(lot_id)["status"]
        if lot_status in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot update a step summary for a canceled or deleted lot.")

        now = _now()
        self.connection.execute(
            """
            UPDATE etapes
            SET summary_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (_json(summary), now, step["id"]),
        )
        return self.get_required(step["id"])


class JobsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        idempotency_key: str,
        status: str = "queued",
        job_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("job status", status, JOB_STATUSES)
        lot = LotsRepository(self.connection).get_required(lot_id)
        if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot create a job for a canceled or deleted lot.")
        now = _now()
        row_id = job_id or _new_id("job")
        self.connection.execute(
            """
            INSERT INTO jobs (
                id, created_at, updated_at, lot_id, step_key, status, run_id,
                idempotency_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, now, now, lot_id, step_key, status, run_id, idempotency_key),
        )
        return self.get_required(row_id)

    def create_owned_running(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        idempotency_key: str,
        lease_owner: str,
        lease_seconds: int,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than 0.")
        job = self.create(
            lot_id=lot_id,
            step_key=step_key,
            run_id=run_id,
            idempotency_key=idempotency_key,
            status="running",
            job_id=job_id,
        )
        now = _now()
        self.connection.execute(
            """
            UPDATE jobs
            SET
                lease_owner = ?,
                lease_version = 1,
                lease_until = ?,
                heartbeat_at = ?,
                started_at = COALESCE(started_at, ?),
                updated_at = ?
            WHERE id = ?
            """,
            (
                lease_owner,
                _now_plus(seconds=lease_seconds),
                now,
                now,
                now,
                job["id"],
            ),
        )
        return self.get_required(job["id"])

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM jobs WHERE id = ?", (job_id,))

    def get_required(self, job_id: str) -> dict[str, Any]:
        row = self.get(job_id)
        if row is None:
            raise KeyError(job_id)
        return row

    def get_by_idempotency_key(
        self,
        *,
        lot_id: str,
        step_key: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            """
            SELECT * FROM jobs
            WHERE lot_id = ? AND step_key = ? AND idempotency_key = ?
            """,
            (lot_id, step_key, idempotency_key),
        )

    def get_active_for_step(self, *, lot_id: str, step_key: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            f"""
            SELECT * FROM jobs
            WHERE jobs.lot_id = ?
              AND step_key = ?
              AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (lot_id, step_key),
        )

    def get_committable_by_run(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        lease_version: int,
        expected_input_fingerprint: str | None = None,
    ) -> dict[str, Any] | None:
        params: list[Any] = [lot_id, step_key, run_id, _now()]
        params.append(lease_version)
        params.extend([expected_input_fingerprint, expected_input_fingerprint])
        return _fetch_one(
            self.connection,
            f"""
            SELECT jobs.* FROM jobs
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            WHERE jobs.lot_id = ?
              AND jobs.step_key = ?
              AND jobs.run_id = ?
              AND jobs.status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND jobs.lease_until IS NOT NULL
              AND jobs.lease_until > ?
              AND etapes.current_run_id = jobs.run_id
              AND jobs.lease_version = ?
              AND (? IS NULL OR etapes.input_fingerprint = ?)
            ORDER BY jobs.created_at DESC
            LIMIT 1
            """,
            tuple(params),
        )

    def get_owned_committable(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        expected_input_fingerprint: str | None = None,
    ) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            f"""
            SELECT jobs.* FROM jobs
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            JOIN lots
              ON lots.id = jobs.lot_id
            WHERE jobs.id = ?
              AND jobs.lease_owner = ?
              AND jobs.run_id = ?
              AND jobs.lease_version = ?
              AND jobs.status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND jobs.lease_until IS NOT NULL
              AND jobs.lease_until > ?
              AND etapes.current_run_id = jobs.run_id
              AND (? IS NULL OR etapes.input_fingerprint = ?)
              AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
            LIMIT 1
            """,
            (
                job_id,
                worker_id,
                run_id,
                lease_version,
                _now(),
                expected_input_fingerprint,
                expected_input_fingerprint,
            ),
        )

    def update_status(self, job_id: str, status: str) -> dict[str, Any]:
        _validate_choice("job status", status, JOB_STATUSES)
        now = _now()
        is_started = 1 if status in {"leased", "running"} else 0
        is_finished = 1 if status in {"succeeded", "failed", "canceled"} else 0
        self.connection.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                updated_at = ?,
                started_at = CASE
                    WHEN ? THEN COALESCE(started_at, ?)
                    ELSE started_at
                END,
                finished_at = CASE
                    WHEN ? THEN COALESCE(finished_at, ?)
                    ELSE finished_at
                END
            WHERE id = ?
            """,
            (status, now, is_started, now, is_finished, now, job_id),
        )
        return self.get_required(job_id)

    def acquire_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
        max_active_jobs: int = 1,
        step_keys: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than 0.")
        if max_active_jobs <= 0:
            raise ValueError("max_active_jobs must be greater than 0.")
        if step_keys is not None and not step_keys:
            return None

        self.expire_stale_leases()
        if self.count_processing() >= max_active_jobs:
            return None
        now = _now()
        lease_until = _now_plus(seconds=lease_seconds)
        step_filter = ""
        params: list[Any] = [now]
        if step_keys is not None:
            step_filter = f"AND jobs.step_key IN ({_placeholders(len(step_keys))})"
            params.extend(step_keys)
        row = self.connection.execute(
            f"""
            SELECT jobs.id
            FROM jobs
            JOIN lots
              ON lots.id = jobs.lot_id
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            WHERE (
                  jobs.status = 'queued'
                  OR (
                      jobs.status = 'expired'
                      AND jobs.lease_until IS NOT NULL
                      AND jobs.lease_until <= ?
                  )
              )
              AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
              AND etapes.status NOT IN ('annule', 'termine', 'termine_avec_alertes', 'bloque')
              AND etapes.current_run_id = jobs.run_id
              {step_filter}
            ORDER BY jobs.created_at ASC, jobs.id ASC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
        if row is None:
            return None

        cursor = self.connection.execute(
            """
            UPDATE jobs
            SET
                status = 'leased',
                lease_owner = ?,
                lease_version = lease_version + 1,
                lease_until = ?,
                heartbeat_at = ?,
                started_at = COALESCE(started_at, ?),
                attempt = attempt + 1,
                updated_at = ?
            WHERE id = ?
              AND status IN ('queued', 'expired')
            """,
            (worker_id, lease_until, now, now, now, row["id"]),
        )
        if cursor.rowcount != 1:
            return None
        return self._get_with_step_input(row["id"])

    def count_processing(self) -> int:
        row = self.connection.execute(
            f"""
            SELECT COUNT(*) FROM jobs
            JOIN lots
              ON lots.id = jobs.lot_id
            WHERE jobs.status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
            """
        ).fetchone()
        return int(row[0])

    def mark_running(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
    ) -> dict[str, Any] | None:
        now = _now()
        cursor = self.connection.execute(
            """
            UPDATE jobs
            SET
                status = 'running',
                started_at = COALESCE(started_at, ?),
                heartbeat_at = ?,
                updated_at = ?
            WHERE id = ?
              AND lease_owner = ?
              AND run_id = ?
              AND lease_version = ?
              AND status = 'leased'
              AND lease_until IS NOT NULL
              AND lease_until > ?
              AND EXISTS (
                  SELECT 1 FROM etapes
                  WHERE etapes.lot_id = jobs.lot_id
                    AND etapes.step_key = jobs.step_key
                    AND etapes.current_run_id = jobs.run_id
              )
            """,
            (now, now, now, job_id, worker_id, run_id, lease_version, now),
        )
        if cursor.rowcount != 1:
            return None
        return self.get_required(job_id)

    def heartbeat(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        lease_seconds: int,
    ) -> dict[str, Any] | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than 0.")
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET lease_until = ?, heartbeat_at = ?, updated_at = ?
            WHERE id = ?
              AND lease_owner = ?
              AND run_id = ?
              AND lease_version = ?
              AND status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND lease_until IS NOT NULL
              AND lease_until > ?
              AND EXISTS (
                  SELECT 1
                  FROM etapes
                  JOIN lots
                    ON lots.id = etapes.lot_id
                  WHERE etapes.lot_id = jobs.lot_id
                    AND etapes.step_key = jobs.step_key
                    AND etapes.current_run_id = jobs.run_id
                    AND lots.status NOT IN ({_check_in(LOT_WRITE_BLOCKED_STATUSES)})
              )
            """,
            (
                _now_plus(seconds=lease_seconds),
                now,
                now,
                job_id,
                worker_id,
                run_id,
                lease_version,
                now,
            ),
        )
        if cursor.rowcount != 1:
            return None
        return self.get_required(job_id)

    def update_progress(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        current: int,
        total: int,
        lease_seconds: int,
    ) -> dict[str, Any] | None:
        if current < 0 or total < 0 or current > total:
            raise ValueError("progress must satisfy 0 <= current <= total.")
        job = self.heartbeat(
            job_id=job_id,
            worker_id=worker_id,
            run_id=run_id,
            lease_version=lease_version,
            lease_seconds=lease_seconds,
        )
        if job is None:
            return None
        self.connection.execute(
            """
            UPDATE etapes
            SET progress_current = ?, progress_total = ?, updated_at = ?
            WHERE lot_id = ? AND step_key = ?
            """,
            (current, total, _now(), job["lot_id"], job["step_key"]),
        )
        return self.get_required(job_id)

    def finish_owned(
        self,
        *,
        job_id: str,
        worker_id: str,
        run_id: str,
        lease_version: int,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        expected_input_fingerprint: str | None = None,
    ) -> dict[str, Any] | None:
        if status not in {"succeeded", "failed", "canceled"}:
            raise ValueError("Owned job can only finish as succeeded, failed or canceled.")
        if self.get_owned_committable(
            job_id=job_id,
            worker_id=worker_id,
            run_id=run_id,
            lease_version=lease_version,
            expected_input_fingerprint=expected_input_fingerprint,
        ) is None:
            return None
        now = _now()
        self.connection.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                finished_at = COALESCE(finished_at, ?),
                heartbeat_at = ?,
                error_code = ?,
                error_message = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (status, now, now, error_code, error_message, now, job_id),
        )
        return self.get_required(job_id)

    def _get_with_step_input(self, job_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT jobs.*, etapes.input_fingerprint AS step_input_fingerprint
            FROM jobs
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            WHERE jobs.id = ?
            """,
            (job_id,),
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return dict(row)

    def expire_stale_leases(self) -> int:
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET status = 'expired', updated_at = ?
            WHERE status IN ({_check_in(COMMITTABLE_JOB_STATUSES)})
              AND lease_until IS NOT NULL
              AND lease_until <= ?
            """,
            (_now(), _now()),
        )
        return cursor.rowcount

    def count_active_for_lot(self, lot_id: str) -> int:
        row = self.connection.execute(
            f"""
            SELECT COUNT(*) FROM jobs
            WHERE lot_id = ? AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            """,
            (lot_id,),
        ).fetchone()
        return int(row[0])

    def request_cancel_for_lot(self, lot_id: str) -> int:
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET cancel_requested_at = COALESCE(cancel_requested_at, ?), updated_at = ?
            WHERE lot_id = ? AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            """,
            (now, now, lot_id),
        )
        return cursor.rowcount

    def cancel_active_for_step(self, lot_id: str, step_key: str) -> int:
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE jobs
            SET
                status = 'canceled',
                cancel_requested_at = COALESCE(cancel_requested_at, ?),
                finished_at = COALESCE(finished_at, ?),
                updated_at = ?
            WHERE lot_id = ?
              AND step_key = ?
              AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            """,
            (now, now, now, lot_id, step_key),
        )
        return cursor.rowcount


class ArtifactsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        kind: str,
        role: str,
        relative_path: str,
        sha256: str,
        size_bytes: int,
        mime_type: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        status: str = "pending",
        artifact_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("artifact status", status, ARTIFACT_STATUSES)
        now = _now()
        row_id = artifact_id or _new_id("artifact")
        self.connection.execute(
            """
            INSERT INTO artefacts (
                id, created_at, updated_at, lot_id, step_key, run_id, status,
                kind, role, relative_path, sha256, size_bytes, schema_version,
                mime_type, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                lot_id,
                step_key,
                run_id,
                status,
                kind,
                role,
                relative_path,
                sha256,
                size_bytes,
                1,
                mime_type,
                _json(metadata or {}),
            ),
        )
        return self.get_required(row_id)

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM artefacts WHERE id = ?", (artifact_id,))

    def get_required(self, artifact_id: str) -> dict[str, Any]:
        row = self.get(artifact_id)
        if row is None:
            raise KeyError(artifact_id)
        return row

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM artefacts ORDER BY created_at, id").fetchall()
        return [dict(row) for row in rows]

    def get_for_lot(self, lot_id: str, artifact_id: str) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            "SELECT * FROM artefacts WHERE lot_id = ? AND id = ?",
            (lot_id, artifact_id),
        )

    def get_for_step_run_role(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str,
        role: str,
    ) -> dict[str, Any] | None:
        return _fetch_one(
            self.connection,
            """
            SELECT * FROM artefacts
            WHERE lot_id = ?
              AND step_key = ?
              AND run_id = ?
              AND role = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (lot_id, step_key, run_id, role),
        )

    def update_status(self, artifact_id: str, status: str) -> dict[str, Any]:
        _validate_choice("artifact status", status, ARTIFACT_STATUSES)
        now = _now()
        timestamp_column = {
            "committed": "committed_at",
            "obsolete": "obsoleted_at",
            "deleted": "deleted_at",
            "quarantined": "quarantined_at",
        }.get(status)
        if timestamp_column is None:
            self.connection.execute(
                "UPDATE artefacts SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, artifact_id),
            )
        else:
            self.connection.execute(
                f"""
                UPDATE artefacts
                SET status = ?, {timestamp_column} = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, now, now, artifact_id),
            )
        return self.get_required(artifact_id)

    def mark_obsolete_for_steps(self, *, lot_id: str, step_keys: tuple[str, ...]) -> int:
        if not step_keys:
            return 0
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE artefacts
            SET
                status = 'obsolete',
                obsoleted_at = COALESCE(obsoleted_at, ?),
                updated_at = ?
            WHERE lot_id = ?
              AND step_key IN ({_placeholders(len(step_keys))})
              AND status IN ('pending', 'committed')
            """,
            (now, now, lot_id, *step_keys),
        )
        LotsRepository(self.connection).refresh_artifact_counters(lot_id)
        return cursor.rowcount


class EventsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        step_key: str | None = None,
        run_id: str | None = None,
        level: str = "info",
        event_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("event level", level, EVENT_LEVELS)
        now = _now()
        row_id = event_id or _new_id("event")
        payload_json = _json_technical_payload(payload or {})
        self.connection.execute(
            """
            INSERT INTO evenements (
                id, created_at, updated_at, lot_id, step_key, run_id, level,
                event_type, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                lot_id,
                step_key,
                run_id,
                level,
                event_type,
                payload_json,
            ),
        )
        return self.get_required(row_id)

    def get(self, event_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM evenements WHERE id = ?", (event_id,))

    def get_required(self, event_id: str) -> dict[str, Any]:
        row = self.get(event_id)
        if row is None:
            raise KeyError(event_id)
        return row

    def update_payload(
        self,
        event_id: str,
        payload: Mapping[str, Any],
        *,
        level: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        payload_json = _json_technical_payload(payload)
        if level is None:
            self.connection.execute(
                "UPDATE evenements SET payload_json = ?, updated_at = ? WHERE id = ?",
                (payload_json, now, event_id),
            )
        else:
            _validate_choice("event level", level, EVENT_LEVELS)
            self.connection.execute(
                """
                UPDATE evenements
                SET payload_json = ?, level = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload_json, level, now, event_id),
            )
        return self.get_required(event_id)

    def list_for_lot(self, lot_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM evenements
            WHERE lot_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (lot_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


class ProblemsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        lot_id: str,
        step_key: str,
        severity: str,
        code: str,
        title: str,
        message: str,
        cause: str | None = None,
        action: str | None = None,
        run_id: str | None = None,
        location: Mapping[str, Any] | None = None,
        technical: Mapping[str, Any] | None = None,
        problem_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("problem severity", severity, PROBLEM_SEVERITIES)
        self._validate_write_allowed(lot_id=lot_id, step_key=step_key, run_id=run_id)
        now = _now()
        row_id = problem_id or _new_id("problem")
        cause_text = cause if cause is not None else message
        action_text = action if action is not None else "Corriger la cause puis relancer l'etape concernee."
        self.connection.execute(
            """
            INSERT INTO problemes (
                id, created_at, updated_at, lot_id, step_key, run_id, severity,
                code, title, cause, message, action, location_json,
                technical_json, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                lot_id,
                step_key,
                run_id,
                severity,
                code,
                title,
                cause_text,
                message,
                action_text,
                _json(location or {}),
                _json(technical or {}),
                "open",
            ),
        )
        LotsRepository(self.connection).refresh_problem_counters(lot_id)
        return self.get_required(row_id)

    def get(self, problem_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM problemes WHERE id = ?", (problem_id,))

    def get_required(self, problem_id: str) -> dict[str, Any]:
        row = self.get(problem_id)
        if row is None:
            raise KeyError(problem_id)
        return row

    def update_status(self, problem_id: str, status: str) -> dict[str, Any]:
        _validate_choice("problem status", status, PROBLEM_STATUSES)
        problem = self.get_required(problem_id)
        now = _now()
        resolved_at = now if status == "resolved" else None
        self.connection.execute(
            """
            UPDATE problemes
            SET status = ?, resolved_at = COALESCE(?, resolved_at), updated_at = ?
            WHERE id = ?
            """,
            (status, resolved_at, now, problem_id),
        )
        LotsRepository(self.connection).refresh_problem_counters(problem["lot_id"])
        return self.get_required(problem_id)

    def _validate_write_allowed(
        self,
        *,
        lot_id: str,
        step_key: str,
        run_id: str | None,
    ) -> None:
        lot = LotsRepository(self.connection).get_required(lot_id)
        if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
            raise ValueError("Cannot record a problem for a canceled or deleted lot.")
        step = StepsRepository(self.connection).get_by_lot_key(lot_id, step_key)
        if step is None:
            raise KeyError(f"{lot_id}:{step_key}")
        current_run_id = step["current_run_id"]
        if run_id is not None and current_run_id is not None and current_run_id != run_id:
            raise ValueError("Problem run_id does not match the current step run_id.")

    def list_for_lot(
        self,
        lot_id: str,
        *,
        include_resolved: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        status_filter = "" if include_resolved else "AND status = 'open'"
        rows = self.connection.execute(
            f"""
            SELECT * FROM problemes
            WHERE lot_id = ?
              {status_filter}
            ORDER BY
                CASE severity
                    WHEN 'bloquant' THEN 0
                    WHEN 'alerte' THEN 1
                    ELSE 2
                END,
                created_at DESC,
                id DESC
            LIMIT ?
            """,
            (lot_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def count_open_for_step_by_severity(
        self,
        *,
        lot_id: str,
        step_key: str,
        severity: str,
    ) -> int:
        _validate_choice("problem severity", severity, PROBLEM_SEVERITIES)
        row = self.connection.execute(
            """
            SELECT COUNT(*) FROM problemes
            WHERE lot_id = ?
              AND step_key = ?
              AND severity = ?
              AND status = 'open'
            """,
            (lot_id, step_key, severity),
        ).fetchone()
        return int(row[0])

    def count_open_by_severity(self, *, lot_id: str, severity: str) -> int:
        _validate_choice("problem severity", severity, PROBLEM_SEVERITIES)
        row = self.connection.execute(
            """
            SELECT COUNT(*) FROM problemes
            WHERE lot_id = ?
              AND severity = ?
              AND status = 'open'
            """,
            (lot_id, severity),
        ).fetchone()
        return int(row[0])

    def mark_open_obsolete_for_steps(self, *, lot_id: str, step_keys: tuple[str, ...]) -> int:
        if not step_keys:
            return 0
        now = _now()
        cursor = self.connection.execute(
            f"""
            UPDATE problemes
            SET status = 'obsolete', updated_at = ?
            WHERE lot_id = ?
              AND step_key IN ({_placeholders(len(step_keys))})
              AND status = 'open'
            """,
            (now, lot_id, *step_keys),
        )
        LotsRepository(self.connection).refresh_problem_counters(lot_id)
        return cursor.rowcount


def _ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _current_schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
    return int(row["version"] or 0)


def _apply_schema_v1(connection: sqlite3.Connection) -> None:
    for statement in _SCHEMA_V1:
        connection.execute(statement)
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
        (1, "initial_schema", _now()),
    )


def _apply_schema_v2(connection: sqlite3.Connection) -> None:
    lot_columns = _table_columns(connection, "lots")
    if "idempotency_key" not in lot_columns:
        connection.execute("ALTER TABLE lots ADD COLUMN idempotency_key TEXT")
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_lots_idempotency_key
        ON lots(idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
        (2, "lot_idempotency_key", _now()),
    )


def _apply_schema_v3(connection: sqlite3.Connection) -> None:
    problem_columns = _table_columns(connection, "problemes")
    if "cause" not in problem_columns:
        connection.execute("ALTER TABLE problemes ADD COLUMN cause TEXT NOT NULL DEFAULT ''")
        connection.execute("UPDATE problemes SET cause = message WHERE cause = ''")
    if "action" not in problem_columns:
        connection.execute(
            "ALTER TABLE problemes ADD COLUMN action TEXT NOT NULL DEFAULT "
            "'Corriger la cause puis relancer l''etape concernee.'"
        )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
        (3, "problem_cause_action", _now()),
    )


def _apply_schema_v4(connection: sqlite3.Connection) -> None:
    _expire_duplicate_active_jobs(connection)
    connection.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_active_lot_step
        ON jobs(lot_id, step_key)
        WHERE status IN ({_check_in(ACTIVE_JOB_STATUSES)})
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
        (4, "active_job_per_step", _now()),
    )


def _expire_duplicate_active_jobs(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        f"""
        SELECT lot_id, step_key, COUNT(*) AS active_count
        FROM jobs
        WHERE status IN ({_check_in(ACTIVE_JOB_STATUSES)})
        GROUP BY lot_id, step_key
        HAVING active_count > 1
        """
    ).fetchall()
    now = _now()
    for row in rows:
        keep = connection.execute(
            f"""
            SELECT jobs.id FROM jobs
            JOIN etapes
              ON etapes.lot_id = jobs.lot_id
             AND etapes.step_key = jobs.step_key
            WHERE jobs.lot_id = ?
              AND jobs.step_key = ?
              AND jobs.status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            ORDER BY
              CASE WHEN jobs.run_id = etapes.current_run_id THEN 0 ELSE 1 END,
              jobs.created_at DESC,
              jobs.id DESC
            LIMIT 1
            """,
            (row["lot_id"], row["step_key"]),
        ).fetchone()
        if keep is None:
            continue
        connection.execute(
            f"""
            UPDATE jobs
            SET status = 'expired', updated_at = ?
            WHERE lot_id = ?
              AND step_key = ?
              AND id != ?
              AND status IN ({_check_in(ACTIVE_JOB_STATUSES)})
            """,
            (now, row["lot_id"], row["step_key"], keep["id"]),
        )


def _refuse_partial_unversioned_schema(connection: sqlite3.Connection) -> None:
    managed_tables = _existing_managed_tables(connection)
    if managed_tables:
        tables = ", ".join(sorted(managed_tables))
        raise SchemaVersionError(
            f"Unversioned SQLite database already contains managed tables: {tables}."
        )


def _validate_schema(connection: sqlite3.Connection) -> None:
    existing_tables = _existing_tables(connection)
    missing_tables = set(MANAGED_TABLES) - existing_tables
    if missing_tables:
        tables = ", ".join(sorted(missing_tables))
        raise SchemaVersionError(f"SQLite schema is missing managed tables: {tables}.")

    for table, expected_columns in EXPECTED_TABLE_COLUMNS.items():
        actual_columns = _table_columns(connection, table)
        missing_columns = expected_columns - actual_columns
        if missing_columns:
            columns = ", ".join(sorted(missing_columns))
            raise SchemaVersionError(f"SQLite table {table} is missing columns: {columns}.")

    missing_indexes = EXPECTED_INDEXES - _index_names(connection)
    if missing_indexes:
        indexes = ", ".join(sorted(missing_indexes))
        raise SchemaVersionError(f"SQLite schema is missing indexes: {indexes}.")

    for table, expected_groups in EXPECTED_FOREIGN_KEY_GROUPS.items():
        missing_groups = expected_groups - _foreign_key_column_groups(connection, table)
        if missing_groups:
            groups = ", ".join(" + ".join(group) for group in sorted(missing_groups))
            raise SchemaVersionError(f"SQLite table {table} is missing foreign keys: {groups}.")

    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise SchemaVersionError("SQLite schema has foreign key integrity errors.")


def _existing_managed_tables(connection: sqlite3.Connection) -> set[str]:
    return _existing_tables(connection) & set(MANAGED_TABLES)


def _existing_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row["name"] for row in rows}


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _index_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'"
    ).fetchall()
    return {row["name"] for row in rows}


def _foreign_key_column_groups(connection: sqlite3.Connection, table: str) -> set[tuple[str, ...]]:
    grouped: dict[int, list[tuple[int, str]]] = {}
    for row in connection.execute(f"PRAGMA foreign_key_list({table})"):
        grouped.setdefault(row["id"], []).append((row["seq"], row["from"]))
    return {
        tuple(column for _sequence, column in sorted(columns))
        for columns in grouped.values()
    }


def _fetch_one(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
) -> dict[str, Any] | None:
    row = connection.execute(sql, params).fetchone()
    if row is None:
        return None
    return dict(row)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _now_plus(*, seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_technical_payload(payload: Mapping[str, Any]) -> str:
    unknown_keys = set(payload) - TECHNICAL_EVENT_PAYLOAD_KEYS
    if unknown_keys:
        keys = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Event payload contains non-technical keys: {keys}.")

    for key, value in payload.items():
        if not isinstance(value, str | int | float | bool | type(None)):
            raise ValueError(f"Event payload value for {key!r} must be scalar.")
        if isinstance(value, str) and ("/" in value or "\\" in value):
            raise ValueError(f"Event payload value for {key!r} must not contain a path.")

    return _json(payload)


def _check_in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _placeholders(count: int) -> str:
    if count <= 0:
        raise ValueError("count must be greater than 0.")
    return ", ".join("?" for _index in range(count))


def _validate_choice(label: str, value: str, allowed_values: tuple[str, ...]) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValueError(f"Invalid {label}: {value!r}. Allowed values: {allowed}.")


_SCHEMA_V1 = [
    f"""
    CREATE TABLE IF NOT EXISTS lots (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ({_check_in(LOT_STATUSES)})),
        title TEXT,
        active_run_id TEXT,
        cancel_requested_at TEXT,
        delete_requested_at TEXT,
        deleted_at TEXT,
        purge_requested_at TEXT,
        bytes_uploaded INTEGER NOT NULL DEFAULT 0 CHECK (bytes_uploaded >= 0),
        bytes_artifacts INTEGER NOT NULL DEFAULT 0 CHECK (bytes_artifacts >= 0),
        artifacts_count INTEGER NOT NULL DEFAULT 0 CHECK (artifacts_count >= 0),
        problems_open_count INTEGER NOT NULL DEFAULT 0 CHECK (problems_open_count >= 0)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS etapes (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        lot_id TEXT NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        step_key TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ({_check_in(STEP_STATUSES)})),
        current_run_id TEXT,
        input_fingerprint TEXT,
        output_fingerprint TEXT,
        progress_current INTEGER NOT NULL DEFAULT 0 CHECK (progress_current >= 0),
        progress_total INTEGER NOT NULL DEFAULT 0 CHECK (progress_total >= 0),
        started_at TEXT,
        finished_at TEXT,
        invalidated_at TEXT,
        summary_json TEXT NOT NULL DEFAULT '{{}}',
        UNIQUE (lot_id, step_key)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        lot_id TEXT NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        step_key TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ({_check_in(JOB_STATUSES)})),
        run_id TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        lease_owner TEXT,
        lease_version INTEGER NOT NULL DEFAULT 0 CHECK (lease_version >= 0),
        lease_until TEXT,
        heartbeat_at TEXT,
        attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
        cancel_requested_at TEXT,
        started_at TEXT,
        finished_at TEXT,
        error_code TEXT,
        error_message TEXT,
        FOREIGN KEY (lot_id, step_key) REFERENCES etapes(lot_id, step_key) ON DELETE CASCADE,
        UNIQUE (lot_id, step_key, idempotency_key)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS artefacts (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        lot_id TEXT NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        step_key TEXT NOT NULL,
        run_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ({_check_in(ARTIFACT_STATUSES)})),
        kind TEXT NOT NULL,
        role TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
        schema_version INTEGER NOT NULL,
        mime_type TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{{}}',
        committed_at TEXT,
        obsoleted_at TEXT,
        deleted_at TEXT,
        quarantined_at TEXT,
        FOREIGN KEY (lot_id, step_key) REFERENCES etapes(lot_id, step_key) ON DELETE CASCADE
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS evenements (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        lot_id TEXT NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        step_key TEXT,
        run_id TEXT,
        level TEXT NOT NULL DEFAULT 'info' CHECK (level IN ({_check_in(EVENT_LEVELS)})),
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{{}}',
        FOREIGN KEY (lot_id, step_key) REFERENCES etapes(lot_id, step_key) ON DELETE CASCADE
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS problemes (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        lot_id TEXT NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        step_key TEXT NOT NULL,
        run_id TEXT,
        severity TEXT NOT NULL CHECK (severity IN ({_check_in(PROBLEM_SEVERITIES)})),
        code TEXT NOT NULL,
        title TEXT NOT NULL,
        cause TEXT NOT NULL DEFAULT '',
        message TEXT NOT NULL,
        action TEXT NOT NULL DEFAULT '',
        location_json TEXT NOT NULL DEFAULT '{{}}',
        technical_json TEXT NOT NULL DEFAULT '{{}}',
        status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ({_check_in(PROBLEM_STATUSES)})),
        resolved_at TEXT,
        FOREIGN KEY (lot_id, step_key) REFERENCES etapes(lot_id, step_key) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_etapes_lot_status ON etapes(lot_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_status_lease ON jobs(status, lease_until)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_lot_step ON jobs(lot_id, step_key)",
    "CREATE INDEX IF NOT EXISTS idx_artefacts_lot_status ON artefacts(lot_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_artefacts_lot_step_run ON artefacts(lot_id, step_key, run_id)",
    "CREATE INDEX IF NOT EXISTS idx_evenements_lot_created ON evenements(lot_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_problemes_lot_status ON problemes(lot_id, status)",
]
