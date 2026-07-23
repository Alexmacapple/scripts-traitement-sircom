from __future__ import annotations

import json
from collections.abc import Container
from datetime import datetime
from typing import Any


def build_business_report(snapshot: dict[str, Any], *, generated_at: str) -> str:
    lot = snapshot["lot"]
    diagnostic = snapshot["diagnostic"]
    mapping = snapshot["mapping"]
    fusion = snapshot["fusion"]
    normalization = snapshot["normalization"]
    sort = snapshot["sort"]
    contract = snapshot["csv_contract"]
    preview = snapshot["csv_preview"]
    inspection = snapshot["inspection"]
    matching = snapshot["matching"]
    integrity = snapshot["integrity"]

    lines: list[str] = [
        "# Rapport métier Sircom 2026",
        "",
        "## Résumé du lot",
        f"- Lot : {_text(lot.get('title')) or _text(lot.get('id'))}",
        f"- Identifiant technique du lot : {_text(lot.get('id'))}",
        f"- Statut courant : {_text(lot.get('status'))}",
        f"- Généré le : {generated_at}",
        f"- Lignes CSV : {integrity['csv_rows_count']}",
        f"- Problèmes ouverts : {integrity['open_problems_count']}",
        "",
        "## Entrées",
        f"- Excel : {_artifact_line(snapshot['artifacts']['excel_source'])}",
        f"- Zip images : {_artifact_line(snapshot['artifacts']['image_zip_source'])}",
        f"- Onglets Excel inspectés : {diagnostic.get('sheet_count', 0)}",
        f"- Images détectées dans le zip : {inspection.get('image_count', 0)}",
        "",
        "## Décisions utilisateur",
        f"- Mapping : {_text(mapping.get('source')) or 'validé'}",
        f"- Tri : {_text(sort.get('decision')) or 'non précisé'}",
        f"- Aperçu CSV validé : {'oui' if preview.get('validated') else 'non'}",
        f"- Résolutions images manuelles : {len(matching.get('manual_resolutions', []))}",
        "",
        "## Diagnostic Excel",
        f"- Importable : {'oui' if diagnostic.get('importable') else 'non'}",
        f"- Alertes : {len(diagnostic.get('warnings', []))}",
        f"- Blocages : {len(diagnostic.get('blockers', []))}",
    ]
    lines.extend(_sheet_lines(diagnostic))
    lines.extend(
        [
            "",
            "## Mapping",
            f"- Colonnes exportées : {_columns_by_status(mapping, 'exporte')}",
            f"- Colonnes supprimées : {_columns_by_status(mapping, 'supprime')}",
            "",
            "| Onglet | Colonne | Nom original | Nom CSV final | Statut |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(_mapping_table_lines(mapping))
    lines.extend(
        [
            "",
            "## Fusion et normalisation",
            f"- Lignes source inspectées : {fusion.get('source_rows_count', 0)}",
            f"- Identifiants source conservés : {integrity['source_ids_count']}",
            f"- Lignes sans id_dossier supprimées : {integrity['removed_rows_without_id_count']}",
            f"- Colonnes entièrement vides supprimées : {integrity['removed_empty_columns_count']}",
            f"- Dates invalides : {normalization.get('invalid_dates_count', 0)}",
            f"- Dates absentes : {normalization.get('missing_dates_count', 0)}",
            "",
            "## CSV",
            "- Fichier final attendu : sircom-indesign-utf16.csv",
            "- Encodage : UTF-16 avec BOM",
            "- Séparateur : virgule",
            f"- Colonnes : {preview.get('headers_count', 0)}",
            f"- Lignes : {preview.get('rows_count', 0)}",
            f"- Contrat InDesign valide : {'oui' if contract.get('valid') else 'non'}",
        ]
    )
    lines.extend(_csv_warning_lines(preview, contract))
    lines.extend(
        [
            "",
            "## Images",
            f"- Flux images : {_image_workflow_line(snapshot)}",
            f"- Images associées : {matching.get('matched_count', 0)}",
            f"- Images traitées : {matching.get('processed_images_count', 0)}",
            f"- Images manquantes : {matching.get('missing_count', 0)}",
            f"- Images ambiguës : {matching.get('ambiguous_count', 0)}",
            f"- Images non référencées : {matching.get('unreferenced_count', 0)}",
            f"- Conversions échouées : {matching.get('conversion_failed_count', 0)}",
            "- Dossier final images : export-jpg-resize/",
        ]
    )
    lines.extend(_unreferenced_image_lines(matching))
    lines.extend(
        [
            "",
            "## Intégrité",
            f"- IDs source : {integrity['source_ids_count']}",
            f"- Lignes CSV : {integrity['csv_rows_count']}",
            f"- Lignes supprimées sans id_dossier : {integrity['removed_rows_without_id_count']}",
            f"- Images présentes : {integrity['present_images_count']}",
            f"- Images manquantes : {integrity['missing_images_count']}",
            f"- Images ignorées : {integrity['ignored_images_count']}",
            "",
            "## Package",
            "- CSV final compatible InDesign : sircom-indesign-utf16.csv",
            _package_images_line(snapshot),
            "- Rapport métier : rapport-metier.md",
            "- Rapport technique : rapport-technique.json",
            "- Mapping utilisé avec provenance complète : mapping-utilise.json",
            "",
            "## Actions attendues",
        ]
    )
    lines.extend(_action_lines(snapshot["problems"]))
    lines.append("")
    return "\n".join(lines)


def build_technical_report(
    snapshot: dict[str, Any],
    *,
    generated_at: str,
    schema_version: int,
    rules_version: str,
    technical_event_payload_keys: Container[str],
) -> dict[str, Any]:
    steps = snapshot["steps"]
    artifacts = snapshot["artifacts"]
    problems = snapshot["problems"]
    events = snapshot["events"]
    return {
        "schema_version": schema_version,
        "rules_version": rules_version,
        "generated_at": generated_at,
        "resume_execution": {
            "lot_id": snapshot["lot"]["id"],
            "status": snapshot["lot"]["status"],
            "open_problem_counts": snapshot["problem_counts"],
        },
        "sources": [
            _technical_artifact_entry(artifact)
            for artifact in artifacts.values()
            if artifact is not None
        ],
        "etapes": [_technical_step_entry(step) for step in steps],
        "compteurs": {
            "excel": {
                "sheets_count": _int(snapshot["diagnostic"].get("sheet_count")),
                "blockers_count": len(snapshot["diagnostic"].get("blockers", [])),
                "warnings_count": len(snapshot["diagnostic"].get("warnings", [])),
            },
            "fusion": {
                "source_rows_count": _int(snapshot["fusion"].get("source_rows_count")),
                "rows_count": _int(snapshot["fusion"].get("rows_count")),
                "rows_removed": _int(
                    snapshot["fusion"].get("removed_rows_without_id_count")
                ),
                "columns_count": _int(snapshot["fusion"].get("columns_count")),
            },
            "normalisation": {
                "rows_count": _int(snapshot["normalization"].get("rows_count")),
                "columns_count": _int(snapshot["normalization"].get("columns_count")),
                "date_issues_count": _int(
                    snapshot["normalization"].get("date_issues_count")
                ),
                "invalid_dates_count": _int(
                    snapshot["normalization"].get("invalid_dates_count")
                ),
                "missing_dates_count": _int(
                    snapshot["normalization"].get("missing_dates_count")
                ),
            },
            "csv": {
                "rows_count": snapshot["integrity"]["csv_rows_count"],
                "columns_count": _int(snapshot["csv_preview"].get("headers_count")),
                "size_bytes": artifacts["csv_final"]["size_bytes"],
            },
            "images": {
                "rows_count": _int(snapshot["matching"].get("rows_count")),
                "missing_count": _int(snapshot["matching"].get("missing_count")),
                "ambiguous_count": _int(snapshot["matching"].get("ambiguous_count")),
                "processed_images_count": _int(
                    snapshot["matching"].get("processed_images_count")
                ),
                "unreferenced_count": _int(
                    snapshot["matching"].get("unreferenced_count")
                ),
                "conversion_failed_count": _int(
                    snapshot["matching"].get("conversion_failed_count")
                ),
                "tolerant_count": _int(snapshot["matching"].get("tolerant_count")),
            },
        },
        "codes_erreur": _technical_problem_codes(problems),
        "traces_anonymisees": [
            _technical_event_entry(
                event,
                technical_event_payload_keys=technical_event_payload_keys,
            )
            for event in events
        ],
    }


def _mapping_table_lines(mapping: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    columns = [
        column for column in mapping.get("columns", []) if isinstance(column, dict)
    ]
    for column in sorted(
        columns,
        key=lambda item: (
            int(item.get("output_position") or 999_999),
            _text(item.get("source_sheet")),
            _text(item.get("source_column_letter")),
            _text(item.get("id")),
        ),
    ):
        sheet = "Système" if column.get("system") else _text(column.get("source_sheet"))
        letter = (
            "Système"
            if column.get("system")
            else _text(column.get("source_column_letter"))
        )
        lines.append(
            "| {sheet} | {letter} | {source} | {csv_name} | {status} |".format(
                sheet=_md_cell(sheet),
                letter=_md_cell(letter),
                source=_md_cell(column.get("source_header")),
                csv_name=_md_cell(column.get("csv_name")),
                status=_md_cell(column.get("status")),
            )
        )
    if not lines:
        lines.append(
            "| Non précisé | Non précisé | Non précisé | Non précisé | Non précisé |"
        )
    return lines


def _sheet_lines(diagnostic: dict[str, Any]) -> list[str]:
    sheets = [
        sheet for sheet in diagnostic.get("sheets", []) if isinstance(sheet, dict)
    ]
    if not sheets:
        return ["- Onglets utiles : non précisé"]
    useful = [sheet for sheet in sheets if not sheet.get("ignored")]
    return [
        f"- Onglets utiles : {len(useful)}",
        "- Détail onglets : "
        + ", ".join(
            f"{_text(sheet.get('name'))} ({sheet.get('rows', 0)} lignes, {sheet.get('columns', 0)} colonnes)"
            for sheet in useful
        ),
    ]


def _csv_warning_lines(preview: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    warnings = [
        warning for warning in preview.get("warnings", []) if isinstance(warning, dict)
    ]
    issues = [issue for issue in contract.get("issues", []) if isinstance(issue, dict)]
    if not warnings and not issues:
        return ["- Alertes CSV : aucune"]
    lines = ["- Alertes CSV :"]
    for warning in warnings:
        lines.append(
            f"  - {_text(warning.get('code'))} : {_text(warning.get('title'))}"
        )
    for issue in issues:
        lines.append(f"  - {_text(issue.get('code'))} : {_text(issue.get('title'))}")
    return lines


def _unreferenced_image_lines(matching: dict[str, Any]) -> list[str]:
    images = [
        image
        for image in matching.get("unreferenced_images", [])
        if isinstance(image, dict)
    ]
    if not images:
        return []
    lines = ["- Images ignorées car non référencées :"]
    for image in images[:50]:
        lines.append(f"  - {_text(image.get('source_name'))}")
    if len(images) > 50:
        lines.append(f"  - ... {len(images) - 50} image(s) supplémentaire(s)")
    return lines


def _action_lines(problems: list[dict[str, Any]]) -> list[str]:
    if not problems:
        return ["- Aucune action bloquante détectée dans le lot courant."]
    lines: list[str] = []
    for problem in problems[:50]:
        lines.append(
            "- {severity} - {code} : {action}".format(
                severity=_text(problem.get("severity")),
                code=_text(problem.get("code")),
                action=_text(problem.get("action")),
            )
        )
    if len(problems) > 50:
        lines.append(f"- ... {len(problems) - 50} action(s) supplémentaire(s)")
    return lines


def _columns_by_status(mapping: dict[str, Any], status: str) -> int:
    return sum(
        1
        for column in mapping.get("columns", [])
        if isinstance(column, dict) and column.get("status") == status
    )


def _artifact_line(artifact: dict[str, Any] | None) -> str:
    if artifact is None:
        return "non fourni"
    metadata = _json_dict(artifact.get("metadata_json"))
    parts = [
        f"artefact {artifact['id']}",
        f"{artifact['size_bytes']} octets",
    ]
    extension = metadata.get("extension")
    if extension:
        parts.append(f"extension {extension}")
    return ", ".join(parts)


def _image_workflow_line(snapshot: dict[str, Any]) -> str:
    if snapshot["artifacts"]["image_zip_source"] is None:
        return "aucun zip images fourni"
    return "zip images traité"


def _package_images_line(snapshot: dict[str, Any]) -> str:
    if snapshot["artifacts"]["image_zip_source"] is None:
        return "- Images renommées et optimisées : aucune image fournie"
    return "- Images renommées et optimisées : export-jpg-resize/"


def _technical_artifact_entry(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": artifact["id"],
        "step_key": artifact["step_key"],
        "run_id": artifact["run_id"],
        "kind": artifact["kind"],
        "role": artifact["role"],
        "status": artifact["status"],
        "size_bytes": artifact["size_bytes"],
        "sha256": artifact["sha256"],
        "mime_type": artifact["mime_type"],
    }


def _technical_step_entry(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_key": step["step_key"],
        "status": step["status"],
        "run_id": step["current_run_id"],
        "input_fingerprint": step["input_fingerprint"],
        "output_fingerprint": step["output_fingerprint"],
        "progress_current": step["progress_current"],
        "progress_total": step["progress_total"],
        "duration_ms": _duration_ms(step.get("started_at"), step.get("finished_at")),
    }


def _technical_problem_codes(problems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for problem in problems:
        key = (_text(problem.get("severity")), _text(problem.get("code")))
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "severity": severity,
            "code": code,
            "count": count,
        }
        for (severity, code), count in sorted(counts.items())
    ]


def _technical_event_entry(
    event: dict[str, Any],
    *,
    technical_event_payload_keys: Container[str],
) -> dict[str, Any]:
    return {
        "created_at": event["created_at"],
        "event_type": event["event_type"],
        "step_key": event["step_key"],
        "run_id": event["run_id"],
        "level": event["level"],
        "payload": _scrub_event_payload(
            _json_dict(event.get("payload_json")),
            technical_event_payload_keys=technical_event_payload_keys,
        ),
    }


def _scrub_event_payload(
    payload: dict[str, Any],
    *,
    technical_event_payload_keys: Container[str],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key in technical_event_payload_keys
        and isinstance(value, str | int | float | bool | type(None))
        and not (isinstance(value, str) and ("/" in value or "\\" in value))
    }


def _duration_ms(started_at: Any, finished_at: Any) -> int | None:
    if not started_at or not finished_at:
        return None
    try:
        start = datetime.fromisoformat(str(started_at))
        finish = datetime.fromisoformat(str(finished_at))
    except ValueError:
        return None
    return max(0, int((finish - start).total_seconds() * 1000))


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _md_cell(value: Any) -> str:
    text = _text(value).replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|") or " "


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
