from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from openpyxl import Workbook

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.csv_contract import verify_indesign_csv_bytes
from sircom2026.database import Database
from sircom2026.worker_runner import run_worker_once


def make_settings(tmpdir: Path):
    return load_settings(
        {
            "SIRCOM_DATA_DIR": str(tmpdir / "data"),
            "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
            "SIRCOM_DISK_FREE_MIN_MB": "0",
        }
    )


def excel_file(path: Path) -> dict[str, tuple[str, bytes, str]]:
    return {
        "file": (
            path.name,
            path.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def create_preview_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dossiers"
    sheet.append(["id_dossier", "Région", "Département", "Nom produit", "Colonne vide"])
    sheet.append(["ID-3", "Occitanie", "31", "Produit, trois", None])
    sheet.append(["ID-1", "Bretagne", "22", "", None])
    sheet.append([None, "Bretagne", "35", "Sans ID", None])
    sheet.append(["ID-2", "Bretagne", "35", 'Produit "deux"', None])
    workbook.save(path)
    workbook.close()


def create_no_sort_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dossiers"
    sheet.append(["id_dossier", "Nom produit"])
    sheet.append(["ID-2", "Produit 2"])
    sheet.append(["ID-1", "Produit 1"])
    workbook.save(path)
    workbook.close()


def mapping_submission(mapping: dict[str, Any]) -> dict[str, Any]:
    return {
        "structural_fingerprint": mapping["structural_fingerprint"],
        "columns": [
            {
                "id": column["id"],
                "status": column["status"],
                "csv_name": column["csv_name"],
                "logical_role": column["logical_role"],
                "suppression_reason": column["suppression_reason"],
            }
            for column in mapping["columns"]
        ],
    }


def prepare_verified_lot(
    client: TestClient,
    settings,
    workbook_path: Path,
    *,
    key: str,
    sort_decision: str,
) -> str:
    lot_id = client.post("/api/lots", json={"title": f"Lot {key}"}).json()["lot"]["id"]
    upload = client.post(
        f"/api/lots/{lot_id}/excel",
        files=excel_file(workbook_path),
        headers={"X-Idempotency-Key": f"upload-{key}"},
    )
    diagnostic = run_worker_once(settings=settings)
    mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
    validate_mapping = client.post(
        f"/api/lots/{lot_id}/mapping/validate",
        json=mapping_submission(mapping),
        headers={"X-Idempotency-Key": f"mapping-{key}"},
    )
    fusion = run_worker_once(settings=settings)
    normalization = run_worker_once(settings=settings)
    csv_contract = run_worker_once(settings=settings)
    validate_sort = client.post(
        f"/api/lots/{lot_id}/tri/validate",
        json={"decision": sort_decision},
        headers={"X-Idempotency-Key": f"sort-{key}"},
    )

    if upload.status_code != 202:
        raise AssertionError(upload.text)
    if validate_mapping.status_code != 200:
        raise AssertionError(validate_mapping.text)
    if validate_sort.status_code != 200:
        raise AssertionError(validate_sort.text)
    for result in (diagnostic, fusion, normalization, csv_contract):
        if result.outcome != "succeeded":
            raise AssertionError(result)
    return lot_id


def download_step_artifact(
    client: TestClient,
    settings,
    *,
    lot_id: str,
    step_key: str,
    role: str,
) -> bytes:
    database = Database(settings.sqlite_path)
    with database.session() as repositories:
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
            raise AssertionError(f"{step_key} {role} artifact is missing.")

    response = client.get(f"/api/lots/{lot_id}/downloads/{artifact['id']}")
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.content


class CsvPreviewApiTest(unittest.TestCase):
    def test_preview_validation_and_final_utf16_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "preview.xlsx"
            create_preview_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = prepare_verified_lot(
                client,
                settings,
                workbook_path,
                key="preview",
                sort_decision="tri_region_departement",
            )

            preview = client.get(f"/api/lots/{lot_id}/csv/preview")
            html_before_validation = client.get(
                f"/?lot_id={lot_id}&view=previsualisation_csv"
            )
            export_before_validation = client.get(f"/api/lots/{lot_id}/csv/export")
            validation = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "preview-validate"},
            )
            replay = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "preview-validate"},
            )
            export_after_validation = client.get(f"/api/lots/{lot_id}/csv/export")
            html_after_validation = client.get(
                f"/?lot_id={lot_id}&view=previsualisation_csv"
            )
            final_csv = client.get(export_after_validation.json()["artifact"]["download_url"])
            lot = client.get(f"/api/lots/{lot_id}").json()["lot"]
            preview_payload = download_step_artifact(
                client,
                settings,
                lot_id=lot_id,
                step_key="previsualisation_csv",
                role="preview",
            )

        self.assertEqual(preview.status_code, 200, preview.text)
        payload = preview.json()["preview"]
        self.assertFalse(payload["validated"])
        self.assertEqual(payload["headers"][:3], ["id_dossier", "imageid", "@pathimg"])
        self.assertEqual(payload["rows_count"], 3)
        self.assertEqual([row["id_dossier"] for row in payload["rows"]], ["ID-1", "ID-2", "ID-3"])
        self.assertEqual(payload["rows"][0]["values"]["imageid"], "dossier-id-1.jpg")
        self.assertEqual(payload["rows"][0]["values"]["@pathimg"], "")
        self.assertEqual(payload["rows"][0]["values"][payload["headers"][3]], "Bretagne")
        self.assertIn("removed_columns", payload)
        self.assertIn("removed_rows", payload)
        self.assertEqual(payload["removed_columns_count"], 1)
        self.assertEqual(payload["removed_rows_without_id_count"], 1)
        self.assertTrue(payload["warnings"])
        self.assertEqual(html_before_validation.status_code, 200)
        self.assertIn("Aperçu CSV", html_before_validation.text)
        self.assertIn("Valider l'aperçu CSV", html_before_validation.text)
        self.assertIn("Colonnes supprimées", html_before_validation.text)
        self.assertEqual(export_before_validation.status_code, 409)
        self.assertEqual(
            export_before_validation.json()["error"]["code"],
            "SIRCOM_CSV_PREVIEW_NOT_VALIDATED",
        )
        self.assertEqual(validation.status_code, 200, validation.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(
            validation.json()["csv_artifact"]["id"],
            replay.json()["csv_artifact"]["id"],
        )
        self.assertEqual(export_after_validation.status_code, 200, export_after_validation.text)
        self.assertEqual(html_after_validation.status_code, 200)
        self.assertIn("Télécharger le CSV final", html_after_validation.text)
        self.assertIn(validation.json()["csv_artifact"]["download_url"], html_after_validation.text)
        self.assertEqual(final_csv.status_code, 200, final_csv.text)
        self.assertTrue(final_csv.content.startswith(b"\xff\xfe"))
        self.assertTrue(verify_indesign_csv_bytes(final_csv.content).valid)
        self.assertIn(b"\x22\x00", final_csv.content)
        self.assertIn(b"\x2c\x00", final_csv.content)
        self.assertIn(b"\x0a\x00", final_csv.content)
        self.assertIn(b"schema_version", preview_payload)
        csv_step = next(step for step in lot["steps"] if step["key"] == "previsualisation_csv")
        self.assertEqual(csv_step["status"], "termine_avec_alertes")

    def test_preview_requires_sort_and_contract_without_blocking_missing_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "missing-sort.xlsx"
            create_no_sort_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot bloqué"}).json()["lot"]["id"]
            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "upload-blocked"},
            )
            diagnostic = run_worker_once(settings=settings)
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "mapping-blocked"},
            )
            fusion = run_worker_once(settings=settings)
            normalization = run_worker_once(settings=settings)
            csv_contract = run_worker_once(settings=settings)

            preview_before_sort = client.get(f"/api/lots/{lot_id}/csv/preview")
            validate_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "ordre_source"},
                headers={"X-Idempotency-Key": "sort-source"},
            )
            preview_after_sort = client.get(f"/api/lots/{lot_id}/csv/preview")

        self.assertEqual(upload.status_code, 202, upload.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        for result in (diagnostic, fusion, normalization, csv_contract):
            self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(preview_before_sort.status_code, 409)
        self.assertEqual(
            preview_before_sort.json()["error"]["code"],
            "SIRCOM_CSV_SORT_NOT_VALIDATED",
        )
        self.assertEqual(validate_sort.status_code, 200, validate_sort.text)
        self.assertEqual(preview_after_sort.status_code, 200, preview_after_sort.text)
        warnings = preview_after_sort.json()["preview"]["warnings"]
        self.assertIn("SIRCOM_CSV_IMAGES_NOT_PROVIDED", {warning["code"] for warning in warnings})

    def test_excel_mapping_and_sort_changes_invalidate_validated_export(self) -> None:
        for change in ("excel", "mapping", "sort"):
            with self.subTest(change=change):
                with tempfile.TemporaryDirectory() as tmp:
                    tmpdir = Path(tmp)
                    workbook_path = tmpdir / "fixtures" / f"{change}.xlsx"
                    create_preview_workbook(workbook_path)
                    settings = make_settings(tmpdir)
                    client = TestClient(create_app(settings))
                    lot_id = prepare_verified_lot(
                        client,
                        settings,
                        workbook_path,
                        key=f"invalidation-{change}",
                        sort_decision="tri_region_departement",
                    )
                    validation = client.post(
                        f"/api/lots/{lot_id}/csv/preview/validate",
                        headers={"X-Idempotency-Key": f"preview-{change}"},
                    )
                    export_before_change = client.get(f"/api/lots/{lot_id}/csv/export")

                    if change == "excel":
                        mutation = client.post(
                            f"/api/lots/{lot_id}/excel",
                            files=excel_file(workbook_path),
                            headers={"X-Idempotency-Key": "upload-new-excel"},
                        )
                    elif change == "mapping":
                        mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
                        mutation = client.post(
                            f"/api/lots/{lot_id}/mapping/validate",
                            json=mapping_submission(mapping),
                            headers={"X-Idempotency-Key": "mapping-new-validation"},
                        )
                    else:
                        mutation = client.post(
                            f"/api/lots/{lot_id}/tri/validate",
                            json={"decision": "ordre_source"},
                            headers={"X-Idempotency-Key": "sort-new-validation"},
                        )

                    export_after_change = client.get(f"/api/lots/{lot_id}/csv/export")
                    old_key_replay = client.post(
                        f"/api/lots/{lot_id}/csv/preview/validate",
                        headers={"X-Idempotency-Key": f"preview-{change}"},
                    )

                    self.assertEqual(validation.status_code, 200, validation.text)
                    self.assertEqual(
                        export_before_change.status_code,
                        200,
                        export_before_change.text,
                    )
                    self.assertIn(mutation.status_code, {200, 202}, mutation.text)
                    self.assertEqual(export_after_change.status_code, 409)
                    self.assertIn(
                        export_after_change.json()["error"]["code"],
                        {
                            "SIRCOM_CSV_EXPORT_PREREQUISITES_MISSING",
                            "SIRCOM_CSV_PREVIEW_NOT_VALIDATED",
                        },
                    )
                    self.assertEqual(old_key_replay.status_code, 409)


if __name__ == "__main__":
    unittest.main()
