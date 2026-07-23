from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from sircom2026.app import create_app
from sircom2026.csv_contract import verify_indesign_csv_bytes
from sircom2026.image_matching import EXPORT_IMAGES_FOLDER
from sircom2026.image_naming import image_id_for_dossier
from sircom2026.lots import V1_STEPS
from sircom2026.pipeline import (
    V1_EXTERNAL_STEP_KEYS,
    V1_INVALIDATION_DAG,
    V1_WORKER_STEP_KEYS,
)
from sircom2026.synthetic_excels import create_synthetic_excels
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
            lot_id = client.post("/api/lots", json={"title": "Lot workflow"}).json()[
                "lot"
            ]["id"]
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

    def test_synthetic_end_to_end_recipe_builds_inspectable_indesign_package(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = create_synthetic_excels(
                tmpdir / "fixtures",
                ["valid_multi_tabs"],
            )["valid_multi_tabs"]
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post(
                "/api/lots",
                json={"title": "Lot recette synthétique"},
            ).json()["lot"]["id"]

            upload_excel = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "e2e-excel"},
            )
            diagnostic = run_until_step(settings, "diagnostic_excel")
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "e2e-mapping"},
            )
            fusion = run_until_step(settings, "fusion_multi_onglets")
            normalization = run_until_step(settings, "normalisation_contenu")
            csv_contract = run_until_step(settings, "verification_csv_indesign")

            upload_images = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file(
                    zip_bytes(
                        [
                            ("Produit A.JPG", image_bytes()),
                            ("produit_b.png", image_bytes()),
                            ("produit-c.webp", image_bytes()),
                            ("image-orpheline.png", image_bytes()),
                        ]
                    )
                ),
                headers={"X-Idempotency-Key": "e2e-images"},
            )
            inspection = run_until_step(settings, "inspection_images")
            matching = run_until_step(settings, "matching_images")
            matching_response = client.get(f"/api/lots/{lot_id}/images/matching")

            validate_region_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "e2e-sort"},
            )
            self.assertEqual(validate_region_sort.status_code, 409)
            self.assertEqual(
                validate_region_sort.json()["error"]["code"],
                "SIRCOM_SORT_COLUMNS_NOT_CLEAR",
            )
            validate_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "ordre_source"},
                headers={"X-Idempotency-Key": "e2e-sort-source"},
            )
            self.assertEqual(validate_sort.status_code, 200, validate_sort.text)
            preview = client.get(f"/api/lots/{lot_id}/csv/preview")
            validate_preview = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "e2e-preview"},
            )
            self.assertEqual(validate_preview.status_code, 200, validate_preview.text)
            csv_export = client.get(f"/api/lots/{lot_id}/csv/export")
            self.assertEqual(csv_export.status_code, 200, csv_export.text)
            final_csv = client.get(csv_export.json()["artifact"]["download_url"])
            reports = run_until_step(settings, "rapports")
            reports_response = client.get(f"/api/lots/{lot_id}/reports")
            business_report = client.get(
                reports_response.json()["business_report_artifact"]["download_url"]
            )

            package_without_warning_acceptance = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": False},
                headers={"X-Idempotency-Key": "e2e-package-no-warnings"},
            )
            package_request = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": True},
                headers={"X-Idempotency-Key": "e2e-package"},
            )
            package = run_until_step(settings, "package_final")
            package_response = client.get(f"/api/lots/{lot_id}/package")
            package_download = client.get(
                package_response.json()["artifact"]["download_url"]
            )
            final_lot = client.get(f"/api/lots/{lot_id}").json()["lot"]

        self.assertEqual(upload_excel.status_code, 202, upload_excel.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        self.assertEqual(upload_images.status_code, 202, upload_images.text)
        for result in (
            diagnostic,
            fusion,
            normalization,
            csv_contract,
            inspection,
            matching,
            reports,
            package,
        ):
            self.assertEqual(result.outcome, "succeeded")

        self.assertEqual(matching_response.status_code, 200, matching_response.text)
        matching_payload = matching_response.json()["matching"]
        self.assertEqual(matching_payload["matched_count"], 3)
        self.assertEqual(matching_payload["processed_images_count"], 3)
        self.assertEqual(matching_payload["missing_count"], 0)
        self.assertEqual(matching_payload["unreferenced_count"], 1)

        self.assertEqual(preview.status_code, 200, preview.text)
        preview_payload = preview.json()["preview"]
        self.assertEqual(preview_payload["rows_count"], 3)
        self.assertEqual(preview_payload["removed_rows_without_id_count"], 1)
        self.assertEqual(
            preview_payload["headers"][:3], ["id_dossier", "imageid", "@pathimg"]
        )
        for row in preview_payload["rows"]:
            expected_image = image_id_for_dossier(row["id_dossier"])
            self.assertEqual(row["values"]["imageid"], expected_image)
            self.assertEqual(
                row["values"]["@pathimg"],
                f"{settings.indesign_image_root}/{expected_image}",
            )

        self.assertEqual(final_csv.status_code, 200, final_csv.text)
        self.assertTrue(final_csv.content.startswith(b"\xff\xfe"))
        self.assertTrue(verify_indesign_csv_bytes(final_csv.content).valid)
        csv_text = final_csv.content.decode("utf-16")
        self.assertIn("id_dossier,imageid,@pathimg", csv_text)
        self.assertIn("Objet de test avec<br>retour ligne", csv_text)
        self.assertIn("12/01/2026", csv_text)
        self.assertIn(f"{settings.indesign_image_root}/", csv_text)

        self.assertEqual(reports_response.status_code, 200, reports_response.text)
        self.assertEqual(business_report.status_code, 200, business_report.text)
        business_text = business_report.content.decode("utf-8")
        self.assertIn("## Package", business_text)
        self.assertIn("Images présentes : 3", business_text)
        self.assertIn("Images ignorées : 1", business_text)

        self.assertEqual(package_without_warning_acceptance.status_code, 409)
        self.assertEqual(
            package_without_warning_acceptance.json()["error"]["code"],
            "SIRCOM_PACKAGE_WARNINGS_DECISION_REQUIRED",
        )
        self.assertEqual(package_request.status_code, 202, package_request.text)
        self.assertEqual(package_response.status_code, 200, package_response.text)
        self.assertEqual(package_download.status_code, 200, package_download.text)

        expected_image_entries = {
            f"{EXPORT_IMAGES_FOLDER}/{image_id_for_dossier(id_dossier)}"
            for id_dossier in (
                "ARA07.2026-HGV",
                "BFC21.2026-TEST",
                "IDF75.2026-ZERO",
            )
        }
        with zipfile.ZipFile(BytesIO(package_download.content)) as archive:
            names = set(archive.namelist())
            root_files = {name for name in names if "/" not in name}
            image_entries = {
                name
                for name in names
                if name.startswith(f"{EXPORT_IMAGES_FOLDER}/")
                and name != f"{EXPORT_IMAGES_FOLDER}/"
            }
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            mapping_payload = json.loads(
                archive.read("mapping-utilise.json").decode("utf-8")
            )
            packaged_csv = archive.read("sircom-indesign-utf16.csv")
            for image_entry in image_entries:
                with Image.open(BytesIO(archive.read(image_entry))) as image:
                    self.assertEqual(image.format, "JPEG")
                    self.assertLessEqual(image.width, 350)

        self.assertEqual(
            root_files,
            {
                "sircom-indesign-utf16.csv",
                "rapport-metier.md",
                "rapport-technique.json",
                "mapping-utilise.json",
                "manifest.json",
            },
        )
        self.assertIn(f"{EXPORT_IMAGES_FOLDER}/", names)
        self.assertEqual(image_entries, expected_image_entries)
        self.assertEqual(packaged_csv, final_csv.content)
        self.assertEqual(manifest["package_filename"], f"sircom-2026-lot-{lot_id}.zip")
        self.assertEqual(
            {source["key"] for source in manifest["source_artifacts"]},
            {
                "csv_final",
                "mapping",
                "matching",
                "processed_images",
                "business_report",
                "technical_report",
            },
        )
        self.assertEqual(
            {entry["path"] for entry in manifest["entries"]},
            {
                "sircom-indesign-utf16.csv",
                "rapport-metier.md",
                "rapport-technique.json",
                "mapping-utilise.json",
                *expected_image_entries,
            },
        )
        self.assertIn("columns", mapping_payload)

        final_statuses = {step["key"]: step["status"] for step in final_lot["steps"]}
        for step in V1_STEPS:
            self.assertIn(final_statuses[step.key], DONE_STATUSES, step.key)


if __name__ == "__main__":
    unittest.main()
