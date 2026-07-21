from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from openpyxl import Workbook
from PIL import Image

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


def image_zip_file(content: bytes) -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("images-confidentielles.zip", content, "application/zip")}


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (20, 12), (30, 90, 150)).save(output, format="PNG")
    return output.getvalue()


def zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return output.getvalue()


def create_reports_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dossiers"
    sheet.append(
        [
            "id_dossier",
            "Région",
            "Département",
            "Photo",
            "Nom produit",
            "Entreprise",
            "Colonne vide",
        ]
    )
    sheet.append(
        [
            "ID-2",
            "Bretagne",
            "35",
            "photo-produit-secret.png",
            "Produit Secret Alpha",
            "Entreprise Confidentielle",
            None,
        ]
    )
    sheet.append([None, "Bretagne", "22", "sans-id.png", "Produit Sans ID", "Entreprise", None])
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


def run_until_step(settings, step_key: str, *, limit: int = 12):
    last_result = None
    for _ in range(limit):
        last_result = run_worker_once(settings=settings)
        if last_result.outcome not in {"succeeded", "idle"}:
            raise AssertionError(last_result)
        if last_result.step_key == step_key:
            return last_result
    raise AssertionError(f"{step_key} not reached, last result: {last_result}")


def run_until_steps(settings, step_keys: set[str], *, limit: int = 16):
    pending = set(step_keys)
    results = {}
    last_result = None
    for _ in range(limit):
        last_result = run_worker_once(settings=settings)
        if last_result.outcome not in {"succeeded", "idle"}:
            raise AssertionError(last_result)
        if last_result.step_key in pending:
            results[last_result.step_key] = last_result
            pending.remove(last_result.step_key)
        if not pending:
            return results
        if last_result.outcome == "idle":
            break
    raise AssertionError(f"{sorted(pending)} not reached, last result: {last_result}")


class ReportsApiTest(unittest.TestCase):
    def test_reports_are_generated_and_technical_surfaces_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "rapports.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot rapports"}).json()["lot"]["id"]

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
                headers={"X-Idempotency-Key": "reports-images"},
            )
            inspection = run_until_step(settings, "inspection_images")
            upload_excel = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "reports-excel"},
            )
            diagnostic = run_until_step(settings, "diagnostic_excel")
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "reports-mapping"},
            )
            fusion = run_until_step(settings, "fusion_multi_onglets")
            normalization = run_until_step(settings, "normalisation_contenu")
            after_normalization = run_until_steps(
                settings,
                {"verification_csv_indesign", "matching_images"},
            )
            csv_contract = after_normalization["verification_csv_indesign"]
            matching = after_normalization["matching_images"]
            validate_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "reports-sort"},
            )
            validate_preview = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "reports-preview"},
            )
            reports_job = run_until_step(settings, "rapports")
            reports = client.get(f"/api/lots/{lot_id}/reports")
            business_download = client.get(
                reports.json()["business_report_artifact"]["download_url"]
            )
            technical_download = client.get(
                reports.json()["technical_report_artifact"]["download_url"]
            )
            html = client.get(f"/?lot_id={lot_id}")
            database = Database(settings.sqlite_path)
            with database.session() as repositories:
                lot = repositories.lots.get_required(lot_id)
                report_step = repositories.steps.get_by_lot_key(lot_id, "rapports")
                events_text = json.dumps(
                    [
                        {
                            "event_type": event["event_type"],
                            "payload_json": event["payload_json"],
                        }
                        for event in repositories.events.list_for_lot(lot_id, limit=200)
                    ],
                    ensure_ascii=False,
                )

        self.assertEqual(upload_images.status_code, 202, upload_images.text)
        self.assertEqual(upload_excel.status_code, 202, upload_excel.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        self.assertEqual(validate_sort.status_code, 200, validate_sort.text)
        self.assertEqual(validate_preview.status_code, 200, validate_preview.text)
        for result in (inspection, diagnostic, fusion, normalization, csv_contract, matching):
            self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(reports_job.outcome, "succeeded")
        self.assertEqual(reports.status_code, 200, reports.text)
        self.assertEqual(report_step["status"], "termine_avec_alertes")
        self.assertEqual(lot["status"], "en_cours")

        business_text = business_download.content.decode("utf-8")
        self.assertIn("rapport-metier.md", business_download.headers["content-disposition"])
        for section in (
            "## Résumé du lot",
            "## Entrées",
            "## Décisions utilisateur",
            "## Diagnostic Excel",
            "## Mapping",
            "## Fusion et normalisation",
            "## CSV",
            "## Images",
            "## Intégrité",
            "## Package",
            "## Actions attendues",
        ):
            self.assertIn(section, business_text)
        self.assertIn("| Dossiers | A | id_dossier | id_dossier | exporte |", business_text)
        self.assertIn("| Dossiers | E | Nom produit |", business_text)
        self.assertIn("Lignes supprimées sans id_dossier : 1", business_text)
        self.assertIn("Images présentes : 1", business_text)
        self.assertIn("Images ignorées : 1", business_text)
        self.assertIn("plan-secret-client.png", business_text)

        technical = technical_download.json()
        self.assertIn("rapport-technique.json", technical_download.headers["content-disposition"])
        self.assertEqual(
            set(technical),
            {
                "schema_version",
                "rules_version",
                "generated_at",
                "resume_execution",
                "sources",
                "etapes",
                "compteurs",
                "codes_erreur",
                "traces_anonymisees",
            },
        )
        self.assertIn("duration_ms", technical["etapes"][0])
        self.assertEqual(technical["compteurs"]["csv"]["rows_count"], 1)
        self.assertEqual(technical["compteurs"]["images"]["processed_images_count"], 1)
        self.assertIn("SIRCOM_IMAGE_MATCHING_UNREFERENCED", str(technical["codes_erreur"]))
        self.assertEqual(html.status_code, 200)
        self.assertIn("Télécharger le rapport métier", html.text)
        self.assertIn("Télécharger le rapport technique", html.text)

        sensitive_values = (
            "Produit Secret Alpha",
            "Entreprise Confidentielle",
            "photo-produit-secret.png",
            "plan-secret-client.png",
            "ID-2",
            "sans-id.png",
        )
        technical_text = json.dumps(technical, ensure_ascii=False)
        for sensitive_value in sensitive_values:
            self.assertNotIn(sensitive_value, technical_text)
            self.assertNotIn(sensitive_value, events_text)


if __name__ == "__main__":
    unittest.main()
