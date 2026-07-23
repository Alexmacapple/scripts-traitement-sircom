from __future__ import annotations

import re
import unicodedata


def image_id_for_dossier(id_dossier: str) -> str:
    return f"{normalize_dossier_id_for_filename(id_dossier)}.jpg"


def normalize_dossier_id_for_filename(id_dossier: str) -> str:
    text = unicodedata.normalize("NFKD", str(id_dossier).strip())
    ascii_text = text.encode("ascii", "ignore").decode("ascii").lower()
    without_spaces_and_dots = re.sub(r"[\s.]+", "", ascii_text)
    normalized = re.sub(r"[^a-z0-9_-]+", "", without_spaces_and_dots)
    return normalized or "sans-id"
