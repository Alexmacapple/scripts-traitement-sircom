from __future__ import annotations

import re
import unicodedata
from typing import Any

from sircom2026.excel_diagnostic import ascii_key, clean_indesign_header


MAPPING_RULES_VERSION = "mapping-v1"
MAPPING_SCHEMA_VERSION = 1
MAPPING_STATUS_VALUES = {"exporte", "supprime"}
MAPPING_LOGICAL_ROLES = {
    "id_dossier",
    "date",
    "region",
    "departement",
    "nom_image_source",
    "siret",
    "telephone",
    "code_postal",
    "code_administratif",
    "texte",
}
SYSTEM_COLUMN_IDS = ("system:imageid", "system:@pathimg")


def useful_sheets(diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    sheets = diagnostic.get("sheets")
    if not isinstance(sheets, list):
        return []
    return [
        sheet
        for sheet in sheets
        if isinstance(sheet, dict)
        and not bool(sheet.get("ignored"))
        and bool(sheet.get("importable"))
        and sheet.get("header_row") is not None
    ]


def structural_payload(sheets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "rules_version": MAPPING_RULES_VERSION,
        "sheets": [
            {
                "name": sheet["name"],
                "headers": [
                    {
                        "letter": header["column"],
                        "name": header["header"],
                    }
                    for header in sheet.get("source_headers", [])
                ],
                "id_columns": [
                    candidate["column"]
                    for candidate in sheet.get("id_candidates", [])
                    if isinstance(candidate, dict)
                ],
            }
            for sheet in sheets
        ],
    }


def logical_roles_by_letter(sheet: dict[str, Any]) -> dict[str, str]:
    roles: dict[str, str] = {}
    candidate_groups = (
        ("id_candidates", "id_dossier"),
        ("region_candidates", "region"),
        ("department_candidates", "departement"),
        ("date_candidates", "date"),
        ("image_candidates", "nom_image_source"),
    )
    for key, role in candidate_groups:
        for candidate in sheet.get(key, []):
            if isinstance(candidate, dict) and candidate.get("column"):
                roles[str(candidate["column"])] = role
    return roles


def role_from_header(header: str) -> str:
    key = ascii_key(header)
    if "siret" in key or "siren" in key:
        return "siret"
    if "telephone" in key or "tel" in key:
        return "telephone"
    if "code postal" in key or "codepostal" in key:
        return "code_postal"
    if "departement" in key:
        return "departement"
    if "code insee" in key or "rna" in key or "tva" in key:
        return "code_administratif"
    return "texte"


def source_column_id(sheet_name: str, letter: str) -> str:
    return f"{sheet_name}!{letter}"


def default_csv_name(letter: str, header: str) -> str:
    prefix = f"{letter.lower()}_"
    body = clean_indesign_header(header) or "colonne"
    return f"{prefix}{body}"[:10]


def clean_submitted_csv_name(
    value: str, *, source_column_letter: str | None = None
) -> str:
    cleaned = value.strip()
    if source_column_letter is None and cleaned in {
        "id_dossier",
        "imageid",
        "@pathimg",
    }:
        return cleaned
    normalized = unicodedata.normalize("NFKD", cleaned)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    csv_name = re.sub(r"[^a-z0-9_]", "", ascii_value)
    if not csv_name:
        return ""
    if source_column_letter is None:
        return csv_name[:10]

    prefix = f"{source_column_letter.lower()}_"
    if csv_name.startswith(prefix):
        return csv_name[:10]
    return f"{prefix}{csv_name}"[:10]


def system_columns() -> list[dict[str, Any]]:
    return [
        {
            "id": "system:imageid",
            "system": True,
            "source_sheet": None,
            "source_column_index": None,
            "source_column_letter": None,
            "source_header": "Image InDesign générée",
            "logical_role": "nom_image_source",
            "status": "exporte",
            "csv_name": "imageid",
            "default_csv_name": "imageid",
            "suppression_reason": None,
            "output_position": None,
            "locked": True,
        },
        {
            "id": "system:@pathimg",
            "system": True,
            "source_sheet": None,
            "source_column_index": None,
            "source_column_letter": None,
            "source_header": "Chemin image InDesign",
            "logical_role": "nom_image_source",
            "status": "exporte",
            "csv_name": "@pathimg",
            "default_csv_name": "@pathimg",
            "suppression_reason": None,
            "output_position": None,
            "locked": True,
        },
    ]


def assign_output_positions(columns: list[dict[str, Any]]) -> None:
    position = 1
    for column in columns:
        if column["status"] == "exporte":
            column["output_position"] = position
            position += 1
        else:
            column["output_position"] = None
