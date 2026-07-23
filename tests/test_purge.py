from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from sircom2026.app import create_app
from sircom2026.artifacts import ArtifactStore
from sircom2026.config import load_settings
from sircom2026.database import Database
from sircom2026.lots import create_lot_with_steps
from sircom2026.purge import (
    delete_lot_and_purge_if_idle,
    lot_id_hash,
    prune_old_quarantine_files,
    purge_expired_lots,
)
from sircom2026 import purge as purge_module
from sircom2026.state import record_problem
from sircom2026.worker import JobResult, WorkerJobContext, enqueue_job
from sircom2026.worker_runner import run_worker_once


SENSITIVE_PRODUCT = "SENTINEL_PRODUIT_CONFIDENTIEL_X9"
SENSITIVE_COMPANY = "SENTINEL_ENTREPRISE_CONFIDENTIELLE_X9"
SENSITIVE_FILENAME = "photo-originale-secret-x9.jpg"


def make_settings(tmpdir: Path, **overrides: str):
    env = {
        "SIRCOM_DATA_DIR": str(tmpdir / "data"),
        "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
        "SIRCOM_DISK_FREE_MIN_MB": "0",
    }
    env.update(overrides)
    return load_settings(env)


def create_owned_running_job(repositories, *, lot_id: str, step_key: str, run_id: str):
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if step is not None:
        repositories.steps.update_status(step["id"], "en_cours", run_id=run_id)
    return repositories.jobs.create_owned_running(
        lot_id=lot_id,
        step_key=step_key,
        run_id=run_id,
        idempotency_key=f"{step_key}:{run_id}",
        lease_owner="test-worker",
        lease_seconds=300,
    )


def count_lot_rows(database: Database, lot_id: str) -> dict[str, int]:
    with database.session() as repositories:
        return {
            table: int(
                repositories.connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE lot_id = ?",
                    (lot_id,),
                ).fetchone()[0]
            )
            for table in ("etapes", "jobs", "artefacts", "evenements", "problemes")
        }


