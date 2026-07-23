#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Règles Sircom 2026 partagées par la copie des anciens scripts."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
DEFAULT_VARIABLES_FILE = SCRIPT_DIR / "variables.md"

DEFAULT_CONFIG = {
    "excel_source_path": (
        "livrables-miweb/livrables-2026/jeux-test-23-juillet/"
        "excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx"
    ),
    "images_source_path": (
        "livrables-miweb/livrables-2026/jeux-test-23-juillet/images-jeux-test-2026.zip"
    ),
    "pathimg_root": "Macintosh HD:Users:victoria:Documents:export-jpg-resize",
    "pathimg_separator": "AUTO",
    "sheet_name": "BDD TT + ANALYSE DGDDI",
    "output_dir": "AUTO",
    "output_dir_name": "livrables_output",
    "output_date_format": "%Y-%m-%d",
    "append_date_suffix": "true",
    "include_hidden_rows": "false",
    "allow_missing_images": "true",
    "empty_cell_marker": "#N/A",
    "empty_value_tokens": "#N/A,N/A,none,None,undefined",
    "imageid_column_name": "imageid",
    "pathimg_column_name": "@pathimg",
    "image_filename_extension": "jpg",
    "source_images_workdir": "images",
    "processed_images_dir": "11-export-images-id-dossier-rename-resize",
    "image_max_width_px": "350",
    "image_jpeg_quality": "100",
    "image_dpi": "300",
    "image_allowed_extensions": (
        "jpg,jpeg,png,gif,webp,tif,tiff,bmp,eps,svg,ico,heic,heif,"
        "psd,raw,hdr,exr,jp2,pgm,ppm,xcf"
    ),
    "source_image_column_candidates": (
        "y_photodu,y_photo,photo_du_produit,photo_produit,photo,"
        "nom_image_source,image_source,source_image"
    ),
    "sort_region_header_contains": "region",
    "sort_departement_header_contains": "departement",
    "sort_departement_header_excludes": "postal",
    "date_header_contains": "date",
    "date_output_format": "%d/%m/%Y",
    "date_input_formats": "%Y-%m-%d,%Y-%m-%d %H:%M:%S,%d/%m/%Y,%d-%m-%Y",
    "linebreak_replacement": "<br>",
    "clean_header_max_length": "10",
    "drop_empty_columns": "true",
    "drop_empty_rows": "true",
    "drop_rows_without_dossier_id": "true",
    "csv_encoding": "utf-16",
    "csv_delimiter": ",",
    "csv_lineterminator": "LF",
    "mapping_csv_encoding": "utf-8-sig",
    "mapping_special_columns": "imageid,@pathimg",
    "mapping_expected_columns": (
        "F=ID du dossier;G=Nom du produit;H=Nom de l'entreprise;"
        "I=Catégorie du produit;J=Description du produit;"
        "K=Prix départ usine;L=% de valeur ajouté en France;"
        "M=Exportation;N=Certification OFG;O=Label IG;"
        "P=Type d'entreprise;Q=Nombre de salariés;R=Chiffre d'affaires;"
        "S=Présentation de l'entreprise;U=Démarche de relocalisation;"
        "V=Label EPV;W=Programme du gouvernement;X=Le(s)quel(s);"
        "Y=Photo du produit"
    ),
    "step_00_output": "00-sircom-source.xlsx",
    "step_01_output": "01-cellules-vide-na.xlsx",
    "step_02_output": "02-header-lettres-colonne.xlsx",
    "step_03_output": "03-image-id.xlsx",
    "step_04_output": "04-tri-region-departement.xlsx",
    "step_05_output": "05-dates-formattees.xlsx",
    "step_06_output": "06-livrable-final.xlsx",
    "step_07_output": "07-clean-headers.xlsx",
    "step_08_output": "08-add-pathimg.xlsx",
    "step_09_output": "09-optimize-content.xlsx",
    "step_10_output": "10-final-sircom-indesign-utf16.csv",
    "mapping_csv_output": "12-mapping-colonnes-sircom-2026.csv",
    "mapping_excel_output": "12-mapping-colonnes-sircom-2026.xlsx",
    "summary_output": "run-2026-summary.json",
}

DEFAULT_SHEET_NAME = DEFAULT_CONFIG["sheet_name"]
DEFAULT_IMAGE_BASE_PATH = DEFAULT_CONFIG["pathimg_root"]
_CONFIG_CACHE: dict[Path, dict[str, str]] = {}


def resolve_variables_file(path: str | Path | None = None) -> Path:
    raw_path = path or os.environ.get("SIRCOM_VARIABLES_FILE") or DEFAULT_VARIABLES_FILE
    variables_path = Path(raw_path).expanduser()
    if not variables_path.is_absolute():
        variables_path = SCRIPT_DIR / variables_path
    return variables_path.resolve()


def load_variables(
    path: str | Path | None = None,
    *,
    include_defaults: bool = True,
) -> dict[str, str]:
    variables_path = resolve_variables_file(path)
    values: dict[str, str] = dict(DEFAULT_CONFIG) if include_defaults else {}
    if not variables_path.exists():
        return values
    if variables_path in _CONFIG_CACHE:
        loaded = _CONFIG_CACHE[variables_path]
    else:
        loaded = parse_variables_markdown(variables_path.read_text(encoding="utf-8"))
        _CONFIG_CACHE[variables_path] = loaded
    values.update(loaded)
    return values


