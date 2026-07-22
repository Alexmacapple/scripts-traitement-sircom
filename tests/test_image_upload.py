from __future__ import annotations

import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from sircom2026.app import create_app
from sircom2026.config import load_settings
from sircom2026.worker_runner import run_worker_once


def make_settings(
    tmpdir: Path,
    *,
    max_zip_mb: int = 50,
    max_unzipped_mb: int = 50,
    max_image_count: int = 10,
    max_image_mb: int = 5,
):
    return load_settings(
        {
            "SIRCOM_DATA_DIR": str(tmpdir / "data"),
            "SIRCOM_SQLITE_PATH": str(tmpdir / "data" / "sircom.sqlite3"),
            "SIRCOM_DISK_FREE_MIN_MB": "0",
            "SIRCOM_MAX_ZIP_MB": str(max_zip_mb),
            "SIRCOM_MAX_UNZIPPED_MB": str(max_unzipped_mb),
            "SIRCOM_MAX_IMAGE_COUNT": str(max_image_count),
            "SIRCOM_MAX_IMAGE_MB": str(max_image_mb),
        }
    )


def zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return output.getvalue()


def zip_bytes_with_encrypted_flag(entries: list[tuple[str, bytes]]) -> bytes:
    content = bytearray(zip_bytes(entries))
    for signature, flags_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        start = 0
        while True:
            index = content.find(signature, start)
            if index < 0:
                break
            offset = index + flags_offset
            flags = int.from_bytes(content[offset : offset + 2], "little") | 0x1
            content[offset : offset + 2] = flags.to_bytes(2, "little")
            start = index + 4
    return bytes(content)


def image_zip_file(
    filename: str,
    content: bytes,
    content_type: str = "application/zip",
) -> dict[str, tuple[str, bytes, str]]:
    return {"file": (filename, content, content_type)}


