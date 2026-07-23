from __future__ import annotations

import importlib
import sys
import zipfile
from pathlib import Path

import pytest
from openpyxl import Workbook
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

image_mapping = importlib.import_module("sircom2026_image_mapping")
image_matching = importlib.import_module("sircom2026_image_matching")
image_processing = importlib.import_module("sircom2026_image_processing")
runner = importlib.import_module("run_jeu_test_2026")

read_excel_mapping = image_mapping.read_excel_mapping
AmbiguousImageMatchError = image_matching.AmbiguousImageMatchError
find_best_match = image_matching.find_best_match
get_available_images = image_processing.get_available_images
process_and_rename_image = image_processing.process_and_rename_image
extract_images = runner.extract_images
generated_paths = runner.generated_paths
default_output_dir = runner.default_output_dir


class Logger:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def info(self, message: str) -> None:
        self.messages.append(("info", message))

    def warning(self, message: str) -> None:
        self.messages.append(("warning", message))

    def error(self, message: str) -> None:
        self.messages.append(("error", message))


def test_find_best_match_accepts_extension_variant() -> None:
    logger = Logger()

    match = find_best_match("31411321.jpg", ["31411321.jpeg"], logger)

    assert match == "31411321.jpeg"


def test_find_best_match_rejects_ambiguous_base_match() -> None:
    logger = Logger()

    with pytest.raises(AmbiguousImageMatchError) as exc_info:
        find_best_match("31411321.jpg", ["31411321.jpeg", "31411321.png"], logger)

    assert exc_info.value.candidates == ["31411321.jpeg", "31411321.png"]


def test_read_excel_mapping_falls_back_to_imageid(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["id_dossier", "imageid"])
    sheet.append(["12345", "12345.jpg"])
    excel_path = tmp_path / "mapping.xlsx"
    workbook.save(excel_path)
    workbook.close()

    mapping = read_excel_mapping(str(excel_path), Logger())

    assert mapping == {
        "12345": {
            "source_name": "12345.jpg",
            "final_name": "12345.jpg",
        }
    }


def test_process_and_rename_image_outputs_jpeg(tmp_path: Path) -> None:
    source_path = tmp_path / "source.png"
    target_dir = tmp_path / "out"
    Image.new("RGBA", (400, 200), (10, 20, 30, 120)).save(source_path)

    success, file_size = process_and_rename_image(
        str(source_path),
        "12345.jpg",
        str(target_dir),
        Logger(),
        max_width=80,
        jpeg_quality=90,
        dpi=300,
    )

    output_path = target_dir / "12345.jpg"
    assert success is True
    assert file_size > 0
    assert output_path.exists()

    with Image.open(output_path) as output:
        assert output.format == "JPEG"
        assert max(output.size) <= 80
        assert output.mode == "RGB"


def test_process_and_rename_image_preserves_pillow_pixel_limit(tmp_path: Path) -> None:
    source_path = tmp_path / "source.png"
    target_dir = tmp_path / "out"
    Image.new("RGB", (10, 10), (10, 20, 30)).save(source_path)
    original_limit = Image.MAX_IMAGE_PIXELS

    try:
        Image.MAX_IMAGE_PIXELS = 123_456
        success, _file_size = process_and_rename_image(
            str(source_path),
            "12345.jpg",
            str(target_dir),
            Logger(),
            max_width=80,
            jpeg_quality=90,
            dpi=300,
        )

        assert success is True
        assert Image.MAX_IMAGE_PIXELS == 123_456
    finally:
        Image.MAX_IMAGE_PIXELS = original_limit


def test_process_and_rename_image_rejects_source_over_pixel_limit(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.png"
    target_dir = tmp_path / "out"
    logger = Logger()
    Image.new("RGB", (4, 4), (10, 20, 30)).save(source_path)

    success, file_size = process_and_rename_image(
        str(source_path),
        "12345.jpg",
        str(target_dir),
        logger,
        max_width=80,
        jpeg_quality=90,
        dpi=300,
        source_max_pixels=15,
    )

    assert success is False
    assert file_size == 0
    assert not (target_dir / "12345.jpg").exists()
    assert any("max_pixels" in message for level, message in logger.messages)


def test_get_available_images_filters_extensions_and_hidden_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "visible.jpg").write_bytes(b"jpg")
    (tmp_path / "visible.png").write_bytes(b"png")
    (tmp_path / ".hidden.jpg").write_bytes(b"hidden")
    (tmp_path / "notes.txt").write_text("non image", encoding="utf-8")

    available = get_available_images(str(tmp_path), ["jpg", "png"])

    assert sorted(available) == ["visible.jpg", "visible.png"]


def test_extract_images_rejects_nested_image_members(tmp_path: Path) -> None:
    source_zip = tmp_path / "images.zip"
    with zipfile.ZipFile(source_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("dossier/photo.jpg", b"jpg")

    with pytest.raises(SystemExit) as exc_info:
        extract_images(source_zip, tmp_path / "images")

    assert "sous-dossier" in str(exc_info.value)


def test_extract_images_rejects_duplicate_root_basenames(tmp_path: Path) -> None:
    source_zip = tmp_path / "images.zip"
    with zipfile.ZipFile(source_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("photo.jpg", b"jpg")
        archive.writestr("PHOTO.JPG", b"jpg")

    with pytest.raises(SystemExit) as exc_info:
        extract_images(source_zip, tmp_path / "images")

    assert "dupliqué" in str(exc_info.value)


def test_generated_paths_rejects_absolute_configured_artifact() -> None:
    with pytest.raises(SystemExit) as exc_info:
        generated_paths({"step_00_output": "/tmp/out.xlsx"})

    assert "non borné" in str(exc_info.value)


def test_generated_paths_rejects_parent_configured_artifact() -> None:
    with pytest.raises(SystemExit) as exc_info:
        generated_paths({"step_00_output": "../out.xlsx"})

    assert "non borné" in str(exc_info.value)


def test_generated_paths_rejects_current_directory_artifact() -> None:
    with pytest.raises(SystemExit) as exc_info:
        generated_paths({"source_images_workdir": "."})

    assert "non borné" in str(exc_info.value)


def test_default_output_dir_rejects_parent_output_name() -> None:
    with pytest.raises(SystemExit) as exc_info:
        default_output_dir(output_dir_name="../livrables")

    assert "non borné" in str(exc_info.value)
