from __future__ import annotations

import tempfile
import unittest
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


def create_sort_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dossiers"
    sheet.append(["id_dossier", "Région", "Département", "Nom produit"])
    sheet.append(["ID-3", "Occitanie", "31", "Produit 3"])
    sheet.append(["ID-2", "Bretagne", "35", "Produit 2"])
    sheet.append(["ID-1", "Auvergne-Rhône-Alpes", "07", "Produit 1"])
    sheet.append(["ID-4", "Bretagne", "22", "Produit 4"])
    sheet.append(["ID-5", "", "99", "Produit 5"])
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


def prepare_normalized_lot(
    client: TestClient,
    settings,
    excel_path: Path,
    *,
    title: str,
    key: str,
    mapping_mutator=None,
) -> tuple[str, dict[str, Any]]:
    lot_id = client.post("/api/lots", json={"title": title}).json()["lot"]["id"]
    upload = client.post(
        f"/api/lots/{lot_id}/excel",
        files=excel_file(excel_path),
        headers={"X-Idempotency-Key": f"upload-{key}"},
    )
    diagnostic_result = run_worker_once(settings=settings)
    mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
    if mapping_mutator is not None:
        mapping_mutator(mapping)
    validate = client.post(
        f"/api/lots/{lot_id}/mapping/validate",
        json=mapping_submission(mapping),
        headers={"X-Idempotency-Key": f"mapping-{key}"},
    )
    fusion_result = run_worker_once(settings=settings)
    normalization_result = run_worker_once(settings=settings)

    if upload.status_code != 202:
        raise AssertionError(upload.text)
    if validate.status_code != 200:
        raise AssertionError(validate.text)
    if diagnostic_result.outcome != "succeeded":
        raise AssertionError(diagnostic_result)
    if fusion_result.outcome != "succeeded":
        raise AssertionError(fusion_result)
    if normalization_result.outcome != "succeeded":
        raise AssertionError(normalization_result)
    return lot_id, mapping


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


def download_sort_payload(client: TestClient, settings, lot_id: str) -> dict[str, Any]:
    database = Database(settings.sqlite_path)
    with database.session() as repositories:
        step = repositories.steps.get_by_lot_key(lot_id, "tri_region_departement")
        if step is None or not step["current_run_id"]:
            raise AssertionError("Sort step has no current run.")
        artifact = repositories.artifacts.get_for_step_run_role(
            lot_id=lot_id,
            step_key="tri_region_departement",
            run_id=step["current_run_id"],
            role="result",
        )
        if artifact is None:
            raise AssertionError("Sort result artifact is missing.")

    response = client.get(f"/api/lots/{lot_id}/downloads/{artifact['id']}")
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


class SortDecisionApiTest(unittest.TestCase):
    def test_user_confirms_detected_region_department_sort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "tri.xlsx"
            create_sort_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id, _mapping = prepare_normalized_lot(
                client,
                settings,
                workbook_path,
                title="Lot tri",
                key="tri",
            )

            proposal = client.get(f"/api/lots/{lot_id}/tri")
            decision = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "tri-confirm"},
            )
            replay = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "tri-confirm"},
            )
            conflicting_replay = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "ordre_source"},
                headers={"X-Idempotency-Key": "tri-confirm"},
            )
            lot = client.get(f"/api/lots/{lot_id}").json()["lot"]
            payload = download_sort_payload(client, settings, lot_id)

        self.assertEqual(proposal.status_code, 200, proposal.text)
        self.assertEqual(proposal.json()["proposal"]["detection_status"], "detected")
        self.assertTrue(proposal.json()["proposal"]["can_sort"])
        self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["artifact"]["id"], decision.json()["artifact"]["id"])
        self.assertEqual(replay.json()["invalidated_steps"], [])
        self.assertEqual(conflicting_replay.status_code, 409)
        self.assertEqual(
            conflicting_replay.json()["error"]["code"],
            "SIRCOM_SORT_IDEMPOTENCY_REUSED",
        )
        self.assertEqual(step_status(lot, "tri_region_departement"), "termine")
        self.assertIn("previsualisation_csv", decision.json()["invalidated_steps"])
        self.assertIn("package_final", decision.json()["invalidated_steps"])

        self.assertEqual(payload["rules_version"], "sort-validation-v1")
        self.assertEqual(payload["decision"], "tri_region_departement")
        self.assertEqual(
            [row["id_dossier"] for row in payload["rows"]],
            ["ID-1", "ID-4", "ID-2", "ID-3", "ID-5"],
        )

    def test_user_confirms_source_order_when_sort_columns_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "sans-tri.xlsx"
            create_no_sort_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id, _mapping = prepare_normalized_lot(
                client,
                settings,
                workbook_path,
                title="Lot sans tri",
                key="sans-tri",
            )

            proposal = client.get(f"/api/lots/{lot_id}/tri")
            refused_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "tri-refused"},
            )
            decision = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "ordre_source"},
                headers={"X-Idempotency-Key": "tri-source"},
            )
            lot = client.get(f"/api/lots/{lot_id}").json()["lot"]
            payload = download_sort_payload(client, settings, lot_id)

        self.assertEqual(proposal.status_code, 200, proposal.text)
        self.assertEqual(proposal.json()["proposal"]["detection_status"], "missing")
        self.assertFalse(proposal.json()["proposal"]["can_sort"])
        self.assertEqual(refused_sort.status_code, 409)
        self.assertEqual(
            refused_sort.json()["error"]["code"],
            "SIRCOM_SORT_COLUMNS_NOT_CLEAR",
        )
        self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(step_status(lot, "tri_region_departement"), "termine_avec_alertes")
        self.assertEqual(payload["decision"], "ordre_source")
        self.assertEqual([row["id_dossier"] for row in payload["rows"]], ["ID-2", "ID-1"])
        alert_codes = {
            problem["code"]
            for problem in lot["problem_groups"]["alerte"]["items"]
        }
        self.assertIn("SIRCOM_SORT_COLUMNS_NOT_DETECTED", alert_codes)

    def test_ambiguous_sort_detection_does_not_auto_select_columns(self) -> None:
        def make_ambiguous(mapping: dict[str, Any]) -> None:
            find_column(mapping, "Dossiers", "D", "Nom produit")["logical_role"] = "region"

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "tri-ambigu.xlsx"
            create_sort_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id, _mapping = prepare_normalized_lot(
                client,
                settings,
                workbook_path,
                title="Lot tri ambigu",
                key="tri-ambigu",
                mapping_mutator=make_ambiguous,
            )

            proposal = client.get(f"/api/lots/{lot_id}/tri")
            refused_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "tri-ambiguous-refused"},
            )

        self.assertEqual(proposal.status_code, 200, proposal.text)
        self.assertEqual(proposal.json()["proposal"]["detection_status"], "ambiguous")
        self.assertFalse(proposal.json()["proposal"]["can_sort"])
        self.assertEqual(refused_sort.status_code, 409)
        self.assertEqual(
            refused_sort.json()["error"]["code"],
            "SIRCOM_SORT_COLUMNS_NOT_CLEAR",
        )


if __name__ == "__main__":
    unittest.main()
