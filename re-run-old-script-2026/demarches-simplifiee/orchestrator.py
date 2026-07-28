#!/usr/bin/env python3
"""Petit orchestrateur pour les exports annuels Démarches simplifiées."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_IDS = ROOT / "data" / "dossier-id.txt"
SCRIPTS = ROOT / "scripts"
RESULTS = ROOT / "results"
DOWNLOADS = Path.home() / "Downloads"
DEFAULT_PHOTOS_DIR = DOWNLOADS / "photos-produits-demarches-2027"
DEFAULT_PHOTOS_REPORT = DOWNLOADS / "rapport-photos-produits-2027.csv"
DEFAULT_PHOTOS_FILTERED_CSV = RESULTS / "photos-produits-dossiers-filtre.csv"
DEFAULT_COMPLETE_DIR = DOWNLOADS / "dossiers-complets-pieces-jointes-2027"
DEFAULT_COMPLETE_REPORT = DOWNLOADS / "rapport-pj-dossiers-complets-2027.csv"
PHOTOS_PREPARED_MARKER = RESULTS / ".photos-prepared"
COMPLETE_PREPARED_MARKER = RESULTS / ".complete-prepared"
IMAGE_ATTACHMENT_RE = re.compile(
    r"(\.(?:avif|gif|heic|heif|jpe?g|png|tiff?|webp)\b|\b(?:AVIF|GIF|HEIC|HEIF|JPE?G|PNG|TIFF?|WEBP)\b)",
    re.IGNORECASE,
)


def extract_id(line: str) -> str | None:
    dossier_url = re.search(r"/dossiers/(\d+)", line)
    if dossier_url:
        return dossier_url.group(1)
    bare_id = re.search(r"\b\d{6,}\b", line)
    return bare_id.group(0) if bare_id else None


def load_ids(path: Path) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    ignored: list[str] = []
    seen: set[str] = set()

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        dossier_id = extract_id(line)
        if not dossier_id:
            ignored.append(line)
            continue
        if dossier_id not in seen:
            ids.append(dossier_id)
            seen.add(dossier_id)

    return ids, ignored


def js_source_block(ids: list[str]) -> str:
    return "const SOURCE = `\n" + "\n".join(ids) + "\n`;"


def inject_script(template_path: Path, output_path: Path, ids: list[str], procedure_id: str) -> None:
    if not procedure_id.isdigit():
        raise ValueError(f"Identifiant de procédure invalide: {procedure_id}")

    text = template_path.read_text(encoding="utf-8")
    text, source_replacements = re.subn(
        r"const SOURCE = `[\s\S]*?`;",
        js_source_block(ids),
        text,
        count=1,
    )
    text, procedure_replacements = re.subn(
        r'const PROCEDURE_ID = "[^"]+";',
        f'const PROCEDURE_ID = "{procedure_id}";',
        text,
        count=1,
    )
    if source_replacements != 1 or procedure_replacements != 1:
        raise ValueError(f"Modèle de script Chrome invalide: {template_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def cmd_check_ids(args: argparse.Namespace) -> int:
    ids_path = args.ids
    ids, ignored = load_ids(ids_path)
    print(f"Fichier: {ids_path}")
    print(f"Dossiers trouvés: {len(ids)}")
    print(f"Lignes ignorées: {len(ignored)}")
    if ignored:
        print("Exemples ignorés:")
        for line in ignored[:10]:
            print(f"- {line}")
    if ids:
        print(f"Premier ID: {ids[0]}")
        print(f"Dernier ID: {ids[-1]}")
    return 0 if ids else 1


def cmd_prepare(args: argparse.Namespace, kind: str) -> int:
    ids, ignored = load_ids(args.ids)
    if not ids:
        print(f"Aucun dossier trouvé dans {args.ids}", file=sys.stderr)
        return 1

    if kind == "photos":
        template = SCRIPTS / "extract_product_photos.js"
        output = RESULTS / "run_extract_product_photos.js"
        marker = PHOTOS_PREPARED_MARKER
    else:
        template = SCRIPTS / "extract_complete_dossiers.js"
        output = RESULTS / "run_extract_complete_dossiers.js"
        marker = COMPLETE_PREPARED_MARKER

    inject_script(template, output, ids, args.procedure_id)
    marker.touch()
    print(f"Script généré: {output}")
    print(f"Dossiers inclus: {len(ids)}")
    if ignored:
        print(f"Lignes ignorées: {len(ignored)}")
    print("Prochaine étape:")
    print(f"  open -a TextEdit {output.relative_to(ROOT)}")
    print("Puis copier le fichier entier dans la console Chrome.")
    return 0


def detect_dialect(csv_path: Path) -> csv.Dialect:
    sample = csv_path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,")
    except csv.Error:
        return csv.get_dialect("excel")


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    dialect = detect_dialect(csv_path)
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames or "download_url" not in reader.fieldnames:
            raise ValueError(f"Colonne obligatoire absente dans {csv_path}: download_url")
        return list(reader)


def write_csv_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    preferred = [
        "dossier_id",
        "attachment_index",
        "field_label",
        "filename",
        "download_url",
        "dossier_url",
        "status",
    ]
    extras = sorted({key for row in rows for key in row if key not in preferred})
    fields = preferred + extras
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def is_image_row(row: dict[str, str]) -> bool:
    haystack = " ".join(
        row.get(key, "")
        for key in ("filename", "field_label", "link_text", "download_url")
    )
    return bool(row.get("download_url") and IMAGE_ATTACHMENT_RE.search(haystack))


def cleaned_attachment_filename(row: dict[str, str]) -> str:
    filename = row.get("filename") or row.get("link_text") or ""
    filename = re.sub(r"^T[eé]l[eé]charger le fichier\s+", "", filename, flags=re.IGNORECASE)
    filename = re.sub(
        r"\s+(?:AVIF|GIF|HEIC|HEIF|JPE?G|PNG|TIFF?|WEBP)\s+[–-].*$",
        "",
        filename,
        flags=re.IGNORECASE,
    )
    return filename.strip() or row.get("filename", "").strip()


def image_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    counters: Counter[str] = Counter()
    selected: list[dict[str, str]] = []
    for row in rows:
        if not is_image_row(row):
            continue
        dossier_id = row.get("dossier_id", "")
        counters[dossier_id] += 1
        selected.append(
            {
                **row,
                "attachment_index": str(counters[dossier_id]),
                "filename": cleaned_attachment_filename(row),
                "status": "ok",
            }
        )
    return selected


def latest_download_csv(
    pattern: str,
    excluded_stem_prefixes: tuple[str, ...] = (),
    prepared_marker: Path | None = None,
) -> Path | None:
    prepared_at = (
        prepared_marker.stat().st_mtime
        if prepared_marker is not None and prepared_marker.exists()
        else None
    )
    candidates = [
        path
        for path in DOWNLOADS.glob(pattern)
        if path.is_file()
        and not any(path.stem.startswith(prefix) for prefix in excluded_stem_prefixes)
        and (prepared_at is None or path.stat().st_mtime >= prepared_at)
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda path: (path.stat().st_mtime_ns, chrome_download_index(path), path.name),
    )


def chrome_download_index(path: Path) -> int:
    match = re.search(r" \((\d+)\)$", path.stem)
    return int(match.group(1)) if match else 0


def default_photos_csv() -> Path | None:
    return latest_download_csv(
        "photos-produits-dossiers*.csv",
        excluded_stem_prefixes=("photos-produits-dossiers-anomalies",),
        prepared_marker=PHOTOS_PREPARED_MARKER,
    )


def default_complete_csv() -> Path | None:
    return latest_download_csv(
        "dossiers-complets-pieces-jointes*.csv",
        prepared_marker=COMPLETE_PREPARED_MARKER,
    )


def default_photo_anomalies_csv() -> Path | None:
    return latest_download_csv(
        "photos-produits-dossiers-anomalies*.csv",
        prepared_marker=PHOTOS_PREPARED_MARKER,
    )


def cmd_check_csv(args: argparse.Namespace) -> int:
    rows = read_csv_rows(args.csv)
    statuses = Counter(row.get("status") or "(vide)" for row in rows)
    urls = sum(1 for row in rows if row.get("download_url"))
    dossier_ids = {row.get("dossier_id") for row in rows if row.get("dossier_id")}
    images = sum(1 for row in rows if is_image_row(row))

    print(f"CSV: {args.csv}")
    print(f"Lignes: {len(rows)}")
    print(f"Dossiers distincts: {len(dossier_ids)}")
    print(f"Lignes avec URL: {urls}")
    print(f"Images détectées: {images}")
    print("Statuts:")
    for status, count in statuses.most_common():
        print(f"- {status}: {count}")

    anomalies = [row for row in rows if row.get("status") not in ("", "ok")]
    if anomalies:
        print("Premières anomalies:")
        for row in anomalies[:10]:
            print(f"- {row.get('dossier_id', '')} | {row.get('status', '')} | {row.get('filename', '')}")

    if not rows:
        print("Erreur: le CSV ne contient aucune ligne.", file=sys.stderr)
        return 1
    if not urls:
        if getattr(args, "kind", None) == "photos":
            next_step = "Utilise le CSV d'anomalies pour basculer vers les pièces jointes."
        elif getattr(args, "kind", None) == "complete":
            next_step = "Relance l'extraction des pièces jointes dans Chrome."
        else:
            next_step = "Vérifie que tu utilises le bon CSV généré par Chrome."
        print(
            f"Erreur: aucune URL de téléchargement. {next_step}",
            file=sys.stderr,
        )
        return 1
    if getattr(args, "require_images", False) and not images:
        print("Erreur: aucune image téléchargeable détectée dans ce CSV.", file=sys.stderr)
        return 1

    if anomalies:
        print(f"Attention: {len(anomalies)} ligne(s) en anomalie.")
    print("Validation: OK")
    return 0


def cmd_check_latest(args: argparse.Namespace, kind: str) -> int:
    csv_path = args.csv
    if csv_path is None:
        csv_path = default_photos_csv() if kind == "photos" else default_complete_csv()
    if csv_path is None:
        label = "photo" if kind == "photos" else "des pièces jointes"
        print(
            f"Aucun CSV {label} récent trouvé dans ~/Downloads. "
            "Lance dans Chrome le script que tu viens de préparer.",
            file=sys.stderr,
        )
        return 1

    return cmd_check_csv(
        argparse.Namespace(
            csv=csv_path,
            require_images=kind == "photos",
            kind=kind,
        )
    )


def cmd_download(args: argparse.Namespace) -> int:
    script = SCRIPTS / "download_attachments_from_csv.py"
    command = [
        sys.executable,
        str(script),
        "--csv",
        str(args.csv),
        "--output-dir",
        str(args.output_dir),
        "--report",
        str(args.report),
        "--workers",
        str(args.workers),
        "--timeout",
        str(args.timeout),
        "--retries",
        str(args.retries),
    ]
    if args.group_by_dossier:
        command.append("--group-by-dossier")
    return subprocess.run(command, check=False).returncode


def cmd_download_photos(args: argparse.Namespace) -> int:
    csv_path = args.csv or default_photos_csv()
    if not csv_path:
        print(
            "Aucun CSV photo récent trouvé dans ~/Downloads. "
            "Lance dans Chrome le script généré par prepare-photos.",
            file=sys.stderr,
        )
        return 1

    rows = read_csv_rows(csv_path)
    photos = image_rows(rows)
    dossier_ids = {row.get("dossier_id") for row in photos if row.get("dossier_id")}
    print(f"CSV source: {csv_path}", flush=True)
    print(f"Images détectées: {len(photos)}", flush=True)
    print(f"Dossiers couverts: {len(dossier_ids)}", flush=True)
    if not photos:
        print("Aucune image téléchargeable détectée dans ce CSV.", file=sys.stderr)
        return 1

    write_csv_rows(args.filtered_csv, photos)
    print(f"CSV filtré: {args.filtered_csv}", flush=True)

    download_args = argparse.Namespace(
        csv=args.filtered_csv,
        output_dir=args.output_dir,
        report=args.report,
        group_by_dossier=args.group_by_dossier,
        workers=args.workers,
        timeout=args.timeout,
        retries=args.retries,
    )
    return cmd_download(download_args)


def cmd_download_complete(args: argparse.Namespace) -> int:
    csv_path = args.csv or default_complete_csv()
    if not csv_path:
        print(
            "Aucun CSV récent de pièces jointes trouvé dans ~/Downloads. "
            "Lance dans Chrome le script généré par prepare-complete.",
            file=sys.stderr,
        )
        return 1

    print(f"CSV source: {csv_path}", flush=True)
    download_args = argparse.Namespace(
        csv=csv_path,
        output_dir=args.output_dir,
        report=args.report,
        group_by_dossier=True,
        workers=args.workers,
        timeout=args.timeout,
        retries=args.retries,
    )
    return cmd_download(download_args)


def cmd_prepare_complete_errors(args: argparse.Namespace) -> int:
    ids_path = args.ids or default_photo_anomalies_csv()
    if ids_path is None:
        print(
            "Aucun CSV récent d'anomalies photo trouvé dans ~/Downloads. "
            "Lance dans Chrome le script généré par prepare-photos.",
            file=sys.stderr,
        )
        return 1

    return cmd_prepare(
        argparse.Namespace(ids=ids_path, procedure_id=args.procedure_id),
        "complete",
    )


def cmd_open(args: argparse.Namespace) -> int:
    target = args.path or ROOT
    subprocess.run(["open", "-R", str(target)], check=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Orchestrateur Démarches simplifiées 2027")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_ids = subparsers.add_parser("check-ids", help="Vérifier data/dossier-id.txt")
    check_ids.add_argument("--ids", type=Path, default=DATA_IDS)
    check_ids.set_defaults(func=cmd_check_ids)

    photos = subparsers.add_parser("prepare-photos", help="Générer le JS des photos produit")
    photos.add_argument("--ids", type=Path, default=DATA_IDS)
    photos.add_argument("--procedure-id", default="140205")
    photos.set_defaults(func=lambda args: cmd_prepare(args, "photos"))

    complete = subparsers.add_parser("prepare-complete", help="Générer le JS des dossiers complets")
    complete.add_argument("--ids", type=Path, default=DATA_IDS)
    complete.add_argument("--procedure-id", default="140205")
    complete.set_defaults(func=lambda args: cmd_prepare(args, "complete"))

    complete_errors = subparsers.add_parser(
        "prepare-complete-errors",
        help="Générer le JS des pièces jointes pour les dossiers sans photo",
    )
    complete_errors.add_argument("--ids", type=Path)
    complete_errors.add_argument("--procedure-id", default="140205")
    complete_errors.set_defaults(func=cmd_prepare_complete_errors)

    check_csv = subparsers.add_parser("check-csv", help="Résumer un CSV généré")
    check_csv.add_argument("--csv", required=True, type=Path)
    check_csv.set_defaults(func=cmd_check_csv)

    check_photos = subparsers.add_parser(
        "check-photos",
        help="Contrôler automatiquement le dernier CSV des photos",
    )
    check_photos.add_argument("--csv", type=Path)
    check_photos.set_defaults(func=lambda args: cmd_check_latest(args, "photos"))

    check_complete = subparsers.add_parser(
        "check-complete",
        help="Contrôler automatiquement le dernier CSV des pièces jointes",
    )
    check_complete.add_argument("--csv", type=Path)
    check_complete.set_defaults(func=lambda args: cmd_check_latest(args, "complete"))

    download = subparsers.add_parser("download", help="Télécharger les URLs d'un CSV")
    download.add_argument("--csv", required=True, type=Path)
    download.add_argument("--output-dir", required=True, type=Path)
    download.add_argument("--report", required=True, type=Path)
    download.add_argument("--group-by-dossier", action="store_true")
    download.add_argument("--workers", default=8, type=int)
    download.add_argument("--timeout", default=45, type=int)
    download.add_argument("--retries", default=2, type=int)
    download.set_defaults(func=cmd_download)

    download_photos = subparsers.add_parser(
        "download-photos",
        help="Filtrer les images d'un CSV DS puis les télécharger avec les chemins par défaut",
    )
    download_photos.add_argument("--csv", type=Path)
    download_photos.add_argument("--output-dir", type=Path, default=DEFAULT_PHOTOS_DIR)
    download_photos.add_argument("--report", type=Path, default=DEFAULT_PHOTOS_REPORT)
    download_photos.add_argument("--filtered-csv", type=Path, default=DEFAULT_PHOTOS_FILTERED_CSV)
    download_photos.add_argument("--group-by-dossier", action="store_true")
    download_photos.add_argument("--workers", default=8, type=int)
    download_photos.add_argument("--timeout", default=45, type=int)
    download_photos.add_argument("--retries", default=2, type=int)
    download_photos.set_defaults(func=cmd_download_photos)

    download_complete = subparsers.add_parser(
        "download-complete",
        help="Télécharger le dernier CSV de pièces jointes et les classer par dossier",
    )
    download_complete.add_argument("--csv", type=Path)
    download_complete.add_argument("--output-dir", type=Path, default=DEFAULT_COMPLETE_DIR)
    download_complete.add_argument("--report", type=Path, default=DEFAULT_COMPLETE_REPORT)
    download_complete.add_argument("--workers", default=8, type=int)
    download_complete.add_argument("--timeout", default=45, type=int)
    download_complete.add_argument("--retries", default=2, type=int)
    download_complete.set_defaults(func=cmd_download_complete)

    reveal = subparsers.add_parser("open", help="Afficher le kit ou un fichier dans Finder")
    reveal.add_argument("path", nargs="?", type=Path)
    reveal.set_defaults(func=cmd_open)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
