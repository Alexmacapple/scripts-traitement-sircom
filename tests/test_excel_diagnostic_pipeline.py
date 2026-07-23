from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.synthetic_excels import create_synthetic_excels
from sircom2026.worker_runner import run_worker_once


def make_settings(tmpdir: Path, **overrides: str):
    env = {
        "SIRCOM_DATA_DIR": str(tmpdir / "data"),
        "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
        "SIRCOM_DISK_FREE_MIN_MB": "0",
    }
    env.update(overrides)
    return load_settings(env)


def excel_file(path: Path) -> dict[str, tuple[str, bytes, str]]:
    return {
        "file": (
            path.name,
            path.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def excel_bytes_file(
    filename: str,
    content: bytes,
) -> dict[str, tuple[str, bytes, str]]:
    return {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def workbook_bytes(*, rows: int, columns: int) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Produits"
    sheet.append(["id_dossier", *(f"colonne_{index}" for index in range(2, columns + 1))])
    for row_number in range(2, rows + 1):
        sheet.append(
            [
                f"DOSSIER-{row_number - 1}",
                *(f"valeur_{row_number}_{column}" for column in range(2, columns + 1)),
            ]
        )
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class ExcelDiagnosticPipelineTest(unittest.TestCase):
    def test_worker_persists_importable_diagnostic_and_exposes_it_by_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(
                tmpdir / "fixtures", ["valid_multi_tabs"]
            )
            client = TestClient(create_app(settings))
            lot_id = client.post(
                "/api/lots", json={"title": "Lot diagnostic OK"}
            ).json()["lot"]["id"]
            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(fixtures["valid_multi_tabs"]),
                headers={"X-Idempotency-Key": "upload-diagnostic-ok"},
            )
            not_ready = client.get(f"/api/lots/{lot_id}/excel/diagnostic")

            worker_result = run_worker_once(settings=settings)
            diagnostic_response = client.get(f"/api/lots/{lot_id}/excel/diagnostic")
            diagnostic_download = client.get(
                diagnostic_response.json()["artifact"]["download_url"]
            )
            lot_response = client.get(f"/api/lots/{lot_id}")

        self.assertEqual(upload.status_code, 202)
        self.assertEqual(not_ready.status_code, 409)
        self.assertTrue(worker_result.processed)
        self.assertEqual(worker_result.outcome, "succeeded")
        self.assertEqual(worker_result.step_key, "diagnostic_excel")
        self.assertEqual(diagnostic_response.status_code, 200)

        payload = diagnostic_response.json()
        diagnostic = payload["diagnostic"]
        self.assertTrue(diagnostic["importable"], diagnostic["blockers"])
        self.assertEqual(diagnostic["sheet_count"], 4)
        self.assertNotIn("path", diagnostic)
        self.assertNotIn(str(tmpdir), str(payload))
        self.assertNotIn("Objet de test", str(payload))
        self.assertEqual(diagnostic_download.status_code, 200)

        sheets = {sheet["name"]: sheet for sheet in diagnostic["sheets"]}
        self.assertTrue(sheets["Avis"]["ignored"])
        self.assertEqual(payload["problems"][0]["step_key"], "diagnostic_excel")
        self.assertTrue(all(problem["title"] for problem in payload["problems"]))
        self.assertTrue(all(problem["cause"] for problem in payload["problems"]))
        self.assertTrue(all(problem["action"] for problem in payload["problems"]))
        self.assertTrue(
            all(problem["location_label"] for problem in payload["problems"])
        )

        lot = lot_response.json()["lot"]
        self.assertEqual(step_status(lot, "diagnostic_excel"), "termine_avec_alertes")
        problem_codes = {problem["code"] for problem in lot["problems"]}
        self.assertIn("SIRCOM_EXCEL_EMPTY_SHEET_IGNORED", problem_codes)
        self.assertIn("SIRCOM_EXCEL_ID_BLANK_ROWS", problem_codes)

    def test_worker_blocks_refused_diagnostic_and_keeps_result_consultable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            settings = make_settings(tmpdir)
            fixtures = create_synthetic_excels(tmpdir / "fixtures", ["missing_id"])
            client = TestClient(create_app(settings))
            lot_id = client.post(
                "/api/lots", json={"title": "Lot diagnostic refus"}
            ).json()["lot"]["id"]

            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(fixtures["missing_id"]),
                headers={"X-Idempotency-Key": "upload-diagnostic-refus"},
            )
            worker_result = run_worker_once(settings=settings)
            diagnostic_response = client.get(f"/api/lots/{lot_id}/excel/diagnostic")
            lot_response = client.get(f"/api/lots/{lot_id}")

        self.assertEqual(upload.status_code, 202)
        self.assertEqual(worker_result.outcome, "succeeded")
        self.assertEqual(diagnostic_response.status_code, 200)
        self.assertFalse(diagnostic_response.json()["diagnostic"]["importable"])

        lot = lot_response.json()["lot"]
        self.assertEqual(lot["status"], "bloque")
        self.assertEqual(step_status(lot, "diagnostic_excel"), "bloque")
        blocking_codes = {
            problem["code"] for problem in lot["problem_groups"]["bloquant"]["items"]
        }
        self.assertIn("SIRCOM_EXCEL_ID_MISSING", blocking_codes)
        self.assertIn(
            "SIRCOM_EXCEL_ID_MISSING",
            {
                problem["code"]
                for problem in diagnostic_response.json()["problem_groups"]["bloquant"][
                    "items"
                ]
            },
        )

    def test_worker_blocks_dimension_violation_found_during_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            upload_settings = make_settings(tmpdir, SIRCOM_MAX_EXCEL_CELLS="100")
            worker_settings = make_settings(tmpdir, SIRCOM_MAX_EXCEL_CELLS="5")
            client = TestClient(create_app(upload_settings))
            lot_id = client.post(
                "/api/lots", json={"title": "Lot diagnostic dimensions"}
            ).json()["lot"]["id"]

            upload = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_bytes_file(
                    "source.xlsx", workbook_bytes(rows=2, columns=3)
                ),
                headers={"X-Idempotency-Key": "upload-diagnostic-dimensions"},
            )
            worker_result = run_worker_once(settings=worker_settings)
            diagnostic_response = client.get(f"/api/lots/{lot_id}/excel/diagnostic")
            lot_response = client.get(f"/api/lots/{lot_id}")

        self.assertEqual(upload.status_code, 202, upload.text)
        self.assertEqual(worker_result.outcome, "succeeded")
        self.assertEqual(diagnostic_response.status_code, 200)

        lot = lot_response.json()["lot"]
        self.assertEqual(step_status(lot, "diagnostic_excel"), "bloque")
        blocking_problems = diagnostic_response.json()["problem_groups"]["bloquant"][
            "items"
        ]
        dimension_problem = next(
            problem
            for problem in blocking_problems
            if problem["code"] == "SIRCOM_EXCEL_DIMENSIONS_EXCEEDED"
        )
        self.assertEqual(dimension_problem["title"], "Classeur Excel hors limites")
        self.assertEqual(dimension_problem["location"]["onglet"], "Produits")
        self.assertEqual(dimension_problem["technical"]["limit_exceeded"], "max_cells")
        self.assertEqual(dimension_problem["technical"]["observed"], 6)
        self.assertEqual(dimension_problem["technical"]["max"], 5)

    def test_worker_persists_structured_problems_for_strict_refusal_cases(self) -> None:
        expected_codes = {
            "missing_id": "SIRCOM_EXCEL_ID_MISSING",
            "duplicate_id": "SIRCOM_EXCEL_ID_DUPLICATES",
            "ambiguous_id": "SIRCOM_EXCEL_ID_AMBIGUOUS",
            "merged_cells": "SIRCOM_EXCEL_MERGED_CELLS",
            "hidden_column": "SIRCOM_EXCEL_HIDDEN_COLUMNS",
            "hidden_row": "SIRCOM_EXCEL_HIDDEN_ROWS",
            "hidden_sheet": "SIRCOM_EXCEL_HIDDEN_SHEET",
            "formula": "SIRCOM_EXCEL_FORMULAS",
            "multirow_header": "SIRCOM_EXCEL_HEADER_MULTIROW",
            "data_without_header": "SIRCOM_EXCEL_DATA_WITHOUT_HEADER",
            "cleaned_header_collision": "SIRCOM_EXCEL_CSV_HEADER_COLLISION",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            fixtures = create_synthetic_excels(tmpdir / "fixtures", expected_codes)

            for case_name, expected_code in expected_codes.items():
                with self.subTest(case=case_name):
                    settings = make_settings(tmpdir / case_name)
                    client = TestClient(create_app(settings))
                    lot_id = client.post(
                        "/api/lots",
                        json={"title": f"Lot {case_name}"},
                    ).json()["lot"]["id"]

                    upload = client.post(
                        f"/api/lots/{lot_id}/excel",
                        files=excel_file(fixtures[case_name]),
                        headers={"X-Idempotency-Key": f"upload-{case_name}"},
                    )
                    worker_result = run_worker_once(settings=settings)
                    diagnostic_response = client.get(
                        f"/api/lots/{lot_id}/excel/diagnostic"
                    )

                    self.assertEqual(upload.status_code, 202)
                    self.assertEqual(worker_result.outcome, "succeeded")
                    self.assertEqual(diagnostic_response.status_code, 200)
                    blocking_codes = {
                        problem["code"]
                        for problem in diagnostic_response.json()["problem_groups"][
                            "bloquant"
                        ]["items"]
                    }
                    self.assertIn(expected_code, blocking_codes)

    def test_unknown_lot_diagnostic_returns_structured_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.get("/api/lots/lot_missing/excel/diagnostic")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_LOT_NOT_FOUND")
        self.assertNotIn("lot_missing", str(response.json()))


def step_status(lot: dict[str, object], step_key: str) -> str:
    for step in lot["steps"]:
        if step["key"] == step_key:
            return str(step["status"])
    raise AssertionError(f"Missing step {step_key}.")


if __name__ == "__main__":
    unittest.main()
