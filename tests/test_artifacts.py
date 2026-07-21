from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from sircom2026.api.security import (
    AccessAction,
    AccessDecision,
    AccessResource,
    ActorContext,
)
from sircom2026.app import create_app
from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError, sha256_file
from sircom2026.config import load_settings
from sircom2026.database import Database
from sircom2026.lots import create_lot_with_steps


def make_settings(tmpdir: Path):
    return load_settings(
        {
            "SIRCOM_DATA_DIR": str(tmpdir / "data"),
            "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
            "SIRCOM_DISK_FREE_MIN_MB": "0",
            "SIRCOM_ARTIFACT_PENDING_TTL_SECONDS": "1",
        }
    )


@dataclass
class RecordingPolicy:
    denied_actions: set[AccessAction] = field(default_factory=set)
    decisions: list[tuple[ActorContext, AccessAction, AccessResource]] = field(default_factory=list)

    def authorize(
        self,
        actor: ActorContext,
        action: AccessAction,
        resource: AccessResource,
    ) -> AccessDecision:
        self.decisions.append((actor, action, resource))
        if action in self.denied_actions:
            return AccessDecision.deny("denied")
        return AccessDecision.allow()


def create_active_job(
    repositories,
    *,
    lot_id: str,
    step_key: str,
    run_id: str,
):
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if step is not None:
        repositories.steps.update_status(step["id"], "en_cours", run_id=run_id)
    job = repositories.jobs.create(
        lot_id=lot_id,
        step_key=step_key,
        status="running",
        run_id=run_id,
        idempotency_key=f"{step_key}:{run_id}",
    )
    repositories.connection.execute(
        """
        UPDATE jobs
        SET lease_owner = ?, lease_version = ?, lease_until = ?
        WHERE id = ?
        """,
        (
            "test-worker",
            1,
            (
                datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=5)
            ).isoformat(),
            job["id"],
        ),
    )
    return repositories.jobs.get_required(job["id"])


