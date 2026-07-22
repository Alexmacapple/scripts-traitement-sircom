from __future__ import annotations

import threading
import tempfile
import unittest
from pathlib import Path

from sircom2026.config import load_settings
from sircom2026.database import Database
from sircom2026.lots import create_lot_with_steps
from sircom2026.worker import (
    IdempotencyKeyConsumedError,
    JobResult,
    LocalWorker,
    WorkerLeaseLost,
    WorkerJobContext,
    enqueue_job,
    request_lot_cancellation,
)
from sircom2026.worker_runner import run_worker_once


class LocalWorkerTest(unittest.TestCase):
    def test_worker_runner_initializes_database_and_is_idle_without_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = load_settings(
                {
                    "SIRCOM_DATA_DIR": str(Path(tmp) / "data"),
                    "SIRCOM_SQLITE_PATH": str(Path(tmp) / "data" / "sircom.sqlite3"),
                }
            )

            result = run_worker_once(settings=settings, handlers={})

            self.assertFalse(result.processed)
            self.assertEqual(result.outcome, "idle")
            self.assertTrue(settings.sqlite_path.exists())

    def test_worker_runner_expires_stale_leases_even_without_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = load_settings(
                {
                    "SIRCOM_DATA_DIR": str(Path(tmp) / "data"),
                    "SIRCOM_SQLITE_PATH": str(Path(tmp) / "data" / "sircom.sqlite3"),
                }
            )
            database = Database(settings.sqlite_path)
            database.migrate()
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot runner restart")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    idempotency_key="diagnostic:restart",
                    run_id="run_diag_restart",
                )
                repositories.connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'running', lease_until = ?
                    WHERE id = ?
                    """,
                    ("2000-01-01T00:00:00+00:00", queued.job["id"]),
                )

            result = run_worker_once(settings=settings, handlers={})

            with database.session() as repositories:
                job = repositories.jobs.get_required(queued.job["id"])

            self.assertFalse(result.processed)
            self.assertEqual(result.outcome, "idle")
            self.assertEqual(job["status"], "expired")

    def test_worker_runner_respects_disabled_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = load_settings(
                {
                    "SIRCOM_DATA_DIR": str(Path(tmp) / "data"),
                    "SIRCOM_SQLITE_PATH": str(Path(tmp) / "data" / "sircom.sqlite3"),
                    "SIRCOM_WORKER_ENABLED": "false",
                }
            )

            result = run_worker_once(settings=settings, handlers={})

            self.assertFalse(result.processed)
            self.assertEqual(result.outcome, "disabled")
            self.assertFalse(settings.sqlite_path.exists())

    def test_job_is_enqueued_acquired_run_and_completed_with_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot worker")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    idempotency_key="diagnostic:1",
                    run_id="run_diag_1",
                    input_fingerprint="input_upload_1",
                )

            def handler(context: WorkerJobContext) -> JobResult:
                context.set_progress(1, 2)
                context.set_progress(2, 2)
                return JobResult()

            worker = LocalWorker(
                database,
                {"diagnostic_excel": handler},
                worker_id="worker-a",
                lease_seconds=60,
            )
            result = worker.run_once()

            with database.session() as repositories:
                job = repositories.jobs.get_required(queued.job["id"])
                step = repositories.steps.get_by_lot_key(lot["id"], "diagnostic_excel")
                event_types = {
                    row["event_type"]
                    for row in repositories.events.list_for_lot(lot["id"], limit=20)
                }

            self.assertTrue(result.processed)
            self.assertEqual(result.outcome, "succeeded")
            self.assertEqual(job["status"], "succeeded")
            self.assertEqual(job["attempt"], 1)
            self.assertEqual(job["lease_owner"], "worker-a")
            self.assertEqual(step["status"], "termine")
            self.assertEqual(step["current_run_id"], "run_diag_1")
            self.assertEqual(step["input_fingerprint"], "input_upload_1")
            self.assertEqual(step["progress_current"], 2)
            self.assertEqual(step["progress_total"], 2)
            self.assertIn("job.acquired", event_types)
            self.assertIn("job.started", event_types)
            self.assertIn("job.progress", event_types)
            self.assertIn("job.succeeded", event_types)

    def test_worker_sends_periodic_heartbeat_while_handler_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot heartbeat")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    idempotency_key="diagnostic:heartbeat",
                    run_id="run_diag_heartbeat",
                    input_fingerprint="input_heartbeat",
                )

            heartbeat_seen = threading.Event()
            observed_intervals: list[float] = []
            original_heartbeat = WorkerJobContext.heartbeat

            def observed_heartbeat(context: WorkerJobContext) -> None:
                original_heartbeat(context)
                observed_intervals.append(context.heartbeat_seconds)
                heartbeat_seen.set()

            def handler(_context: WorkerJobContext) -> JobResult:
                heartbeat_seen.wait(1.0)
                return JobResult()

            WorkerJobContext.heartbeat = observed_heartbeat
            try:
                worker = LocalWorker(
                    database,
                    {"diagnostic_excel": handler},
                    worker_id="worker-a",
                    lease_seconds=60,
                    heartbeat_seconds=0.01,
                )
                result = worker.run_once()
            finally:
                WorkerJobContext.heartbeat = original_heartbeat

            with database.session() as repositories:
                job = repositories.jobs.get_required(queued.job["id"])

            self.assertTrue(heartbeat_seen.is_set())
            self.assertIn(0.01, observed_intervals)
            self.assertEqual(result.outcome, "succeeded")
            self.assertEqual(job["status"], "succeeded")

    def test_double_submission_returns_existing_active_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot double submit")
                first = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    idempotency_key="mapping:validate",
                    run_id="run_mapping_1",
                )
                same_key = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    idempotency_key="mapping:validate",
                    run_id="run_mapping_ignored",
                )
                other_key = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    idempotency_key="mapping:double-click",
                    run_id="run_mapping_ignored_2",
                )
                active_jobs = repositories.connection.execute(
                    """
                    SELECT COUNT(*) FROM jobs
                    WHERE lot_id = ?
                      AND step_key = ?
                      AND status IN ('queued', 'leased', 'running')
                    """,
                    (lot["id"], "mapping"),
                ).fetchone()[0]

            self.assertTrue(first.created)
            self.assertFalse(same_key.created)
            self.assertFalse(other_key.created)
            self.assertEqual(first.job["id"], same_key.job["id"])
            self.assertEqual(first.job["id"], other_key.job["id"])
            self.assertEqual(active_jobs, 1)

    def test_consumed_idempotency_key_is_not_reused_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot idempotence")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    idempotency_key="diagnostic:consumed",
                    run_id="run_diag_consumed",
                    input_fingerprint="input_consumed",
                )

            worker = LocalWorker(
                database,
                {"diagnostic_excel": lambda _context: JobResult()},
                worker_id="worker-idempotence",
                lease_seconds=60,
            )
            result = worker.run_once()
            self.assertEqual(result.outcome, "succeeded")

            with database.transaction() as repositories:
                with self.assertRaises(IdempotencyKeyConsumedError):
                    enqueue_job(
                        repositories,
                        lot_id=lot["id"],
                        step_key="diagnostic_excel",
                        idempotency_key="diagnostic:consumed",
                        run_id="run_diag_new",
                    )

    def test_lease_prevents_two_workers_from_acquiring_the_same_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot lease")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="fusion_multi_onglets",
                    idempotency_key="fusion:1",
                    run_id="run_fusion_1",
                )
                first = repositories.jobs.acquire_next(
                    worker_id="worker-a",
                    lease_seconds=60,
                    step_keys=("fusion_multi_onglets",),
                )
                second = repositories.jobs.acquire_next(
                    worker_id="worker-b",
                    lease_seconds=60,
                    step_keys=("fusion_multi_onglets",),
                )

            self.assertIsNotNone(first)
            self.assertIsNone(second)
            self.assertEqual(first["lease_owner"], "worker-a")
            self.assertEqual(first["lease_version"], 1)

    def test_worker_uses_handler_order_when_jobs_share_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot priority")
                repositories.steps.prepare_run(
                    lot_id=lot["id"],
                    step_key="inspection_images",
                    run_id="run_inspection_priority",
                    input_fingerprint="input_inspection",
                )
                repositories.jobs.create(
                    lot_id=lot["id"],
                    step_key="inspection_images",
                    run_id="run_inspection_priority",
                    idempotency_key="inspection:priority",
                    job_id="job_a_inspection_priority",
                )
                repositories.steps.prepare_run(
                    lot_id=lot["id"],
                    step_key="verification_csv_indesign",
                    run_id="run_csv_priority",
                    input_fingerprint="input_csv",
                )
                repositories.jobs.create(
                    lot_id=lot["id"],
                    step_key="verification_csv_indesign",
                    run_id="run_csv_priority",
                    idempotency_key="csv:priority",
                    job_id="job_z_csv_priority",
                )
                repositories.connection.execute(
                    "UPDATE jobs SET created_at = ?, updated_at = ? WHERE lot_id = ?",
                    ("2026-07-21T00:00:00+00:00", "2026-07-21T00:00:00+00:00", lot["id"]),
                )

            worker = LocalWorker(
                database,
                {
                    "verification_csv_indesign": lambda _context: JobResult(),
                    "inspection_images": lambda _context: JobResult(),
                },
                worker_id="worker-priority",
                lease_seconds=60,
            )
            leased = worker.acquire_next()

            self.assertIsNotNone(leased)
            self.assertEqual(leased.step_key, "verification_csv_indesign")

    def test_lease_prevents_two_connections_from_acquiring_the_same_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sqlite_path = Path(tmp) / "sircom.sqlite3"
            database_a = Database(sqlite_path)
            database_b = Database(sqlite_path)
            database_a.migrate()
            with database_a.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot lease connexions")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="fusion_multi_onglets",
                    idempotency_key="fusion:connection",
                    run_id="run_fusion_connection",
                )

            worker_a = LocalWorker(
                database_a,
                {"fusion_multi_onglets": lambda _context: JobResult()},
                worker_id="worker-a",
                lease_seconds=60,
            )
            worker_b = LocalWorker(
                database_b,
                {"fusion_multi_onglets": lambda _context: JobResult()},
                worker_id="worker-b",
                lease_seconds=60,
            )

            first = worker_a.acquire_next()
            second = worker_b.acquire_next()

            self.assertIsNotNone(first)
            self.assertIsNone(second)

    def test_max_active_jobs_prevents_parallel_processing_on_different_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot max active")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    idempotency_key="diagnostic:1",
                    run_id="run_diag_1",
                )
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    idempotency_key="mapping:1",
                    run_id="run_mapping_1",
                )

            worker_a = LocalWorker(
                database,
                {
                    "diagnostic_excel": lambda _context: JobResult(),
                    "mapping": lambda _context: JobResult(),
                },
                worker_id="worker-a",
                lease_seconds=60,
                max_active_jobs=1,
            )
            worker_b = LocalWorker(
                database,
                {
                    "diagnostic_excel": lambda _context: JobResult(),
                    "mapping": lambda _context: JobResult(),
                },
                worker_id="worker-b",
                lease_seconds=60,
                max_active_jobs=1,
            )

            first = worker_a.acquire_next()
            second = worker_b.acquire_next()

            self.assertIsNotNone(first)
            self.assertIsNone(second)

    def test_active_job_on_deleted_lot_does_not_block_other_lots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                deleted_lot = create_lot_with_steps(repositories, title="Lot supprime")
                active_deleted_job = enqueue_job(
                    repositories,
                    lot_id=deleted_lot["id"],
                    step_key="diagnostic_excel",
                    idempotency_key="diagnostic:deleted",
                    run_id="run_deleted",
                )
                repositories.connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'running'
                    WHERE id = ?
                    """,
                    (active_deleted_job.job["id"],),
                )
                repositories.lots.mark_deleted(deleted_lot["id"])

                current_lot = create_lot_with_steps(repositories, title="Lot courant")
                queued_current = enqueue_job(
                    repositories,
                    lot_id=current_lot["id"],
                    step_key="mapping",
                    idempotency_key="mapping:current",
                    run_id="run_current",
                )

            worker = LocalWorker(
                database,
                {"mapping": lambda _context: JobResult()},
                worker_id="worker-a",
                lease_seconds=60,
                max_active_jobs=1,
            )

            leased = worker.acquire_next()

            self.assertIsNotNone(leased)
            self.assertEqual(leased.job_id, queued_current.job["id"])

    def test_expired_lease_can_be_reclaimed_without_changing_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot restart")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    idempotency_key="normalisation:1",
                    run_id="run_norm_1",
                )
                first = repositories.jobs.acquire_next(
                    worker_id="worker-a",
                    lease_seconds=60,
                    step_keys=("normalisation_contenu",),
                )
                repositories.connection.execute(
                    "UPDATE jobs SET lease_until = ? WHERE id = ?",
                    ("2000-01-01T00:00:00+00:00", queued.job["id"]),
                )

            with database.transaction() as repositories:
                expired = repositories.jobs.expire_stale_leases()
                reclaimed = repositories.jobs.acquire_next(
                    worker_id="worker-b",
                    lease_seconds=60,
                    step_keys=("normalisation_contenu",),
                )

            self.assertEqual(expired, 1)
            self.assertIsNotNone(reclaimed)
            self.assertEqual(reclaimed["id"], first["id"])
            self.assertEqual(reclaimed["run_id"], "run_norm_1")
            self.assertEqual(reclaimed["attempt"], 2)
            self.assertEqual(reclaimed["lease_owner"], "worker-b")
            self.assertEqual(reclaimed["lease_version"], 2)

    def test_enqueue_returns_existing_expired_reclaimable_job_for_same_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot expired idempotence")
                first = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    idempotency_key="normalisation:expired",
                    run_id="run_norm_expired",
                )
                repositories.jobs.acquire_next(
                    worker_id="worker-a",
                    lease_seconds=60,
                    step_keys=("normalisation_contenu",),
                )
                repositories.connection.execute(
                    "UPDATE jobs SET lease_until = ? WHERE id = ?",
                    ("2000-01-01T00:00:00+00:00", first.job["id"]),
                )
                repositories.jobs.expire_stale_leases()

                same_key = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    idempotency_key="normalisation:expired",
                    run_id="run_norm_ignored",
                )

            self.assertFalse(same_key.created)
            self.assertEqual(same_key.job["id"], first.job["id"])
            self.assertEqual(same_key.job["status"], "expired")

    def test_expired_job_without_lease_until_is_not_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot expired no lease")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    idempotency_key="normalisation:no-lease",
                    run_id="run_norm_no_lease",
                )
                repositories.connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'expired', lease_until = NULL
                    WHERE id = ?
                    """,
                    (queued.job["id"],),
                )

            worker = LocalWorker(
                database,
                {"normalisation_contenu": lambda _context: JobResult()},
                worker_id="worker-a",
                lease_seconds=60,
            )
            reclaimed = worker.acquire_next()

            self.assertIsNone(reclaimed)

    def test_stale_run_cannot_finish_current_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot stale run")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="previsualisation_csv",
                    idempotency_key="preview:1",
                    run_id="run_preview_old",
                )

            worker = LocalWorker(
                database,
                {"previsualisation_csv": lambda _context: JobResult()},
                worker_id="worker-a",
                lease_seconds=60,
            )
            leased = worker.acquire_next()
            if leased is None:
                self.fail("Expected a leased job.")
            self.assertTrue(worker.start_job(leased))

            with database.transaction() as repositories:
                step = repositories.steps.get_by_lot_key(lot["id"], "previsualisation_csv")
                if step is None:
                    self.fail("Expected previsualisation_csv step to exist.")
                repositories.steps.update_status(step["id"], "en_cours", run_id="run_preview_new")

            finished = worker.finish_success(leased)

            with database.session() as repositories:
                job = repositories.jobs.get_required(leased.job_id)
                step_after = repositories.steps.get_by_lot_key(lot["id"], "previsualisation_csv")
                event_types = {
                    row["event_type"]
                    for row in repositories.events.list_for_lot(lot["id"], limit=20)
                }

            self.assertFalse(finished)
            self.assertEqual(job["status"], "running")
            self.assertEqual(step_after["status"], "en_cours")
            self.assertEqual(step_after["current_run_id"], "run_preview_new")
            self.assertIn("job.finish_rejected", event_types)

    def test_stale_run_cannot_be_reclaimed_after_current_run_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot stale reclaim")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_images",
                    idempotency_key="images:old",
                    run_id="run_images_old",
                )
                old_job = repositories.jobs.acquire_next(
                    worker_id="worker-a",
                    lease_seconds=60,
                    step_keys=("upload_images",),
                )
                if old_job is None:
                    self.fail("Expected old job to be leased.")
                repositories.connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'expired', lease_until = ?
                    WHERE id = ?
                    """,
                    ("2000-01-01T00:00:00+00:00", old_job["id"]),
                )
                step = repositories.steps.get_by_lot_key(lot["id"], "upload_images")
                if step is None:
                    self.fail("Expected upload_images step to exist.")
                repositories.steps.update_status(step["id"], "pret", run_id="run_images_new")
                new_job = repositories.jobs.create(
                    lot_id=lot["id"],
                    step_key="upload_images",
                    run_id="run_images_new",
                    idempotency_key="images:new",
                )

            worker = LocalWorker(
                database,
                {"upload_images": lambda _context: JobResult()},
                worker_id="worker-b",
                lease_seconds=60,
            )
            reclaimed = worker.acquire_next()

            self.assertIsNotNone(reclaimed)
            self.assertEqual(reclaimed.job_id, new_job["id"])
            self.assertNotEqual(reclaimed.job_id, old_job["id"])

    def test_stale_run_cannot_extend_lease_or_update_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot stale progress")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="rapports",
                    idempotency_key="reports:1",
                    run_id="run_reports_old",
                )

            worker = LocalWorker(
                database,
                {"rapports": lambda _context: JobResult()},
                worker_id="worker-a",
                lease_seconds=60,
            )
            leased = worker.acquire_next()
            if leased is None:
                self.fail("Expected a leased job.")
            self.assertTrue(worker.start_job(leased))

            with database.transaction() as repositories:
                step = repositories.steps.get_by_lot_key(lot["id"], "rapports")
                if step is None:
                    self.fail("Expected rapports step to exist.")
                repositories.steps.update_status(step["id"], "en_cours", run_id="run_reports_new")

            context = WorkerJobContext(
                database=database,
                leased_job=leased,
                worker_id="worker-a",
                lease_seconds=60,
            )

            with self.assertRaises(WorkerLeaseLost):
                context.set_progress(1, 2)

    def test_changed_input_fingerprint_rejects_worker_finish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot fingerprint")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="verification_csv_indesign",
                    idempotency_key="csv-contract:1",
                    run_id="run_csv_1",
                    input_fingerprint="input_old",
                )

            worker = LocalWorker(
                database,
                {"verification_csv_indesign": lambda _context: JobResult()},
                worker_id="worker-a",
                lease_seconds=60,
            )
            leased = worker.acquire_next()
            if leased is None:
                self.fail("Expected a leased job.")
            self.assertEqual(leased.input_fingerprint, "input_old")
            self.assertTrue(worker.start_job(leased))

            with database.transaction() as repositories:
                repositories.connection.execute(
                    """
                    UPDATE etapes
                    SET input_fingerprint = ?
                    WHERE lot_id = ? AND step_key = ?
                    """,
                    ("input_new", lot["id"], "verification_csv_indesign"),
                )

            finished = worker.finish_success(leased, JobResult(output_fingerprint="output_old"))

            with database.session() as repositories:
                job = repositories.jobs.get_required(queued.job["id"])
                step = repositories.steps.get_by_lot_key(lot["id"], "verification_csv_indesign")
                event_types = {
                    row["event_type"]
                    for row in repositories.events.list_for_lot(lot["id"], limit=20)
                }

            self.assertFalse(finished)
            self.assertEqual(job["status"], "running")
            self.assertEqual(step["status"], "en_cours")
            self.assertEqual(step["output_fingerprint"], None)
            self.assertIn("job.finish_rejected", event_types)

    def test_dependent_step_without_input_fingerprint_cannot_finish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot missing fingerprint")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    idempotency_key="mapping:no-input",
                    run_id="run_mapping_no_input",
                )

            worker = LocalWorker(
                database,
                {"mapping": lambda _context: JobResult(output_fingerprint="output_mapping")},
                worker_id="worker-a",
                lease_seconds=60,
            )
            result = worker.run_once()

            with database.session() as repositories:
                job = repositories.jobs.get_required(queued.job["id"])
                step = repositories.steps.get_by_lot_key(lot["id"], "mapping")
                events = repositories.events.list_for_lot(lot["id"], limit=20)

            self.assertEqual(result.outcome, "rejected")
            self.assertEqual(job["status"], "running")
            self.assertEqual(step["status"], "en_cours")
            self.assertEqual(step["output_fingerprint"], None)
            self.assertTrue(
                any(
                    event["event_type"] == "job.finish_rejected"
                    and "input_fingerprint_missing" in event["payload_json"]
                    for event in events
                )
            )

    def test_worker_success_persists_output_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot output fingerprint")
                enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="verification_csv_indesign",
                    idempotency_key="csv-contract:2",
                    run_id="run_csv_2",
                    input_fingerprint="input_current",
                )

            worker = LocalWorker(
                database,
                {
                    "verification_csv_indesign": lambda _context: JobResult(
                        output_fingerprint="output_current"
                    )
                },
                worker_id="worker-a",
                lease_seconds=60,
            )
            result = worker.run_once()

            with database.session() as repositories:
                step = repositories.steps.get_by_lot_key(lot["id"], "verification_csv_indesign")

            self.assertEqual(result.outcome, "succeeded")
            self.assertEqual(step["status"], "termine")
            self.assertEqual(step["input_fingerprint"], "input_current")
            self.assertEqual(step["output_fingerprint"], "output_current")

    def test_cancellation_request_is_observed_between_substeps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot cancel")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_images",
                    idempotency_key="images:1",
                    run_id="run_images_1",
                )

            def handler(context: WorkerJobContext) -> JobResult:
                context.set_progress(1, 3)
                with context.database.transaction() as repositories:
                    request_lot_cancellation(repositories, context.lot_id)
                context.raise_if_cancelled()
                return JobResult()

            worker = LocalWorker(
                database,
                {"upload_images": handler},
                worker_id="worker-a",
                lease_seconds=60,
            )
            result = worker.run_once()

            with database.session() as repositories:
                lot_after = repositories.lots.get_required(lot["id"])
                job = repositories.jobs.get_required(queued.job["id"])
                step = repositories.steps.get_by_lot_key(lot["id"], "upload_images")

            self.assertEqual(result.outcome, "canceled")
            self.assertEqual(lot_after["status"], "annule")
            self.assertIsNotNone(lot_after["cancel_requested_at"])
            self.assertEqual(job["status"], "canceled")
            self.assertIsNotNone(job["cancel_requested_at"])
            self.assertEqual(step["status"], "annule")
            self.assertEqual(step["progress_current"], 1)
            self.assertEqual(step["progress_total"], 3)

    def test_unexpected_handler_error_marks_job_failed_and_step_echoue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot error")
                queued = enqueue_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="package_final",
                    idempotency_key="package:1",
                    run_id="run_package_1",
                )

            def handler(_context: WorkerJobContext) -> JobResult:
                raise RuntimeError("message potentiellement sensible")

            worker = LocalWorker(
                database,
                {"package_final": handler},
                worker_id="worker-a",
                lease_seconds=60,
            )
            result = worker.run_once()

            with database.session() as repositories:
                lot_after = repositories.lots.get_required(lot["id"])
                job = repositories.jobs.get_required(queued.job["id"])
                step = repositories.steps.get_by_lot_key(lot["id"], "package_final")
                problems = repositories.problems.list_for_lot(lot["id"])

            self.assertEqual(result.outcome, "failed")
            self.assertEqual(lot_after["status"], "echoue")
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["error_code"], "RuntimeError")
            self.assertEqual(job["error_message"], "RuntimeError")
            self.assertEqual(step["status"], "echoue")
            self.assertEqual(problems[0]["code"], "SIRCOM_WORKER_UNEXPECTED_ERROR")
            self.assertNotIn("message potentiellement sensible", str(problems))


def migrated_database(tmp: str) -> Database:
    database = Database(Path(tmp) / "sircom.sqlite3")
    database.migrate()
    return database


if __name__ == "__main__":
    unittest.main()
