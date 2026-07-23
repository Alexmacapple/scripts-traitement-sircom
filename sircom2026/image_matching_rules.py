from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


MATCHING_RULES_VERSION = "image-matching-v1"
MATCHING_SCHEMA_VERSION = 1
MATCHABLE_IMAGE_SOURCE_ROLE = "nom_image_source"
PARTIAL_SUGGESTION_MIN_LENGTH = 4
PARTIAL_SUGGESTION_LIMIT = 10


def mark_duplicate_automatic_sources(bindings: list[dict[str, Any]]) -> None:
    matched_sources = Counter(
        str(binding["source_name"])
        for binding in bindings
        if binding.get("status") == "matched" and binding.get("source_name")
    )
    duplicate_sources = {
        source_name for source_name, count in matched_sources.items() if count > 1
    }
    if not duplicate_sources:
        return
    for binding in bindings:
        source_name = binding.get("source_name")
        if binding.get("status") == "matched" and source_name in duplicate_sources:
            binding["status"] = "ambiguous"
            binding["pathimg"] = ""
            binding["match_level"] = "source_duplicate"
            binding["duplicate_source_name"] = source_name


def match_row_image(
    *,
    id_dossier: str,
    original_names: list[str],
    final_name: str,
    manual_source: str | None,
    duplicate_manual_sources: set[str],
    duplicate_final_names: set[str],
    image_inventory: dict[str, Any],
    source_artifact_id: str,
    source_zip_sha256: str,
    rules_fingerprint: str,
) -> dict[str, Any]:
    base = {
        "id_dossier": id_dossier,
        "original_filenames": original_names,
        "source_name": None,
        "source_artifact_id": source_artifact_id,
        "source_zip_fingerprint": source_zip_sha256,
        "source_image_zip_sha256": source_zip_sha256,
        "rules_version": MATCHING_RULES_VERSION,
        "rules_fingerprint": rules_fingerprint,
        "imageid": final_name,
        "final_name": final_name,
        "final_sha256": None,
        "pathimg": "",
        "status": "missing",
        "match_level": "none",
        "fallback_used": False,
        "manual_resolution": manual_source,
        "candidates": [],
        "suggestions": [],
    }
    if final_name in duplicate_final_names:
        return {
            **base,
            "status": "ambiguous",
            "match_level": "final_name_collision",
        }
    if manual_source:
        manual_match = _image_by_name(image_inventory, manual_source)
        if manual_source in duplicate_manual_sources or manual_match is None:
            return {
                **base,
                "status": "ambiguous",
                "match_level": "manual_invalid",
                "candidates": _public_images(
                    image_inventory["images"]
                    if manual_match is None
                    else [manual_match]
                ),
            }
        return {
            **base,
            "status": "matched",
            "match_level": "manual",
            "source_name": manual_match["name"],
            "candidates": _public_images([manual_match]),
        }

    for original_name in original_names:
        match = _unique_match(
            _full_name_key(original_name),
            image_inventory["exact_name"],
        )
        if match["status"] == "matched":
            image = match["images"][0]
            return {
                **base,
                "status": "matched",
                "match_level": "original_exact",
                "source_name": image["name"],
                "candidates": _public_images(match["images"]),
            }

    for original_name in original_names:
        match = _unique_match(
            _exact_stem(original_name),
            image_inventory["exact_stem"],
        )
        if match["status"] == "matched":
            image = match["images"][0]
            return {
                **base,
                "status": "matched",
                "match_level": "original_exact_stem",
                "source_name": image["name"],
                "candidates": _public_images(match["images"]),
            }
        if match["status"] == "ambiguous":
            return {
                **base,
                "status": "ambiguous",
                "match_level": "original_exact_stem",
                "candidates": _public_images(match["images"]),
            }

    for original_name in original_names:
        match = _unique_match(
            _tolerant_stem_key(original_name),
            image_inventory["tolerant_stem"],
        )
        if match["status"] == "matched":
            image = match["images"][0]
            return {
                **base,
                "status": "matched",
                "match_level": "original_tolerant",
                "source_name": image["name"],
                "candidates": _public_images(match["images"]),
            }
        if match["status"] == "ambiguous":
            return {
                **base,
                "status": "ambiguous",
                "match_level": "original_tolerant",
                "candidates": _public_images(match["images"]),
            }

    fallback = _fallback_match(id_dossier, final_name, image_inventory)
    if fallback["status"] == "matched":
        image = fallback["images"][0]
        return {
            **base,
            "status": "matched",
            "match_level": str(fallback["match_level"]),
            "fallback_used": True,
            "source_name": image["name"],
            "candidates": _public_images(fallback["images"]),
        }
    if fallback["status"] == "ambiguous":
        return {
            **base,
            "status": "ambiguous",
            "match_level": str(fallback["match_level"]),
            "fallback_used": True,
            "candidates": _public_images(fallback["images"]),
        }

    suggestions = _partial_suggestions(
        [*original_names, id_dossier, Path(final_name).stem],
        image_inventory["images"],
    )
    if suggestions:
        return {
            **base,
            "status": "ambiguous",
            "match_level": "partial_suggestion",
            "suggestions": _public_images(suggestions),
        }
    return base


