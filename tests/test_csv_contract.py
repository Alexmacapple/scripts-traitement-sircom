from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from openpyxl import Workbook

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.csv_contract import (
    compare_csv_format_to_reference,
    verify_indesign_csv_bytes,
    write_indesign_csv_bytes,
)
from sircom2026.database import Database
from sircom2026.worker_runner import run_worker_once


REFERENCE_CSV_2025 = (
    Path(__file__).resolve().parents[1]
    / "livrables-miweb-2025"
    / "livrables-miweb-1-2025"
    / "9-final-sircom-indesign-utf16.csv"
)


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


def create_csv_contract_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dossiers"
    sheet.append(["id_dossier", "Région", "Nom produit"])
    sheet.append(["ID-1", "Bretagne", "Produit, spécial"])
    sheet.append(["ID-2", "", 'Texte "fin"'])
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


def step_status(lot: dict[str, object], step_key: str) -> str:
    for step in lot["steps"]:
        if step["key"] == step_key:
            return str(step["status"])
    raise AssertionError(f"Missing step {step_key}.")


def download_step_payload(
    client: TestClient,
    settings,
    *,
    lot_id: str,
    step_key: str,
) -> dict[str, Any]:
    database = Database(settings.sqlite_path)
    with database.session() as repositories:
        step = repositories.steps.get_by_lot_key(lot_id, step_key)
        if step is None or not step["current_run_id"]:
            raise AssertionError(f"{step_key} has no current run.")
        artifact = repositories.artifacts.get_for_step_run_role(
            lot_id=lot_id,
            step_key=step_key,
            run_id=step["current_run_id"],
            role="result",
        )
        if artifact is None:
            raise AssertionError(f"{step_key} result artifact is missing.")

    response = client.get(f"/api/lots/{lot_id}/downloads/{artifact['id']}")
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


class CsvContractTest(unittest.TestCase):
    def test_writer_and_verifier_match_golden_bytes_and_accept_automatic_quotes(self) -> None:
        headers = ["id_dossier", "imageid", "@pathimg", "b_region", "c_nom"]
        rows = [
            ["ID-1", "", "", "Bretagne", "Produit, spécial"],
            [
                "ID-2",
                "img-2",
                "/Users/victoria/Documents/export-jpg-resize/img-2.jpg",
                "",
                'Texte "fin"',
            ],
        ]

        content = write_indesign_csv_bytes(headers, rows)
        expected_text = (
            'id_dossier,imageid,@pathimg,b_region,c_nom\n'
            'ID-1,,,Bretagne,"Produit, spécial"\n'
            'ID-2,img-2,/Users/victoria/Documents/export-jpg-resize/img-2.jpg,'
            ',"Texte ""fin"""\n'
        )
        expected = b"\xff\xfe" + expected_text.encode("utf-16-le")
        report = verify_indesign_csv_bytes(content, expected_headers=headers)

        self.assertEqual(content, expected)
        self.assertTrue(report.valid, report.to_public_dict())
        self.assertEqual(report.format_signature["encoding"], "utf-16-le-bom")
        self.assertEqual(report.format_signature["line_ending"], "lf")
        self.assertEqual(report.format_signature["delimiter"], "comma")
        self.assertEqual(report.headers, headers)
        self.assertEqual(report.rows_count, 2)

    def test_verifier_rejects_contract_breaks_without_normalizing_newlines(self) -> None:
        headers = ["id_dossier", "imageid", "@pathimg"]
        bad_text = "id_dossier,imageid,@pathimg\r\nID-1,#N/A,\r\nID-2\r\nID-3,n/c,\r\n"
        content = b"\xff\xfe" + bad_text.encode("utf-16-le")

        report = verify_indesign_csv_bytes(content, expected_headers=headers)
        codes = {issue["code"] for issue in report.to_public_dict()["issues"]}

        self.assertFalse(report.valid)
        self.assertIn("SIRCOM_CSV_LINE_ENDING_NOT_LF", codes)
        self.assertIn("SIRCOM_CSV_FORBIDDEN_VALUE", codes)
        self.assertIn("SIRCOM_CSV_ROW_WIDTH_MISMATCH", codes)
        forbidden_count = sum(
            issue["code"] == "SIRCOM_CSV_FORBIDDEN_VALUE"
            for issue in report.to_public_dict()["issues"]
        )
        self.assertEqual(forbidden_count, 2)

    def test_verifier_rejects_missing_bom_duplicate_headers_and_bad_positions(self) -> None:
        content = "imageid,id_dossier,id_dossier,@pathimg\nimg-1,ID-1,ID-1,\n".encode("utf-16-le")

        report = verify_indesign_csv_bytes(
            content,
            expected_headers=["id_dossier", "imageid", "@pathimg"],
        )
        codes = {issue["code"] for issue in report.to_public_dict()["issues"]}

        self.assertFalse(report.valid)
        self.assertIn("SIRCOM_CSV_UTF16_BOM_MISSING", codes)
        self.assertIn("SIRCOM_CSV_HEADERS_NOT_UNIQUE", codes)
        self.assertIn("SIRCOM_CSV_HEADERS_ORDER_INVALID", codes)
        self.assertIn("SIRCOM_CSV_REQUIRED_HEADERS_INVALID", codes)

    def test_structure_comparison_uses_reference_format_not_2025_header_list(self) -> None:
        candidate = write_indesign_csv_bytes(
            ["id_dossier", "imageid", "@pathimg", "z_champ"],
            [["ID-1", "", "", "Valeur"]],
        )

        comparison = compare_csv_format_to_reference(
            REFERENCE_CSV_2025.read_bytes(),
            candidate,
        )

        self.assertTrue(comparison["format_matches"], comparison)
        self.assertFalse(comparison["header_list_compared_as_normative"])
        self.assertGreater(comparison["reference"]["headers_count"], 4)
        self.assertEqual(comparison["candidate"]["headers_count"], 4)

    def test_worker_verifies_current_normalization_payload_and_persists_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "csv-contract.xlsx"
            create_csv_contract_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))

            lot_id = client.post("/api/lots", json={"title": "Lot CSV"}).json()["lot"]["id"]
            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "csv-upload"},
            )
            diagnostic = run_worker_once(settings=settings)
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "csv-mapping"},
            )
            fusion = run_worker_once(settings=settings)
            normalization = run_worker_once(settings=settings)
            verification = run_worker_once(settings=settings)
            lot = client.get(f"/api/lots/{lot_id}").json()["lot"]
            payload = download_step_payload(
                client,
                settings,
                lot_id=lot_id,
                step_key="verification_csv_indesign",
            )

        self.assertEqual(upload.status_code, 202, upload.text)
        self.assertEqual(validate.status_code, 200, validate.text)
        self.assertEqual(diagnostic.outcome, "succeeded")
        self.assertEqual(fusion.outcome, "succeeded")
        self.assertEqual(normalization.outcome, "succeeded")
        self.assertEqual(verification.step_key, "verification_csv_indesign")
        self.assertEqual(verification.outcome, "succeeded")
        self.assertEqual(step_status(lot, "verification_csv_indesign"), "termine")
        self.assertTrue(payload["valid"], payload)
        self.assertEqual(payload["format_signature"]["encoding"], "utf-16-le-bom")
        self.assertEqual(payload["format_signature"]["line_ending"], "lf")
        self.assertEqual(payload["headers"][:3], ["id_dossier", "imageid", "@pathimg"])
        self.assertEqual(payload["rows_count"], 2)
        self.assertEqual(payload["issues"], [])


if __name__ == "__main__":
    unittest.main()
