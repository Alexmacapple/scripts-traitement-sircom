#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Point d'entrée CLI du traitement images Sircom 2026.

Le script garde la compatibilité avec l'ancien usage :

```bash
python3 11-process-images.py --source-dir images --target-dir export --excel-file data.xlsx
```

La logique métier est volontairement déléguée à trois modules locaux :
matching, lecture du mapping Excel et traitement physique des images.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sircom2026_image_mapping import read_excel_mapping
from sircom2026_image_matching import AmbiguousImageMatchError, find_best_match
from sircom2026_image_processing import get_available_images, process_and_rename_image
from sircom2026_rules import config_int, config_list, config_value


MAX_WIDTH = config_int("image_max_width_px", default=350, minimum=1)
JPEG_QUALITY = config_int("image_jpeg_quality", default=100, minimum=1)
DPI = config_int("image_dpi", default=300, minimum=1)

EXCEL_FILE = config_value("step_08_output")
SOURCE_DIR = config_value("source_images_workdir", "images")
TARGET_DIR = config_value("processed_images_dir")
ALLOWED_EXTENSIONS = config_list("image_allowed_extensions")


@dataclass
class ImageRunStats:
    success_count: int = 0
    error_count: int = 0
    not_found_count: int = 0
    total_size: int = 0
    used_images: set[str] = field(default_factory=set)


