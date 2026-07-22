from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.database import Database
from sircom2026.invalidation import (
    RetryNotAllowedError,
    downstream_step_keys,
    fingerprint_payload,
    record_human_validation_snapshot,
    record_input_change,
    retry_step,
    step_input_fingerprint,
)
from sircom2026.lots import create_lot_with_steps
from sircom2026.state import complete_step, fail_step


class InvalidationContractTest(unittest.TestCase):
    def test_dag_is_centralized_and_fingerprints_are_canonical(self) -> None:
        self.assertEqual(
            downstream_step_keys("mapping"),
            (
                "fusion_multi_onglets",
                "normalisation_contenu",
                "tri_region_departement",
                "verification_csv_indesign",
                "previsualisation_csv",
                "matching_images",
                "rapports",
                "package_final",
            ),
        )

        first = fingerprint_payload(
            {"version": 1, "rules": {"mapping": "v1"}, "columns": ["B_nom", "C_label"]}
        )
        second = fingerprint_payload(
            {"columns": ["B_nom", "C_label"], "rules": {"mapping": "v1"}, "version": 1}
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertEqual(downstream_step_keys("package_final"), ())
        self.assertEqual(
            downstream_step_keys("package_final", include_external=True),
            ("purge_retention",),
        )

    def test_retry_failed_step_enqueues_new_run_and_invalidates_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot retry")
                complete_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    run_id="run_upload_1",
                )
                fail_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    run_id="run_norm_old",
                    code="SIRCOM_NORMALISATION_ERROR",
                    title="Normalisation interrompue",
                    cause="La normalisation a echoue.",
                    action="Relancer l'etape apres correction.",
                )
                complete_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="previsualisation_csv",
                    run_id="run_preview_old",
                )
                artifact = repositories.artifacts.create(
                    lot_id=lot["id"],
                    step_key="previsualisation_csv",
                    run_id="run_preview_old",
                    kind="csv",
                    role="preview",
                    relative_path="lots/lot_retry/artifacts/preview/preview.csv",
                    sha256="a" * 64,
                    size_bytes=42,
                    status="committed",
                )

                first_retry = retry_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    idempotency_key="retry:norm:1",
                    input_payload={
                        "rules_version": "normalisation-v1",
                        "upstream": "run_fusion_1",
                    },
                )
                same_retry = retry_step(
                    repositories,
                    lot_id=lot["id"],
                    step_key="normalisation_contenu",
                    idempotency_key="retry:norm:1",
                    input_payload={
                        "upstream": "run_fusion_1",
                        "rules_version": "normalisation-v1",
                    },
                )

            with database.session() as repositories:
                source = repositories.steps.get_by_lot_key(lot["id"], "normalisation_contenu")
                invalidated = {
                    step["step_key"]: step
                    for step in repositories.steps.list_for_lot(lot["id"])
                    if step["step_key"] in first_retry.invalidated_steps
                }
                obsolete_artifact = repositories.artifacts.get_required(artifact["id"])
                jobs = repositories.connection.execute(
                    """
                    SELECT * FROM jobs
                    WHERE lot_id = ? AND step_key = ?
                    ORDER BY created_at ASC
                    """,
                    (lot["id"], "normalisation_contenu"),
                ).fetchall()
                events = repositories.events.list_for_lot(lot["id"], limit=50)
                problems = repositories.problems.list_for_lot(
                    lot["id"],
                    include_resolved=True,
                )

            self.assertTrue(first_retry.job_created)
            self.assertFalse(same_retry.job_created)
            self.assertEqual(first_retry.job["id"], same_retry.job["id"])
            self.assertEqual(len(jobs), 1)
            self.assertEqual(source["status"], "pret")
            self.assertNotEqual(source["current_run_id"], "run_norm_old")
            self.assertEqual(source["input_fingerprint"], first_retry.input_fingerprint)
            self.assertEqual(source["output_fingerprint"], None)
            self.assertEqual(
                first_retry.invalidated_steps,
                (
                    "tri_region_departement",
                    "verification_csv_indesign",
                    "previsualisation_csv",
                    "matching_images",
                    "rapports",
                    "package_final",
                ),
            )
            self.assertEqual({step["status"] for step in invalidated.values()}, {"invalide"})
            self.assertEqual(
                {step["current_run_id"] for step in invalidated.values()},
                {None},
            )
            self.assertEqual(obsolete_artifact["status"], "obsolete")
            self.assertEqual({problem["status"] for problem in problems}, {"obsolete"})
            self.assertIn("retry.requested", {event["event_type"] for event in events})
            self.assertIn("step.invalidated", {event["event_type"] for event in events})

    def test_input_and_human_decision_changes_invalidate_the_contractual_branches(self) -> None:
        expected = {
            "upload_excel": (
                "diagnostic_excel",
                "mapping",
                "fusion_multi_onglets",
                "normalisation_contenu",
                "tri_region_departement",
                "verification_csv_indesign",
                "previsualisation_csv",
                "matching_images",
                "rapports",
                "package_final",
            ),
            "mapping": (
                "fusion_multi_onglets",
                "normalisation_contenu",
                "tri_region_departement",
                "verification_csv_indesign",
                "previsualisation_csv",
                "matching_images",
                "rapports",
                "package_final",
            ),
            "tri_region_departement": (
                "previsualisation_csv",
                "rapports",
                "package_final",
            ),
            "upload_images": (
                "previsualisation_csv",
                "inspection_images",
                "matching_images",
                "rapports",
                "package_final",
            ),
            "matching_images": (
                "previsualisation_csv",
                "rapports",
                "package_final",
            ),
        }

        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot branches")
                for source_step, expected_downstream in expected.items():
                    self.assertEqual(downstream_step_keys(source_step), expected_downstream)

                excel_change = record_input_change(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_excel",
                    input_payload={
                        "artifact_id": "artifact_excel_1",
                        "rules_version": "upload-excel-v1",
                        "sha256": "b" * 64,
                    },
                    reason="new_excel",
                )
                zip_change = record_input_change(
                    repositories,
                    lot_id=lot["id"],
                    step_key="upload_images",
                    input_payload={
                        "artifact_id": "artifact_zip_1",
                        "rules_version": "zip-images-v1",
                        "sha256": "c" * 64,
                    },
                    reason="new_zip",
                )
                mapping_snapshot = record_human_validation_snapshot(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                    decision_payload={
                        "profile_version": 1,
                        "rules_version": "mapping-v1",
                        "selected_columns": ["B_nom", "C_label"],
                    },
                    run_id="run_mapping_validation_1",
                    reason="mapping_changed",
                )
                mapping_input_fingerprint = step_input_fingerprint(
                    repositories,
                    lot_id=lot["id"],
                    step_key="mapping",
                )
                tri_snapshot = record_human_validation_snapshot(
                    repositories,
                    lot_id=lot["id"],
                    step_key="tri_region_departement",
                    decision_payload={
                        "rules_version": "tri-v1",
                        "sort": ["region", "departement"],
                    },
                    run_id="run_tri_validation_1",
                    reason="tri_changed",
                )
                image_snapshot = record_human_validation_snapshot(
                    repositories,
                    lot_id=lot["id"],
                    step_key="matching_images",
                    decision_payload={
                        "rules_version": "image-bindings-v1",
                        "ambiguous_resolutions": ["image_1"],
                    },
                    run_id="run_matching_validation_1",
                    reason="image_ambiguity_resolved",
                )

            with database.session() as repositories:
                upload_excel = repositories.steps.get_by_lot_key(lot["id"], "upload_excel")
                upload_images = repositories.steps.get_by_lot_key(lot["id"], "upload_images")
                mapping = repositories.steps.get_by_lot_key(lot["id"], "mapping")
                tri = repositories.steps.get_by_lot_key(lot["id"], "tri_region_departement")
                matching = repositories.steps.get_by_lot_key(lot["id"], "matching_images")
                event_payloads = [
                    json.loads(event["payload_json"])
                    for event in repositories.events.list_for_lot(lot["id"], limit=100)
                ]

            self.assertEqual(upload_excel["output_fingerprint"], excel_change.source_fingerprint)
            self.assertEqual(upload_images["output_fingerprint"], zip_change.source_fingerprint)
            self.assertEqual(mapping["input_fingerprint"], mapping_input_fingerprint)
            self.assertEqual(mapping["output_fingerprint"], mapping_snapshot.output_fingerprint)
            self.assertEqual(tri["output_fingerprint"], tri_snapshot.output_fingerprint)
            self.assertEqual(matching["output_fingerprint"], image_snapshot.output_fingerprint)
            self.assertNotIn("B_nom", str(event_payloads))
            self.assertNotIn("image_1", str(event_payloads))

    def test_retry_is_refused_for_deleted_or_non_retryable_lot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot refuse")

                with self.assertRaises(RetryNotAllowedError):
                    retry_step(
                        repositories,
                        lot_id=lot["id"],
                        step_key="diagnostic_excel",
                        idempotency_key="retry:diag:not-ready",
                    )

                repositories.lots.mark_deleted(lot["id"])
                with self.assertRaises(RetryNotAllowedError):
                    retry_step(
                        repositories,
                        lot_id=lot["id"],
                        step_key="diagnostic_excel",
                        idempotency_key="retry:diag:deleted",
                    )

    def test_retry_is_refused_for_human_validation_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = migrated_database(tmp)
            with database.transaction() as repositories:
                lot = create_lot_with_steps(repositories, title="Lot human retry")
                mapping = repositories.steps.get_by_lot_key(lot["id"], "mapping")
                if mapping is None:
                    self.fail("Expected mapping step to exist.")
                repositories.steps.update_status(mapping["id"], "invalide")

                with self.assertRaises(RetryNotAllowedError):
                    retry_step(
                        repositories,
                        lot_id=lot["id"],
                        step_key="mapping",
                        idempotency_key="retry:mapping:not-worker",
                    )

            with database.session() as repositories:
                jobs_count = repositories.connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM jobs
                    WHERE lot_id = ? AND step_key = ?
                    """,
                    (lot["id"], "mapping"),
                ).fetchone()[0]

            self.assertEqual(jobs_count, 0)

    def test_retry_route_returns_structured_result_and_reuses_idempotency_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = load_settings(
                {
                    "SIRCOM_DATA_DIR": str(Path(tmp) / "data"),
                    "SIRCOM_SQLITE_PATH": str(Path(tmp) / "data" / "sircom.sqlite3"),
                    "SIRCOM_DISK_FREE_MIN_MB": "0",
                }
            )
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot retry API"}).json()["lot"]["id"]
            database = Database(
                settings.sqlite_path,
                busy_timeout_ms=settings.sqlite_busy_timeout_ms,
            )
            with database.transaction() as repositories:
                fail_step(
                    repositories,
                    lot_id=lot_id,
                    step_key="diagnostic_excel",
                    run_id="run_diag_old",
                    code="SIRCOM_DIAGNOSTIC_ERROR",
                    title="Diagnostic interrompu",
                    cause="Le diagnostic a echoue.",
                    action="Relancer le diagnostic.",
                )

            ui_response = client.get(f"/lots/{lot_id}")
            first_response = client.post(
                f"/api/lots/{lot_id}/retry",
                json={"step_key": "diagnostic_excel"},
                headers={"X-Idempotency-Key": "retry-api-diag-1"},
            )
            second_response = client.post(
                f"/api/lots/{lot_id}/retry",
                json={"step_key": "diagnostic_excel"},
                headers={"X-Idempotency-Key": "retry-api-diag-1"},
            )
            conflict_response = client.post(
                f"/api/lots/{lot_id}/retry",
                json={"step_key": "upload_excel"},
                headers={"X-Idempotency-Key": "retry-api-upload-1"},
            )

        self.assertEqual(ui_response.status_code, 200)
        self.assertIn("Relancer", ui_response.text)
        self.assertIn('data-retry-step-key="diagnostic_excel"', ui_response.text)
        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(second_response.status_code, 202)
        self.assertEqual(conflict_response.status_code, 409)
        self.assertEqual(first_response.json()["job"]["id"], second_response.json()["job"]["id"])
        self.assertTrue(first_response.json()["job"]["created"])
        self.assertFalse(second_response.json()["job"]["created"])
        self.assertEqual(
            first_response.json()["invalidated_steps"],
            [
                "mapping",
                "fusion_multi_onglets",
                "normalisation_contenu",
                "tri_region_departement",
                "verification_csv_indesign",
                "previsualisation_csv",
                "matching_images",
                "rapports",
                "package_final",
            ],
        )
        self.assertEqual(
            conflict_response.json()["error"]["code"],
            "SIRCOM_RETRY_NOT_ALLOWED",
        )


def migrated_database(tmp: str) -> Database:
    database = Database(Path(tmp) / "sircom.sqlite3")
    database.migrate()
    return database


if __name__ == "__main__":
    unittest.main()
