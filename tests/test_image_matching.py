from __future__ import annotations

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
from sircom2026.image_matching import (
    EXPORT_IMAGES_FOLDER,
    build_image_matching_payload,
    build_processed_images_zip,
    image_id_for_dossier,
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


def image_bytes(
    size: tuple[int, int] = (12, 8),
    *,
    mode: str = "RGB",
    color: tuple[int, ...] = (20, 80, 120),
    image_format: str = "PNG",
) -> bytes:
    output = BytesIO()
    Image.new(mode, size, color).save(output, format=image_format)
    return output.getvalue()


def zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return output.getvalue()


def image_zip_file(content: bytes) -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("images.zip", content, "application/zip")}


def excel_file(path: Path) -> dict[str, tuple[str, bytes, str]]:
    return {
        "file": (
            path.name,
            path.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def normalized_payload(rows: list[tuple[str, str]]) -> dict[str, Any]:
    columns = [
        {
            "id": "Dossiers!A",
            "system": False,
            "source_sheet": "Dossiers",
            "source_column_letter": "A",
            "source_header": "id_dossier",
            "logical_role": "id_dossier",
            "csv_name": "id_dossier",
            "output_position": 1,
        },
        {
            "id": "system:imageid",
            "system": True,
            "source_sheet": None,
            "source_column_letter": None,
            "source_header": "Image InDesign générée",
            "logical_role": "nom_image_source",
            "csv_name": "imageid",
            "output_position": 2,
        },
        {
            "id": "system:@pathimg",
            "system": True,
            "source_sheet": None,
            "source_column_letter": None,
            "source_header": "Chemin image InDesign",
            "logical_role": "nom_image_source",
            "csv_name": "@pathimg",
            "output_position": 3,
        },
        {
            "id": "Dossiers!B",
            "system": False,
            "source_sheet": "Dossiers",
            "source_column_letter": "B",
            "source_header": "Photo",
            "logical_role": "nom_image_source",
            "csv_name": "b_photo",
            "output_position": 4,
        },
    ]
    payload_rows = []
    for index, (id_dossier, source_name) in enumerate(rows, start=1):
        payload_rows.append(
            {
                "source_rank": index,
                "id_dossier": id_dossier,
                "values": {
                    "id_dossier": id_dossier,
                    "imageid": "",
                    "@pathimg": "",
                    "b_photo": source_name,
                },
            }
        )
    return {
        "schema_version": 1,
        "rules_version": "content-normalisation-v1",
        "rows_count": len(payload_rows),
        "columns_count": len(columns),
        "columns": columns,
        "rows": payload_rows,
    }


def inspection_payload(names: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rules_version": "image-zip-inspection-v1",
        "inspectable": True,
        "image_count": len(names),
        "images": [
            {
                "name": name,
                "normalized_name": name.casefold(),
                "extension": Path(name).suffix.lower(),
                "size_bytes": 100,
                "compressed_size_bytes": 90,
            }
            for name in names
        ],
    }


def source_artifact() -> dict[str, Any]:
    return {
        "id": "artifact_source_zip",
        "sha256": "0" * 64,
    }


def row_by_id(matching: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {binding["id_dossier"]: binding for binding in matching["bindings"]}


def create_image_matching_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dossiers"
    sheet.append(["id_dossier", "Photo", "Nom produit"])
    sheet.append(["ID-1", "produit.jpg", "Produit un"])
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


def run_until_step(settings, step_key: str, *, limit: int = 8):
    last_result = None
    for _ in range(limit):
        last_result = run_worker_once(settings=settings)
        if last_result.outcome not in {"succeeded", "idle"}:
            raise AssertionError(last_result)
        if last_result.step_key == step_key:
            return last_result
    raise AssertionError(f"{step_key} not reached, last result: {last_result}")


class ImageMatchingRulesTest(unittest.TestCase):
    def test_matches_exact_tolerant_fallback_missing_and_unreferenced_images(self) -> None:
        matching = build_image_matching_payload(
            normalized_payload(
                [
                    ("ID-EXACT", "photo-produit.jpg"),
                    ("ID-TOL", "Photo Deux.JPG"),
                    ("ABC-3", ""),
                    ("ID-MISSING", "absente.jpg"),
                ]
            ),
            inspection_payload(
                [
                    "photo-produit.jpg",
                    "photo_deux.png",
                    "dossier-abc-3.webp",
                    "orpheline.jpg",
                ]
            ),
            source_image_zip_artifact=source_artifact(),
            source_normalization_artifact_id="artifact_normalized",
            source_inspection_artifact_id="artifact_inspection",
            indesign_image_root="/Users/victoria/Documents/export-jpg-resize",
        )

        rows = row_by_id(matching)
        self.assertEqual(rows["ID-EXACT"]["status"], "matched")
        self.assertEqual(rows["ID-EXACT"]["match_level"], "original_exact")
        self.assertEqual(rows["ID-EXACT"]["source_zip_fingerprint"], "0" * 64)
        self.assertEqual(len(rows["ID-EXACT"]["rules_fingerprint"]), 64)
        self.assertEqual(rows["ID-TOL"]["status"], "matched")
        self.assertEqual(rows["ID-TOL"]["match_level"], "original_tolerant")
        self.assertEqual(rows["ABC-3"]["status"], "matched")
        self.assertTrue(rows["ABC-3"]["fallback_used"])
        self.assertTrue(rows["ABC-3"]["match_level"].startswith("id_fallback"))
        self.assertEqual(rows["ID-MISSING"]["status"], "missing")
        self.assertEqual(rows["ID-MISSING"]["imageid"], "dossier-id-missing.jpg")
        self.assertEqual(rows["ID-MISSING"]["pathimg"], "")
        self.assertEqual(matching["matched_count"], 3)
        self.assertEqual(matching["missing_count"], 1)
        self.assertEqual(matching["fallback_count"], 1)
        self.assertEqual(matching["tolerant_count"], 1)
        self.assertEqual(matching["unreferenced_count"], 1)
        self.assertEqual(matching["unreferenced_images"][0]["source_name"], "orpheline.jpg")

    def test_partial_similarity_is_a_suggestion_not_an_automatic_match(self) -> None:
        matching = build_image_matching_payload(
            normalized_payload([("ID-PARTIAL", "produit.jpg")]),
            inspection_payload(["produit-retouche.jpg"]),
            source_image_zip_artifact=source_artifact(),
            source_normalization_artifact_id="artifact_normalized",
            source_inspection_artifact_id="artifact_inspection",
            indesign_image_root="/Users/victoria/Documents/export-jpg-resize",
        )

        binding = matching["bindings"][0]
        self.assertTrue(matching["blocking"])
        self.assertEqual(binding["status"], "ambiguous")
        self.assertEqual(binding["match_level"], "partial_suggestion")
        self.assertEqual(binding["source_name"], None)
        self.assertEqual(binding["suggestions"][0]["name"], "produit-retouche.jpg")

    def test_tolerant_ambiguity_blocks_until_manual_resolution(self) -> None:
        unresolved = build_image_matching_payload(
            normalized_payload([("ID-A", "Photo A.jpg")]),
            inspection_payload(["photo-a.jpg", "photo_a.png"]),
            source_image_zip_artifact=source_artifact(),
            source_normalization_artifact_id="artifact_normalized",
            source_inspection_artifact_id="artifact_inspection",
            indesign_image_root="/Users/victoria/Documents/export-jpg-resize",
        )
        resolved = build_image_matching_payload(
            normalized_payload([("ID-A", "Photo A.jpg")]),
            inspection_payload(["photo-a.jpg", "photo_a.png"]),
            source_image_zip_artifact=source_artifact(),
            source_normalization_artifact_id="artifact_normalized",
            source_inspection_artifact_id="artifact_inspection",
            indesign_image_root="/Users/victoria/Documents/export-jpg-resize",
            manual_resolutions={"ID-A": "photo_a.png"},
        )

        self.assertTrue(unresolved["blocking"])
        self.assertEqual(unresolved["bindings"][0]["status"], "ambiguous")
        self.assertEqual(
            [candidate["name"] for candidate in unresolved["bindings"][0]["candidates"]],
            ["photo-a.jpg", "photo_a.png"],
        )
        self.assertFalse(resolved["blocking"])
        self.assertEqual(resolved["bindings"][0]["status"], "matched")
        self.assertEqual(resolved["bindings"][0]["match_level"], "manual")
        self.assertEqual(resolved["bindings"][0]["source_name"], "photo_a.png")

    def test_processed_zip_converts_to_final_jpg_folder_and_updates_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "images.zip"
            source = Image.new("RGBA", (700, 200), (0, 0, 0, 0))
            payload = BytesIO()
            source.save(payload, format="PNG")
            zip_path.write_bytes(zip_bytes([("wide.PNG", payload.getvalue())]))
            matching = build_image_matching_payload(
                normalized_payload([("ID. 4-A", "wide.png")]),
                inspection_payload(["wide.PNG"]),
                source_image_zip_artifact=source_artifact(),
                source_normalization_artifact_id="artifact_normalized",
                source_inspection_artifact_id="artifact_inspection",
                indesign_image_root="/Users/victoria/Documents/export-jpg-resize",
            )

            processed = build_processed_images_zip(zip_path, matching)

            with zipfile.ZipFile(BytesIO(processed)) as archive:
                names = archive.namelist()
                final_name = image_id_for_dossier("ID. 4-A")
                content = archive.read(f"{EXPORT_IMAGES_FOLDER}/{final_name}")
            with Image.open(BytesIO(content)) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (350, 100))
                self.assertEqual(tuple(round(value) for value in image.info["dpi"]), (300, 300))
                self.assertGreater(image.getpixel((0, 0))[0], 240)

        binding = matching["bindings"][0]
        self.assertIn(f"{EXPORT_IMAGES_FOLDER}/", names)
        self.assertEqual(binding["final_name"], "dossier-id4-a.jpg")
        self.assertEqual(binding["status"], "matched")
        self.assertEqual(len(binding["final_sha256"]), 64)
        self.assertEqual(
            binding["pathimg"],
            "/Users/victoria/Documents/export-jpg-resize/dossier-id4-a.jpg",
        )


class ImageMatchingApiTest(unittest.TestCase):
    def test_matching_is_enqueued_after_normalization_when_images_are_inspected_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "images-first.xlsx"
            create_image_matching_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot images d'abord"}).json()["lot"]["id"]

            upload_images = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file(zip_bytes([("produit.jpg", image_bytes())])),
                headers={"X-Idempotency-Key": "first-images-upload-zip"},
            )
            inspection = run_until_step(settings, "inspection_images")

            upload_excel = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "first-images-upload-excel"},
            )
            run_until_step(settings, "diagnostic_excel")
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "first-images-mapping"},
            )
            run_until_step(settings, "fusion_multi_onglets")
            normalization = run_until_step(settings, "normalisation_contenu")
            matching = run_until_step(settings, "matching_images")
            matching_payload = client.get(f"/api/lots/{lot_id}/images/matching")

        self.assertEqual(upload_images.status_code, 202, upload_images.text)
        self.assertEqual(inspection.outcome, "succeeded")
        self.assertEqual(upload_excel.status_code, 202, upload_excel.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        self.assertEqual(normalization.outcome, "succeeded")
        self.assertEqual(matching.outcome, "succeeded")
        self.assertEqual(matching_payload.status_code, 200, matching_payload.text)
        self.assertEqual(matching_payload.json()["matching"]["matched_count"], 1)

    def test_worker_blocks_partial_match_then_persists_manual_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            workbook_path = tmpdir / "fixtures" / "images.xlsx"
            create_image_matching_workbook(workbook_path)
            settings = make_settings(tmpdir)
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot images"}).json()["lot"]["id"]

            upload_excel = client.post(
                f"/api/lots/{lot_id}/excel",
                files=excel_file(workbook_path),
                headers={"X-Idempotency-Key": "images-upload-excel"},
            )
            run_until_step(settings, "diagnostic_excel")
            mapping = client.get(f"/api/lots/{lot_id}/mapping").json()["mapping"]
            validate_mapping = client.post(
                f"/api/lots/{lot_id}/mapping/validate",
                json=mapping_submission(mapping),
                headers={"X-Idempotency-Key": "images-mapping"},
            )
            run_until_step(settings, "fusion_multi_onglets")
            run_until_step(settings, "normalisation_contenu")
            upload_images = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file(zip_bytes([("produit-retouche.png", image_bytes())])),
                headers={"X-Idempotency-Key": "images-upload-zip"},
            )
            run_until_step(settings, "inspection_images")
            first_matching = run_until_step(settings, "matching_images")
            blocked_matching = client.get(f"/api/lots/{lot_id}/images/matching")

            resolution = client.post(
                f"/api/lots/{lot_id}/images/resolutions",
                json={
                    "resolutions": [
                        {
                            "id_dossier": "ID-1",
                            "source_name": "produit-retouche.png",
                        }
                    ]
                },
                headers={"X-Idempotency-Key": "images-resolution"},
            )
            second_matching = run_until_step(settings, "matching_images")
            resolved_matching = client.get(f"/api/lots/{lot_id}/images/matching")
            processed_download = client.get(
                resolved_matching.json()["processed_images_artifact"]["download_url"]
            )
            validate_sort = client.post(
                f"/api/lots/{lot_id}/tri/validate",
                json={"decision": "ordre_source"},
                headers={"X-Idempotency-Key": "images-sort"},
            )
            preview = client.get(f"/api/lots/{lot_id}/csv/preview")
            validate_preview = client.post(
                f"/api/lots/{lot_id}/csv/preview/validate",
                headers={"X-Idempotency-Key": "images-preview"},
            )
            csv_download = client.get(validate_preview.json()["csv_artifact"]["download_url"])
            lot = client.get(f"/api/lots/{lot_id}").json()["lot"]
            html = client.get(f"/?lot_id={lot_id}")
            database = Database(settings.sqlite_path)
            with database.session() as repositories:
                step = repositories.steps.get_by_lot_key(lot_id, "matching_images")
                summary = step["summary_json"] if step else ""

        self.assertEqual(upload_excel.status_code, 202, upload_excel.text)
        self.assertEqual(validate_mapping.status_code, 200, validate_mapping.text)
        self.assertEqual(upload_images.status_code, 202, upload_images.text)
        self.assertEqual(first_matching.outcome, "succeeded")
        self.assertEqual(blocked_matching.status_code, 200, blocked_matching.text)
        self.assertTrue(blocked_matching.json()["matching"]["blocking"])
        self.assertEqual(
            blocked_matching.json()["matching"]["bindings"][0]["status"],
            "ambiguous",
        )
        self.assertEqual(resolution.status_code, 202, resolution.text)
        self.assertIn("package_final", resolution.json()["invalidated_steps"])
        self.assertEqual(resolution.json()["job"]["step_key"], "matching_images")
        self.assertEqual(second_matching.outcome, "succeeded")
        self.assertEqual(resolved_matching.status_code, 200, resolved_matching.text)
        matching_payload = resolved_matching.json()["matching"]
        self.assertFalse(matching_payload["blocking"])
        self.assertEqual(matching_payload["matched_count"], 1)
        self.assertEqual(matching_payload["processed_images_count"], 1)
        self.assertEqual(matching_payload["bindings"][0]["match_level"], "manual")
        self.assertEqual(processed_download.status_code, 200)
        with zipfile.ZipFile(BytesIO(processed_download.content)) as archive:
            self.assertIn("export-jpg-resize/dossier-id-1.jpg", archive.namelist())
        self.assertEqual(validate_sort.status_code, 200, validate_sort.text)
        self.assertEqual(preview.status_code, 200, preview.text)
        preview_payload = preview.json()["preview"]
        self.assertEqual(
            preview_payload["rows"][0]["values"]["imageid"],
            "dossier-id-1.jpg",
        )
        self.assertEqual(
            preview_payload["rows"][0]["values"]["@pathimg"],
            "/Users/victoria/Documents/export-jpg-resize/dossier-id-1.jpg",
        )
        self.assertEqual(validate_preview.status_code, 200, validate_preview.text)
        self.assertIn("dossier-id-1.jpg", csv_download.content.decode("utf-16"))
        self.assertIn(
            "/Users/victoria/Documents/export-jpg-resize/dossier-id-1.jpg",
            csv_download.content.decode("utf-16"),
        )
        self.assertIn("produit-retouche.png", summary)
        self.assertEqual(step_status(lot, "matching_images"), "termine")
        self.assertEqual(html.status_code, 200)
        self.assertIn("Association images", html.text)
        self.assertIn("Télécharger les images traitées", html.text)


def step_status(lot: dict[str, object], step_key: str) -> str:
    for step in lot["steps"]:
        if step["key"] == step_key:
            return str(step["status"])
    raise AssertionError(f"Missing step {step_key}.")


if __name__ == "__main__":
    unittest.main()
