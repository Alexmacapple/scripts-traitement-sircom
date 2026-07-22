from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from sircom2026.app import create_app
from sircom2026.artifacts import ArtifactStore
from sircom2026.database import Database
from sircom2026.invalidation import step_input_fingerprint
from sircom2026.lots import V1_STEPS, create_lot_with_steps
from sircom2026.pipeline import V1_WORKER_STEP_KEYS
from sircom2026.worker import enqueue_job
from sircom2026.worker_runner import run_worker_once
from tests.test_package import _prepare_lot_until_reports_without_images
from tests.test_reports import (
    create_reports_workbook,
    excel_file,
    make_settings,
    mapping_submission,
    run_until_step,
)


FAILURE_PATH_COVERAGE = {
    "upload_excel": (
        "tests/test_excel_upload.py",
        "test_invalid_extension_is_rejected_with_structured_error",
    ),
    "diagnostic_excel": (
        "tests/test_workflow_failure_paths.py",
        "SIRCOM_EXCEL_SOURCE_MISSING",
    ),
    "mapping": (
        "tests/test_mapping.py",
        "test_validation_blocks_collisions_and_default_cleaning_handles_accents",
    ),
    "fusion_multi_onglets": (
        "tests/test_workflow_failure_paths.py",
        "SIRCOM_FUSION_MAPPING_NOT_VALIDATED",
    ),
    "normalisation_contenu": (
        "tests/test_workflow_failure_paths.py",
        "SIRCOM_NORMALIZATION_FUSION_NOT_READY",
    ),
    "tri_region_departement": (
        "tests/test_sorting.py",
        "test_ambiguous_sort_detection_does_not_auto_select_columns",
    ),
    "verification_csv_indesign": (
        "tests/test_workflow_failure_paths.py",
        "SIRCOM_CSV_NORMALIZATION_NOT_READY",
    ),
    "previsualisation_csv": (
        "tests/test_csv_preview.py",
        "test_export_refuses_non_current_or_unreadable_final_artifact",
    ),
    "upload_images": (
        "tests/test_image_upload.py",
        "test_invalid_zip_signature_is_rejected",
    ),
    "inspection_images": (
        "tests/test_workflow_failure_paths.py",
        "SIRCOM_IMAGE_ZIP_SOURCE_MISSING",
    ),
    "matching_images": (
        "tests/test_workflow_failure_paths.py",
        "SIRCOM_IMAGE_MATCHING_NORMALIZATION_MISSING",
    ),
    "rapports": (
        "tests/test_workflow_failure_paths.py",
        "test_reports_recover_after_current_preview_is_revalidated",
    ),
    "package_final": (
        "tests/test_workflow_failure_paths.py",
        "test_package_worker_blocks_when_report_artifact_disappears_after_enqueue",
    ),
}

MISSING_PREREQUISITE_WORKER_CODES = {
    "diagnostic_excel": "SIRCOM_EXCEL_SOURCE_MISSING",
    "fusion_multi_onglets": "SIRCOM_FUSION_MAPPING_NOT_VALIDATED",
    "normalisation_contenu": "SIRCOM_NORMALIZATION_FUSION_NOT_READY",
    "verification_csv_indesign": "SIRCOM_CSV_NORMALIZATION_NOT_READY",
    "inspection_images": "SIRCOM_IMAGE_ZIP_SOURCE_MISSING",
    "matching_images": "SIRCOM_IMAGE_MATCHING_NORMALIZATION_MISSING",
    "rapports": "SIRCOM_REPORTS_PREREQUISITE_MISSING",
    "package_final": "SIRCOM_PACKAGE_PREREQUISITE_MISSING",
}