def root_image_inventory(inspection_payload: dict[str, Any]) -> dict[str, Any]:
    images = [
        dict(image)
        for image in inspection_payload.get("images", [])
        if isinstance(image, dict) and image.get("name")
    ]
    exact_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exact_stem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tolerant_stem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for image in images:
        name = str(image["name"])
        exact_name[_full_name_key(name)].append(image)
        exact_stem[_exact_stem(name)].append(image)
        tolerant_stem[_tolerant_stem_key(name)].append(image)
    return {
        "images": images,
        "exact_name": exact_name,
        "exact_stem": exact_stem,
        "tolerant_stem": tolerant_stem,
    }


def source_image_columns(normalized_payload: dict[str, Any]) -> list[dict[str, Any]]:
    columns = []
    for column in normalized_payload.get("columns", []):
        if not isinstance(column, dict):
            continue
        csv_name = str(column.get("csv_name") or "")
        if bool(column.get("system")) or csv_name in {"imageid", "@pathimg"}:
            continue
        if column.get("logical_role") == MATCHABLE_IMAGE_SOURCE_ROLE:
            columns.append(
                {
                    "csv_name": csv_name,
                    "source_sheet": column.get("source_sheet"),
                    "source_column_letter": column.get("source_column_letter"),
                    "source_header": column.get("source_header"),
                }
            )
    return columns


def source_image_values(
    values: dict[str, Any], columns: list[dict[str, Any]]
) -> list[str]:
    result: list[str] = []
    for column in columns:
        raw_value = values.get(str(column["csv_name"]), "")
        for value in _split_source_image_value(raw_value):
            if value not in result:
                result.append(value)
    return result


def _fallback_match(
    id_dossier: str,
    final_name: str,
    image_inventory: dict[str, Any],
) -> dict[str, Any]:
    probes = [
        ("id_fallback_exact", _exact_stem(id_dossier), image_inventory["exact_stem"]),
        (
            "id_fallback_exact_final_name",
            _exact_stem(final_name),
            image_inventory["exact_stem"],
        ),
        (
            "id_fallback_tolerant",
            _tolerant_stem_key(id_dossier),
            image_inventory["tolerant_stem"],
        ),
        (
            "id_fallback_tolerant_final_name",
            _tolerant_stem_key(final_name),
            image_inventory["tolerant_stem"],
        ),
    ]
    for match_level, key, lookup in probes:
        match = _unique_match(key, lookup)
        if match["status"] != "missing":
            return {**match, "match_level": match_level}
    return {"status": "missing", "images": (), "match_level": "none"}


def _split_source_image_value(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    parts = re.split(r"(?:<br>|\r\n|\r|\n)+", text)
    return [Path(part.strip()).name for part in parts if part.strip()]


def _unique_match(key: str, lookup: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if not key:
        return {"status": "missing", "images": ()}
    images = lookup.get(key, [])
    if len(images) == 1:
        return {"status": "matched", "images": tuple(images)}
    if len(images) > 1:
        return {"status": "ambiguous", "images": tuple(images)}
    return {"status": "missing", "images": ()}


def _partial_suggestions(
    probes: list[str],
    images: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    probe_keys = [
        _tolerant_stem_key(probe)
        for probe in probes
        if len(_tolerant_stem_key(probe)) >= PARTIAL_SUGGESTION_MIN_LENGTH
    ]
    for image in images:
        image_key = _tolerant_stem_key(str(image.get("name") or ""))
        if len(image_key) < PARTIAL_SUGGESTION_MIN_LENGTH:
            continue
        if any(
            probe_key in image_key or image_key in probe_key for probe_key in probe_keys
        ):
            suggestions.append(image)
            if len(suggestions) >= PARTIAL_SUGGESTION_LIMIT:
                break
    return suggestions


def _public_images(
    images: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    return [
        {
            "name": str(image.get("name") or ""),
            "extension": str(image.get("extension") or ""),
            "size_bytes": int(image.get("size_bytes") or 0),
        }
        for image in images
    ]


def _image_by_name(
    image_inventory: dict[str, Any],
    source_name: str,
) -> dict[str, Any] | None:
    exact = _full_name_key(source_name)
    for image in image_inventory["images"]:
        if _full_name_key(str(image.get("name") or "")) == exact:
            return image
    return None


def _full_name_key(value: str) -> str:
    return unicodedata.normalize("NFC", Path(str(value)).name)


def _exact_stem(value: str) -> str:
    return unicodedata.normalize("NFC", Path(Path(str(value)).name).stem)


def _tolerant_stem_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", _exact_stem(value))
    ascii_text = text.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[\s._-]+", "", ascii_text)
