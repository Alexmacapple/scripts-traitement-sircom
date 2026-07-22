from __future__ import annotations

import importlib.util
import logging
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook
from PIL import Image


def load_process_images_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts-2025" / "10-process-images.py"
    spec = importlib.util.spec_from_file_location("sircom2025_process_images", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load 2025 process images script.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProcessImages2025Test(unittest.TestCase):
    def test_uses_source_photo_column_and_keeps_imageid_as_final_name(self) -> None:
        module = load_process_images_module()
        logger = logging.getLogger("test-process-images-2025")

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            excel_path = tmpdir / "7-add-pathimg.xlsx"
            source_dir = tmpdir / "images"
            target_dir = tmpdir / "export_images_id_dossier_rename_resize"
            source_dir.mkdir()
            target_dir.mkdir()
            Image.new("RGB", (20, 12), (30, 90, 150)).save(
                source_dir / "packshot-source.png",
                format="PNG",
            )
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["f_id", "imageid", "@pathimg", "y_photodu"])
            sheet.append(
                [
                    "ID.1",
                    "dossier-id-1.jpg",
                    "/Users/victoria/Documents/export-jpg-resize/dossier-id-1.jpg",
                    "packshot-source.png",
                ]
            )
            workbook.save(excel_path)
            workbook.close()

            mapping = module.read_excel_mapping(excel_path, logger)
            available = module.get_available_images(source_dir)
            image_mapping = mapping["ID.1"]
            matched_file = module.find_best_match(
                image_mapping["source_name"],
                available.keys(),
                logger,
            )
            success, _file_size = module.process_and_rename_image(
                available[matched_file],
                image_mapping["final_name"],
                target_dir,
                logger,
            )

            self.assertEqual(
                image_mapping,
                {
                    "source_name": "packshot-source.png",
                    "final_name": "dossier-id-1.jpg",
                },
            )
            self.assertEqual(matched_file, "packshot-source.png")
            self.assertTrue(success)
            self.assertTrue((target_dir / "dossier-id-1.jpg").exists())
            self.assertFalse((target_dir / "packshot-source.jpg").exists())


if __name__ == "__main__":
    unittest.main()
