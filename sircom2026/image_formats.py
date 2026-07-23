from __future__ import annotations

from dataclasses import dataclass
import re
import struct
from typing import Any

from sircom2026.config import (
    DEFAULT_MAX_IMAGE_HEIGHT_PX,
    DEFAULT_MAX_IMAGE_PIXELS,
    DEFAULT_MAX_IMAGE_WIDTH_PX,
)


@dataclass(frozen=True)
class SourceImageFormat:
    name: str
    extensions: tuple[str, ...]
    pillow_format: str


@dataclass(frozen=True)
class ImageDimensionLimits:
    max_pixels: int
    max_width_px: int
    max_height_px: int


@dataclass(frozen=True)
class ImageDimensionLimitViolation:
    limit_exceeded: str
    observed: int
    maximum: int
    width: int
    height: int
    image: str | None = None

    def public_details(self) -> dict[str, Any]:
        details: dict[str, Any] = {
            "limit_exceeded": self.limit_exceeded,
            "observed": self.observed,
            "max": self.maximum,
            "width": self.width,
            "height": self.height,
        }
        if self.image:
            details["image"] = self.image
        return details


class ImageDimensionLimitError(ValueError):
    def __init__(self, violation: ImageDimensionLimitViolation) -> None:
        super().__init__(
            f"{violation.limit_exceeded}: {violation.observed} > {violation.maximum}"
        )
        self.violation = violation


ACCEPTED_SOURCE_IMAGE_FORMATS = (
    SourceImageFormat("JPEG", (".jpg", ".jpeg"), "JPEG"),
    SourceImageFormat("PNG", (".png",), "PNG"),
    SourceImageFormat("WEBP", (".webp",), "WEBP"),
    SourceImageFormat("TIFF", (".tif", ".tiff"), "TIFF"),
)
ACCEPTED_SOURCE_IMAGE_EXTENSIONS = tuple(
    extension
    for source_format in ACCEPTED_SOURCE_IMAGE_FORMATS
    for extension in source_format.extensions
)
REFUSED_SOURCE_IMAGE_EXTENSIONS = {
    ".heic": "HEIC refusé en V1 : non enregistré par Pillow core dans l'environnement local.",
    ".heif": "HEIF refusé en V1 : non enregistré par Pillow core dans l'environnement local.",
}
REFUSED_SOURCE_IMAGE_EXTENSION_CODES = {
    ".heic": "SIRCOM_IMAGE_HEIC_REFUSED",
    ".heif": "SIRCOM_IMAGE_HEIF_REFUSED",
}
HEIC_DECISION = "refused"
IMAGE_DIMENSIONS_EXCEEDED_CODE = "SIRCOM_IMAGE_DIMENSIONS_EXCEEDED"
DEFAULT_IMAGE_DIMENSION_LIMITS = ImageDimensionLimits(
    max_pixels=DEFAULT_MAX_IMAGE_PIXELS,
    max_width_px=DEFAULT_MAX_IMAGE_WIDTH_PX,
    max_height_px=DEFAULT_MAX_IMAGE_HEIGHT_PX,
)
_PILLOW_BOMB_RE = re.compile(
    r"Image size \((?P<observed>\d+) pixels\) exceeds limit of (?P<maximum>\d+) pixels"
)
_JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def pillow_support_report() -> dict[str, Any]:
    from PIL import Image, features

    registered_extensions = Image.registered_extensions()
    return {
        "pillow_version": Image.__version__,
        "accepted_extensions": list(ACCEPTED_SOURCE_IMAGE_EXTENSIONS),
        "accepted_formats": {
            source_format.name: {
                "extensions": list(source_format.extensions),
                "registered": all(
                    registered_extensions.get(extension) == source_format.pillow_format
                    for extension in source_format.extensions
                ),
                "pillow_format": source_format.pillow_format,
            }
            for source_format in ACCEPTED_SOURCE_IMAGE_FORMATS
        },
        "features": {
            "jpeg": _check_pillow_feature(features, "jpg"),
            "libjpeg_turbo": _check_pillow_feature(features, "libjpeg_turbo"),
            "littlecms2": _check_pillow_feature(features, "littlecms2"),
            "png_zlib": _check_pillow_feature(features, "zlib"),
            "zlib_ng": _check_pillow_feature(features, "zlib_ng"),
            "tiff": _check_pillow_feature(features, "libtiff"),
            "webp": _check_pillow_feature(features, "webp"),
        },
        "feature_versions": {
            "jpeg": _pillow_feature_version(features, "jpg"),
            "libjpeg_turbo": _pillow_feature_version(features, "libjpeg_turbo"),
            "littlecms2": _pillow_feature_version(features, "littlecms2"),
            "png_zlib": _pillow_feature_version(features, "zlib"),
            "tiff": _pillow_feature_version(features, "libtiff"),
            "webp": _pillow_feature_version(features, "webp"),
            "zlib_ng": _pillow_feature_version(features, "zlib_ng"),
        },
        "heic": {
            "decision": HEIC_DECISION,
            "registered_heic": registered_extensions.get(".heic"),
            "registered_heif": registered_extensions.get(".heif"),
            "reason": REFUSED_SOURCE_IMAGE_EXTENSIONS[".heic"],
        },
    }


