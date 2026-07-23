from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from openpyxl import Workbook

from sircom2026.app import create_app
from sircom2026.config import load_settings
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


def create_normalization_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dossiers"
    sheet.append(
        [
            "id_dossier",
            "Description",
            "Date dépôt",
            "SIRET",
            "Téléphone",
            "Code postal",
            "Département",
            "Code INSEE",
            "Prix TTC",
            "Colonne espaces",
        ]
    )
    sheet.append(
        [
            " 00123 ",
            "  Ligne 1\n  Ligne   2  ",
            date(2026, 7, 21),
            " 00123456789012 ",
            " 06  01  02 03 04 ",
            " 01230 ",
            " 05 ",
            " 00123 ",
            "  12,50  %  ",
            "     ",
        ]
    )
    sheet.append(
        [
            "ID-B",
            "Texte  multiple",
            "pas une date",
            "",
            "",
            "",
            "",
            "",
            "  1000,00  EUR  ",
            "  ",
        ]
    )
    sheet.append(["ID-C", None, None, None, None, None, None, None, None, None])
    workbook.save(path)
    workbook.close()


def prepare_importable_lot(
    client: TestClient,
    settings,
    excel_path: Path,
    *,
    title: str,
    key: str,
) -> str:
    lot_id = client.post("/api/lots", json={"title": title}).json()["lot"]["id"]
    upload = client.post(
        f"/api/lots/{lot_id}/excel",
        files=excel_file(excel_path),
        headers={"X-Idempotency-Key": f"upload-{key}"},
    )
    worker_result = run_worker_once(settings=settings)

    if upload.status_code != 202:
        raise AssertionError(upload.text)
    if worker_result.outcome != "succeeded":
        raise AssertionError(worker_result)
    return lot_id


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


def find_column(
    mapping: dict[str, Any],
    sheet: str,
    letter: str,
    header: str,
) -> dict[str, Any]:
    for column in mapping["columns"]:
        if (
            column["source_sheet"] == sheet
            and column["source_column_letter"] == letter
            and column["source_header"] == header
        ):
            return column
    raise AssertionError(f"Missing column {sheet}!{letter}:{header}.")


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


class ContentNormalizationWorkerTest(unittest.TestCase):
    def test_worker_normalizes_flat_merge_payload_and_reports_date_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "normalisation.xlsx"
            create_normalization_workbook(workbook_path)

            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = prepare_importable_lot(
                client,
                settings,
                workbook_path,
                title="Lot normalisation",
                key="normalisation",
            )
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            names = {
                "description": find_column(mapping, "Dossiers", "B", "Description")[
                    "csv_name"
                ],
                "date": find_column(mapping, "Dossiers", "C", "Date dépôt")["csv_name"],
                "siret": find_column(mapping, "Dossiers", "D", "SIRET")["csv_name"],
                "telephone": find_column(mapping, "Dossiers", "E", "Téléphone")[
                    "csv_name"
                ],
                "code_postal": find_column(mapping, "Dossiers", "F", "Code postal")[
                    "csv_name"
                ],
                "departement": find_column(mapping, "Dossiers", "G", "Département")[
                    "csv_name"
                ],
                "code_insee": find_column(mapping, "Dossiers", "H", "Code INSEE")[
                    "csv_name"
                ],
                "prix": find_column(mapping, "Dossiers", "I", "Prix TTC")["csv_name"],
                "spaces": find_column(mapping, "Dossiers", "J", "Colonne espaces")[
                    "csv_name"
                ],
            }

            validate = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "normalisation-mapping-validate"},
            )
            fusion_result = run_worker_once(settings=settings)
            after_fusion = client.get(f"/api/lots/{lot_id}").json()["lot"]
            normalization_result = run_worker_once(settings=settings)
            lot = client.get(f"/api/lots/{lot_id}").json()["lot"]
            payload = download_step_payload(
                client,
                settings,
                lot_id=lot_id,
                step_key="normalisation_contenu",
            )

        self.assertEqual(validate.status_code, 200, validate.text)
        self.assertEqual(fusion_result.step_key, "fusion_multi_onglets")
        self.assertEqual(fusion_result.outcome, "succeeded")
        self.assertEqual(step_status(after_fusion, "normalisation_contenu"), "pret")
        self.assertEqual(normalization_result.step_key, "normalisation_contenu")
        self.assertEqual(normalization_result.outcome, "succeeded")
        self.assertEqual(
            step_status(lot, "normalisation_contenu"), "termine_avec_alertes"
        )

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["rules_version"], "content-normalisation-v1")
        self.assertEqual(payload["rows_count"], 3)
        self.assertEqual(payload["date_issues_count"], 2)
        self.assertEqual(payload["invalid_dates_count"], 1)
        self.assertEqual(payload["missing_dates_count"], 1)
        self.assertEqual(payload["removed_empty_columns_count"], 1)
        self.assertNotIn(
            names["spaces"], [column["csv_name"] for column in payload["columns"]]
        )

        row_by_id = {row["id_dossier"]: row["values"] for row in payload["rows"]}
        first_row = row_by_id["00123"]
        self.assertEqual(first_row[names["description"]], "Ligne 1<br>Ligne 2")
        self.assertEqual(first_row[names["date"]], "21/07/2026")
        self.assertEqual(first_row[names["siret"]], "00123456789012")
        self.assertEqual(first_row[names["telephone"]], "06 01 02 03 04")
        self.assertEqual(first_row[names["code_postal"]], "01230")
        self.assertEqual(first_row[names["departement"]], "05")
        self.assertEqual(first_row[names["code_insee"]], "00123")
        self.assertEqual(first_row[names["prix"]], "12,50 %")
        self.assertIsInstance(first_row[names["prix"]], str)
        self.assertEqual(row_by_id["ID-B"][names["date"]], "")
        self.assertEqual(row_by_id["ID-C"][names["date"]], "")
        self.assertEqual(row_by_id["ID-C"][names["description"]], "")
        self.assertNotIn("pas une date", str(payload["date_issues"]))
        self.assertNotIn("None", str(payload["rows"]))
        self.assertNotIn("nan", str(payload["rows"]).lower())

        alert_codes = {
            problem["code"] for problem in lot["problem_groups"]["alerte"]["items"]
        }
        self.assertIn("SIRCOM_NORMALIZATION_DATE_VALUES_INVALID", alert_codes)


if __name__ == "__main__":
    unittest.main()
