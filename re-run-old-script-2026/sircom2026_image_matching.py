#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Correspondance entre noms d'images attendus et fichiers disponibles."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Protocol


class ImageMatchLogger(Protocol):
    def info(self, message: str) -> None: ...


class AmbiguousImageMatchError(ValueError):
    """Signalée quand plusieurs fichiers peuvent correspondre à la même image."""

    def __init__(self, target_name: str, candidates: Iterable[str]) -> None:
        self.target_name = target_name
        self.candidates = sorted(candidates)
        super().__init__(
            f"Plusieurs images correspondent à {target_name!r} : "
            + ", ".join(self.candidates)
        )


def normalize_filename(filename: str | None) -> str:
    """Normalise un nom de fichier pour la comparaison."""
    if not filename:
        return ""
    return re.sub(r"\s+", " ", filename.strip())


def find_best_match(
    target_name: str,
    available_files: Iterable[str],
    logger: ImageMatchLogger,
) -> str | None:
    """Trouve la meilleure correspondance pour un nom de fichier attendu."""
    available = list(available_files)
    target_normalized = normalize_filename(target_name)

    exact_candidates = [filename for filename in available if filename == target_name]
    if len(exact_candidates) == 1:
        return target_name
    if len(exact_candidates) > 1:
        raise AmbiguousImageMatchError(target_name, exact_candidates)

    normalized_candidates = [
        filename
        for filename in available
        if normalize_filename(filename) == target_normalized
    ]
    if len(normalized_candidates) == 1:
        logger.info(f"  Correspondance normalisée trouvée : {normalized_candidates[0]}")
        return normalized_candidates[0]
    if len(normalized_candidates) > 1:
        raise AmbiguousImageMatchError(target_name, normalized_candidates)

    target_base = os.path.splitext(target_normalized)[0]
    base_candidates = [
        filename
        for filename in available
        if os.path.splitext(normalize_filename(filename))[0] == target_base
    ]
    if len(base_candidates) == 1:
        logger.info(f"  Correspondance par nom de base trouvée : {base_candidates[0]}")
        return base_candidates[0]
    if len(base_candidates) > 1:
        raise AmbiguousImageMatchError(target_name, base_candidates)

    if len(target_base) > 10:
        keywords = target_base.split("_")[:2]
        if keywords:
            main_keyword = keywords[0]
            candidates = [
                filename
                for filename in available
                if main_keyword.lower() in filename.lower()
            ]
            if len(candidates) == 1:
                logger.info(f"  Correspondance partielle trouvée : {candidates[0]}")
                return candidates[0]
            if len(candidates) > 1:
                raise AmbiguousImageMatchError(target_name, candidates)

    return None