def prepare_image_for_jpeg(image: Any) -> Any:
    from PIL import Image, ImageOps

    transposed = ImageOps.exif_transpose(image)
    icc_profile = transposed.info.get("icc_profile")
    if _has_alpha(transposed):
        rgba = transposed.convert("RGBA")
        prepared = Image.new("RGB", rgba.size, (255, 255, 255))
        prepared.paste(rgba, mask=rgba.getchannel("A"))
    elif transposed.mode == "RGB":
        prepared = transposed.copy()
    else:
        prepared = transposed.convert("RGB")
    if icc_profile:
        prepared.info["icc_profile"] = icc_profile
    return prepared


def image_dimension_limits_from_settings(settings: object) -> ImageDimensionLimits:
    return ImageDimensionLimits(
        max_pixels=int(getattr(settings, "max_image_pixels")),
        max_width_px=int(getattr(settings, "max_image_width_px")),
        max_height_px=int(getattr(settings, "max_image_height_px")),
    )


def check_image_dimensions(
    image: Any,
    limits: ImageDimensionLimits = DEFAULT_IMAGE_DIMENSION_LIMITS,
    *,
    image_name: str | None = None,
) -> None:
    width = max(0, int(image.width))
    height = max(0, int(image.height))
    pixels = width * height
    if width > limits.max_width_px:
        raise ImageDimensionLimitError(
            ImageDimensionLimitViolation(
                limit_exceeded="max_width_px",
                observed=width,
                maximum=limits.max_width_px,
                width=width,
                height=height,
                image=image_name,
            )
        )
    if height > limits.max_height_px:
        raise ImageDimensionLimitError(
            ImageDimensionLimitViolation(
                limit_exceeded="max_height_px",
                observed=height,
                maximum=limits.max_height_px,
                width=width,
                height=height,
                image=image_name,
            )
        )
    if pixels > limits.max_pixels:
        raise ImageDimensionLimitError(
            ImageDimensionLimitViolation(
                limit_exceeded="max_pixels",
                observed=pixels,
                maximum=limits.max_pixels,
                width=width,
                height=height,
                image=image_name,
            )
        )


def decompression_bomb_violation(
    exc: BaseException,
    limits: ImageDimensionLimits,
    *,
    image_name: str | None = None,
    dimensions: tuple[int, int] | None = None,
) -> ImageDimensionLimitViolation:
    width, height = dimensions or (0, 0)
    observed = width * height if width and height else _pillow_bomb_observed_pixels(exc)
    return ImageDimensionLimitViolation(
        limit_exceeded="max_pixels",
        observed=observed,
        maximum=limits.max_pixels,
        width=width,
        height=height,
        image=image_name,
    )


def sniff_image_dimensions(prefix: bytes) -> tuple[int, int] | None:
    return (
        _sniff_png_dimensions(prefix)
        or _sniff_jpeg_dimensions(prefix)
        or _sniff_webp_dimensions(prefix)
    )


def _pillow_bomb_observed_pixels(exc: BaseException) -> int:
    match = _PILLOW_BOMB_RE.search(str(exc))
    if match is None:
        return 0
    return int(match.group("observed"))


def _sniff_png_dimensions(prefix: bytes) -> tuple[int, int] | None:
    if not prefix.startswith(b"\x89PNG\r\n\x1a\n") or len(prefix) < 24:
        return None
    if prefix[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", prefix[16:24])


def _sniff_jpeg_dimensions(prefix: bytes) -> tuple[int, int] | None:
    if not prefix.startswith(b"\xff\xd8"):
        return None
    offset = 2
    while offset + 4 <= len(prefix):
        if prefix[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(prefix) and prefix[offset] == 0xFF:
            offset += 1
        if offset >= len(prefix):
            return None
        marker = prefix[offset]
        offset += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(prefix):
            return None
        segment_length = int.from_bytes(prefix[offset : offset + 2], "big")
        if segment_length < 2:
            return None
        segment_start = offset + 2
        segment_end = offset + segment_length
        if marker in _JPEG_SOF_MARKERS:
            if segment_start + 5 > len(prefix):
                return None
            height = int.from_bytes(
                prefix[segment_start + 1 : segment_start + 3], "big"
            )
            width = int.from_bytes(prefix[segment_start + 3 : segment_start + 5], "big")
            return width, height
        offset = segment_end
    return None


def _sniff_webp_dimensions(prefix: bytes) -> tuple[int, int] | None:
    if len(prefix) < 30 or prefix[:4] != b"RIFF" or prefix[8:12] != b"WEBP":
        return None
    chunk = prefix[12:16]
    if chunk == b"VP8X" and len(prefix) >= 30:
        width = int.from_bytes(prefix[24:27], "little") + 1
        height = int.from_bytes(prefix[27:30], "little") + 1
        return width, height
    if chunk == b"VP8L" and len(prefix) >= 25 and prefix[20] == 0x2F:
        bits = int.from_bytes(prefix[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    return None


def _check_pillow_feature(features: Any, name: str) -> bool:
    try:
        return bool(features.check(name))
    except (AttributeError, ValueError):
        return False


def _pillow_feature_version(features: Any, name: str) -> str | None:
    try:
        version = features.version(name)
    except (AttributeError, ValueError):
        return None
    if version is None:
        return None
    return str(version)


def _has_alpha(image: Any) -> bool:
    return image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
