from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "orchestrator.py"


def load_orchestrator():
    spec = importlib.util.spec_from_file_location("demarches_orchestrator", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OrchestratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_orchestrator()

    @staticmethod
    def write_csv(
        path: Path,
        *,
        download_url: str,
        status: str = "ok",
        filename: str = "produit.jpg",
        field_label: str = "Photo du produit",
        link_text: str = "produit.jpg JPG",
    ) -> None:
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
        row = {
            "dossier_id": "12345678",
            "attachment_index": "1",
            "field_label": field_label,
            "filename": filename,
            "download_url": download_url,
            "dossier_url": "https://example.test/dossiers/12345678",
            "status": status,
            "link_text": link_text,
        }
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
            writer.writeheader()
            writer.writerow(row)

    def test_latest_numbered_photo_csv_is_selected_and_anomalies_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            downloads = Path(tmp)
            old = downloads / "photos-produits-dossiers.csv"
            latest = downloads / "photos-produits-dossiers (2).csv"
            anomaly = downloads / "photos-produits-dossiers-anomalies.csv"
            for path in (old, latest, anomaly):
                self.write_csv(path, download_url="https://example.test/photo.jpg")
            old.touch()
            latest.touch()
            anomaly.touch()
            old_mtime = 1_700_000_000
            latest_mtime = old_mtime + 10
            anomaly_mtime = old_mtime + 20
            import os

            os.utime(old, (old_mtime, old_mtime))
            os.utime(latest, (latest_mtime, latest_mtime))
            os.utime(anomaly, (anomaly_mtime, anomaly_mtime))

            with (
                patch.object(self.module, "DOWNLOADS", downloads),
                patch.object(
                    self.module,
                    "PHOTOS_PREPARED_MARKER",
                    downloads / ".missing-photo-marker",
                ),
            ):
                selected = self.module.default_photos_csv()

            self.assertEqual(selected, latest)

    def test_latest_numbered_complete_csv_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            downloads = Path(tmp)
            base = downloads / "dossiers-complets-pieces-jointes.csv"
            latest = downloads / "dossiers-complets-pieces-jointes (1).csv"
            self.write_csv(base, download_url="https://example.test/a.pdf")
            self.write_csv(latest, download_url="https://example.test/b.pdf")
            import os

            os.utime(base, (1_700_000_000, 1_700_000_000))
            os.utime(latest, (1_700_000_010, 1_700_000_010))

            with (
                patch.object(self.module, "DOWNLOADS", downloads),
                patch.object(
                    self.module,
                    "COMPLETE_PREPARED_MARKER",
                    downloads / ".missing-complete-marker",
                ),
            ):
                selected = self.module.default_complete_csv()

            self.assertEqual(selected, latest)

    def test_latest_numbered_anomalies_csv_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            downloads = Path(tmp)
            base = downloads / "photos-produits-dossiers-anomalies.csv"
            latest = downloads / "photos-produits-dossiers-anomalies (1).csv"
            self.write_csv(base, download_url="", status="pièce photo introuvable")
            self.write_csv(latest, download_url="", status="pièce photo introuvable")
            import os

            os.utime(base, (1_700_000_000, 1_700_000_000))
            os.utime(latest, (1_700_000_010, 1_700_000_010))

            with (
                patch.object(self.module, "DOWNLOADS", downloads),
                patch.object(
                    self.module,
                    "PHOTOS_PREPARED_MARKER",
                    downloads / ".missing-photo-marker",
                ),
            ):
                selected = self.module.default_photo_anomalies_csv()

            self.assertEqual(selected, latest)

    def test_csv_older_than_prepare_marker_is_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            downloads = Path(tmp)
            csv_path = downloads / "photos-produits-dossiers.csv"
            marker = downloads / ".photos-prepared"
            self.write_csv(csv_path, download_url="https://example.test/photo.jpg")
            marker.touch()
            import os

            os.utime(csv_path, (1_700_000_000, 1_700_000_000))
            os.utime(marker, (1_700_000_010, 1_700_000_010))

            with (
                patch.object(self.module, "DOWNLOADS", downloads),
                patch.object(self.module, "PHOTOS_PREPARED_MARKER", marker),
            ):
                selected = self.module.default_photos_csv()

            self.assertIsNone(selected)

    def test_check_csv_fails_when_no_url_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "anomalies.csv"
            self.write_csv(csv_path, download_url="", status="pièce photo introuvable")
            output = io.StringIO()
            errors = io.StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                status = self.module.cmd_check_csv(argparse.Namespace(csv=csv_path))

            self.assertEqual(status, 1)
            self.assertIn("aucune URL", errors.getvalue())

    def test_check_photos_requires_an_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "photos-produits-dossiers.csv"
            self.write_csv(
                csv_path,
                download_url="https://example.test/document.pdf",
                filename="document.pdf",
                field_label="Documentation commerciale",
                link_text="document.pdf PDF",
            )
            output = io.StringIO()
            errors = io.StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                status = self.module.cmd_check_csv(
                    argparse.Namespace(csv=csv_path, require_images=True)
                )

            self.assertEqual(status, 1)
            self.assertIn("aucune image", errors.getvalue())

    def test_prepare_injects_ids_and_procedure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template = tmp_path / "template.js"
            output = tmp_path / "generated.js"
            template.write_text(
                'const SOURCE = `\\n000000\\n`;\\nconst PROCEDURE_ID = "1";\\n',
                encoding="utf-8",
            )

            self.module.inject_script(
                template,
                output,
                ["12345678", "87654321"],
                "140205",
            )

            generated = output.read_text(encoding="utf-8")
            self.assertIn("12345678\n87654321", generated)
            self.assertIn('const PROCEDURE_ID = "140205";', generated)

    def test_download_photos_uses_latest_csv_and_writes_filtered_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            downloads = tmp_path / "downloads"
            downloads.mkdir()
            csv_path = downloads / "photos-produits-dossiers (1).csv"
            self.write_csv(
                csv_path,
                download_url="https://example.test/produit.jpg",
            )
            filtered_csv = tmp_path / "filtered.csv"
            args = argparse.Namespace(
                csv=None,
                filtered_csv=filtered_csv,
                output_dir=tmp_path / "output",
                report=tmp_path / "report.csv",
                group_by_dossier=False,
                workers=1,
                timeout=1,
                retries=0,
            )

            with (
                patch.object(self.module, "DOWNLOADS", downloads),
                patch.object(
                    self.module,
                    "PHOTOS_PREPARED_MARKER",
                    downloads / ".missing-photo-marker",
                ),
                patch.object(self.module, "cmd_download", return_value=0) as download,
            ):
                status = self.module.cmd_download_photos(args)

            self.assertEqual(status, 0)
            self.assertTrue(filtered_csv.exists())
            self.assertEqual(download.call_args.args[0].csv, filtered_csv)

    def test_download_complete_uses_latest_csv_and_groups_by_dossier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            downloads = tmp_path / "downloads"
            downloads.mkdir()
            csv_path = downloads / "dossiers-complets-pieces-jointes (1).csv"
            self.write_csv(
                csv_path,
                download_url="https://example.test/document.pdf",
                filename="document.pdf",
                field_label="Documentation commerciale",
                link_text="document.pdf PDF",
            )
            args = argparse.Namespace(
                csv=None,
                output_dir=tmp_path / "output",
                report=tmp_path / "report.csv",
                workers=1,
                timeout=1,
                retries=0,
            )

            with (
                patch.object(self.module, "DOWNLOADS", downloads),
                patch.object(
                    self.module,
                    "COMPLETE_PREPARED_MARKER",
                    downloads / ".missing-complete-marker",
                ),
                patch.object(self.module, "cmd_download", return_value=0) as download,
            ):
                status = self.module.cmd_download_complete(args)

            self.assertEqual(status, 0)
            forwarded = download.call_args.args[0]
            self.assertEqual(forwarded.csv, csv_path)
            self.assertTrue(forwarded.group_by_dossier)

    def test_parser_exposes_simple_commands_for_both_flows(self) -> None:
        parser = self.module.build_parser()
        self.assertEqual(parser.parse_args(["check-photos"]).command, "check-photos")
        self.assertEqual(
            parser.parse_args(["check-complete"]).command,
            "check-complete",
        )
        self.assertEqual(
            parser.parse_args(["download-complete"]).command,
            "download-complete",
        )
        self.assertEqual(
            parser.parse_args(["prepare-complete-errors"]).command,
            "prepare-complete-errors",
        )


if __name__ == "__main__":
    unittest.main()
