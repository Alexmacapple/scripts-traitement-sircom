from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from sircom2026.app import create_app
from sircom2026.database import Database
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


class PackageApiTest(unittest.TestCase):
    def test_package_requires_warning_acceptance_then_generates_zip_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "package.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = _prepare_lot_until_reports(client, settings, workbook_path)

            without_warning_acceptance = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": False},
                headers={"X-Idempotency-Key": "package-no-warnings"},
            )
            html_before = client.get(f"/lots/{lot_id}?view=package_final")
            enqueue = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": True},
                headers={"X-Idempotency-Key": "package-with-warnings"},
            )
            package_job = run_until_step(settings, "package_final")
            package_response = client.get(f"/api/lots/{lot_id}/package")
            download = client.get(package_response.json()["artifact"]["download_url"])
            html_after = client.get(f"/lots/{lot_id}?view=package_final")
            database = Database(settings.sqlite_path)
            with database.session() as repositories:
                lot = repositories.lots.get_required(lot_id)
                package_step = repositories.steps.get_by_lot_key(lot_id, "package_final")

        self.assertEqual(without_warning_acceptance.status_code, 409)
        self.assertEqual(
            without_warning_acceptance.json()["error"]["code"],
            "SIRCOM_PACKAGE_WARNINGS_DECISION_REQUIRED",
        )
        self.assertEqual(html_before.status_code, 200)
        self.assertIn("Générer le package final", html_before.text)
        self.assertEqual(enqueue.status_code, 202, enqueue.text)
        self.assertTrue(enqueue.json()["job"]["created"])
        self.assertEqual(package_job.outcome, "succeeded")
        self.assertEqual(package_response.status_code, 200, package_response.text)
        self.assertEqual(download.status_code, 200, download.text)
        self.assertIn(
            f"sircom-2026-lot-{lot_id}.zip",
            download.headers["content-disposition"],
        )
        self.assertEqual(package_step["status"], "termine_avec_alertes")
        self.assertEqual(lot["status"], "termine_avec_alertes")
        self.assertIn("Télécharger le package final", html_after.text)

        archive = zipfile.ZipFile(BytesIO(download.content))
        with archive:
            names = set(archive.namelist())
            root_files = {name for name in names if "/" not in name}
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
            self.assertIn("export-jpg-resize/", names)
            image_entries = sorted(
                name
                for name in names
                if name.startswith("export-jpg-resize/") and name != "export-jpg-resize/"
            )
            self.assertEqual(len(image_entries), 1)
            self.assertTrue(image_entries[0].endswith(".jpg"))

            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            csv_text = archive.read("sircom-indesign-utf16.csv").decode("utf-16")
            technical_text = archive.read("rapport-technique.json").decode("utf-8")

        self.assertEqual(manifest["package_filename"], f"sircom-2026-lot-{lot_id}.zip")
        self.assertEqual(manifest["notes"]["manifest_self_hash"], "excluded")
        self.assertEqual(
            {entry["path"] for entry in manifest["entries"]},
            {
                "sircom-indesign-utf16.csv",
                "rapport-metier.md",
                "rapport-technique.json",
                "mapping-utilise.json",
                *image_entries,
            },
        )
        self.assertNotIn("manifest.json", {entry["path"] for entry in manifest["entries"]})
        for entry in manifest["entries"]:
            self.assertIn("role", entry)
            self.assertGreater(entry["size_bytes"], 0)
            self.assertEqual(len(entry["sha256"]), 64)
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
        self.assertIn(f"{settings.indesign_image_root}/", csv_text)

        technical = json.loads(technical_text)
        self.assertEqual(technical["schema_version"], 1)
        confidential_values = (
            "Produit Secret Alpha",
            "Entreprise Confidentielle",
            "photo-produit-secret.png",
            "plan-secret-client.png",
            "ID-2",
            "sans-id.png",
        )
        manifest_text = json.dumps(manifest, ensure_ascii=False)
        for value in confidential_values:
            self.assertNotIn(value, technical_text)
            self.assertNotIn(value, manifest_text)

    def test_package_refuses_open_blocking_problem_before_enqueue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot bloqué"}).json()["lot"]["id"]
            database = Database(settings.sqlite_path)
            with database.transaction() as repositories:
                repositories.problems.create(
                    lot_id=lot_id,
                    step_key="package_final",
                    severity="bloquant",
                    code="SIRCOM_SYNTHETIC_BLOCKER",
                    title="Blocage synthétique",
                    message="Blocage synthétique",
                    cause="Un problème bloquant synthétique est ouvert.",
                    action="Résoudre le blocage synthétique.",
                )

            response = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": True},
                headers={"X-Idempotency-Key": "package-blocked"},
            )
            with database.session() as repositories:
                active_job = repositories.jobs.get_active_for_step(
                    lot_id=lot_id,
                    step_key="package_final",
                )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_PACKAGE_BLOCKERS_OPEN")
        self.assertIsNone(active_job)

    def test_package_generates_without_image_zip_when_reports_are_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "package-sans-images.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = _prepare_lot_until_reports_without_images(client, settings, workbook_path)

            enqueue = client.post(
                f"/api/lots/{lot_id}/package",
                json={"accept_warnings": True},
                headers={"X-Idempotency-Key": "package-no-images"},
            )
            if enqueue.status_code != 202:
                raise AssertionError(enqueue.text)
            package_job = run_until_step(settings, "package_final")
            package_response = client.get(f"/api/lots/{lot_id}/package")
            download = client.get(package_response.json()["artifact"]["download_url"])

        self.assertEqual(enqueue.status_code, 202, enqueue.text)
        self.assertTrue(enqueue.json()["job"]["created"])
        self.assertEqual(package_job.outcome, "succeeded")
        self.assertEqual(package_response.status_code, 200, package_response.text)
        self.assertEqual(download.status_code, 200, download.text)

        archive = zipfile.ZipFile(BytesIO(download.content))
        with archive:
            names = set(archive.namelist())
            image_entries = sorted(
                name
                for name in names
                if name.startswith("export-jpg-resize/") and name != "export-jpg-resize/"
            )
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))

        self.assertIn("export-jpg-resize/", names)
        self.assertEqual(image_entries, [])
        self.assertNotIn(
            "matching",
            {source["key"] for source in manifest["source_artifacts"]},
        )
        self.assertNotIn(
            "processed_images",
            {source["key"] for source in manifest["source_artifacts"]},
        )


