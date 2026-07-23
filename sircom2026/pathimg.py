from __future__ import annotations


DEFAULT_INDESIGN_IMAGE_ROOT = "Macintosh HD:Users:victoria:Documents:export-jpg-resize"


def clean_pathimg_root(value: object) -> str:
    return str(value or "").strip()


def pathimg_path(root: object, final_name: object) -> str:
    name = str(final_name or "").strip()
    clean_root = clean_pathimg_root(root)
    if not clean_root:
        return name
    return f"{pathimg_prefix(clean_root)}{name}"


def pathimg_prefix(root: object) -> str:
    clean_root = clean_pathimg_root(root)
    if not clean_root:
        return ""
    if clean_root.endswith(("/", ":")):
        return clean_root
    return f"{clean_root}{_pathimg_separator(clean_root)}"


def _pathimg_separator(root: str) -> str:
    if ":" in root and "/" not in root:
        return ":"
    return "/"
