from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

from sircom2026.app import create_app
from sircom2026.config import load_settings


def make_settings(tmpdir: Path, *, max_excel_mb: int = 50):
    return load_settings(
        {
            "SIRCOM_DATA_DIR": str(tmpdir / "data"),
            "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
            "SIRCOM_DISK_FREE_MIN_MB": "0",
            "SIRCOM_MAX_EXCEL_MB": str(max_excel_mb),
        }
    )


def valid_xlsx_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Produits"
    sheet.append(["id_dossier", "nom_produit"])
    sheet.append(["DOSSIER-1", "Produit test"])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def excel_file(
    filename: str,
    content: bytes,
    content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
) -> dict[str, tuple[str, bytes, str]]:
    return {"file": (filename, content, content_type)}


class ExcelUploadApiTest(unittest.TestCase):
    def test_valid_excel_is_stored_as_artifact_and_schedules_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot Excel"}).json()["lot"]["id"]
            content = valid_xlsx_bytes()

            response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("../source-secret.xlsx", content),
                headers={"X-Idempotency-Key": "upload-excel-1"},
            )

            payload = response.json()
            artifact = payload["artifact"]
            diagnostic_job = payload["job"]
            lot = payload["lot"]
            download = client.get(f"/api/lots/{lot_id}/downloads/{artifact['id']}")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(artifact["kind"], "excel")
        self.assertEqual(artifact["role"], "source")
        self.assertEqual(artifact["status"], "committed")
        self.assertEqual(artifact["size_bytes"], len(content))
        self.assertEqual(len(artifact["sha256"]), 64)
        self.assertNotIn("relative_path", artifact)
        self.assertNotIn("source-secret", str(payload))
        self.assertEqual(diagnostic_job["step_key"], "diagnostic_excel")
        self.assertEqual(diagnostic_job["status"], "queued")
        self.assertEqual(step_status(lot, "upload_excel"), "termine")
        self.assertEqual(step_status(lot, "diagnostic_excel"), "pret")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, content)

    def test_new_excel_upload_obsoletes_previous_source_and_invalidates_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot nouvel Excel"}).json()["lot"][
                "id"
            ]
            first_content = valid_xlsx_bytes()
            second_content = valid_xlsx_bytes()

            first_response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("premier.xlsx", first_content),
                headers={"X-Idempotency-Key": "upload-excel-first"},
            )
            first_artifact_id = first_response.json()["artifact"]["id"]
            second_response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("second.xlsx", second_content),
                headers={"X-Idempotency-Key": "upload-excel-second"},
            )
            payload = second_response.json()
            old_download = client.get(f"/api/lots/{lot_id}/downloads/{first_artifact_id}")
            new_download = client.get(payload["artifact"]["download_url"])

        self.assertEqual(second_response.status_code, 202)
        self.assertEqual(old_download.status_code, 404)
        self.assertEqual(old_download.json()["error"]["code"], "SIRCOM_ARTIFACT_NOT_FOUND")
        self.assertEqual(new_download.status_code, 200)
        self.assertIn("diagnostic_excel", payload["invalidated_steps"])
        self.assertIn("mapping", payload["invalidated_steps"])
        self.assertEqual(step_status(payload["lot"], "diagnostic_excel"), "pret")
        self.assertEqual(step_status(payload["lot"], "mapping"), "invalide")

    def test_upload_excel_reuses_successful_idempotency_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot idempotent"}).json()["lot"][
                "id"
            ]
            headers = {"X-Idempotency-Key": "upload-excel-idempotent"}

            first_response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("source.xlsx", valid_xlsx_bytes()),
                headers=headers,
            )
            second_response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("source.xlsx", valid_xlsx_bytes()),
                headers=headers,
            )

        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(second_response.status_code, 202)
        self.assertEqual(
            first_response.json()["artifact"]["id"],
            second_response.json()["artifact"]["id"],
        )
        self.assertTrue(first_response.json()["job"]["created"])
        self.assertFalse(second_response.json()["job"]["created"])

    def test_invalid_extension_is_rejected_with_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot extension"}).json()["lot"][
                "id"
            ]

            response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("source.csv", valid_xlsx_bytes(), "text/csv"),
            )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_EXCEL_EXTENSION_UNSUPPORTED")

    def test_oversized_excel_is_rejected_before_archive_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp), max_excel_mb=1)))
            lot_id = client.post("/api/lots", json={"title": "Lot taille"}).json()["lot"]["id"]

            response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("source.xlsx", b"x" * (1024 * 1024 + 1)),
            )

        self.assertEqual(response.status_code, 413)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "SIRCOM_EXCEL_TOO_LARGE")
        self.assertEqual(payload["error"]["details"]["max_mb"], 1)

    def test_corrupted_excel_archive_is_rejected_with_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot corrompu"}).json()["lot"][
                "id"
            ]

            response = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file("source.xlsx", b"not an excel archive"),
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_EXCEL_UNREADABLE")

    def test_lot_target_is_checked_before_excel_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            deleted_lot_id = client.post("/api/lots", json={"title": "Lot supprime"}).json()[
                "lot"
            ]["id"]
            client.delete(f"/api/lots/{deleted_lot_id}")

            missing_response = client.post(
                "/api/lots/lot_missing/excel",
                files=excel_file("source.csv", b"not an excel archive", "text/csv"),
            )
            deleted_response = client.post(
                f"/api/lots/{deleted_lot_id}/excel",
                files=excel_file("source.csv", b"not an excel archive", "text/csv"),
            )

        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["error"]["code"], "SIRCOM_LOT_NOT_FOUND")
        self.assertEqual(deleted_response.status_code, 409)
        self.assertEqual(deleted_response.json()["error"]["code"], "SIRCOM_LOT_NOT_MUTABLE")

    def test_unknown_lot_returns_structured_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.post(
                "/api/lots/lot_missing/excel",
                files=excel_file("source.xlsx", valid_xlsx_bytes()),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_LOT_NOT_FOUND")
        self.assertNotIn("lot_missing", str(response.json()))

    def test_home_ui_exposes_excel_upload_form_for_selected_lot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot UI Excel"}).json()["lot"]["id"]

            response = client.get(f"/?lot_id={lot_id}")

        html = response.text
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="excel-upload-form"', html)
        self.assertIn('for="excel-file"', html)
        self.assertIn('type="file"', html)
        self.assertIn('accept=".xlsx,.xlsm"', html)
        self.assertIn(f'data-excel-upload-lot-id="{lot_id}"', html)
        self.assertNotIn('href="#"', html)
        self.assertNotIn(str(Path(tmp)), html)


def step_status(lot: dict[str, object], step_key: str) -> str:
    for step in lot["steps"]:
        if step["key"] == step_key:
            return str(step["status"])
    raise AssertionError(f"Missing step {step_key}.")


if __name__ == "__main__":
    unittest.main()
