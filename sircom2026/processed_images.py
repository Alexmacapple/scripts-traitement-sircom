from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from sircom2026.image_formats import (
    DEFAULT_IMAGE_DIMENSION_LIMITS,
    IMAGE_DIMENSIONS_EXCEEDED_CODE,
    ImageDimensionLimitError,
    ImageDimensionLimits,
    check_image_dimensions,
    decompression_bomb_violation,
    prepare_image_for_jpeg,
    sniff_image_dimensions,
)
from sircom2026.pathimg import pathimg_path


EXPORT_IMAGES_FOLDER = "export-jpg-resize"
FINAL_IMAGE_MAX_WIDTH_PX = 350
FINAL_IMAGE_JPEG_QUALITY = 100
FINAL_IMAGE_DPI = 300


def build_processed_images_zip(
    source_zip_path: Path,
    matching_payload: dict[str, Any],
    *,
    image_limits: ImageDimensionLimits = DEFAULT_IMAGE_DIMENSION_LIMITS,
) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        target.writestr(f"{EXPORT_IMAGES_FOLDER}/", b"")
        try:
            with zipfile.ZipFile(source_zip_path) as source:
                for binding in matching_payload.get("bindings", []):
                    if (
                        not isinstance(binding, dict)
                        or binding.get("status") != "matched"
                    ):
                        continue
                    source_name = str(binding.get("source_name") or "")
                    final_name = str(binding.get("final_name") or "")
                    if not source_name or not final_name:
                        continue
                    try:
                        final_content = _convert_source_image_to_jpeg(
                            source,
                            source_name,
                            image_limits=image_limits,
                        )
                    except ImageDimensionLimitError as exc:
                        binding["status"] = "conversion_failed"
                        binding["pathimg"] = ""
                        binding["conversion_error"] = IMAGE_DIMENSIONS_EXCEEDED_CODE
                        binding["dimension_limits_exceeded"] = [
                            exc.violation.public_details()
                        ]
                        continue
                    except (
                        KeyError,
                        OSError,
                        RuntimeError,
                        UnidentifiedImageError,
                        ValueError,
                    ) as exc:
                        binding["status"] = "conversion_failed"
                        binding["pathimg"] = ""
                        binding["conversion_error"] = exc.__class__.__name__
                        continue
                    final_relative_path = f"{EXPORT_IMAGES_FOLDER}/{final_name}"
                    target.writestr(final_relative_path, final_content)
                    binding["final_sha256"] = hashlib.sha256(final_content).hexdigest()
                    binding["final_size_bytes"] = len(final_content)
                    binding["pathimg"] = pathimg_path(
                        str(matching_payload.get("image_root") or ""),
                        final_name,
                    )
        except zipfile.BadZipFile:
            for binding in matching_payload.get("bindings", []):
                if isinstance(binding, dict) and binding.get("status") == "matched":
                    binding["status"] = "conversion_failed"
                    binding["pathimg"] = ""
                    binding["conversion_error"] = "BadZipFile"
    return output.getvalue()


def _convert_source_image_to_jpeg(
    source: zipfile.ZipFile,
    source_name: str,
    *,
    image_limits: ImageDimensionLimits = DEFAULT_IMAGE_DIMENSION_LIMITS,
) -> bytes:
    try:
        with source.open(source_name) as handle:
            with Image.open(handle) as image:
                check_image_dimensions(image, image_limits, image_name=source_name)
                prepared = prepare_image_for_jpeg(image)
                if prepared.width > FINAL_IMAGE_MAX_WIDTH_PX:
                    ratio = FINAL_IMAGE_MAX_WIDTH_PX / prepared.width
                    height = max(1, round(prepared.height * ratio))
                    prepared = prepared.resize(
                        (FINAL_IMAGE_MAX_WIDTH_PX, height),
                        Image.Resampling.LANCZOS,
                    )
                output = BytesIO()
                save_kwargs: dict[str, Any] = {
                    "format": "JPEG",
                    "quality": FINAL_IMAGE_JPEG_QUALITY,
                    "dpi": (FINAL_IMAGE_DPI, FINAL_IMAGE_DPI),
                }
                icc_profile = prepared.info.get("icc_profile")
                if icc_profile:
                    save_kwargs["icc_profile"] = icc_profile
                prepared.save(output, **save_kwargs)
                return output.getvalue()
    except Image.DecompressionBombError as exc:
        raise ImageDimensionLimitError(
            decompression_bomb_violation(
                exc,
                image_limits,
                image_name=source_name,
                dimensions=_sniff_source_image_dimensions(source, source_name),
            )
        ) from exc


def _sniff_source_image_dimensions(
    source: zipfile.ZipFile,
    source_name: str,
    *,
    prefix_size: int = 65536,
) -> tuple[int, int] | None:
    try:
        with source.open(source_name) as handle:
            return sniff_image_dimensions(handle.read(prefix_size))
    except (KeyError, OSError, RuntimeError, ValueError, zipfile.BadZipFile):
        return None
