from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceImageFormat:
    name: str
    extensions: tuple[str, ...]
    pillow_format: str


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
