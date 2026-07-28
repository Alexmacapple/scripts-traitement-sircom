from __future__ import annotations

import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "download_attachments_from_csv.py"
JPEG_BYTES = b"\xff\xd8\xffsynthetic image"


def load_downloader():
    spec = importlib.util.spec_from_file_location("demarches_downloader", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse(io.BytesIO):
    status = 200
    headers: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False


class DownloaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_downloader()

    @staticmethod
    def row(index: str = "1") -> dict[str, str]:
        return {
            "dossier_id": "12345678",
            "attachment_index": index,
            "field_label": "Photo",
            "filename": "produit.jpg",
            "download_url": "https://example.test/produit.jpg",
            "dossier_url": "https://example.test/dossiers/12345678",
            "status": "ok",
        }

    @staticmethod
    def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        fields = [
            "dossier_id",
            "attachment_index",
            "field_label",
            "filename",
            "download_url",
            "dossier_url",
            "status",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    def test_existing_file_is_skipped_without_creating_numbered_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            row = self.row()
            target = self.module.target_path(row, output_dir, False)
            target.write_bytes(JPEG_BYTES)

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                side_effect=AssertionError("network must not be called"),
            ):
                result = self.module.download_one(
                    row,
                    output_dir,
                    group_by_dossier=False,
                    timeout=1,
                    retries=0,
                )

            self.assertEqual(result["download_status"], "skipped_existing")
            self.assertEqual(Path(result["local_path"]), target)
            self.assertFalse(target.with_name(f"{target.stem} (2){target.suffix}").exists())

    def test_duplicate_targets_are_stable_across_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "attachments.csv"
            output_dir = tmp_path / "downloads"
            report_path = tmp_path / "report.csv"
            rows = [self.row(), self.row()]
            self.write_csv(csv_path, rows)

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                side_effect=lambda *_args, **_kwargs: FakeResponse(JPEG_BYTES),
            ):
                first_status = self.module.run_download(
                    csv_path,
                    output_dir,
                    report_path,
                    workers=1,
                    retries=0,
                )

            expected = output_dir / "12345678 - 01 - produit.jpg"
            duplicate = output_dir / "12345678 - 01 - produit (2).jpg"
            self.assertEqual(first_status, 0)
            self.assertEqual(expected.read_bytes(), JPEG_BYTES)
            self.assertEqual(duplicate.read_bytes(), JPEG_BYTES)

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                side_effect=AssertionError("network must not be called on rerun"),
            ):
                second_status = self.module.run_download(
                    csv_path,
                    output_dir,
                    report_path,
                    workers=2,
                    retries=0,
                )

            self.assertEqual(second_status, 0)
            report_rows = self.module.read_rows(report_path)
            self.assertEqual(
                [row["download_status"] for row in report_rows],
                ["skipped_existing", "skipped_existing"],
            )

    def test_empty_response_is_reported_as_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            row = self.row()

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=FakeResponse(b""),
            ):
                result = self.module.download_one(
                    row,
                    output_dir,
                    group_by_dossier=False,
                    timeout=1,
                    retries=0,
                )

            self.assertTrue(result["download_status"].startswith("error:"))
            self.assertFalse(self.module.target_path(row, output_dir, False).exists())

    def test_mislabeled_html_response_is_not_saved_as_an_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            row = self.row()
            response = FakeResponse(b"<html>expired</html>")
            response.headers = {"Content-Type": "application/octet-stream"}

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=response,
            ):
                result = self.module.download_one(
                    row,
                    output_dir,
                    group_by_dossier=False,
                    timeout=1,
                    retries=0,
                )

            self.assertIn("invalide", result["download_status"])
            self.assertFalse(self.module.target_path(row, output_dir, False).exists())

    def test_mislabeled_json_response_with_unknown_suffix_is_not_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            row = {
                **self.row(),
                "filename": "erreur.bin",
                "download_url": "https://example.test/erreur.bin",
            }
            response = FakeResponse(b'{"error":"expired"}')
            response.headers = {"Content-Type": "application/octet-stream"}

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=response,
            ):
                result = self.module.download_one(
                    row,
                    output_dir,
                    group_by_dossier=False,
                    timeout=1,
                    retries=0,
                )

            self.assertIn("invalide", result["download_status"])
            self.assertFalse(self.module.target_path(row, output_dir, False).exists())

    def test_docx_container_is_saved_as_a_valid_complete_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            row = {
                **self.row(),
                "filename": "fiche.docx",
                "download_url": "https://example.test/fiche.docx",
            }
            response = FakeResponse(b"PK\x03\x04synthetic office document")
            response.headers = {
                "Content-Type": (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                )
            }

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=response,
            ):
                result = self.module.download_one(
                    row,
                    output_dir,
                    group_by_dossier=False,
                    timeout=1,
                    retries=0,
                )

            self.assertEqual(result["download_status"], "downloaded")
            self.assertEqual(
                self.module.target_path(row, output_dir, False).read_bytes(),
                b"PK\x03\x04synthetic office document",
            )

    def test_rtf_attachment_is_not_confused_with_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fiche.rtf"
            path.write_bytes(b"{\\rtf1 synthetic document}")

            self.assertTrue(self.module.file_is_usable(path, ".rtf"))

    def test_existing_html_file_is_replaced_instead_of_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            row = self.row()
            target = self.module.target_path(row, output_dir, False)
            target.write_bytes(b"<html>old error</html>")

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=FakeResponse(JPEG_BYTES),
            ):
                result = self.module.download_one(
                    row,
                    output_dir,
                    group_by_dossier=False,
                    timeout=1,
                    retries=0,
                )

            self.assertEqual(result["download_status"], "downloaded")
            self.assertEqual(target.read_bytes(), JPEG_BYTES)

    def test_mixed_csv_keeps_missing_url_anomaly_in_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "attachments.csv"
            output_dir = tmp_path / "downloads"
            report_path = tmp_path / "report.csv"
            rows = [
                self.row(),
                {
                    **self.row(index=""),
                    "dossier_id": "87654321",
                    "filename": "",
                    "download_url": "",
                    "status": "aucune pièce jointe",
                },
            ]
            self.write_csv(csv_path, rows)

            with patch.object(
                self.module.urllib.request,
                "urlopen",
                return_value=FakeResponse(JPEG_BYTES),
            ):
                status = self.module.run_download(
                    csv_path,
                    output_dir,
                    report_path,
                    workers=1,
                    retries=0,
                )

            report_rows = self.module.read_rows(report_path)
            self.assertEqual(status, 1)
            self.assertEqual(len(report_rows), 2)
            anomaly = next(row for row in report_rows if row["dossier_id"] == "87654321")
            self.assertIn("aucune URL", anomaly["download_status"])

    def test_csv_without_download_urls_returns_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "attachments.csv"
            output_dir = tmp_path / "downloads"
            report_path = tmp_path / "report.csv"
            self.write_csv(csv_path, [{**self.row(), "download_url": ""}])

            status = self.module.run_download(
                csv_path,
                output_dir,
                report_path,
                workers=1,
                retries=0,
            )

            self.assertEqual(status, 1)
            self.assertTrue(report_path.exists())

    def test_parent_directory_is_not_a_safe_filename(self) -> None:
        self.assertEqual(self.module.safe_filename("..", "dossier"), "dossier")

    def test_long_attachment_name_keeps_its_extension(self) -> None:
        filename = self.module.safe_attachment_filename(f"{'é' * 200}.jpeg")
        self.assertLessEqual(len(filename.encode("utf-8")), 180)
        self.assertTrue(filename.endswith(".jpeg"))


if __name__ == "__main__":
    unittest.main()
