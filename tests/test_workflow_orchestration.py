from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from sircom2026.app import create_app
from sircom2026.lots import V1_STEPS
from sircom2026.pipeline import (
    V1_EXTERNAL_STEP_KEYS,
    V1_INVALIDATION_DAG,
    V1_WORKER_STEP_KEYS,
)
from tests.test_reports import (
    create_reports_workbook,
    excel_file,
    image_bytes,
    image_zip_file,
    make_settings,
    mapping_submission,
    run_until_step,
    run_until_steps,
    zip_bytes,
)


DONE_STATUSES = {"termine", "termine_avec_alertes"}


class WorkflowOrchestrationTest(unittest.TestCase):
    def test_v1_dag_matches_declared_workflow_steps(self) -> None:
        declared_steps = tuple(step.key for step in V1_STEPS)
        declared_step_keys = set(declared_steps)
        expected_edges = {
            ("upload_excel", "diagnostic_excel"),
            ("diagnostic_excel", "mapping"),
            ("mapping", "fusion_multi_onglets"),
            ("fusion_multi_onglets", "normalisation_contenu"),
            ("normalisation_contenu", "tri_region_departement"),
            ("normalisation_contenu", "verification_csv_indesign"),
            ("normalisation_contenu", "matching_images"),
            ("tri_region_departement", "previsualisation_csv"),
            ("verification_csv_indesign", "previsualisation_csv"),
            ("previsualisation_csv", "rapports"),
            ("previsualisation_csv", "package_final"),
            ("upload_images", "inspection_images"),
            ("inspection_images", "matching_images"),
            ("matching_images", "previsualisation_csv"),
            ("matching_images", "rapports"),
            ("matching_images", "package_final"),
            ("rapports", "package_final"),
            ("package_final", "purge_retention"),
        }
        actual_edges = {
            (source, child)
            for source, children in V1_INVALIDATION_DAG.items()
            for child in children
        }

        self.assertEqual(
            set(V1_INVALIDATION_DAG),
            declared_step_keys | set(V1_EXTERNAL_STEP_KEYS),
        )
        self.assertEqual(actual_edges, expected_edges)
        self.assertTrue(set(V1_WORKER_STEP_KEYS).issubset(declared_step_keys))

    def test_full_workflow_reaches_every_internal_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "workflow.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot workflow"}).json()["lot"][
                "id"
            ]
            initial_lot = client.get(f"/api/lots/{lot_id}").json()["lot"]

            upload_images = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file(
                    zip_bytes(
                        [
                            ("photo-produit-secret.png", image_bytes()),
                            ("plan-secret-client.png", image_bytes()),
                        ]
                    )
                ),
                headers={"X-Idempotency-Key": "workflow-images"},
            )
            inspection = run_until_step(settings, "inspection_images")
            upload_excel = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "workflow-excel"},
            )
            diagnostic = run_until_step(settings, "diagnostic_excel")
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "workflow-mapping"},
            )
            fusion = run_until_step(settings, "fusion_multi_onglets")
            normalization = run_until_step(settings, "normalisation_contenu")
            downstream = run_until_steps(
                settings,
                {"verification_csv_indesign", "matching_images"},
            )
            validate_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "workflow-sort"},
            )
            validate_preview = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "workflow-preview"},
            )
            reports = run_until_step(settings, "rapports")
            package_without_warning_acceptance = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": False},
                headers={"X-Idempotency-Key": "workflow-package-no-warnings"},
            )
            package_request = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": True},
                headers={"X-Idempotency-Key": "workflow-package"},
            )
            package = run_until_step(settings, "package_final")
            package_response = client.get(f"/api/lots/{lot_id}/package")
            final_lot = client.get(f"/api/lots/{lot_id}").json()["lot"]

        self.assertEqual(
            [step["key"] for step in initial_lot["steps"]],
            [step.key for step in V1_STEPS],
        )
        self.assertEqual(upload_images.status_code, 202, upload_images.text)
        self.assertEqual(upload_excel.status_code, 202, upload_excel.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        self.assertEqual(validate_sort.status_code, 200, validate_sort.text)
        self.assertEqual(validate_preview.status_code, 200, validate_preview.text)
        self.assertEqual(package_without_warning_acceptance.status_code, 409)
        self.assertEqual(
            package_without_warning_acceptance.json()["error"]["code"],
            "SIRCOM_PACKAGE_WARNINGS_DECISION_REQUIRED",
        )
        self.assertEqual(package_request.status_code, 202, package_request.text)
        self.assertEqual(package_response.status_code, 200, package_response.text)

        worker_steps_seen = {
            result.step_key
            for result in (
                inspection,
                diagnostic,
                fusion,
                normalization,
                downstream["verification_csv_indesign"],
                downstream["matching_images"],
                reports,
                package,
            )
        }
        self.assertEqual(worker_steps_seen, set(V1_WORKER_STEP_KEYS))
        for result in (
            inspection,
            diagnostic,
            fusion,
            normalization,
            downstream["verification_csv_indesign"],
            downstream["matching_images"],
            reports,
            package,
        ):
            self.assertEqual(result.outcome, "succeeded")

        final_statuses = {step["key"]: step["status"] for step in final_lot["steps"]}
        for step in V1_STEPS:
            self.assertIn(final_statuses[step.key], DONE_STATUSES, step.key)


if __name__ == "__main__":
    unittest.main()
