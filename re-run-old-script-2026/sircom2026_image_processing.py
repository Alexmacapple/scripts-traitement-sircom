#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Traitement physique des fichiers images."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from PIL import Image


class ImageProcessingLogger(Protocol):
    def info(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...


def get_available_images(
    source_dir: str,
    allowed_extensions: list[str],
) -> dict[str, str]:
    """Récupère les images disponibles dans le répertoire source."""
    image_files = {}
    allowed = {extension.lower().lstrip(".") for extension in allowed_extensions}

    for filename in os.listdir(source_dir):
        if filename.startswith("."):
            continue

        extension = os.path.splitext(filename)[1][1:].lower()
        if extension in allowed:
            image_files[filename] = os.path.join(source_dir, filename)

    return image_files


def process_and_rename_image(
    image_path: str,
    new_name: str,
    target_dir: str,
    logger: ImageProcessingLogger,
    *,
    max_width: int,
    jpeg_quality: int,
    dpi: int,
) -> tuple[bool, int]:
    """Redimensionne, convertit en JPEG et renomme une image."""
    try:
        Image.MAX_IMAGE_PIXELS = None

        with Image.open(image_path) as image:
            image.thumbnail((max_width, max_width), Image.Resampling.LANCZOS)

            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background

            if image.mode != "RGB":
                image = image.convert("RGB")

            Path(target_dir).mkdir(parents=True, exist_ok=True)
            output_path = os.path.join(target_dir, new_name)
            image.save(output_path, "JPEG", quality=jpeg_quality, dpi=(dpi, dpi))

            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"  Image traitée : {new_name} ({file_size:,} octets)")
                return True, file_size

            logger.error(f"  Fichier de sortie non créé : {new_name}")
            return False, 0

    except Exception as exc:
        logger.error(f"  ERREUR lors du traitement : {exc}")
        return False, 0