class WorkflowFailurePathsTest(unittest.TestCase):
    def test_failure_path_matrix_covers_every_declared_workflow_step(self) -> None:
        declared_step_keys = {step.key for step in V1_STEPS}
        self.assertEqual(set(FAILURE_PATH_COVERAGE), declared_step_keys)

        repo_root = Path(__file__).resolve().parents[1]
        for step_key, (relative_path, marker) in FAILURE_PATH_COVERAGE.items():
            with self.subTest(step_key=step_key):
                source = repo_root / relative_path
                self.assertTrue(source.exists(), relative_path)
                self.assertIn(marker, source.read_text(encoding="utf-8"))

    def test_worker_steps_block_on_missing_current_prerequisite(self) -> None:
        self.assertEqual(
            set(MISSING_PREREQUISITE_WORKER_CODES),
            set(V1_WORKER_STEP_KEYS),
        )
        for step_key, expected_code in MISSING_PREREQUISITE_WORKER_CODES.items():
            with self.subTest(step_key=step_key):
                with tempfile.TemporaryDirectory() as tmp:
                    settings = make_settings(Path(tmp))
                    database = _migrated_database(settings)
                    with database.transaction() as repositories:
                        lot = create_lot_with_steps(
                            repositories,
                            title=f"Lot prérequis {step_key}",
                        )
                        input_fingerprint = step_input_fingerprint(
                            repositories,
                            lot_id=lot["id"],
                            step_key=step_key,
                        )
                        enqueue_job(
                            repositories,
                            lot_id=lot["id"],
                            step_key=step_key,
                            idempotency_key=f"missing-prerequisite:{step_key}",
                            input_fingerprint=input_fingerprint,
                        )

                    result = run_worker_once(settings=settings)

                    with database.session() as repositories:
                        lot_after = repositories.lots.get_required(lot["id"])
                        step_after = repositories.steps.get_by_lot_key(lot["id"], step_key)
                        problems = repositories.problems.list_for_lot(lot["id"])

                self.assertEqual(result.outcome, "succeeded")
                self.assertEqual(result.step_key, step_key)
                self.assertIsNotNone(step_after)
                self.assertEqual(step_after["status"], "bloque")
                self.assertEqual(lot_after["status"], "bloque")
                self.assertIn(expected_code, {problem["code"] for problem in problems})

    def test_reports_recover_after_current_preview_is_revalidated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "reports-retry.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = _prepare_lot_until_preview_without_images(
                client,
                settings,
                workbook_path,
            )
            preview_path = _current_artifact_path(
                settings,
                lot_id=lot_id,
                step_key="previsualisation_csv",
                role="preview",
            )
            preview_path.unlink()

            blocked_reports = run_worker_once(settings=settings)
            revalidate_preview = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "reports-retry-preview-regenerated"},
            )
            recovered_reports = run_worker_once(settings=settings)

            with _database(settings).session() as repositories:
                lot = repositories.lots.get_required(lot_id)
                reports_step = repositories.steps.get_by_lot_key(lot_id, "rapports")
                package_step = repositories.steps.get_by_lot_key(lot_id, "package_final")
                problems = repositories.problems.list_for_lot(
                    lot_id,
                    include_resolved=True,
                )

        prerequisite_problems = [
            problem
            for problem in problems
            if problem["code"] == "SIRCOM_REPORTS_PREREQUISITE_MISSING"
        ]
        self.assertEqual(blocked_reports.outcome, "succeeded")
        self.assertEqual(blocked_reports.step_key, "rapports")
        self.assertEqual(revalidate_preview.status_code, 200, revalidate_preview.text)
        self.assertIn("rapports", revalidate_preview.json()["invalidated_steps"])
        self.assertIn("package_final", revalidate_preview.json()["invalidated_steps"])
        self.assertEqual(recovered_reports.outcome, "succeeded")
        self.assertEqual(recovered_reports.step_key, "rapports")
        self.assertIsNotNone(reports_step)
        self.assertIn(reports_step["status"], {"termine", "termine_avec_alertes"})
        self.assertIsNotNone(package_step)
        self.assertEqual(package_step["status"], "action_requise")
        self.assertEqual(lot["status"], "action_requise")
        self.assertTrue(prerequisite_problems)
        self.assertEqual({problem["status"] for problem in prerequisite_problems}, {"obsolete"})

    def test_package_worker_blocks_when_report_artifact_disappears_after_enqueue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "package-missing-report.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = _prepare_lot_until_reports_without_images(
                client,
                settings,
                workbook_path,
            )
            enqueue_package = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": True},
                headers={"X-Idempotency-Key": "package-missing-report"},
            )
            report_path = _current_artifact_path(
                settings,
                lot_id=lot_id,
                step_key="rapports",
                role="rapport-metier",
            )
            report_path.unlink()

            package = run_worker_once(settings=settings)
            package_response = client.get(f"/api/lots/{lot_id}/package")

            with _database(settings).session() as repositories:
                lot = repositories.lots.get_required(lot_id)
                package_step = repositories.steps.get_by_lot_key(lot_id, "package_final")
                problems = repositories.problems.list_for_lot(lot_id)

        self.assertEqual(enqueue_package.status_code, 202, enqueue_package.text)
        self.assertEqual(package.outcome, "succeeded")
        self.assertEqual(package.step_key, "package_final")
        self.assertEqual(package_response.status_code, 409)
        self.assertIsNotNone(package_step)
        self.assertEqual(package_step["status"], "bloque")
        self.assertEqual(lot["status"], "bloque")
        self.assertIn(
            "SIRCOM_PACKAGE_PREREQUISITE_MISSING",
            {problem["code"] for problem in problems},
        )


