from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "orchestrator.py"


class IntegrationTest(unittest.TestCase):
    def test_download_photos_cli_is_idempotent_and_uses_latest_numbered_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            home = tmp_path / "home"
            downloads = home / "Downloads"
            downloads.mkdir(parents=True)
            source = tmp_path / "source.jpg"
            source.write_bytes(b"\xff\xd8\xffsynthetic image")

            csv_path = downloads / "photos-produits-dossiers (3).csv"
            fields = [
                "dossier_id",
                "attachment_index",
                "field_label",
                "filename",
                "download_url",
                "dossier_url",
                "status",
                "link_text",
            ]
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
                writer.writeheader()
                writer.writerow(
                    {
                        "dossier_id": "12345678",
                        "attachment_index": "1",
                        "field_label": "Photo du produit",
                        "filename": "produit.jpg",
                        "download_url": source.as_uri(),
                        "dossier_url": "https://example.test/dossiers/12345678",
                        "status": "ok",
                        "link_text": "produit.jpg JPG",
                    }
                )

            output_dir = tmp_path / "output"
            report = tmp_path / "report.csv"
            filtered = tmp_path / "filtered.csv"
            command = [
                sys.executable,
                str(ORCHESTRATOR),
                "download-photos",
                "--output-dir",
                str(output_dir),
                "--report",
                str(report),
                "--filtered-csv",
                str(filtered),
                "--workers",
                "1",
                "--timeout",
                "1",
                "--retries",
                "0",
            ]
            env = {**os.environ, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"}

            first = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            target = output_dir / "12345678 - 01 - produit.jpg"
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn(str(csv_path), first.stdout)
            self.assertEqual(target.read_bytes(), b"\xff\xd8\xffsynthetic image")
            self.assertTrue(report.exists())

            second = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("déjà_présentes=1", second.stdout)
            self.assertEqual(list(output_dir.glob("*.jpg")), [target])

    def test_download_complete_cli_groups_attachments_by_dossier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            home = tmp_path / "home"
            downloads = home / "Downloads"
            downloads.mkdir(parents=True)
            source = tmp_path / "document.pdf"
            source.write_bytes(b"%PDF-1.4\nsynthetic document")

            csv_path = downloads / "dossiers-complets-pieces-jointes (2).csv"
            fields = [
                "dossier_id",
                "attachment_index",
                "field_label",
                "filename",
                "download_url",
                "dossier_url",
                "status",
                "link_text",
            ]
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
                writer.writeheader()
                writer.writerow(
                    {
                        "dossier_id": "87654321",
                        "attachment_index": "1",
                        "field_label": "Documentation",
                        "filename": "document.pdf",
                        "download_url": source.as_uri(),
                        "dossier_url": "https://example.test/dossiers/87654321",
                        "status": "ok",
                        "link_text": "document.pdf PDF",
                    }
                )

            output_dir = tmp_path / "output"
            report = tmp_path / "report.csv"
            command = [
                sys.executable,
                str(ORCHESTRATOR),
                "download-complete",
                "--output-dir",
                str(output_dir),
                "--report",
                str(report),
                "--workers",
                "1",
                "--timeout",
                "1",
                "--retries",
                "0",
            ]
            env = {**os.environ, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"}

            result = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            target = output_dir / "87654321" / "01 - document.pdf"
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(target.read_bytes(), b"%PDF-1.4\nsynthetic document")
            self.assertTrue(report.exists())


if __name__ == "__main__":
    unittest.main()
