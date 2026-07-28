#!/usr/bin/env python3
"""Télécharger les pièces jointes listées dans un CSV Démarches simplifiées.

Le CSV doit contenir une colonne `download_url`. Les fichiers peuvent être
rangés par dossier avec `--group-by-dossier`.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ERROR_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "application/json",
    "application/problem+json",
    "application/xml",
    "text/xml",
}
ZIP_CONTAINER_SUFFIXES = {
    ".docx",
    ".odp",
    ".ods",
    ".odt",
    ".pptx",
    ".xlsx",
    ".zip",
}
OLE_CONTAINER_SUFFIXES = {".doc", ".ppt", ".xls"}
TEXT_ATTACHMENT_SUFFIXES = {".csv", ".md", ".rtf", ".txt"}


def clean_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned in {".", ".."}:
        return ""
    return cleaned


def truncate_utf8(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def safe_filename(value: str, fallback: str = "fichier") -> str:
    return truncate_utf8(clean_filename(value), 180) or fallback


def safe_attachment_filename(value: str, fallback: str = "fichier") -> str:
    cleaned = clean_filename(value)
    if not cleaned:
        return fallback

    suffix = Path(cleaned).suffix
    if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", suffix):
        suffix = ""
    if len(cleaned.encode("utf-8")) <= 180:
        return cleaned

    stem = cleaned[: -len(suffix)] if suffix else cleaned
    stem_limit = 180 - len(suffix.encode("utf-8"))
    shortened = truncate_utf8(stem, stem_limit).rstrip(" .")
    return f"{shortened}{suffix}" if shortened else fallback


def detect_dialect(csv_path: Path) -> csv.Dialect:
    sample = csv_path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,")
    except csv.Error:
        return csv.get_dialect("excel")


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    dialect = detect_dialect(csv_path)
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames or "download_url" not in reader.fieldnames:
            raise ValueError(f"Colonne obligatoire absente dans {csv_path}: download_url")
        return list(reader)


def target_path(row: dict[str, str], output_dir: Path, group_by_dossier: bool) -> Path:
    base_dir = output_dir
    if group_by_dossier:
        base_dir = output_dir / safe_filename(row.get("dossier_id", ""), "dossier")

    dossier_id = safe_filename(row.get("dossier_id", ""), "dossier")
    index = safe_filename(str(row.get("attachment_index") or ""), "")
    filename = safe_attachment_filename(row.get("filename", ""), "fichier")

    if group_by_dossier:
        prefix = f"{index.zfill(2)} - " if index else ""
    else:
        prefix = f"{dossier_id} - "
        if index:
            prefix += f"{index.zfill(2)} - "

    return base_dir / f"{prefix}{filename}"


def numbered_path(path: Path, occurrence: int) -> Path:
    if occurrence <= 1:
        return path

    return path.with_name(f"{path.stem} ({occurrence}){path.suffix}")


def plan_downloads(
    rows: list[dict[str, str]],
    output_dir: Path,
    group_by_dossier: bool,
) -> list[tuple[dict[str, str], Path]]:
    occurrences: Counter[Path] = Counter()
    planned: list[tuple[dict[str, str], Path]] = []
    for row in rows:
        base_target = target_path(row, output_dir, group_by_dossier)
        occurrences[base_target] += 1
        planned.append((row, numbered_path(base_target, occurrences[base_target])))
    return planned


def looks_like_html_document(header: bytes) -> bool:
    stripped = header.lstrip().lower()
    return stripped.startswith(b"<!doctype html") or b"<html" in stripped[:512]


def looks_like_structured_error_document(header: bytes) -> bool:
    stripped = header.lstrip().lower()
    if stripped.startswith(b"{\\rtf"):
        return False
    return stripped.startswith((b"{", b"[", b"<?xml"))


def looks_like_binary_document(header: bytes) -> bool:
    if header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return True
    if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return True

    sample = header[:512]
    if not sample:
        return False
    if b"\x00" in sample:
        return True

    printable = sum(byte in b"\t\r\n" or 32 <= byte <= 126 for byte in sample)
    return printable / len(sample) < 0.85


def file_is_usable(path: Path, expected_suffix: str = "") -> bool:
    try:
        if path.stat().st_size == 0:
            return False
        with path.open("rb") as handle:
            header = handle.read(1024)
    except OSError:
        return False

    if looks_like_html_document(header):
        return False

    suffix = (expected_suffix or path.suffix).lower()
    if suffix in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if suffix == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix == ".gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if suffix == ".webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if suffix in {".tif", ".tiff"}:
        return header.startswith((b"II*\x00", b"MM\x00*"))
    if suffix == ".pdf":
        return b"%PDF-" in header
    if suffix in {".avif", ".heic", ".heif"}:
        return header[4:8] == b"ftyp" and any(
            brand in header[8:32]
            for brand in (b"avif", b"avis", b"heic", b"heix", b"heif", b"mif1")
        )
    if suffix in ZIP_CONTAINER_SUFFIXES:
        return header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
    if suffix in OLE_CONTAINER_SUFFIXES:
        return header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if suffix in TEXT_ATTACHMENT_SUFFIXES:
        return not looks_like_structured_error_document(header)
    if looks_like_structured_error_document(header):
        return False
    return looks_like_binary_document(header)


def download_one(
    row: dict[str, str],
    output_dir: Path,
    group_by_dossier: bool,
    timeout: int,
    retries: int,
    planned_target: Path | None = None,
) -> dict[str, str]:
    target = planned_target or target_path(row, output_dir, group_by_dossier)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.part")

    if target.exists() and file_is_usable(target, target.suffix):
        return {**row, "local_path": str(target), "download_status": "skipped_existing"}

    headers = {"User-Agent": "Mozilla/5.0"}
    last_error = ""
    for attempt in range(1, retries + 2):
        try:
            request = urllib.request.Request(row["download_url"], headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", None) or 200
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
                if status >= 400:
                    raise urllib.error.HTTPError(
                        row["download_url"],
                        status,
                        "HTTP error",
                        response.headers,
                        None,
                    )
                if (
                    content_type in ERROR_CONTENT_TYPES
                    or content_type.endswith("+json")
                    or content_type.endswith("+xml")
                ):
                    raise OSError(
                        "la réponse est une page ou erreur structurée au lieu d'une pièce jointe "
                        "(URL expirée ou session invalide)"
                    )
                with partial.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 512)
                        if not chunk:
                            break
                        handle.write(chunk)
            if not file_is_usable(partial, target.suffix):
                raise OSError("fichier téléchargé vide, HTML ou invalide")
            os.replace(partial, target)
            return {**row, "local_path": str(target), "download_status": "downloaded"}
        except Exception as exc:  # noqa: BLE001 - report exact network errors.
            last_error = str(exc)
            try:
                partial.unlink()
            except FileNotFoundError:
                pass
            if attempt <= retries:
                time.sleep(0.8 * attempt)

    return {**row, "local_path": str(target), "download_status": f"error: {last_error}"}


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    preferred = [
        "dossier_id",
        "attachment_index",
        "field_label",
        "filename",
        "local_path",
        "download_status",
        "download_url",
        "dossier_url",
        "status",
    ]
    extras = sorted({key for row in rows for key in row if key not in preferred})
    fields = preferred + extras
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def run_download(
    csv_path: Path,
    output_dir: Path,
    report_path: Path,
    group_by_dossier: bool = False,
    workers: int = 8,
    timeout: int = 45,
    retries: int = 2,
) -> int:
    if workers < 1:
        raise ValueError("--workers doit être supérieur ou égal à 1")
    if timeout < 1:
        raise ValueError("--timeout doit être supérieur ou égal à 1")
    if retries < 0:
        raise ValueError("--retries doit être supérieur ou égal à 0")

    rows = read_rows(csv_path)
    downloadable_rows = [row for row in rows if row.get("download_url")]
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Pièces jointes à télécharger: {len(downloadable_rows)}")
    print(f"Dossier cible: {output_dir}")

    results: list[dict[str, str]] = [
        {
            **row,
            "local_path": "",
            "download_status": (
                "error: aucune URL de téléchargement"
                + (f" ({row.get('status')})" if row.get("status") else "")
            ),
        }
        for row in rows
        if not row.get("download_url")
    ]
    if not downloadable_rows:
        write_report(report_path, results)
        print(
            "Erreur: aucune URL de téléchargement dans le CSV. "
            "Relance d'abord l'extraction dans Chrome.",
            file=sys.stderr,
        )
        print(f"Erreurs: {len(results)}")
        return 1

    planned = plan_downloads(downloadable_rows, output_dir, group_by_dossier)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                download_one,
                row,
                output_dir,
                group_by_dossier,
                timeout,
                retries,
                target,
            )
            for row, target in planned
        ]
        for done, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if done % 25 == 0 or done == len(downloadable_rows):
                downloaded = sum(1 for row in results if row["download_status"] == "downloaded")
                skipped = sum(1 for row in results if row["download_status"] == "skipped_existing")
                errors = sum(1 for row in results if row["download_status"].startswith("error:"))
                print(
                    f"{done}/{len(downloadable_rows)} - téléchargées={downloaded} "
                    f"déjà_présentes={skipped} erreurs={errors}",
                    flush=True,
                )
                write_report(report_path, results)

    results.sort(key=lambda row: (row.get("dossier_id", ""), row.get("attachment_index", ""), row.get("filename", "")))
    write_report(report_path, results)
    errors = [row for row in results if row["download_status"].startswith("error:")]
    print(f"Terminé. Rapport: {report_path}")
    print(f"Erreurs: {len(errors)}")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--group-by-dossier", action="store_true")
    parser.add_argument("--workers", default=8, type=int)
    parser.add_argument("--timeout", default=45, type=int)
    parser.add_argument("--retries", default=2, type=int)
    args = parser.parse_args()

    try:
        return run_download(
            csv_path=args.csv,
            output_dir=args.output_dir,
            report_path=args.report,
            group_by_dossier=args.group_by_dossier,
            workers=args.workers,
            timeout=args.timeout,
            retries=args.retries,
        )
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
