from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sircom2026.database import (
    SCHEMA_VERSION,
    Database,
    SchemaVersionError,
    connect_sqlite,
    migrate_database,
)


class FakeConnection:
    row_factory: object | None = None

    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, sql: str, *args: object) -> FakeConnection:
        self.statements.append(sql)
        if sql == "PRAGMA journal_mode = WAL":
            raise sqlite3.OperationalError("wal unavailable at /private/tmp/source.sqlite3")
        return self


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row["name"] for row in rows}


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def index_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'"
    ).fetchall()
    return {row["name"] for row in rows}


def foreign_key_column_groups(connection: sqlite3.Connection, table: str) -> set[tuple[str, ...]]:
    grouped: dict[int, list[tuple[int, str]]] = {}
    for row in connection.execute(f"PRAGMA foreign_key_list({table})"):
        grouped.setdefault(row["id"], []).append((row["seq"], row["from"]))
    return {
        tuple(column for _sequence, column in sorted(columns))
        for columns in grouped.values()
    }


class DatabaseMigrationTest(unittest.TestCase):
    def test_migrate_empty_database_creates_normative_tables_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sqlite_path = Path(tmp) / "sircom.sqlite3"

            migrate_database(sqlite_path)

            connection = connect_sqlite(sqlite_path)
            try:
                self.assertEqual(
                    {
                        "schema_migrations",
                        "lots",
                        "etapes",
                        "jobs",
                        "artefacts",
                        "evenements",
                        "problemes",
                    },
                    table_names(connection),
                )
                migration = connection.execute(
                    """
                    SELECT version, name
                    FROM schema_migrations
                    ORDER BY version DESC
                    LIMIT 1
                    """
                ).fetchone()
                user_version = connection.execute("PRAGMA user_version").fetchone()[0]
                self.assertEqual(migration["version"], SCHEMA_VERSION)
                self.assertEqual(migration["name"], "active_job_per_step")
                self.assertEqual(user_version, SCHEMA_VERSION)

                for table in ("lots", "etapes", "jobs", "artefacts", "evenements", "problemes"):
                    self.assertTrue(
                        {"id", "created_at", "updated_at"}.issubset(
                            table_columns(connection, table)
                        )
                    )

                self.assertTrue(
                    {
                        "idx_lots_idempotency_key",
                        "idx_etapes_lot_status",
                        "idx_jobs_status_lease",
                        "idx_jobs_lot_step",
                        "idx_jobs_active_lot_step",
                        "idx_artefacts_lot_status",
                        "idx_artefacts_lot_step_run",
                        "idx_evenements_lot_created",
                        "idx_problemes_lot_status",
                    }.issubset(index_names(connection))
                )
                self.assertTrue(
                    {("lot_id",), ("lot_id", "step_key")}.issubset(
                        foreign_key_column_groups(connection, "jobs")
                    )
                )
                self.assertTrue(
                    {("lot_id",), ("lot_id", "step_key")}.issubset(
                        foreign_key_column_groups(connection, "artefacts")
                    )
                )

                self.assertTrue(
                    {
                        "idempotency_key",
                        "active_run_id",
                        "cancel_requested_at",
                        "delete_requested_at",
                        "purge_requested_at",
                    }.issubset(table_columns(connection, "lots"))
                )
                self.assertTrue(
                    {
                        "current_run_id",
                        "input_fingerprint",
                        "output_fingerprint",
                        "progress_current",
                        "progress_total",
                    }.issubset(table_columns(connection, "etapes"))
                )
                self.assertTrue(
                    {
                        "run_id",
                        "idempotency_key",
                        "lease_owner",
                        "lease_version",
                        "lease_until",
                        "heartbeat_at",
                    }.issubset(table_columns(connection, "jobs"))
                )
                self.assertTrue(
                    {
                        "run_id",
                        "status",
                        "relative_path",
                        "sha256",
                        "committed_at",
                        "obsoleted_at",
                        "deleted_at",
                        "quarantined_at",
                    }.issubset(table_columns(connection, "artefacts"))
                )
                self.assertTrue(
                    {
                        "severity",
                        "code",
                        "title",
                        "cause",
                        "message",
                        "action",
                        "location_json",
                        "technical_json",
                    }.issubset(table_columns(connection, "problemes"))
                )
            finally:
                connection.close()

    def test_migrations_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sqlite_path = Path(tmp) / "sircom.sqlite3"

            migrate_database(sqlite_path)
            migrate_database(sqlite_path)

            connection = connect_sqlite(sqlite_path)
            try:
                migration_count = connection.execute(
                    "SELECT COUNT(*) FROM schema_migrations"
                ).fetchone()[0]
                self.assertEqual(migration_count, SCHEMA_VERSION)
                self.assertIn("jobs", table_names(connection))
            finally:
                connection.close()

    def test_migration_v4_expires_duplicate_active_jobs_before_unique_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sqlite_path = Path(tmp) / "sircom.sqlite3"
            migrate_database(sqlite_path)

            connection = connect_sqlite(sqlite_path)
            try:
                connection.execute("DROP INDEX idx_jobs_active_lot_step")
                connection.execute("DELETE FROM schema_migrations WHERE version = 4")
                connection.execute("PRAGMA user_version = 3")
                connection.execute(
                    """
                    INSERT INTO lots (id, created_at, updated_at, status, title)
                    VALUES (
                        'lot_migrate', '2026-07-21T00:00:00+00:00',
                        '2026-07-21T00:00:00+00:00', 'brouillon', 'Lot migration'
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO etapes (
                        id, created_at, updated_at, lot_id, step_key, status,
                        current_run_id
                    )
                    VALUES (
                        'step_migrate', '2026-07-21T00:00:00+00:00',
                        '2026-07-21T00:00:00+00:00', 'lot_migrate',
                        'diagnostic_excel', 'pret', 'run_old'
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO jobs (
                        id, created_at, updated_at, lot_id, step_key, status,
                        run_id, idempotency_key
                    )
                    VALUES (
                        'job_old', '2026-07-21T00:00:00+00:00',
                        '2026-07-21T00:00:00+00:00', 'lot_migrate',
                        'diagnostic_excel', 'queued', 'run_old', 'idem_old'
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO jobs (
                        id, created_at, updated_at, lot_id, step_key, status,
                        run_id, idempotency_key
                    )
                    VALUES (
                        'job_new', '2026-07-21T00:01:00+00:00',
                        '2026-07-21T00:01:00+00:00', 'lot_migrate',
                        'diagnostic_excel', 'queued', 'run_new', 'idem_new'
                    )
                    """
                )
                connection.commit()
            finally:
                connection.close()

            migrate_database(sqlite_path)

            connection = connect_sqlite(sqlite_path)
            try:
                statuses = {
                    row["id"]: row["status"]
                    for row in connection.execute(
                        "SELECT id, status FROM jobs ORDER BY id"
                    )
                }
                self.assertEqual(statuses["job_old"], "queued")
                self.assertEqual(statuses["job_new"], "expired")
                self.assertIn("idx_jobs_active_lot_step", index_names(connection))
            finally:
                connection.close()

    def test_migration_refuses_newer_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sqlite_path = Path(tmp) / "sircom.sqlite3"
            connection = connect_sqlite(sqlite_path)
            try:
                connection.execute(
                    """
                    CREATE TABLE schema_migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at)
                    VALUES (99, 'future', 'now')
                    """
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(SchemaVersionError):
                migrate_database(sqlite_path)

    def test_migration_refuses_partial_unversioned_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sqlite_path = Path(tmp) / "sircom.sqlite3"
            connection = connect_sqlite(sqlite_path)
            try:
                connection.execute("CREATE TABLE lots (id TEXT PRIMARY KEY)")
                connection.commit()
            finally:
                connection.close()

            with self.assertRaises(SchemaVersionError):
                migrate_database(sqlite_path)

    def test_constraints_foreign_keys_unique_and_status_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "sircom.sqlite3")
            database.migrate()

            with database.transaction() as repos:
                lot = repos.lots.create(title="Lot de test")
                repos.steps.create(lot_id=lot["id"], step_key="upload_excel")
                repos.steps.create(lot_id=lot["id"], step_key="diagnostic_excel")

                with self.assertRaises(sqlite3.IntegrityError):
                    repos.steps.create(lot_id=lot["id"], step_key="upload_excel")

                with self.assertRaises(sqlite3.IntegrityError):
                    repos.connection.execute(
                        """
                        INSERT INTO lots (id, created_at, updated_at, status)
                        VALUES ('lot_bad', 'now', 'now', 'mauvais')
                        """
                    )

                with self.assertRaises(sqlite3.IntegrityError):
                    repos.connection.execute(
                        """
                        INSERT INTO etapes (
                            id, created_at, updated_at, lot_id, step_key, status
                        )
                        VALUES ('step_bad', 'now', 'now', 'lot_missing', 'x', 'pret')
                        """
                    )

                with self.assertRaises(sqlite3.IntegrityError):
                    repos.connection.execute(
                        """
                        INSERT INTO artefacts (
                            id, created_at, updated_at, lot_id, step_key, run_id,
                            status, kind, role, relative_path, sha256, size_bytes,
                            schema_version
                        )
                        VALUES (
                            'artifact_bad', 'now', 'now', ?, 'upload_excel', 'run_1',
                            'mauvais', 'excel', 'source', 'lots/x/source.xlsx',
                            'abc', 1, 1
                        )
                        """,
                        (lot["id"],),
                    )

                with self.assertRaises(sqlite3.IntegrityError):
                    repos.jobs.create(
                        lot_id=lot["id"],
                        step_key="mapping_absent",
                        run_id="run_missing_step",
                        idempotency_key="idem_missing_step",
                    )

                repos.jobs.create(
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    run_id="run_1",
                    idempotency_key="idem_1",
                )
                with self.assertRaises(sqlite3.IntegrityError):
                    repos.jobs.create(
                        lot_id=lot["id"],
                        step_key="diagnostic_excel",
                        run_id="run_2",
                        idempotency_key="idem_1",
                    )

                with self.assertRaises(sqlite3.IntegrityError):
                    repos.jobs.create(
                        lot_id=lot["id"],
                        step_key="diagnostic_excel",
                        run_id="run_3",
                        idempotency_key="idem_2",
                    )

    def test_repositories_create_read_and_rollback_transactionally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "sircom.sqlite3")
            database.migrate()

            with database.transaction() as repos:
                lot = repos.lots.create(title="Lot complet")
                step = repos.steps.create(lot_id=lot["id"], step_key="upload_excel")
                job = repos.jobs.create(
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                    idempotency_key="upload_excel:1",
                )
                artifact = repos.artifacts.create(
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                    kind="excel",
                    role="source",
                    relative_path="lots/lot_1/uploads/source.xlsx",
                    sha256="abc123",
                    size_bytes=42,
                )
                event = repos.events.create(
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                    event_type="lot.created",
                    payload={"steps_total": 1},
                )
                problem = repos.problems.create(
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                    severity="alerte",
                    code="SIRCOM_TEST_WARNING",
                    title="Alerte test",
                    message="Message test",
                    cause="Cause test",
                    action="Action test",
                )

                lot = repos.lots.update_status(lot["id"], "en_cours")
                step = repos.steps.update_status(
                    step["id"],
                    "en_cours",
                    run_id="run_upload_1",
                )
                job = repos.jobs.update_status(job["id"], "running")
                artifact = repos.artifacts.update_status(artifact["id"], "committed")
                event = repos.events.update_payload(
                    event["id"],
                    {"steps_total": 2, "status": "updated"},
                    level="warning",
                )
                problem = repos.problems.update_status(problem["id"], "resolved")

            with database.transaction() as repos:
                self.assertEqual(
                    repos.lots.get_required(lot["id"])["status"],
                    "en_cours",
                )
                self.assertEqual(
                    repos.steps.get_required(step["id"])["current_run_id"],
                    "run_upload_1",
                )
                self.assertEqual(repos.jobs.get_required(job["id"])["status"], "running")
                self.assertEqual(
                    repos.artifacts.get_required(artifact["id"])["status"],
                    "committed",
                )
                self.assertIsNotNone(
                    repos.artifacts.get_required(artifact["id"])["committed_at"]
                )
                self.assertEqual(repos.events.get_required(event["id"])["level"], "warning")
                self.assertEqual(
                    repos.events.get_required(event["id"])["payload_json"],
                    '{"status":"updated","steps_total":2}',
                )
                self.assertEqual(repos.problems.get_required(problem["id"])["status"], "resolved")
                self.assertIsNotNone(repos.problems.get_required(problem["id"])["resolved_at"])
                self.assertEqual(repos.problems.get_required(problem["id"])["cause"], "Cause test")
                self.assertEqual(repos.problems.get_required(problem["id"])["action"], "Action test")

            with self.assertRaises(RuntimeError):
                with database.transaction() as repos:
                    repos.lots.update_status(lot["id"], "echoue")
                    raise RuntimeError("rollback")

            with database.transaction() as repos:
                self.assertEqual(repos.lots.get_required(lot["id"])["status"], "en_cours")

    def test_connect_applies_sqlite_pragmas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            connection = connect_sqlite(Path(tmp) / "sircom.sqlite3", busy_timeout_ms=1234)
            try:
                foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
                busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
            finally:
                connection.close()

        self.assertEqual(foreign_keys, 1)
        self.assertEqual(busy_timeout, 1234)

    def test_connect_reports_wal_failure_without_raw_path(self) -> None:
        fake_connection = FakeConnection()
        warnings: list[tuple[str, str]] = []

        with tempfile.TemporaryDirectory() as tmp:
            with patch("sircom2026.database.sqlite3.connect", return_value=fake_connection):
                with self.assertLogs("sircom2026.database", level="WARNING") as logs:
                    connection = connect_sqlite(
                        Path(tmp) / "sircom.sqlite3",
                        warning_handler=lambda code, detail: warnings.append((code, detail)),
                    )

        self.assertIs(connection, fake_connection)
        self.assertIn("PRAGMA foreign_keys = ON", fake_connection.statements)
        self.assertIn("SIRCOM_SQLITE_WAL_UNAVAILABLE", str(warnings))
        self.assertIn("OperationalError", logs.output[0])
        self.assertEqual(
            warnings,
            [("SIRCOM_SQLITE_WAL_UNAVAILABLE", "OperationalError")],
        )
        self.assertNotIn("/private/tmp", str(warnings))

    def test_event_payload_rejects_unknown_business_keys_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(Path(tmp) / "sircom.sqlite3")
            database.migrate()

            with database.transaction() as repos:
                lot = repos.lots.create(title="Lot de test")
                repos.steps.create(lot_id=lot["id"], step_key="upload_excel")

                with self.assertRaises(ValueError):
                    repos.events.create(
                        lot_id=lot["id"],
                        step_key="upload_excel",
                        event_type="event.business",
                        payload={"nom_produit": "valeur métier"},
                    )

                with self.assertRaises(ValueError):
                    repos.events.create(
                        lot_id=lot["id"],
                        step_key="upload_excel",
                        event_type="event.path",
                        payload={"code": "/Users/alex/source.xlsx"},
                    )


if __name__ == "__main__":
    unittest.main()