def parse_variables_markdown(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    current_key: str | None = None
    awaiting_value_for: str | None = None

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        table_value = parse_variables_table_line(stripped)
        if table_value:
            key, value = table_value
            values[key] = value
            continue

        if stripped.startswith("### "):
            candidate = clean_markdown_cell(stripped[4:])
            current_key = candidate if candidate in DEFAULT_CONFIG else None
            awaiting_value_for = None
            continue

        if current_key and stripped.startswith("Valeur :"):
            inline_value = stripped.removeprefix("Valeur :").strip()
            if inline_value:
                values[current_key] = clean_markdown_cell(inline_value)
                current_key = None
            else:
                awaiting_value_for = current_key
            continue

        if awaiting_value_for:
            values[awaiting_value_for] = clean_markdown_cell(stripped)
            current_key = None
            awaiting_value_for = None

    return values


def parse_variables_table_line(line: str) -> tuple[str, str] | None:
    if not line.startswith("|") or line.startswith("| ---"):
        return None
    cells = [clean_markdown_cell(cell) for cell in line.strip("|").split("|")]
    if len(cells) < 2 or cells[0].lower() == "variable":
        return None
    key = cells[0]
    if key not in DEFAULT_CONFIG:
        return None
    return key, cells[1]


def clean_markdown_cell(value: str) -> str:
    text = value.strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        text = text[1:-1]
    return text.strip()


def config_value(key: str, default: str | None = None) -> str:
    env_name = f"SIRCOM_{key.upper()}"
    if env_name in os.environ:
        return os.environ[env_name]
    config = load_variables()
    fallback = DEFAULT_CONFIG.get(key, "" if default is None else default)
    return config.get(key, fallback)


def config_bool(key: str, *, default: bool) -> bool:
    value = config_value(key, "true" if default else "false")
    text = str(value).strip().lower()
    if text in {"1", "true", "vrai", "yes", "oui", "on"}:
        return True
    if text in {"0", "false", "faux", "no", "non", "off"}:
        return False
    raise ValueError(f"Variable booléenne invalide : {key}={value!r}")


def config_int(key: str, *, default: int, minimum: int | None = None) -> int:
    value = config_value(key, str(default))
    try:
        integer = int(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"Variable entière invalide : {key}={value!r}") from exc
    if minimum is not None and integer < minimum:
        raise ValueError(f"Variable trop petite : {key}={integer} < {minimum}")
    return integer


def config_list(key: str, *, default: str | None = None) -> list[str]:
    value = config_value(key, "" if default is None else default)
    return [item.strip() for item in str(value).split(",") if item.strip()]


def config_mapping(key: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for part in config_value(key, "").split(";"):
        if "=" not in part:
            continue
        left, right = part.split("=", 1)
        left = left.strip()
        right = right.strip()
        if left:
            mapping[left] = right
    return mapping


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_DIR / path
    return path.resolve()


def empty_cell_marker() -> str:
    return config_value("empty_cell_marker", "#N/A")


def imageid_column_name() -> str:
    return config_value("imageid_column_name", "imageid")


def pathimg_column_name() -> str:
    return config_value("pathimg_column_name", "@pathimg")


def display_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def normalize_ascii(value: object) -> str:
    text = unicodedata.normalize("NFKD", display_text(value))
    return text.encode("ascii", "ignore").decode("ascii").lower()


def normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_ascii(strip_excel_letter_prefix(value)))


def strip_excel_letter_prefix(value: object) -> str:
    text = display_text(value)
    return re.sub(r"^[A-Z]{1,3}_", "", text)


def is_empty_value(value: object) -> bool:
    tokens = {"", empty_cell_marker()}
    tokens.update(config_list("empty_value_tokens"))
    return display_text(value) in tokens


def is_dossier_id_header(value: object) -> bool:
    normalized = normalize_header(value)
    return normalized in {
        "dossierid",
        "iddossier",
        "idduossier",
        "iddudossier",
        "id",
        "fid",
        "bid",
    } or normalized.endswith("dossierid")


def find_dossier_id_column(sheet) -> tuple[int | None, str | None]:
    for cell in sheet[1]:
        if is_dossier_id_header(cell.value):
            return cell.column, display_text(cell.value)
    return None, None


def normalize_dossier_id_for_filename(value: object) -> str:
    text = normalize_ascii(value)
    without_spaces_and_dots = re.sub(r"[\s.]+", "", text)
    normalized = re.sub(r"[^a-z0-9_-]+", "", without_spaces_and_dots)
    return normalized or "sans-id"


def image_id_for_dossier(value: object) -> str:
    extension = config_value("image_filename_extension", "jpg").strip().lstrip(".")
    return f"{normalize_dossier_id_for_filename(value)}.{extension or 'jpg'}"


def pathimg_prefix(root: object) -> str:
    clean_root = display_text(root)
    if not clean_root:
        return ""
    if clean_root.endswith(("/", ":")):
        return clean_root
    return f"{clean_root}{pathimg_separator(clean_root)}"


def pathimg_separator(root: str) -> str:
    configured = config_value("pathimg_separator", "AUTO").strip()
    if configured and configured.upper() != "AUTO":
        return configured
    if ":" in root and "/" not in root:
        return ":"
    return "/"


def pathimg_path(root: object, final_name: object) -> str:
    return f"{pathimg_prefix(root)}{display_text(final_name)}"


def clean_csv_header(value: object) -> str:
    original = display_text(value)
    pathimg_header = pathimg_column_name()
    if original == pathimg_header:
        return pathimg_header
    normalized = normalize_header(original)
    imageid_header = imageid_column_name()
    if (
        normalized in {normalize_header(imageid_header), "image"}
        and "image" in normalized
    ):
        return imageid_header
    if is_dossier_id_header(original):
        return "id_dossier"
    text = normalize_ascii(original)
    text = re.sub(r"[^\w]", "", text)
    return text[: config_int("clean_header_max_length", default=10, minimum=1)]
