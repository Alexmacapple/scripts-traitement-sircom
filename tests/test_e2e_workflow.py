from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from sircom2026.app import create_app
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


class EndToEndWorkflowApiTest(unittest.TestCase):
    def test_excel_mapping_images_reports_package_workflow_generates_indesign_zip(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "e2e-workflow.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))

            create_lot = client.post("/api/lots", json={"title": "Lot E2E"})
            lot_id = create_lot.json()["lot"]["id"]

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
                headers={"X-Idempotency-Key": "e2e-images"},
            )
            inspection = run_until_step(settings, "inspection_images")
            images_status = client.get(f"/api/lots/{lot_id}/images/status")

            upload_excel = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "e2e-excel"},
            )
            diagnostic = run_until_step(settings, "diagnostic_excel")
            diagnostic_payload = client.get(f"/api/lots/{lot_id}/excel/diagnostic")

            mapping_payload = client.get(f"/api/lots/{lot_id}/mapping")
            mapping = mapping_payload.json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "e2e-mapping"},
            )
            fusion = run_until_step(settings, "fusion_multi_onglets")
            normalization = run_until_step(settings, "normalisation_contenu")
            downstream = run_until_steps(
                settings, {"verification_csv_indesign", "matching_images"}
            )
            matching_payload = client.get(f"/api/lots/{lot_id}/images/matching")

            tri = client.get(f"/api/lots/{lot_id}/tri")
            validate_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "e2e-sort"},
            )
            preview = client.get(f"/api/lots/{lot_id}/csv/preview")
            validate_preview = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "e2e-preview"},
            )

            reports = run_until_step(settings, "rapports")
            reports_payload = client.get(f"/api/lots/{lot_id}/reports")

            enqueue_package = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": True},
                headers={"X-Idempotency-Key": "e2e-package"},
            )
            package = run_until_step(settings, "package_final")
            package_payload = client.get(f"/api/lots/{lot_id}/package")
            download = client.get(package_payload.json()["artifact"]["download_url"])
            lot_payload = client.get(f"/api/lots/{lot_id}")

        self.assertEqual(create_lot.status_code, 201, create_lot.text)
        self.assertEqual(upload_images.status_code, 202, upload_images.text)
        self.assertEqual(images_status.status_code, 200, images_status.text)
        self.assertEqual(upload_excel.status_code, 202, upload_excel.text)
        self.assertEqual(diagnostic_payload.status_code, 200, diagnostic_payload.text)
        self.assertEqual(mapping_payload.status_code, 200, mapping_payload.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        self.assertEqual(matching_payload.status_code, 200, matching_payload.text)
        self.assertEqual(tri.status_code, 200, tri.text)
        self.assertEqual(validate_sort.status_code, 200, validate_sort.text)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(validate_preview.status_code, 200, validate_preview.text)
        self.assertEqual(reports_payload.status_code, 200, reports_payload.text)
        self.assertEqual(enqueue_package.status_code, 202, enqueue_package.text)
        self.assertEqual(package_payload.status_code, 200, package_payload.text)
        self.assertEqual(download.status_code, 200, download.text)

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

        diagnostic_json = diagnostic_payload.json()["diagnostic"]
        self.assertTrue(diagnostic_json["importable"], diagnostic_json["blockers"])
        self.assertEqual(diagnostic_json["sheet_count"], 1)
        self.assertFalse(matching_payload.json()["matching"]["blocking"])
        self.assertEqual(matching_payload.json()["matching"]["matched_count"], 1)
        self.assertIsNotNone(reports_payload.json()["business_report_artifact"])
        self.assertIsNotNone(reports_payload.json()["technical_report_artifact"])

        lot = lot_payload.json()["lot"]
        steps_by_key = {step["key"]: step for step in lot["steps"]}
        expected_done_steps = {
            "upload_excel",
            "diagnostic_excel",
            "mapping",
            "fusion_multi_onglets",
            "normalisation_contenu",
            "verification_csv_indesign",
            "tri_region_departement",
            "previsualisation_csv",
            "upload_images",
            "inspection_images",
            "matching_images",
            "rapports",
            "package_final",
        }
        self.assertLessEqual(expected_done_steps, set(steps_by_key))
        for step_key in expected_done_steps:
            self.assertIn(steps_by_key[step_key]["status"], DONE_STATUSES, step_key)

        archive = zipfile.ZipFile(BytesIO(download.content))
        with archive:
            names = set(archive.namelist())
            image_entries = {
                name
                for name in names
                if name.startswith("export-jpg-resize/")
                and name != "export-jpg-resize/"
            }
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            csv_text = archive.read("sircom-indesign-utf16.csv").decode("utf-16")

        self.assertIn("rapport-metier.md", names)
        self.assertIn("rapport-technique.json", names)
        self.assertIn("mapping-utilise.json", names)
        self.assertEqual(len(image_entries), 1)
        self.assertIn(f"{settings.indesign_image_root}/", csv_text)
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


if __name__ == "__main__":
    unittest.main()