class PurgeTest(unittest.TestCase):
    def test_delete_idle_lot_purges_files_rows_and_keeps_anonymized_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            database = Database(settings.sqlite_path)
            store = ArtifactStore(settings.data_dir)
            lot_id = client.post(
                "/api/lots",
                json={"title": f"{SENSITIVE_PRODUCT} {SENSITIVE_COMPANY}"},
            ).json()["lot"]["id"]

            with database.transaction() as repositories:
                job = create_owned_running_job(
                    repositories,
                    lot_id=lot_id,
                    step_key="upload_excel",
                    run_id="run_purge_idle",
                )
                artifact = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot_id,
                    step_key="upload_excel",
                    run_id="run_purge_idle",
                    kind="excel",
                    role="source",
                    filename=SENSITIVE_FILENAME,
                    content=f"{SENSITIVE_PRODUCT},{SENSITIVE_COMPANY}".encode("utf-8"),
                    metadata={"download_filename": SENSITIVE_FILENAME},
                    lease_version=job["lease_version"],
                )
                artifact_path = store.path_for(artifact["relative_path"])
                record_problem(
                    repositories,
                    lot_id=lot_id,
                    step_key="upload_excel",
                    severity="alerte",
                    code="SIRCOM_TEST_SENTINEL",
                    title=f"Alerte {SENSITIVE_PRODUCT}",
                    cause=f"Cause {SENSITIVE_COMPANY}",
                    action="Corriger le fichier de test.",
                    run_id="run_purge_idle",
                )
                repositories.jobs.update_status(job["id"], "succeeded")
                repositories.steps.update_status(
                    repositories.steps.get_by_lot_key(lot_id, "upload_excel")["id"],
                    "termine_avec_alertes",
                    run_id="run_purge_idle",
                )

            storage_before = client.get("/api/storage")
            response = client.delete(f"/api/lots/{lot_id}")
            second_response = client.delete(f"/api/lots/{lot_id}")
            detail_response = client.get(f"/api/lots/{lot_id}")
            list_response = client.get("/api/lots")
            download_response = client.get(
                f"/api/lots/{lot_id}/downloads/{artifact['id']}"
            )
            storage_after = client.get("/api/storage")

            with database.session() as repositories:
                lot = repositories.lots.get_required(lot_id)
                trace = repositories.purge_traces.get_by_lot_id_hash(
                    lot_id_hash(lot_id)
                )
            row_counts = count_lot_rows(database, lot_id)
            artifact_exists_after_delete = artifact_path.exists()
            serialized = json.dumps(
                {
                    "delete": response.json(),
                    "storage": storage_after.json(),
                    "trace": dict(trace),
                },
                ensure_ascii=False,
            )

        self.assertEqual(storage_before.status_code, 200)
        storage_lots = storage_before.json()["storage"]["lots"]
        self.assertGreaterEqual(
            next(item for item in storage_lots if item["id"] == lot_id)["size_bytes"],
            artifact["size_bytes"],
        )
        self.assertFalse(artifact_exists_after_delete)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["lot"]["status"], "purge")
        self.assertEqual(response.json()["purge"]["status"], "purged")
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()["purge"]["status"], "already_purged")
        self.assertEqual(detail_response.json()["lot"]["status"], "purge")
        self.assertIsNone(detail_response.json()["lot"]["title"])
        self.assertEqual(list_response.json()["items"], [])
        self.assertEqual(download_response.status_code, 404)
        self.assertEqual(
            row_counts,
            {
                "etapes": 0,
                "jobs": 0,
                "artefacts": 0,
                "evenements": 0,
                "problemes": 0,
            },
        )
        self.assertEqual(lot["title"], None)
        self.assertEqual(lot["status"], "purge")
        self.assertIsNotNone(trace)
        self.assertNotIn(SENSITIVE_PRODUCT, serialized)
        self.assertNotIn(SENSITIVE_COMPANY, serialized)
        self.assertNotIn(SENSITIVE_FILENAME, serialized)
        self.assertNotIn(str(settings.data_dir), serialized)
        self.assertIn("lot_id_hash", serialized)

    def test_delete_during_running_job_cancels_then_purges_after_worker_cycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            database = Database(settings.sqlite_path)
            lot_id = client.post("/api/lots", json={"title": "Lot actif"}).json()[
                "lot"
            ]["id"]
            delete_status_codes: list[int] = []

            with database.transaction() as repositories:
                enqueue_job(
                    repositories,
                    lot_id=lot_id,
                    step_key="diagnostic_excel",
                    idempotency_key="diagnostic:purge-active",
                    run_id="run_purge_active",
                )

            def handler(context: WorkerJobContext) -> JobResult:
                (settings.data_dir / "lots" / lot_id / "tmp").mkdir(
                    parents=True, exist_ok=True
                )
                (
                    settings.data_dir / "lots" / lot_id / "tmp" / "worker.part"
                ).write_text(
                    "temporary",
                    encoding="utf-8",
                )
                delete_response = client.delete(f"/api/lots/{lot_id}")
                delete_status_codes.append(delete_response.status_code)
                context.raise_if_cancelled()
                return JobResult()

            result = run_worker_once(
                settings=settings,
                handlers={"diagnostic_excel": handler},
            )

            with database.session() as repositories:
                lot = repositories.lots.get_required(lot_id)
                trace = repositories.purge_traces.get_by_lot_id_hash(
                    lot_id_hash(lot_id)
                )
            lot_dir_exists = (settings.data_dir / "lots" / lot_id).exists()
            row_counts = count_lot_rows(database, lot_id)

        self.assertEqual(delete_status_codes, [202])
        self.assertEqual(result.outcome, "canceled")
        self.assertEqual(lot["status"], "purge")
        self.assertIsNotNone(trace)
        self.assertFalse(lot_dir_exists)
        self.assertEqual(
            row_counts,
            {
                "etapes": 0,
                "jobs": 0,
                "artefacts": 0,
                "evenements": 0,
                "problemes": 0,
            },
        )

    def test_delete_lot_expires_stale_lease_before_purging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            database = Database(settings.sqlite_path)
            lot_id = client.post("/api/lots", json={"title": "Lot bail expire"}).json()[
                "lot"
            ]["id"]
            lot_dir = settings.data_dir / "lots" / lot_id
            lot_dir.mkdir(parents=True)
            (lot_dir / "fichier.txt").write_text("contenu", encoding="utf-8")

            with database.transaction() as repositories:
                job = create_owned_running_job(
                    repositories,
                    lot_id=lot_id,
                    step_key="diagnostic_excel",
                    run_id="run_stale_lease",
                )
                repositories.connection.execute(
                    """
                    UPDATE jobs
                    SET lease_until = ?
                    WHERE id = ?
                    """,
                    ("2000-01-01T00:00:00+00:00", job["id"]),
                )

            response = client.delete(f"/api/lots/{lot_id}")
            with database.session() as repositories:
                lot = repositories.lots.get_required(lot_id)
                trace = repositories.purge_traces.get_by_lot_id_hash(
                    lot_id_hash(lot_id)
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["purge"]["status"], "purged")
        self.assertEqual(lot["status"], "purge")
        self.assertIsNotNone(trace)
        self.assertFalse(lot_dir.exists())

    def test_quarantine_retention_removes_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir, SIRCOM_PURGE_TRACE_RETENTION_DAYS="1")
            old_file = settings.data_dir / "quarantine" / "excel" / "old.xlsx"
            fresh_file = settings.data_dir / "quarantine" / "excel" / "fresh.xlsx"
            old_file.parent.mkdir(parents=True)
            old_file.write_bytes(b"ancien")
            fresh_file.write_bytes(b"recent")
            old_timestamp = (datetime.now(UTC) - timedelta(days=2)).timestamp()
            os.utime(old_file, (old_timestamp, old_timestamp))

            removed_count = prune_old_quarantine_files(settings=settings)
            old_file_exists = old_file.exists()
            fresh_file_exists = fresh_file.exists()

        self.assertEqual(removed_count, 1)
        self.assertFalse(old_file_exists)
        self.assertTrue(fresh_file_exists)

    def test_purge_resumes_after_files_deleted_but_sql_finalization_failed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            database = Database(settings.sqlite_path)
            database.migrate()

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot reprise purge")
                lot_id = lot["id"]
                lot_dir = settings.data_dir / "lots" / lot_id
                lot_dir.mkdir(parents=True)
                (lot_dir / "artefact.txt").write_text(
                    "contenu temporaire", encoding="utf-8"
                )

            real_remove_lot_directory = purge_module.remove_lot_directory

            def remove_then_fail(path: Path):
                usage = real_remove_lot_directory(path)
                raise RuntimeError(
                    f"panne apres suppression de {usage.files_count} fichier"
                )

            with patch(
                "sircom2026.purge.remove_lot_directory", side_effect=remove_then_fail
            ):
                with self.assertRaises(RuntimeError):
                    with database.transaction() as repositories:
                        delete_lot_and_purge_if_idle(
                            repositories,
                            settings=settings,
                            lot_id=lot_id,
                        )

            with database.session() as repositories:
                lot_after_failure = repositories.lots.get_required(lot_id)
                trace_after_failure = repositories.purge_traces.get_by_lot_id_hash(
                    lot_id_hash(lot_id)
                )
                rows_after_failure = {
                    table: int(
                        repositories.connection.execute(
                            f"SELECT COUNT(*) FROM {table} WHERE lot_id = ?",
                            (lot_id,),
                        ).fetchone()[0]
                    )
                    for table in (
                        "etapes",
                        "jobs",
                        "artefacts",
                        "evenements",
                        "problemes",
                    )
                }
                lot_dir_exists_after_failure = lot_dir.exists()

            with database.transaction() as repositories:
                resumed_outcome = delete_lot_and_purge_if_idle(
                    repositories,
                    settings=settings,
                    lot_id=lot_id,
                )

            with database.session() as repositories:
                lot_after_resume = repositories.lots.get_required(lot_id)
                trace_after_resume = repositories.purge_traces.get_by_lot_id_hash(
                    lot_id_hash(lot_id)
                )
            rows_after_resume = count_lot_rows(database, lot_id)
            lot_dir_exists_after_resume = lot_dir.exists()

        self.assertEqual(lot_after_failure["status"], "supprime")
        self.assertFalse(lot_dir_exists_after_failure)
        self.assertIsNotNone(trace_after_failure)
        self.assertEqual(
            json.loads(trace_after_failure["trace_json"])["purge"]["status"], "started"
        )
        self.assertGreater(rows_after_failure["etapes"], 0)
        self.assertEqual(resumed_outcome.purge_status, "purged")
        self.assertEqual(lot_after_resume["status"], "purge")
        self.assertFalse(lot_dir_exists_after_resume)
        self.assertEqual(
            rows_after_resume,
            {
                "etapes": 0,
                "jobs": 0,
                "artefacts": 0,
                "evenements": 0,
                "problemes": 0,
            },
        )
        resumed_trace = json.loads(trace_after_resume["trace_json"])
        self.assertEqual(resumed_trace["purge"]["status"], "completed")
        self.assertEqual(resumed_trace["purge"]["files_deleted"], 1)
        self.assertGreater(resumed_trace["purge"]["bytes_deleted"], 0)

    def test_retention_purge_only_removes_expired_deleted_lots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir, SIRCOM_RETENTION_DAYS="7")
            database = Database(settings.sqlite_path)
            database.migrate()
            old_deleted_at = (datetime.now(UTC) - timedelta(days=8)).isoformat(
                timespec="seconds"
            )

            with database.transaction() as repositories:
                old_lot = create_lot_with_steps(repositories, title="Ancien lot")
                fresh_lot = create_lot_with_steps(repositories, title="Lot récent")
                repositories.lots.mark_deleted(old_lot["id"])
                repositories.lots.mark_deleted(fresh_lot["id"])
                repositories.connection.execute(
                    "UPDATE lots SET deleted_at = ?, updated_at = ? WHERE id = ?",
                    (old_deleted_at, old_deleted_at, old_lot["id"]),
                )
                (settings.data_dir / "lots" / old_lot["id"]).mkdir(parents=True)
                (settings.data_dir / "lots" / fresh_lot["id"]).mkdir(parents=True)

                outcomes = purge_expired_lots(repositories, settings=settings)
                old_after = repositories.lots.get_required(old_lot["id"])
                fresh_after = repositories.lots.get_required(fresh_lot["id"])
                old_dir_exists = (settings.data_dir / "lots" / old_lot["id"]).exists()
                fresh_dir_exists = (
                    settings.data_dir / "lots" / fresh_lot["id"]
                ).exists()

        self.assertEqual([outcome.lot["id"] for outcome in outcomes], [old_lot["id"]])
        self.assertEqual(old_after["status"], "purge")
        self.assertEqual(fresh_after["status"], "supprime")
        self.assertFalse(old_dir_exists)
        self.assertTrue(fresh_dir_exists)


if __name__ == "__main__":
    unittest.main()
