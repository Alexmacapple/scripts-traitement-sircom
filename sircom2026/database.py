from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sircom2026._database_shared import (
    ACTIVE_JOB_STATUSES,
    ARTIFACT_STATUSES,
    COMMITTABLE_JOB_STATUSES,
    EVENT_LEVELS,
    EXPECTED_FOREIGN_KEY_GROUPS,
    EXPECTED_INDEXES,
    EXPECTED_TABLE_COLUMNS,
    JOB_STATUSES,
    LOT_STATUSES,
    LOT_WRITE_BLOCKED_STATUSES,
    MANAGED_TABLES,
    PROBLEM_SEVERITIES,
    PROBLEM_STATUSES,
    SCHEMA_VERSION,
    STEP_STATUSES,
    TECHNICAL_EVENT_PAYLOAD_KEYS,
    _check_in,
    _now,
)
from sircom2026.database_repositories import (
    ArtifactsRepository,
    EventsRepository,
    JobsRepository,
    LotsRepository,
    ProblemsRepository,
    PurgeTracesRepository,
    Repositories,
    StepsRepository,
)

LOGGER = logging.getLogger(__name__)

__all__ = [
    "ACTIVE_JOB_STATUSES",
    "ARTIFACT_STATUSES",
    "ArtifactsRepository",
    "COMMITTABLE_JOB_STATUSES",
    "Database",
    "EVENT_LEVELS",
    "EventsRepository",
    "JOB_STATUSES",
    "JobsRepository",
    "LOT_STATUSES",
    "LOT_WRITE_BLOCKED_STATUSES",
    "LotsRepository",
    "PROBLEM_SEVERITIES",
    "PROBLEM_STATUSES",
    "ProblemsRepository",
    "PurgeTracesRepository",
    "Repositories",
    "SCHEMA_VERSION",
    "STEP_STATUSES",
    "SchemaVersionError",
    "StepsRepository",
    "TECHNICAL_EVENT_PAYLOAD_KEYS",
    "connect_sqlite",
    "migrate_database",
]


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
            if connection.in_transaction:
                connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
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
        if current_version < 5:
            _apply_schema_v5(connection)
        _validate_schema(connection)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


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
    row = connection.execute(
        "SELECT MAX(version) AS version FROM schema_migrations"
    ).fetchone()
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
        connection.execute(
            "ALTER TABLE problemes ADD COLUMN cause TEXT NOT NULL DEFAULT ''"
        )
        connection.execute("UPDATE problemes SET cause = message WHERE cause = ''")
    if "action" not in problem_columns:
        connection.execute(
            "ALTER TABLE problemes ADD COLUMN action TEXT NOT NULL DEFAULT "
            "'Corriger la cause puis relancer l''étape concernée.'"
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


def _apply_schema_v5(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purge_traces (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            lot_id_hash TEXT NOT NULL UNIQUE,
            lot_created_at TEXT,
            lot_deleted_at TEXT,
            purged_at TEXT NOT NULL,
            final_status TEXT NOT NULL,
            trace_json TEXT NOT NULL DEFAULT '{}',
            trace_schema_version INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_purge_traces_purged_at
        ON purge_traces(purged_at)
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
        (5, "purge_traces", _now()),
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
            raise SchemaVersionError(
                f"SQLite table {table} is missing columns: {columns}."
            )

    missing_indexes = EXPECTED_INDEXES - _index_names(connection)
    if missing_indexes:
        indexes = ", ".join(sorted(missing_indexes))
        raise SchemaVersionError(f"SQLite schema is missing indexes: {indexes}.")

    for table, expected_groups in EXPECTED_FOREIGN_KEY_GROUPS.items():
        missing_groups = expected_groups - _foreign_key_column_groups(connection, table)
        if missing_groups:
            groups = ", ".join(" + ".join(group) for group in sorted(missing_groups))
            raise SchemaVersionError(
                f"SQLite table {table} is missing foreign keys: {groups}."
            )

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


def _foreign_key_column_groups(
    connection: sqlite3.Connection, table: str
) -> set[tuple[str, ...]]:
    grouped: dict[int, list[tuple[int, str]]] = {}
    for row in connection.execute(f"PRAGMA foreign_key_list({table})"):
        grouped.setdefault(row["id"], []).append((row["seq"], row["from"]))
    return {
        tuple(column for _sequence, column in sorted(columns))
        for columns in grouped.values()
    }


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
        action TEXT NOT NULL DEFAULT 'Corriger la cause puis relancer l''étape concernée.',
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