class ImageZipUploadApiTest(unittest.TestCase):
    def test_valid_zip_is_stored_and_schedules_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot images"}).json()["lot"][
                "id"
            ]
            content = zip_bytes(
                [
                    ("photo-1.JPG", b"image-1"),
                    ("photo-2.png", b"image-2"),
                    ("__MACOSX/._photo-1.JPG", b"mac"),
                    (".DS_Store", b"finder"),
                ]
            )

            response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("../photos-secretes.zip", content),
                headers={"X-Idempotency-Key": "upload-images-1"},
            )
            payload = response.json()
            artifact = payload["artifact"]
            inspection_job = payload["job"]
            source_download = client.get(f"/api/lots/{lot_id}/downloads/{artifact['id']}")

            worker_result = run_worker_once(settings=settings)
            status_response = client.get(f"/api/lots/{lot_id}/images/status")
            lot_response = client.get(f"/api/lots/{lot_id}")
            ui_response = client.get(f"/?lot_id={lot_id}&view=inspection_images")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(artifact["kind"], "zip")
        self.assertEqual(artifact["role"], "source")
        self.assertEqual(artifact["status"], "committed")
        self.assertEqual(artifact["size_bytes"], len(content))
        self.assertEqual(len(artifact["sha256"]), 64)
        self.assertNotIn("relative_path", artifact)
        self.assertNotIn("photos-secretes", str(payload))
        self.assertEqual(inspection_job["step_key"], "inspection_images")
        self.assertEqual(inspection_job["status"], "queued")
        self.assertEqual(step_status(payload["lot"], "upload_images"), "termine")
        self.assertEqual(step_status(payload["lot"], "inspection_images"), "pret")
        self.assertEqual(source_download.status_code, 200)
        self.assertEqual(source_download.content, content)

        self.assertTrue(worker_result.processed)
        self.assertEqual(worker_result.outcome, "succeeded")
        self.assertEqual(worker_result.step_key, "inspection_images")
        self.assertEqual(status_response.status_code, 200)
        inspection = status_response.json()["inspection"]
        self.assertTrue(inspection["inspectable"])
        self.assertEqual(inspection["image_count"], 2)
        self.assertEqual(
            [image["name"] for image in inspection["images"]],
            ["photo-1.JPG", "photo-2.png"],
        )
        self.assertEqual(inspection["ignored_entries_count"], 2)
        self.assertEqual(step_status(lot_response.json()["lot"], "inspection_images"), "termine")
        self.assertEqual(ui_response.status_code, 200)
        self.assertIn("Inspection images", ui_response.text)
        self.assertIn("photo-1.JPG", ui_response.text)

    def test_new_zip_upload_replaces_previous_source_and_invalidates_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot nouveau zip"}).json()["lot"][
                "id"
            ]

            first_response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("premier.zip", zip_bytes([("a.jpg", b"a")])),
                headers={"X-Idempotency-Key": "upload-images-first"},
            )
            first_artifact_id = first_response.json()["artifact"]["id"]
            second_response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("second.zip", zip_bytes([("b.jpg", b"b")])),
                headers={"X-Idempotency-Key": "upload-images-second"},
            )
            payload = second_response.json()
            old_download = client.get(f"/api/lots/{lot_id}/downloads/{first_artifact_id}")
            new_download = client.get(payload["artifact"]["download_url"])

        self.assertEqual(second_response.status_code, 202)
        self.assertEqual(old_download.status_code, 404)
        self.assertEqual(new_download.status_code, 200)
        self.assertIn("inspection_images", payload["invalidated_steps"])
        self.assertIn("matching_images", payload["invalidated_steps"])
        self.assertIn("package_final", payload["invalidated_steps"])
        self.assertEqual(step_status(payload["lot"], "inspection_images"), "pret")

    def test_upload_reuses_successful_idempotency_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot idempotent"}).json()["lot"][
                "id"
            ]
            headers = {"X-Idempotency-Key": "upload-images-idempotent"}

            first_response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("images.zip", zip_bytes([("a.jpg", b"a")])),
                headers=headers,
            )
            second_response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("images.zip", zip_bytes([("a.jpg", b"a")])),
                headers=headers,
            )
            artifact_files = [
                path
                for path in (settings.data_dir / "lots" / lot_id / "artifacts").glob("*/*")
                if path.is_file()
            ]
            temp_files = [
                path
                for path in (settings.data_dir / "lots" / lot_id / "tmp").glob("*")
                if path.is_file()
            ]

        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(second_response.status_code, 202)
        self.assertEqual(
            first_response.json()["artifact"]["id"],
            second_response.json()["artifact"]["id"],
        )
        self.assertTrue(first_response.json()["job"]["created"])
        self.assertFalse(second_response.json()["job"]["created"])
        self.assertEqual(len(artifact_files), 1)
        self.assertEqual(temp_files, [])

    def test_invalid_zip_extension_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot extension"}).json()["lot"][
                "id"
            ]

            response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("images.rar", zip_bytes([("a.jpg", b"a")])),
            )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(
            response.json()["error"]["code"],
            "SIRCOM_IMAGE_ZIP_EXTENSION_UNSUPPORTED",
        )

    def test_invalid_zip_signature_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot signature"}).json()["lot"][
                "id"
            ]

            response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("images.zip", b"not a zip archive"),
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_IMAGE_ZIP_SIGNATURE_INVALID")

    def test_oversized_zip_is_rejected_before_signature_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp), max_zip_mb=1)))
            lot_id = client.post("/api/lots", json={"title": "Lot taille"}).json()["lot"]["id"]

            response = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("images.zip", b"x" * (1024 * 1024 + 1)),
            )

        self.assertEqual(response.status_code, 413)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "SIRCOM_IMAGE_ZIP_TOO_LARGE")
        self.assertEqual(payload["error"]["details"]["max_mb"], 1)

    def test_lot_target_is_checked_before_zip_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            deleted_lot_id = client.post("/api/lots", json={"title": "Lot supprime"}).json()[
                "lot"
            ]["id"]
            client.delete(f"/api/lots/{deleted_lot_id}")

            missing_response = client.post(
                "/api/lots/lot_missing/images",
                files=image_zip_file("images.rar", b"not a zip archive"),
            )
            deleted_response = client.post(
                f"/api/lots/{deleted_lot_id}/images",
                files=image_zip_file("images.rar", b"not a zip archive"),
            )

        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["error"]["code"], "SIRCOM_LOT_NOT_FOUND")
        self.assertFalse((settings.data_dir / "lots" / "lot_missing").exists())
        self.assertEqual(deleted_response.status_code, 409)
        self.assertEqual(deleted_response.json()["error"]["code"], "SIRCOM_LOT_NOT_MUTABLE")

    def test_unknown_lot_returns_structured_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))

            response = client.post(
                "/api/lots/lot_missing/images",
                files=image_zip_file("images.zip", zip_bytes([("a.jpg", b"a")])),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "SIRCOM_LOT_NOT_FOUND")
        self.assertNotIn("lot_missing", str(response.json()))

    def test_home_ui_exposes_image_zip_upload_form_for_selected_lot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(make_settings(Path(tmp))))
            lot_id = client.post("/api/lots", json={"title": "Lot UI images"}).json()["lot"][
                "id"
            ]

            response = client.get(f"/?lot_id={lot_id}&view=upload_images")

        html = response.text
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="image-upload-form"', html)
        self.assertIn('for="image-zip-file"', html)
        self.assertIn('type="file"', html)
        self.assertIn('accept=".zip"', html)
        self.assertIn(f'data-image-upload-lot-id="{lot_id}"', html)
        self.assertNotIn(str(Path(tmp)), html)