class ArtifactStoreTest(unittest.TestCase):
    def test_put_temp_then_commit_writes_atomically_and_persists_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot artefact")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                )
                artifact = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                    kind="excel",
                    role="source",
                    filename="../source.xlsx",
                    content=b"contenu test",
                    metadata={"format": "xlsx"},
                    lease_version=1,
                )
                refreshed_lot = repositories.lots.get_required(lot["id"])

            artifact_path = store.path_for(artifact["relative_path"])
            temp_path = settings.data_dir / "lots" / lot["id"] / "tmp" / f"{artifact['id']}.part"
            self.assertEqual(artifact["status"], "committed")
            self.assertEqual(artifact["kind"], "excel")
            self.assertEqual(artifact["role"], "source")
            self.assertEqual(artifact["size_bytes"], len(b"contenu test"))
            self.assertEqual(artifact["sha256"], sha256_file(artifact_path))
            self.assertEqual(json.loads(artifact["metadata_json"]), {"format": "xlsx"})
            self.assertTrue(artifact_path.is_file())
            self.assertFalse(temp_path.exists())
            self.assertEqual(artifact_path.read_bytes(), b"contenu test")
            self.assertFalse(Path(artifact["relative_path"]).is_absolute())
            self.assertNotIn(str(settings.data_dir), artifact["relative_path"])
            self.assertNotIn("source", artifact["relative_path"])
            self.assertEqual(refreshed_lot["artifacts_count"], 1)
            self.assertEqual(refreshed_lot["bytes_artifacts"], len(b"contenu test"))

    def test_pending_artifact_after_failure_is_not_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot pending")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                )
                artifact = store.create_pending(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                    kind="excel",
                    role="source",
                    filename="source.xlsx",
                    content=b"contenu non publie",
                    lease_version=1,
                )
                temp_path = (
                    settings.data_dir / "lots" / lot["id"] / "tmp" / f"{artifact['id']}.part"
                )

                with self.assertRaises(ArtifactUnavailableError):
                    store.open_for_read(
                        repositories,
                        lot_id=lot["id"],
                        artifact_id=artifact["id"],
                    )

            self.assertEqual(artifact["status"], "pending")
            self.assertTrue(temp_path.is_file())
            self.assertFalse(store.path_for(artifact["relative_path"]).exists())

    def test_run_without_active_job_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot sans job")
                with self.assertRaises(ArtifactUnavailableError):
                    store.create_pending(
                        repositories,
                        lot_id=lot["id"],
                        step_key="upload_excel",
                        run_id="run_unknown",
                        kind="excel",
                        role="source",
                        filename="source.xlsx",
                        content=b"contenu",
                        lease_version=1,
                    )
                event = repositories.connection.execute(
                    "SELECT event_type FROM evenements WHERE event_type = ?",
                    ("artifact.commit_rejected",),
                ).fetchone()

            self.assertIsNotNone(event)

    def test_previous_step_run_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot ancien run")
                step = repositories.steps.get_by_lot_key(lot["id"], "upload_excel")
                if step is None:
                    self.fail("Expected upload_excel step to exist.")
                repositories.steps.update_status(step["id"], "en_cours", run_id="run_new")
                repositories.jobs.create(
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    status="running",
                    run_id="run_old",
                    idempotency_key="upload_excel:run_old",
                )
                repositories.connection.execute(
                    """
                    UPDATE jobs
                    SET lease_owner = ?, lease_version = ?, lease_until = ?
                    WHERE run_id = ?
                    """,
                    (
                        "test-worker",
                        1,
                        (
                            datetime.now(UTC).replace(microsecond=0)
                            + timedelta(minutes=5)
                        ).isoformat(),
                        "run_old",
                    ),
                )

                with self.assertRaises(ArtifactUnavailableError):
                    store.create_pending(
                        repositories,
                        lot_id=lot["id"],
                        step_key="upload_excel",
                        run_id="run_old",
                        kind="excel",
                        role="source",
                        filename="source.xlsx",
                        content=b"source",
                        lease_version=1,
                    )

    def test_wrong_lease_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot lease")
                job = create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                repositories.connection.execute(
                    "UPDATE jobs SET lease_version = ? WHERE id = ?",
                    (2, job["id"]),
                )

                with self.assertRaises(ArtifactUnavailableError):
                    store.create_pending(
                        repositories,
                        lot_id=lot["id"],
                        step_key="upload_excel",
                        run_id="run_1",
                        kind="excel",
                        role="source",
                        filename="source.xlsx",
                        content=b"source",
                        lease_version=1,
                    )

    def test_running_job_without_lease_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot sans lease")
                step = repositories.steps.get_by_lot_key(lot["id"], "upload_excel")
                if step is None:
                    self.fail("Expected upload_excel step to exist.")
                repositories.steps.update_status(step["id"], "en_cours", run_id="run_1")
                repositories.jobs.create(
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    status="running",
                    run_id="run_1",
                    idempotency_key="upload_excel:run_1",
                )

                with self.assertRaises(ArtifactUnavailableError):
                    store.create_pending(
                        repositories,
                        lot_id=lot["id"],
                        step_key="upload_excel",
                        run_id="run_1",
                        kind="excel",
                        role="source",
                        filename="source.xlsx",
                        content=b"source",
                        lease_version=0,
                    )

    def test_unsafe_artifact_id_cannot_escape_temporary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot chemin")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                with self.assertRaises(ValueError):
                    store.create_pending(
                        repositories,
                        lot_id=lot["id"],
                        step_key="upload_excel",
                        run_id="run_1",
                        kind="excel",
                        role="source",
                        filename="source.xlsx",
                        content=b"source",
                        artifact_id="../escape",
                        lease_version=1,
                    )

            self.assertFalse((settings.data_dir / "lots" / lot["id"] / "escape.part").exists())

    def test_database_failure_removes_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot erreur")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    run_id="run_2",
                )
                store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                    kind="text",
                    role="source",
                    filename="source.txt",
                    content=b"source",
                    artifact_id="artifact_fixed",
                    lease_version=1,
                )

                with self.assertRaises(sqlite3.IntegrityError):
                    store.create_pending(
                        repositories,
                        lot_id=lot["id"],
                        step_key="diagnostic_excel",
                        run_id="run_2",
                        kind="json",
                        role="duplicate",
                        filename="duplicate.json",
                        content=b"duplicate",
                        artifact_id="artifact_fixed",
                        lease_version=1,
                    )

            temp_path = (
                settings.data_dir / "lots" / lot["id"] / "tmp" / "artifact_fixed.part"
            )
            self.assertFalse(temp_path.exists())

    def test_reconcile_detects_orphan_missing_hash_mismatch_and_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir, pending_ttl_seconds=1)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot reconcile")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    run_id="run_2",
                )
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    run_id="run_3",
                )
                missing = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                    kind="excel",
                    role="missing",
                    filename="missing.xlsx",
                    content=b"missing",
                    lease_version=1,
                )
                mismatch = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    run_id="run_2",
                    kind="json",
                    role="mismatch",
                    filename="diagnostic.json",
                    content=b"expected",
                    lease_version=1,
                )
                pending = store.create_pending(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    run_id="run_3",
                    kind="json",
                    role="pending",
                    filename="mapping.json",
                    content=b"pending",
                    lease_version=1,
                )
                repositories.connection.execute(
                    "UPDATE artefacts SET created_at = ? WHERE id = ?",
                    ("2000-01-01T00:00:00+00:00", pending["id"]),
                )

            store.path_for(missing["relative_path"]).unlink()
            store.path_for(mismatch["relative_path"]).write_bytes(b"tampered")
            orphan_path = settings.data_dir / "lots" / lot["id"] / "artifacts" / "orphan.bin"
            orphan_path.parent.mkdir(parents=True, exist_ok=True)
            orphan_path.write_bytes(b"orphan")
            orphan_temp_path = settings.data_dir / "lots" / lot["id"] / "tmp" / "orphan.part"
            orphan_temp_path.parent.mkdir(parents=True, exist_ok=True)
            orphan_temp_path.write_bytes(b"orphan temp")

            with database.transaction() as repositories:
                report = store.reconcile(repositories)
                missing_after = repositories.artifacts.get_required(missing["id"])
                mismatch_after = repositories.artifacts.get_required(mismatch["id"])
                pending_after = repositories.artifacts.get_required(pending["id"])
                refreshed_lot = repositories.lots.get_required(lot["id"])
                problem_codes = [
                    row["code"]
                    for row in repositories.connection.execute(
                        "SELECT code FROM problemes ORDER BY code"
                    ).fetchall()
                ]

            self.assertEqual(
                report.to_dict(),
                {
                    "orphan_files": 2,
                    "missing_files": 1,
                    "hash_mismatches": 1,
                    "expired_pending": 1,
                },
            )
            self.assertEqual(missing_after["status"], "obsolete")
            self.assertEqual(mismatch_after["status"], "obsolete")
            self.assertEqual(pending_after["status"], "quarantined")
            self.assertFalse(orphan_path.exists())
            self.assertFalse(orphan_temp_path.exists())
            self.assertTrue((settings.data_dir / "quarantine" / "orphans").is_dir())
            self.assertTrue((settings.data_dir / "quarantine" / "pending").is_dir())
            self.assertEqual(
                problem_codes,
                [
                    "SIRCOM_ARTIFACT_FILE_MISSING",
                    "SIRCOM_ARTIFACT_HASH_MISMATCH",
                ],
            )
            self.assertEqual(refreshed_lot["artifacts_count"], 0)
            self.assertEqual(refreshed_lot["bytes_artifacts"], 0)