def setup_logging() -> logging.Logger:
    """Configure le journal du traitement images."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"images-processing-{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("TRAITEMENT GÉNÉRIQUE DES IMAGES - SIRCOM 2026")
    logger.info("=" * 80)
    logger.info(
        f"Date/heure de début : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}"
    )
    logger.info(f"Fichier de log : {log_filename}")
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Traiter les images source Sircom 2026."
    )
    parser.add_argument(
        "--source-dir",
        default=SOURCE_DIR,
        help="Dossier contenant les images source",
    )
    parser.add_argument(
        "--target-dir",
        default=TARGET_DIR,
        help="Dossier de sortie des images JPG traitées",
    )
    parser.add_argument(
        "--excel-file",
        default=EXCEL_FILE,
        help="Fichier Excel de mapping image à lire",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Retourner un succès si au moins une image est traitée et que seules des images manquent.",
    )
    return parser.parse_args()


def check_prerequisites(
    excel_file: str,
    source_dir: str,
    logger: logging.Logger,
) -> bool:
    """Vérifie que le fichier Excel et les images source sont disponibles."""
    logger.info("VÉRIFICATION DES PRÉREQUIS")

    if not os.path.exists(excel_file):
        logger.error(f"Fichier Excel manquant : {excel_file}")
        return False
    logger.info(f"Fichier Excel trouvé : {excel_file}")

    if not os.path.exists(source_dir):
        logger.error(f"Répertoire d'images manquant : {source_dir}")
        logger.error("Veuillez créer le répertoire et y placer les images à traiter")
        return False
    logger.info(f"Répertoire d'images trouvé : {source_dir}")

    image_files = get_available_images(source_dir, ALLOWED_EXTENSIONS)
    if not image_files:
        logger.error(f"Aucune image trouvée dans : {source_dir}")
        logger.error(f"Extensions supportées : {', '.join(ALLOWED_EXTENSIONS)}")
        return False
    logger.info(f"{len(image_files)} images trouvées dans le répertoire source")

    return True


def process_images(
    mapping: dict[str, dict[str, str]],
    available_images: dict[str, str],
    target_dir: str,
    logger: logging.Logger,
) -> ImageRunStats:
    """Traite les images selon le mapping ID dossier -> image finale."""
    stats = ImageRunStats()

    for dossier_id, image_mapping in mapping.items():
        source_image_name = image_mapping["source_name"]
        new_name = image_mapping["final_name"]

        try:
            matched_file = find_best_match(
                source_image_name, available_images.keys(), logger
            )
        except AmbiguousImageMatchError as exc:
            logger.error(
                "Image ambiguë : %s (dossier %s). Candidats : %s",
                source_image_name,
                dossier_id,
                ", ".join(exc.candidates),
            )
            stats.error_count += 1
            continue

        if not matched_file:
            logger.warning(
                f"Image non trouvée : {source_image_name} (dossier {dossier_id})"
            )
            stats.not_found_count += 1
            continue

        logger.info(f"Traitement : {matched_file} -> {new_name}")
        logger.info(f"  ID Dossier : {dossier_id}")
        if matched_file != source_image_name:
            logger.info(f"  Nom dans Excel : {source_image_name}")

        success, file_size = process_and_rename_image(
            available_images[matched_file],
            new_name,
            target_dir,
            logger,
            max_width=MAX_WIDTH,
            jpeg_quality=JPEG_QUALITY,
            dpi=DPI,
        )
        stats.used_images.add(matched_file)
        if success:
            stats.success_count += 1
            stats.total_size += file_size
        else:
            stats.error_count += 1

    return stats


def log_unused_images(
    available_images: dict[str, str],
    used_images: set[str],
    logger: logging.Logger,
) -> None:
    unused_images = [image for image in available_images if image not in used_images]
    if not unused_images:
        return

    logger.warning("IMAGES NON RÉFÉRENCÉES DANS EXCEL (non traitées) :")
    for image in unused_images:
        logger.warning(f"  {image}")


def log_summary(target_dir: str, stats: ImageRunStats, logger: logging.Logger) -> None:
    logger.info("=" * 80)
    logger.info("RÉSUMÉ DU TRAITEMENT")
    logger.info("=" * 80)
    logger.info(f"Images traitées avec succès : {stats.success_count}")
    logger.info(f"Erreurs de traitement : {stats.error_count}")
    logger.info(f"Images référencées mais non trouvées : {stats.not_found_count}")
    logger.info(f"Répertoire de sortie : {target_dir}")
    logger.info(
        f"Espace disque utilisé : {stats.total_size:,} octets "
        f"({stats.total_size / 1024 / 1024:.2f} MB)"
    )

    if os.path.exists(target_dir):
        output_files = sorted(os.listdir(target_dir))
        logger.info(f"\nFICHIERS CRÉÉS DANS {target_dir} :")
        for filename in output_files[:10]:
            logger.info(f"  - {filename}")
        if len(output_files) > 10:
            logger.info(f"  ... et {len(output_files) - 10} autres fichiers")
        logger.info(f"Total fichiers créés : {len(output_files)}")


def run(args: argparse.Namespace, logger: logging.Logger) -> bool:
    logger.info("PARAMÈTRES DE TRAITEMENT :")
    logger.info(f"  - Largeur max : {MAX_WIDTH}px")
    logger.info(f"  - Qualité JPEG : {JPEG_QUALITY}%")
    logger.info(f"  - DPI : {DPI}")
    logger.info(f"  - Source : {args.source_dir}")
    logger.info(f"  - Destination : {args.target_dir}")

    if not check_prerequisites(args.excel_file, args.source_dir, logger):
        logger.error("Prérequis non satisfaits - Arrêt du traitement")
        return False

    mapping = read_excel_mapping(args.excel_file, logger)
    if not mapping:
        logger.error("Impossible de continuer sans mapping ID/image")
        return False

    available_images = get_available_images(args.source_dir, ALLOWED_EXTENSIONS)
    logger.info(f"{len(available_images)} images disponibles dans {args.source_dir}")

    Path(args.target_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"Répertoire de destination : {args.target_dir}")

    logger.info("=" * 80)
    logger.info("DÉBUT DU TRAITEMENT ET RENOMMAGE DES IMAGES")
    logger.info("=" * 80)

    stats = process_images(mapping, available_images, args.target_dir, logger)
    log_unused_images(available_images, stats.used_images, logger)
    log_summary(args.target_dir, stats, logger)

    if (
        stats.success_count > 0
        and stats.error_count == 0
        and (stats.not_found_count == 0 or args.allow_missing)
    ):
        logger.info("TRAITEMENT TERMINÉ AVEC SUCCÈS !")
        if stats.not_found_count:
            logger.warning("Images manquantes acceptées par l'option --allow-missing")
        return True

    if stats.success_count > 0:
        logger.error("TRAITEMENT INCOMPLET : erreurs ou images manquantes")
    else:
        logger.error("AUCUNE IMAGE N'A PU ÊTRE TRAITÉE")
    return False


def main() -> bool:
    logger = setup_logging()
    try:
        return run(parse_args(), logger)
    except Exception as exc:
        logger.error(f"Erreur critique : {exc}")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
