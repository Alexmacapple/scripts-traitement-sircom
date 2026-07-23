#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Runner reproductible du jeu de test Sircom 2026 pour la voie scriptée."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

from sircom2026_rules import (
    DEFAULT_CONFIG,
    DEFAULT_IMAGE_BASE_PATH,
    DEFAULT_SHEET_NAME,
    DEFAULT_VARIABLES_FILE,
    load_variables as load_config_variables,
    resolve_repo_path,
    resolve_variables_file,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
OUTPUT_DIR_PREFIX = DEFAULT_CONFIG["output_dir_name"]
LEGACY_OUTPUT_DIR = SCRIPT_DIR / OUTPUT_DIR_PREFIX
DEFAULT_EXCEL = resolve_repo_path(DEFAULT_CONFIG["excel_source_path"])
DEFAULT_IMAGES_SOURCE = resolve_repo_path(DEFAULT_CONFIG["images_source_path"])

GENERATED_PATHS = [
    "Sircom.xlsx",
    "Sircom_vide_na.xlsx",
    "1-header-lettres-colonne-excel-mapping-excel.xlsx",
    "2-image-id-adder-excel-fusion.xlsx",
    "3-fusion-tri-region-departement.xlsx",
    "4-changer-date.xlsx",
    "5-livrable-final-word.xlsx",
    "6-clean-headers.xlsx",
    "7-add-pathimg.xlsx",
    "8-optimize-content.xlsx",
    "9-final-sircom-indesign-utf16.csv",
    "00-sircom-source.xlsx",
    "01-cellules-vide-na.xlsx",
    "02-header-lettres-colonne.xlsx",
    "03-image-id.xlsx",
    "04-tri-region-departement.xlsx",
    "05-dates-formattees.xlsx",
    "06-livrable-final.xlsx",
    "07-clean-headers.xlsx",
    "08-add-pathimg.xlsx",
    "09-optimize-content.xlsx",
    "10-final-sircom-indesign-utf16.csv",
    "12-mapping-colonnes-sircom-2026.csv",
    "12-mapping-colonnes-sircom-2026.xlsx",
    "run-2026-summary.json",
    "images",
    "export_images_id_dossier_rename_resize",
    "11-export-images-id-dossier-rename-resize",
    "__pycache__",
]
GENERATED_GLOBS = [
    "images-processing-*.log",
    "mapping_colonnes_*.csv",
    "mapping_colonnes_*.xlsx",
]
CONFIGURED_GENERATED_PATH_KEYS = [
    "step_00_output",
    "step_01_output",
    "step_02_output",
    "step_03_output",
    "step_04_output",
    "step_05_output",
    "step_06_output",
    "step_07_output",
    "step_08_output",
    "step_09_output",
    "step_10_output",
    "mapping_csv_output",
    "mapping_excel_output",
    "summary_output",
    "source_images_workdir",
    "processed_images_dir",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exécuter la copie scriptée 2026 sur le jeu officiel.",
    )
    parser.add_argument(
        "--variables",
        default=str(DEFAULT_VARIABLES_FILE),
        help="Fichier Markdown de variables.",
    )
    parser.add_argument("--excel", default=None, help="Excel source.")
    parser.add_argument(
        "--images-zip",
        default=None,
        help="Alias historique de --images-source.",
    )
    parser.add_argument(
        "--images-source",
        default=None,
        help="ZIP ou répertoire contenant les images source.",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help="Onglet source à extraire.",
    )
    parser.add_argument(
        "--pathimg-root",
        default=None,
        help="Racine InDesign à écrire dans @pathimg.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Dossier des livrables générés.",
    )
    parser.add_argument(
        "--include-hidden-rows",
        action="store_true",
        help="Inclure les lignes masquées, quelle que soit la configuration.",
    )
    parser.add_argument(
        "--require-all-images",
        action="store_true",
        help="Échouer si des images référencées manquent.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Supprimer uniquement les artefacts générés connus avant exécution.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    variables_file = resolve_variables_file(args.variables)
    config = load_config_variables(variables_file)
    validate_generated_paths(config)
    excel_path = resolve_input_path(
        coalesce(args.excel, config.get("excel_source_path"), str(DEFAULT_EXCEL))
    )
    images_source_path = resolve_input_path(
        coalesce(
            args.images_source,
            args.images_zip,
            config.get("images_source_path"),
            str(DEFAULT_IMAGES_SOURCE),
        )
    )
    sheet_name = coalesce(args.sheet, config.get("sheet_name"), DEFAULT_SHEET_NAME)
    pathimg_root = coalesce(
        args.pathimg_root,
        config.get("pathimg_root"),
        DEFAULT_IMAGE_BASE_PATH,
    )
    output_dir_name = coalesce(config.get("output_dir_name"), OUTPUT_DIR_PREFIX)
    output_date_format = coalesce(config.get("output_date_format"), "%Y-%m-%d")
    append_date_suffix = parse_bool(config.get("append_date_suffix"), default=True)
    output_dir = resolve_output_dir(
        coalesce(args.output_dir, config.get("output_dir"), "AUTO"),
        output_dir_name=output_dir_name,
        output_date_format=output_date_format,
        append_date_suffix=append_date_suffix,
    )
    include_hidden_rows = args.include_hidden_rows or parse_bool(
        config.get("include_hidden_rows"), default=False
    )
    allow_missing_images = not args.require_all_images and parse_bool(
        config.get("allow_missing_images"), default=True
    )
    if not excel_path.exists():
        raise SystemExit(f"Excel introuvable : {excel_path}")
    if not images_source_path.exists():
        raise SystemExit(f"Source images introuvable : {images_source_path}")

    if args.clean:
        clean_generated_paths(output_dir, config)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = build_env(config, variables_file, pathimg_root)

    extract_step = [
        "00-extract_departement_to_sircom.py",
        "--source",
        str(excel_path),
        "--output",
        config["step_00_output"],
        "--sheet",
        sheet_name,
    ]
    if include_hidden_rows:
        extract_step.append("--include-hidden-rows")

    steps = [
        extract_step,
        ["01-si-cellule-vide-na.py"],
        ["02-header_lettres_colonne.py"],
        ["03-image_id_adder.py"],
        ["04-fusion_tri_region_departement.py"],
        ["05-changer-date-format.py"],
        ["06-livrable-final.py"],
        ["07-clean_headers_excel.py"],
        ["08-add_pathimg_excel.py"],
        ["09-optimize_content_excel.py"],
        ["10-export_csv_utf16_final.py"],
    ]
    for step in steps:
        run_python(step, env, output_dir)

    source_images_workdir = config["source_images_workdir"]
    processed_images_dir = config["processed_images_dir"]
    prepare_images(images_source_path, output_dir / source_images_workdir)
    image_step = [
        "11-process-images.py",
        "--source-dir",
        source_images_workdir,
        "--target-dir",
        processed_images_dir,
        "--excel-file",
        config["step_08_output"],
    ]
    if allow_missing_images:
        image_step.append("--allow-missing")
    run_python(image_step, env, output_dir)
    run_python(["12-create_mapping_excel.py"], env, output_dir)
    run_python(["13-verify_data_integrity.py"], env, output_dir)
    write_summary(
        args,
        config,
        variables_file,
        excel_path,
        images_source_path,
        output_dir,
        sheet_name,
        pathimg_root,
        output_dir_name,
        output_date_format,
        append_date_suffix,
        include_hidden_rows,
        allow_missing_images,
    )
    return 0


def coalesce(*values: str | None) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.upper() != "AUTO":
            return text
        if text.upper() == "AUTO":
            return "AUTO"
    return ""


def parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "vrai", "yes", "oui", "on"}:
        return True
    if text in {"0", "false", "faux", "no", "non", "off"}:
        return False
    return default


def resolve_input_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = REPO_DIR / path
    return path.resolve()


def resolve_output_dir(
    raw_output_dir: str,
    *,
    output_dir_name: str,
    output_date_format: str,
    append_date_suffix: bool,
) -> Path:
    if not raw_output_dir or raw_output_dir.upper() == "AUTO":
        return default_output_dir(
            output_dir_name=output_dir_name,
            output_date_format=output_date_format,
            append_date_suffix=append_date_suffix,
        ).resolve()
    output_dir = Path(raw_output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = SCRIPT_DIR / output_dir
    return output_dir.resolve()


def default_output_dir(
    today: date | None = None,
    *,
    output_dir_name: str = OUTPUT_DIR_PREFIX,
    output_date_format: str = "%Y-%m-%d",
    append_date_suffix: bool = True,
) -> Path:
    current_date = today or date.today()
    clean_name = output_dir_name.strip() or OUTPUT_DIR_PREFIX
    clean_name = safe_generated_path_fragment("output_dir_name", clean_name)
    if append_date_suffix:
        date_suffix = current_date.strftime(output_date_format or "%Y-%m-%d")
        clean_name = f"{clean_name}_{date_suffix}"
    return SCRIPT_DIR / clean_name


def clean_generated_paths(output_dir: Path, config: dict[str, str]) -> None:
    # Nettoie aussi les anciens artefacts à la racine pour éviter les livrables périmés.
    legacy_output_dir = LEGACY_OUTPUT_DIR.resolve()
    for base_dir in dict.fromkeys([output_dir, legacy_output_dir, SCRIPT_DIR]):
        for relative_path in generated_paths(config):
            delete_generated_path(base_dir, relative_path)
        for pattern in GENERATED_GLOBS:
            for path in base_dir.glob(pattern):
                if path.is_file():
                    path.unlink()
        if (
            base_dir == legacy_output_dir
            and base_dir != output_dir
            and base_dir.exists()
        ):
            try:
                base_dir.rmdir()
            except OSError:
                pass


def generated_paths(config: dict[str, str]) -> list[str]:
    configured = [
        safe_generated_path_fragment(key, config.get(key, ""))
        for key in CONFIGURED_GENERATED_PATH_KEYS
    ]
    return sorted({path for path in [*GENERATED_PATHS, *configured] if path})


def validate_generated_paths(config: dict[str, str]) -> None:
    generated_paths(config)


def safe_generated_path_fragment(key: str, raw_path: str) -> str:
    text = str(raw_path).strip()
    if not text or text.upper() == "AUTO":
        return ""
    path = Path(text).expanduser()
    normalized_path = path.as_posix()
    if (
        path.is_absolute()
        or normalized_path in {"", "."}
        or any(part in {".."} for part in path.parts)
    ):
        raise SystemExit(
            f"Chemin d'artefact généré non borné pour {key} : {raw_path!r}. "
            "Utiliser un chemin relatif sans '..'."
        )
    return normalized_path


def delete_generated_path(base_dir: Path, relative_path: str) -> None:
    base = base_dir.resolve()
    path = base / relative_path
    if not path.exists() and not path.is_symlink():
        return
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise SystemExit(
            f"Refus de supprimer un artefact hors du dossier de nettoyage : {path}"
        ) from exc
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def build_env(
    config: dict[str, str],
    variables_file: Path,
    pathimg_root: str,
) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["SIRCOM_VARIABLES_FILE"] = str(variables_file)
    for key, value in config.items():
        env[f"SIRCOM_{key.upper()}"] = value
    env["SIRCOM_PATHIMG_ROOT"] = pathimg_root
    env["SIRCOM_IMAGE_BASE_PATH"] = pathimg_root
    return env


def run_python(args: list[str], env: dict[str, str], output_dir: Path) -> None:
    script_name, *script_args = args
    command = [sys.executable, str(SCRIPT_DIR / script_name), *script_args]
    print()
    print("=" * 80)
    print("RUN", " ".join(command))
    print("CWD", output_dir)
    print("=" * 80)
    subprocess.run(command, cwd=output_dir, env=env, check=True)


def prepare_images(source_path: Path, target_dir: Path) -> None:
    if source_path.is_dir():
        copy_images(source_path, target_dir)
    else:
        extract_images(source_path, target_dir)


def copy_images(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source_path in sorted(source_dir.iterdir()):
        if not source_path.is_file() or source_path.name.startswith("."):
            continue
        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)
        copied += 1
    print(f"Images copiées : {copied} vers {target_dir}")


def extract_images(source_zip: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    members_to_extract: list[tuple[zipfile.ZipInfo, str]] = []
    seen_names: dict[str, str] = {}
    blockers: list[str] = []
    with zipfile.ZipFile(source_zip) as archive:
        for member in archive.infolist():
            name = member.filename
            if member.is_dir() or name.startswith("__MACOSX/"):
                continue
            filename = Path(name).name
            if not filename or filename.startswith("."):
                continue
            if Path(name).as_posix() != filename:
                blockers.append(f"image en sous-dossier : {name}")
                continue
            normalized_filename = filename.casefold()
            previous_name = seen_names.get(normalized_filename)
            if previous_name is not None:
                blockers.append(f"nom d'image dupliqué : {previous_name} / {name}")
                continue
            seen_names[normalized_filename] = name
            members_to_extract.append((member, filename))
        if blockers:
            raise SystemExit("Zip images non supporté : " + "; ".join(blockers[:5]))
        for member, filename in members_to_extract:
            target_path = target_dir / filename
            with archive.open(member) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)
    print(f"Images extraites : {len(members_to_extract)} vers {target_dir}")


def write_summary(
    args: argparse.Namespace,
    config: dict[str, str],
    variables_file: Path,
    excel_path: Path,
    images_source_path: Path,
    output_dir: Path,
    sheet_name: str,
    pathimg_root: str,
    output_dir_name: str,
    output_date_format: str,
    append_date_suffix: bool,
    include_hidden_rows: bool,
    allow_missing_images: bool,
) -> None:
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "variables": str(variables_file),
        "excel": str(excel_path),
        "images_source": str(images_source_path),
        "sheet": sheet_name,
        "pathimg_root": pathimg_root,
        "output_dir_name": output_dir_name,
        "output_date_format": output_date_format,
        "append_date_suffix": append_date_suffix,
        "include_hidden_rows": include_hidden_rows,
        "allow_missing_images": allow_missing_images,
        "output_dir": str(output_dir),
        "outputs": {
            "csv": str(output_dir / config["step_10_output"]),
            "images": str(output_dir / config["processed_images_dir"]),
            "mapping_excel": str(output_dir / config["mapping_excel_output"]),
            "mapping_csv": str(output_dir / config["mapping_csv_output"]),
            "verification": "13-verify_data_integrity.py",
        },
        "rules": {
            "empty_cells": config["empty_cell_marker"],
            "imageid": (
                "{id_dossier_normalise}."
                f"{config['image_filename_extension'].lstrip('.')}"
            ),
            "imageid_column": config["imageid_column_name"],
            "pathimg_column": config["pathimg_column_name"],
            "hidden_rows": (
                "included by extraction"
                if include_hidden_rows
                else "ignored by extraction"
            ),
        },
        "selected_variables": {
            key: config[key]
            for key in sorted(config)
            if key not in {"mapping_expected_columns"}
        },
    }
    output = output_dir / config["summary_output"]
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Résumé écrit : {output}")


if __name__ == "__main__":
    raise SystemExit(main())
