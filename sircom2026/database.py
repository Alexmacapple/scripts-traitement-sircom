from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
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
MANAGED_TABLES = ("lots", "etapes", "jobs", "artefacts", "evenements", "problemes")
EXPECTED_TABLE_COLUMNS = {
    "lots": {
        "id",
        "created_at",
        "updated_at",
        "status",
        "title",
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
        "message",
        "location_json",
        "technical_json",
        "status",
        "resolved_at",
    },
}
EXPECTED_INDEXES = {
    "idx_etapes_lot_status",
    "idx_jobs_status_lease",
    "idx_jobs_lot_step",
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
    "code",
    "count",
    "duration_ms",
    "error_code",
    "free_mb",
    "job_id",
    "level",
    "lot_id",
    "required_mb",
    "run_id",
    "size_bytes",
    "status",
    "step_key",
    "warning_code",
}


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
    ) -> dict[str, Any]:
        _validate_choice("lot status", status, LOT_STATUSES)
        now = _now()
        row_id = lot_id or _new_id("lot")
        self.connection.execute(
            """
            INSERT INTO lots (id, created_at, updated_at, status, title)
            VALUES (?, ?, ?, ?, ?)
            """,
            (row_id, now, now, status, title),
        )
        return self.get_required(row_id)

    def get(self, lot_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM lots WHERE id = ?", (lot_id,))

    def get_required(self, lot_id: str) -> dict[str, Any]:
        row = self.get(lot_id)
        if row is None:
            raise KeyError(lot_id)
        return row

    def update_status(self, lot_id: str, status: str) -> dict[str, Any]:
        _validate_choice("lot status", status, LOT_STATUSES)
        self.connection.execute(
            "UPDATE lots SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), lot_id),
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

    def update_status(
        self,
        step_id: str,
        status: str,
        *,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("step status", status, STEP_STATUSES)
        self.connection.execute(
            """
            UPDATE etapes
            SET status = ?, current_run_id = COALESCE(?, current_run_id), updated_at = ?
            WHERE id = ?
            """,
            (status, run_id, _now(), step_id),
        )
        return self.get_required(step_id)


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

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _fetch_one(self.connection, "SELECT * FROM jobs WHERE id = ?", (job_id,))

    def get_required(self, job_id: str) -> dict[str, Any]:
        row = self.get(job_id)
        if row is None:
            raise KeyError(job_id)
        return row

    def update_status(self, job_id: str, status: str) -> dict[str, Any]:
        _validate_choice("job status", status, JOB_STATUSES)
        self.connection.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), job_id),
        )
        return self.get_required(job_id)


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
                kind, role, relative_path, sha256, size_bytes, schema_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        run_id: str | None = None,
        location: Mapping[str, Any] | None = None,
        technical: Mapping[str, Any] | None = None,
        problem_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_choice("problem severity", severity, PROBLEM_SEVERITIES)
        now = _now()
        row_id = problem_id or _new_id("problem")
        self.connection.execute(
            """
            INSERT INTO problemes (
                id, created_at, updated_at, lot_id, step_key, run_id, severity,
                code, title, message, location_json, technical_json, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                message,
                _json(location or {}),
                _json(technical or {}),
                "open",
            ),
        )
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
        return self.get_required(problem_id)


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
        message TEXT NOT NULL,
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