def _prepare_lot_until_preview_without_images(
    client: TestClient,
    settings,
    workbook_path: Path,
) -> str:
    lot_id = client.post("/api/lots", json={"title": "Lot reports retry"}).json()["lot"]["id"]
    upload_excel = client.post(
        f"/api/lots/{lot_id}/excel",
        files=excel_file(workbook_path),
        headers={"X-Idempotency-Key": "reports-retry-excel"},
    )
    diagnostic = run_until_step(settings, "diagnostic_excel")
    mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
    validate_mapping = client.post(
        f"/api/lots/{lot_id}/mapping/validate",
        json=mapping_submission(mapping),
        headers={"X-Idempotency-Key": "reports-retry-mapping"},
    )
    fusion = run_until_step(settings, "fusion_multi_onglets")
    normalization = run_until_step(settings, "normalisation_contenu")
    csv_contract = run_until_step(settings, "verification_csv_indesign")
    validate_sort = client.post(
        f"/api/lots/{lot_id}/tri/validate",
        json={"decision": "tri_region_departement"},
        headers={"X-Idempotency-Key": "reports-retry-sort"},
    )
    validate_preview = client.post(
        f"/api/lots/{lot_id}/csv/preview/validate",
        headers={"X-Idempotency-Key": "reports-retry-preview"},
    )

    if upload_excel.status_code != 202:
        raise AssertionError(upload_excel.text)
    if validate_mapping.status_code != 200:
        raise AssertionError(validate_mapping.text)
    if validate_sort.status_code != 200:
        raise AssertionError(validate_sort.text)
    if validate_preview.status_code != 200:
        raise AssertionError(validate_preview.text)
    for result in (diagnostic, fusion, normalization, csv_contract):
        if result.outcome != "succeeded":
            raise AssertionError(result)
    return lot_id


def _current_artifact_path(settings, *, lot_id: str, step_key: str, role: str) -> Path:
    with _database(settings).session() as repositories:
        step = repositories.steps.get_by_lot_key(lot_id, step_key)
        if step is None or not step["current_run_id"]:
            raise AssertionError(f"{step_key} has no current run.")
        artifact = repositories.artifacts.get_for_step_run_role(
            lot_id=lot_id,
            step_key=step_key,
            run_id=step["current_run_id"],
            role=role,
        )
        if artifact is None:
            raise AssertionError(f"{step_key}:{role} artifact is missing.")
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    return store.path_for(artifact["relative_path"])


def _database(settings) -> Database:
    return Database(
        settings.sqlite_path,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )


def _migrated_database(settings) -> Database:
    database = _database(settings)
    database.migrate()
    return database


if __name__ == "__main__":
    unittest.main()