class ImageZipInspectionPipelineTest(unittest.TestCase):
    def test_worker_persists_warning_for_zip_without_treatable_images(self) -> None:
        cases = {
            "empty_zip": [],
            "no_image_files": [("README.txt", b"notes"), ("__MACOSX/._x", b"mac")],
        }
        for case_name, entries in cases.items():
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory() as tmp:
                    settings = make_settings(Path(tmp))
                    client = TestClient(create_app(settings))
                    lot_id = client.post(
                        "/api/lots",
                        json={"title": f"Lot {case_name}"},
                    ).json()["lot"]["id"]

                    upload = client.post(
                        f"/api/lots/{lot_id}/images",
                        files=image_zip_file("images.zip", zip_bytes(entries)),
                        headers={"X-Idempotency-Key": f"upload-{case_name}"},
                    )
                    worker_result = run_worker_once(settings=settings)
                    status_response = client.get(f"/api/lots/{lot_id}/images/status")
                    lot_response = client.get(f"/api/lots/{lot_id}")

                self.assertEqual(upload.status_code, 202)
                self.assertEqual(worker_result.outcome, "succeeded")
                self.assertEqual(status_response.status_code, 200)
                payload = status_response.json()
                self.assertTrue(payload["inspection"]["inspectable"])
                self.assertEqual(payload["inspection"]["image_count"], 0)
                self.assertEqual(
                    step_status(lot_response.json()["lot"], "inspection_images"),
                    "termine_avec_alertes",
                )
                warning_codes = {
                    problem["code"]
                    for problem in payload["problem_groups"]["alerte"]["items"]
                }
                self.assertEqual(warning_codes, {"SIRCOM_IMAGE_ZIP_NO_TREATABLE_IMAGE"})

    def test_worker_blocks_security_and_structure_refusal_cases(self) -> None:
        cases = {
            "traversal": (
                [("../photo.jpg", b"image")],
                "SIRCOM_IMAGE_ZIP_UNSAFE_PATH",
            ),
            "absolute_path": (
                [("/photo.jpg", b"image")],
                "SIRCOM_IMAGE_ZIP_UNSAFE_PATH",
            ),
            "dangerous_directory": (
                [("../", b""), ("racine.jpg", b"image")],
                "SIRCOM_IMAGE_ZIP_UNSAFE_PATH",
            ),
            "empty_path_part": (
                [("dossier//photo.jpg", b"image")],
                "SIRCOM_IMAGE_ZIP_EMPTY_NAME",
            ),
            "control_characters": (
                [("photo-\x01.jpg", b"image")],
                "SIRCOM_IMAGE_ZIP_CONTROL_CHARACTERS",
            ),
            "subfolder_only": (
                [("dossier/photo.jpg", b"image")],
                "SIRCOM_IMAGE_ZIP_IMAGE_IN_SUBFOLDER",
            ),
            "mixed_root_and_subfolder": (
                [("racine.jpg", b"image"), ("dossier/photo.jpg", b"image")],
                "SIRCOM_IMAGE_ZIP_IMAGE_IN_SUBFOLDER",
            ),
            "subfolder_non_system_file": (
                [("dossier/readme.txt", b"notes")],
                "SIRCOM_IMAGE_ZIP_ENTRY_IN_SUBFOLDER",
            ),
            "duplicate_normalized_names": (
                [("PHOTO.jpg", b"image"), ("photo.JPG", b"image")],
                "SIRCOM_IMAGE_ZIP_DUPLICATE_NAMES",
            ),
            "too_many_images": (
                [("a.jpg", b"a"), ("b.jpg", b"b"), ("c.jpg", b"c")],
                "SIRCOM_IMAGE_ZIP_TOO_MANY_IMAGES",
            ),
            "too_many_files": (
                [("a.txt", b"a"), ("b.txt", b"b"), ("c.txt", b"c")],
                "SIRCOM_IMAGE_ZIP_TOO_MANY_FILES",
            ),
            "image_too_large": (
                [("a.jpg", b"a" * (1024 * 1024 + 1))],
                "SIRCOM_IMAGE_ZIP_IMAGE_TOO_LARGE",
            ),
            "heic_refused": (
                [("photo.heic", b"heic")],
                "SIRCOM_IMAGE_HEIC_REFUSED",
            ),
            "heif_refused": (
                [("photo.heif", b"heif")],
                "SIRCOM_IMAGE_HEIF_REFUSED",
            ),
            "unzipped_too_large": (
                [("a.jpg", b"a" * (1024 * 1024)), ("b.jpg", b"b" * (1024 * 1024))],
                "SIRCOM_IMAGE_ZIP_UNCOMPRESSED_TOO_LARGE",
            ),
        }
        for case_name, (entries, expected_code) in cases.items():
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory() as tmp:
                    settings = make_settings(
                        Path(tmp),
                        max_image_count=2,
                        max_image_mb=1,
                        max_unzipped_mb=1,
                    )
                    client = TestClient(create_app(settings))
                    lot_id = client.post(
                        "/api/lots",
                        json={"title": f"Lot {case_name}"},
                    ).json()["lot"]["id"]

                    upload = client.post(
                        f"/api/lots/{lot_id}/images",
                        files=image_zip_file("images.zip", zip_bytes(entries)),
                        headers={"X-Idempotency-Key": f"upload-{case_name}"},
                    )
                    worker_result = run_worker_once(settings=settings)
                    status_response = client.get(f"/api/lots/{lot_id}/images/status")
                    lot_response = client.get(f"/api/lots/{lot_id}")
                    inspection_tmp = list(
                        (settings.data_dir / "lots" / lot_id / "tmp").glob("inspection-*")
                    )

                self.assertEqual(upload.status_code, 202)
                self.assertEqual(worker_result.outcome, "succeeded")
                self.assertEqual(status_response.status_code, 200)
                self.assertFalse(status_response.json()["inspection"]["inspectable"])
                self.assertEqual(
                    step_status(lot_response.json()["lot"], "inspection_images"),
                    "bloque",
                )
                blocking_codes = {
                    problem["code"]
                    for problem in status_response.json()["problem_groups"]["bloquant"][
                        "items"
                    ]
                }
                self.assertIn(expected_code, blocking_codes)
                self.assertEqual(inspection_tmp, [])

    def test_worker_blocks_encrypted_zip_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot chiffre"}).json()[
                "lot"
            ]["id"]

            upload = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file(
                    "images.zip",
                    zip_bytes_with_encrypted_flag([("photo.jpg", b"image")]),
                ),
                headers={"X-Idempotency-Key": "upload-encrypted"},
            )
            worker_result = run_worker_once(settings=settings)
            status_response = client.get(f"/api/lots/{lot_id}/images/status")

        self.assertEqual(upload.status_code, 202)
        self.assertEqual(worker_result.outcome, "succeeded")
        self.assertEqual(status_response.status_code, 200)
        payload = status_response.json()
        self.assertFalse(payload["inspection"]["inspectable"])
        blocking_codes = {
            problem["code"]
            for problem in payload["problem_groups"]["bloquant"]["items"]
        }
        self.assertIn("SIRCOM_IMAGE_ZIP_ENCRYPTED_ENTRY", blocking_codes)

    def test_status_before_worker_returns_structured_409(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(Path(tmp))
            client = TestClient(create_app(settings))
            lot_id = client.post("/api/lots", json={"title": "Lot attente"}).json()["lot"][
                "id"
            ]

            upload = client.post(
                f"/api/lots/{lot_id}/images",
                files=image_zip_file("images.zip", zip_bytes([("a.jpg", b"a")])),
            )
            status_response = client.get(f"/api/lots/{lot_id}/images/status")

        self.assertEqual(upload.status_code, 202)
        self.assertEqual(status_response.status_code, 409)
        self.assertEqual(
            status_response.json()["error"]["code"],
            "SIRCOM_IMAGE_INSPECTION_NOT_READY",
        )


def step_status(lot: dict[str, object], step_key: str) -> str:
    for step in lot["steps"]:
        if step["key"] == step_key:
            return str(step["status"])
    raise AssertionError(f"Missing step {step_key}.")


if __name__ == "__main__":
    unittest.main()