class ArtifactDownloadApiTest(unittest.TestCase):
    def test_startup_expires_stale_job_leases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot lease expire")
                job = create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                repositories.connection.execute(
                    "UPDATE jobs SET lease_until = ? WHERE id = ?",
                    ("2000-01-01T00:00:00+00:00", job["id"]),
                )

            with TestClient(create_app(settings)) as client:
                response = client.get("/health")

            self.assertEqual(response.status_code, 200)
            with database.session() as repositories:
                expired_job = repositories.jobs.get_required(job["id"])

            self.assertEqual(expired_job["status"], "expired")

    def test_startup_reconciles_committed_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)

            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot startup")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                artifact = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                    kind="excel",
                    role="source",
                    filename="source.xlsx",
                    content=b"source",
                    lease_version=1,
                )

            store.path_for(artifact["relative_path"]).unlink()

            with TestClient(create_app(settings)) as client:
                response = client.get("/health")

            self.assertEqual(response.status_code, 200)
            with database.session() as repositories:
                reconciled = repositories.artifacts.get_required(artifact["id"])
                problem = repositories.connection.execute(
                    "SELECT code FROM problemes WHERE lot_id = ?",
                    (lot["id"],),
                ).fetchone()

            self.assertEqual(reconciled["status"], "obsolete")
            self.assertEqual(problem["code"], "SIRCOM_ARTIFACT_FILE_MISSING")

    def test_download_committed_artifact_by_id_without_exposing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot download")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                artifact = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                    kind="text",
                    role="rapport",
                    filename="rapport.txt",
                    content=b"rapport export",
                    lease_version=1,
                )

            response = client.get(f"/api/lots/{lot['id']}/downloads/{artifact['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"rapport export")
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertNotIn(str(settings.data_dir), str(response.headers))
        self.assertNotIn(artifact["relative_path"], str(response.headers))

    def test_download_missing_file_records_problem_before_hidden_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot missing")
                create_active_job(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                )
                artifact = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                    kind="excel",
                    role="source",
                    filename="source.xlsx",
                    content=b"source",
                    lease_version=1,
                )

            store.path_for(artifact["relative_path"]).unlink()
            response = client.get(f"/api/lots/{lot['id']}/downloads/{artifact['id']}")

            with database.session() as repositories:
                artifact_after = repositories.artifacts.get_required(artifact["id"])
                problem = repositories.connection.execute(
                    "SELECT code FROM problemes WHERE lot_id = ?",
                    (lot["id"],),
                ).fetchone()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(artifact_after["status"], "obsolete")
        self.assertEqual(problem["code"], "SIRCOM_ARTIFACT_FILE_MISSING")

    def test_download_hidden_404_is_indistinguishable_for_non_current_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            database = Database(settings.sqlite_path)
            database.migrate()
            store = ArtifactStore(settings.data_dir)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot courant")
                other_lot = create_lot_with_steps(repositories, title="Autre lot")
                for step_key, run_id in (
                    ("upload_excel", "run_1"),
                    ("diagnostic_excel", "run_2"),
                    ("mapping", "run_3"),
                    ("fusion_multi_onglets", "run_4"),
                ):
                    create_active_job(
                        repositories,
                        lot_id=lot["id"],
                        step_key=step_key,
                        run_id=run_id,
                    )
                committed = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_1",
                    kind="text",
                    role="source",
                    filename="source.txt",
                    content=b"source",
                    lease_version=1,
                )
                pending = store.create_pending(
                    repositories,
                    lot_id=lot["id"],
                    step_key="diagnostic_excel",
                    run_id="run_2",
                    kind="json",
                    role="pending",
                    filename="pending.json",
                    content=b"pending",
                    lease_version=1,
                )
                obsolete = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    run_id="run_3",
                    kind="json",
                    role="obsolete",
                    filename="obsolete.json",
                    content=b"obsolete",
                    lease_version=1,
                )
                deleted = store.put_temp_then_commit(
                    repositories,
                    lot_id=lot["id"],
                    step_key="fusion_multi_onglets",
                    run_id="run_4",
                    kind="json",
                    role="deleted",
                    filename="deleted.json",
                    content=b"deleted",
                    lease_version=1,
                )
                repositories.artifacts.update_status(obsolete["id"], "obsolete")
                repositories.artifacts.update_status(deleted["id"], "deleted")
                repositories.lots.refresh_artifact_counters(lot["id"])

            urls = [
                f"/api/lots/{lot['id']}/downloads/artifact_missing",
                f"/api/lots/{other_lot['id']}/downloads/{committed['id']}",
                f"/api/lots/{lot['id']}/downloads/{pending['id']}",
                f"/api/lots/{lot['id']}/downloads/{obsolete['id']}",
                f"/api/lots/{lot['id']}/downloads/{deleted['id']}",
            ]
            responses = [client.get(url) for url in urls]

        payloads = [response.json() for response in responses]
        self.assertTrue(all(response.status_code == 404 for response in responses))
        self.assertTrue(all(payload == payloads[0] for payload in payloads))
        self.assertEqual(
            payloads[0],
            {
                "error": {
                    "code": "SIRCOM_ARTIFACT_NOT_FOUND",
                    "message": "Artefact introuvable.",
                }
            },
        )
        serialized = str(payloads)
        self.assertNotIn(committed["id"], serialized)
        self.assertNotIn(lot["id"], serialized)
        self.assertNotIn(other_lot["id"], serialized)

    def test_download_route_verifies_access_policy(self) -> None:
        policy = RecordingPolicy({AccessAction.ARTIFACT_DOWNLOAD})
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings, access_policy=policy))

            response = client.get("/api/lots/lot_1/downloads/artifact_1")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(policy.decisions[0][1], AccessAction.ARTIFACT_DOWNLOAD)
        self.assertEqual(policy.decisions[0][2].lot_id, "lot_1")
        self.assertEqual(policy.decisions[0][2].artifact_id, "artifact_1")


if __name__ == "__main__":
    unittest.main()
