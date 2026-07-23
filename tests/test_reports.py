from __future__ import annotations

import inspect
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

import sircom2026.reports as reports_module
from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.database import Database
from sircom2026.reports import (
    BUSINESS_REPORT_ARTIFACT_KIND,
    BUSINESS_REPORT_ARTIFACT_ROLE,
    BUSINESS_REPORT_FILENAME,
    BUSINESS_REPORT_MIME_TYPE,
    REPORTS_RULES_VERSION,
    REPORTS_SCHEMA_VERSION,
    REPORTS_STEP_KEY,
    TECHNICAL_REPORT_ARTIFACT_KIND,
    TECHNICAL_REPORT_ARTIFACT_ROLE,
    TECHNICAL_REPORT_FILENAME,
    TECHNICAL_REPORT_MIME_TYPE,
    CurrentJsonArtifact,
    PersistedReports,
    ReportsNotReady,
    ReportsPrerequisiteMissing,
)
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
    sheet.append(
        [None, "Bretagne", "22", "sans-id.png", "Produit Sans ID", "Entreprise", None]
    )
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


class ReportsPublicContractTest(unittest.TestCase):
    def test_public_reports_module_contract_entries_are_stable(self) -> None:
        public_callables = {
            "run_reports_job",
            "get_persisted_reports",
            "build_business_report",
            "build_technical_report",
        }

        for name in public_callables:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(reports_module, name, None)))

        public_signatures = {
            "run_reports_job": ("context", "settings"),
            "get_persisted_reports": ("repositories", "settings", "lot_id"),
            "build_business_report": ("snapshot", "generated_at"),
            "build_technical_report": ("snapshot", "generated_at"),
        }
        for name, expected_parameters in public_signatures.items():
            with self.subTest(signature=name):
                signature = inspect.signature(getattr(reports_module, name))
                self.assertEqual(tuple(signature.parameters), expected_parameters)

        self.assertEqual(
            inspect.signature(reports_module.get_persisted_reports)
            .parameters["settings"]
            .kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        self.assertEqual(
            inspect.signature(reports_module.get_persisted_reports)
            .parameters["lot_id"]
            .kind,
            inspect.Parameter.KEYWORD_ONLY,
        )

        self.assertEqual(REPORTS_STEP_KEY, "rapports")
        self.assertEqual(REPORTS_RULES_VERSION, "reports-v1")
        self.assertEqual(REPORTS_SCHEMA_VERSION, 1)
        self.assertEqual(BUSINESS_REPORT_ARTIFACT_KIND, "markdown")
        self.assertEqual(BUSINESS_REPORT_ARTIFACT_ROLE, "rapport-metier")
        self.assertEqual(BUSINESS_REPORT_FILENAME, "rapport-metier.md")
        self.assertEqual(BUSINESS_REPORT_MIME_TYPE, "text/markdown; charset=utf-8")
        self.assertEqual(TECHNICAL_REPORT_ARTIFACT_KIND, "json")
        self.assertEqual(TECHNICAL_REPORT_ARTIFACT_ROLE, "rapport-technique")
        self.assertEqual(TECHNICAL_REPORT_FILENAME, "rapport-technique.json")
        self.assertEqual(TECHNICAL_REPORT_MIME_TYPE, "application/json")
        self.assertEqual(
            tuple(CurrentJsonArtifact.__dataclass_fields__),
            ("artifact", "payload"),
        )
        self.assertEqual(
            tuple(PersistedReports.__dataclass_fields__),
            ("business_artifact", "technical_artifact"),
        )
        self.assertTrue(issubclass(ReportsNotReady, RuntimeError))
        prerequisite_error = ReportsPrerequisiteMissing("rapports", "result")
        self.assertEqual(prerequisite_error.step_key, "rapports")
        self.assertEqual(prerequisite_error.role, "result")


class ReportsApiTest(unittest.TestCase):
    def test_reports_are_generated_and_technical_surfaces_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "rapports.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot rapports"}).json()[
                "lot"
            ]["id"]

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
            html = client.get(f"/?lot_id={lot_id}&view=rapports")
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
        for result in (
            inspection,
            diagnostic,
            fusion,
            normalization,
            csv_contract,
            matching,
        ):
            self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(reports_job.outcome, "succeeded")
        self.assertEqual(reports.status_code, 200, reports.text)
        self.assertEqual(report_step["status"], "termine_avec_alertes")
        self.assertEqual(lot["status"], "action_requise")
        report_payload = reports.json()
        artifact_fields = {
            "id",
            "kind",
            "role",
            "status",
            "size_bytes",
            "sha256",
            "mime_type",
            "download_url",
        }
        self.assertEqual(
            set(report_payload),
            {"business_report_artifact", "technical_report_artifact"},
        )
        self.assertEqual(
            artifact_fields,
            set(report_payload["business_report_artifact"]),
        )
        self.assertEqual(
            artifact_fields,
            set(report_payload["technical_report_artifact"]),
        )
        self.assertEqual(report_payload["business_report_artifact"]["kind"], "markdown")
        self.assertEqual(
            report_payload["business_report_artifact"]["role"], "rapport-metier"
        )
        self.assertEqual(report_payload["technical_report_artifact"]["kind"], "json")
        self.assertEqual(
            report_payload["technical_report_artifact"]["role"], "rapport-technique"
        )

        business_text = business_download.content.decode("utf-8")
        self.assertIn(
            "rapport-metier.md", business_download.headers["content-disposition"]
        )
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
        self.assertIn(
            "| Dossiers | A | id_dossier | id_dossier | exporte |", business_text
        )
        self.assertIn("| Dossiers | E | Nom produit |", business_text)
        self.assertIn("Lignes supprimées sans id_dossier : 1", business_text)
        self.assertIn("Images présentes : 1", business_text)
        self.assertIn("Images ignorées : 1", business_text)
        self.assertIn("plan-secret-client.png", business_text)

        technical = technical_download.json()
        self.assertIn(
            "rapport-technique.json", technical_download.headers["content-disposition"]
        )
        self.assertEqual(technical["schema_version"], 1)
        self.assertEqual(technical["rules_version"], "reports-v1")
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
        self.assertEqual(
            set(technical["resume_execution"]),
            {"lot_id", "status", "open_problem_counts"},
        )
        self.assertIn("duration_ms", technical["etapes"][0])
        self.assertTrue(
            all(
                {
                    "step_key",
                    "status",
                    "run_id",
                    "input_fingerprint",
                    "output_fingerprint",
                    "progress_current",
                    "progress_total",
                    "duration_ms",
                }
                == set(step)
                for step in technical["etapes"]
            )
        )
        self.assertEqual(
            set(technical["compteurs"]),
            {"excel", "fusion", "normalisation", "csv", "images"},
        )
        compteur_fields = {
            "excel": {"sheets_count", "blockers_count", "warnings_count"},
            "fusion": {
                "source_rows_count",
                "rows_count",
                "rows_removed",
                "columns_count",
            },
            "normalisation": {
                "rows_count",
                "columns_count",
                "date_issues_count",
                "invalid_dates_count",
                "missing_dates_count",
            },
            "csv": {"rows_count", "columns_count", "size_bytes"},
            "images": {
                "rows_count",
                "missing_count",
                "ambiguous_count",
                "processed_images_count",
                "unreferenced_count",
                "conversion_failed_count",
                "tolerant_count",
            },
        }
        for name, expected_fields in compteur_fields.items():
            with self.subTest(compteur=name):
                self.assertEqual(set(technical["compteurs"][name]), expected_fields)
                self.assertTrue(
                    all(
                        isinstance(value, int)
                        for value in technical["compteurs"][name].values()
                    )
                )
        self.assertEqual(technical["compteurs"]["csv"]["rows_count"], 1)
        self.assertGreater(technical["compteurs"]["csv"]["size_bytes"], 0)
        self.assertEqual(technical["compteurs"]["images"]["processed_images_count"], 1)
        self.assertIn(
            "SIRCOM_IMAGE_MATCHING_UNREFERENCED", str(technical["codes_erreur"])
        )
        self.assertTrue(technical["codes_erreur"])
        self.assertTrue(
            all(
                set(error_code) == {"severity", "code", "count"}
                for error_code in technical["codes_erreur"]
            )
        )
        source_fields = {
            "artifact_id",
            "step_key",
            "run_id",
            "kind",
            "role",
            "status",
            "size_bytes",
            "sha256",
            "mime_type",
        }
        self.assertTrue(technical["sources"])
        self.assertTrue(
            all(set(source) == source_fields for source in technical["sources"])
        )
        self.assertTrue(
            all(source["status"] == "committed" for source in technical["sources"])
        )
        self.assertTrue(
            all(source["size_bytes"] > 0 for source in technical["sources"])
        )
        self.assertTrue(
            all(len(source["sha256"]) == 64 for source in technical["sources"])
        )
        self.assertFalse(
            any("relative_path" in source for source in technical["sources"])
        )
        source_steps = {
            (source["step_key"], source["role"]) for source in technical["sources"]
        }
        self.assertIn(("matching_images", "processed_images"), source_steps)
        trace_fields = {
            "created_at",
            "event_type",
            "step_key",
            "run_id",
            "level",
            "payload",
        }
        self.assertTrue(technical["traces_anonymisees"])
        self.assertTrue(
            all(set(trace) == trace_fields for trace in technical["traces_anonymisees"])
        )
        for trace in technical["traces_anonymisees"]:
            self.assertIsInstance(trace["payload"], dict)
            for value in trace["payload"].values():
                self.assertIsInstance(value, str | int | float | bool | type(None))
                if isinstance(value, str):
                    self.assertNotIn("/", value)
                    self.assertNotIn("\\", value)
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

    def test_reports_are_generated_without_image_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "rapports-sans-images.xlsx"
            create_reports_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot sans images"}).json()[
                "lot"
            ]["id"]

            upload_excel = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "reports-no-images-excel"},
            )
            diagnostic = run_until_step(settings, "diagnostic_excel")
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "reports-no-images-mapping"},
            )
            fusion = run_until_step(settings, "fusion_multi_onglets")
            normalization = run_until_step(settings, "normalisation_contenu")
            csv_contract = run_until_step(settings, "verification_csv_indesign")
            validate_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "tri_region_departement"},
                headers={"X-Idempotency-Key": "reports-no-images-sort"},
            )
            validate_preview = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "reports-no-images-preview"},
            )
            reports_job = run_until_step(settings, "rapports")
            reports = client.get(f"/api/lots/{lot_id}/reports")
            business_download = client.get(
                reports.json()["business_report_artifact"]["download_url"]
            )
            technical_download = client.get(
                reports.json()["technical_report_artifact"]["download_url"]
            )
            database = Database(settings.sqlite_path)
            with database.session() as repositories:
                report_step = repositories.steps.get_by_lot_key(lot_id, "rapports")
                matching_step = repositories.steps.get_by_lot_key(
                    lot_id, "matching_images"
                )
                problem_codes = [
                    problem["code"]
                    for problem in repositories.problems.list_for_lot(
                        lot_id,
                        include_resolved=True,
                    )
                ]

        self.assertEqual(upload_excel.status_code, 202, upload_excel.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        self.assertEqual(validate_sort.status_code, 200, validate_sort.text)
        self.assertEqual(validate_preview.status_code, 200, validate_preview.text)
        for result in (diagnostic, fusion, normalization, csv_contract, reports_job):
            self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(reports.status_code, 200, reports.text)
        self.assertIn(report_step["status"], {"termine", "termine_avec_alertes"})
        self.assertNotIn(matching_step["status"], {"termine", "termine_avec_alertes"})
        self.assertNotIn("SIRCOM_REPORTS_PREREQUISITE_MISSING", problem_codes)

        business_text = business_download.content.decode("utf-8")
        self.assertIn("Zip images : non fourni", business_text)
        self.assertIn("Images détectées dans le zip : 0", business_text)
        self.assertIn("Flux images : aucun zip images fourni", business_text)
        self.assertIn("Images présentes : 0", business_text)
        self.assertIn(
            "Images renommées et optimisées : aucune image fournie", business_text
        )

        technical = technical_download.json()
        self.assertEqual(technical["compteurs"]["images"]["processed_images_count"], 0)
        self.assertEqual(technical["compteurs"]["images"]["missing_count"], 0)
        source_steps = {
            (source["step_key"], source["role"]) for source in technical["sources"]
        }
        self.assertNotIn(("upload_images", "source"), source_steps)
        self.assertNotIn(("inspection_images", "result"), source_steps)
        self.assertNotIn(("matching_images", "result"), source_steps)
        self.assertNotIn(("matching_images", "processed_images"), source_steps)


if __name__ == "__main__":
    unittest.main()