def _prepare_lot_until_reports(
    client: TestClient,
    settings,
    workbook_path: Path,
) -> str:
    lot_id = client.post("/api/lots", json={"title": "Lot package"}).json()["lot"]["id"]
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
        headers={"X-Idempotency-Key": "package-images"},
    )
    inspection = run_until_step(settings, "inspection_images")
    upload_excel = client.post(
        f"/api/lots/{lot_id}/excel",
        files=excel_file(workbook_path),
        headers={"X-Idempotency-Key": "package-excel"},
    )
    diagnostic = run_until_step(settings, "diagnostic_excel")
    mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
    validate_mapping = client.post(
        f"/api/lots/{lot_id}/mapping/validate",
        json=mapping_submission(mapping),
        headers={"X-Idempotency-Key": "package-mapping"},
    )
    fusion = run_until_step(settings, "fusion_multi_onglets")
    normalization = run_until_step(settings, "normalisation_contenu")
    downstream = run_until_steps(settings, {"verification_csv_indesign", "matching_images"})
    validate_sort = client.post(
        f"/api/lots/{lot_id}/tri/validate",
        json={"decision": "tri_region_departement"},
        headers={"X-Idempotency-Key": "package-sort"},
    )
    validate_preview = client.post(
        f"/api/lots/{lot_id}/csv/preview/validate",
        headers={"X-Idempotency-Key": "package-preview"},
    )
    reports = run_until_step(settings, "rapports")

    if upload_images.status_code != 202:
        raise AssertionError(upload_images.text)
    if upload_excel.status_code != 202:
        raise AssertionError(upload_excel.text)
    if validate_mapping.status_code != 200:
        raise AssertionError(validate_mapping.text)
    if validate_sort.status_code != 200:
        raise AssertionError(validate_sort.text)
    if validate_preview.status_code != 200:
        raise AssertionError(validate_preview.text)
    for result in (
        inspection,
        diagnostic,
        fusion,
        normalization,
        downstream["verification_csv_indesign"],
        downstream["matching_images"],
        reports,
    ):
        if result.outcome != "succeeded":
            raise AssertionError(result)
    return lot_id


def _prepare_lot_until_reports_without_images(
    client: TestClient,
    settings,
    workbook_path: Path,
) -> str:
    lot_id = client.post("/api/lots", json={"title": "Lot package sans images"}).json()["lot"][
        "id"
    ]
    upload_excel = client.post(
        f"/api/lots/{lot_id}/excel",
        files=excel_file(workbook_path),
        headers={"X-Idempotency-Key": "package-no-images-excel"},
    )
    diagnostic = run_until_step(settings, "diagnostic_excel")
    mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
    validate_mapping = client.post(
        f"/api/lots/{lot_id}/mapping/validate",
        json=mapping_submission(mapping),
        headers={"X-Idempotency-Key": "package-no-images-mapping"},
    )
    fusion = run_until_step(settings, "fusion_multi_onglets")
    normalization = run_until_step(settings, "normalisation_contenu")
    csv_contract = run_until_step(settings, "verification_csv_indesign")
    validate_sort = client.post(
        f"/api/lots/{lot_id}/tri/validate",
        json={"decision": "tri_region_departement"},
        headers={"X-Idempotency-Key": "package-no-images-sort"},
    )
    validate_preview = client.post(
        f"/api/lots/{lot_id}/csv/preview/validate",
        headers={"X-Idempotency-Key": "package-no-images-preview"},
    )
    reports = run_until_step(settings, "rapports")

    if upload_excel.status_code != 202:
        raise AssertionError(upload_excel.text)
    if validate_mapping.status_code != 200:
        raise AssertionError(validate_mapping.text)
    if validate_sort.status_code != 200:
        raise AssertionError(validate_sort.text)
    if validate_preview.status_code != 200:
        raise AssertionError(validate_preview.text)
    for result in (diagnostic, fusion, normalization, csv_contract, reports):
        if result.outcome != "succeeded":
            raise AssertionError(result)
    return lot_id


if __name__ == "__main__":
    unittest.main()
