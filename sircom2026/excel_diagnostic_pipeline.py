from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError
from sircom2026.config import Settings
from sircom2026.database import Repositories
from sircom2026.excel_diagnostic import (
    EXCEL_DIMENSIONS_EXCEEDED_CODE,
    SheetDiagnostic,
    WorkbookDiagnostic,
    diagnose_workbook,
    excel_dimension_limits_from_settings,
)
from sircom2026.invalidation import fingerprint_payload
from sircom2026.state import record_problem
from sircom2026.worker import JobResult, WorkerJobContext, WorkerLeaseLost


UPLOAD_STEP_KEY = "upload_excel"
DIAGNOSTIC_STEP_KEY = "diagnostic_excel"
DIAGNOSTIC_ARTIFACT_KIND = "json"
DIAGNOSTIC_ARTIFACT_ROLE = "result"
DIAGNOSTIC_RULES_VERSION = "excel-diagnostic-v1"
DIAGNOSTIC_MIME_TYPE = "application/json"


class ExcelDiagnosticNotReady(RuntimeError):
    """Raised when no current diagnostic artifact can be exposed yet."""


@dataclass(frozen=True)
class PersistedExcelDiagnostic:
    diagnostic: dict[str, Any]
    artifact: dict[str, Any]


def run_excel_diagnostic_job(
    context: WorkerJobContext, *, settings: Settings
) -> JobResult:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    context.set_progress(1, 3)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        source_artifact = _current_excel_source_artifact(repositories, context.lot_id)
        if source_artifact is None:
            _record_missing_source_problem(repositories, context)
            return JobResult(final_step_status="bloque")
        try:
            readable = store.open_for_read(
                repositories,
                lot_id=context.lot_id,
                artifact_id=source_artifact["id"],
            )
        except (ArtifactUnavailableError, KeyError, ValueError):
            _record_missing_source_problem(repositories, context)
            return JobResult(final_step_status="bloque")

    context.set_progress(2, 3)
    diagnostic = diagnose_workbook(
        readable.path,
        limits=excel_dimension_limits_from_settings(settings),
    )
    public_diagnostic = serialize_workbook_diagnostic(diagnostic)
    diagnostic_content = json.dumps(
        public_diagnostic,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        repositories.problems.mark_open_obsolete_for_steps(
            lot_id=context.lot_id,
            step_keys=(DIAGNOSTIC_STEP_KEY,),
        )
        repositories.artifacts.mark_obsolete_for_steps(
            lot_id=context.lot_id,
            step_keys=(DIAGNOSTIC_STEP_KEY,),
        )
        artifact = store.put_temp_then_commit(
            repositories,
            lot_id=context.lot_id,
            step_key=DIAGNOSTIC_STEP_KEY,
            run_id=context.run_id,
            kind=DIAGNOSTIC_ARTIFACT_KIND,
            role=DIAGNOSTIC_ARTIFACT_ROLE,
            filename="diagnostic-excel.json",
            content=diagnostic_content,
            metadata={
                "blockers_count": len(diagnostic.blockers),
                "importable": diagnostic.importable,
                "rules_version": DIAGNOSTIC_RULES_VERSION,
                "source_artifact_id": source_artifact["id"],
                "warnings_count": len(diagnostic.warnings),
            },
            mime_type=DIAGNOSTIC_MIME_TYPE,
            lease_version=context.leased_job.lease_version,
        )
        problem_counts = persist_diagnostic_problems(
            repositories,
            lot_id=context.lot_id,
            run_id=context.run_id,
            diagnostic=diagnostic,
        )
        output_fingerprint = fingerprint_payload(
            {
                "artifact_sha256": artifact["sha256"],
                "diagnostic_artifact_id": artifact["id"],
                "importable": diagnostic.importable,
                "kind": "excel_diagnostic",
                "schema_version": 1,
                "source_artifact_id": source_artifact["id"],
            }
        )
        repositories.events.create(
            lot_id=context.lot_id,
            step_key=DIAGNOSTIC_STEP_KEY,
            run_id=context.run_id,
            event_type="excel.diagnostic_completed",
            payload={
                "artifact_id": artifact["id"],
                "status": "bloque" if problem_counts["bloquant"] else "termine",
                "step_key": DIAGNOSTIC_STEP_KEY,
            },
        )

    context.set_progress(3, 3)
    if problem_counts["bloquant"]:
        return JobResult(
            final_step_status="bloque",
            output_fingerprint=output_fingerprint,
        )
    return JobResult(
        with_warnings=problem_counts["alerte"] > 0,
        output_fingerprint=output_fingerprint,
    )


def get_persisted_excel_diagnostic(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PersistedExcelDiagnostic:
    repositories.lots.get_required(lot_id)
    artifact = _current_diagnostic_artifact(repositories, lot_id)
    if artifact is None:
        raise ExcelDiagnosticNotReady("Excel diagnostic is not ready.")
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    try:
        readable = store.open_for_read(
            repositories,
            lot_id=lot_id,
            artifact_id=artifact["id"],
        )
    except (ArtifactUnavailableError, KeyError, ValueError) as exc:
        raise ExcelDiagnosticNotReady(
            "Excel diagnostic artifact is unavailable."
        ) from exc
    try:
        diagnostic = json.loads(readable.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExcelDiagnosticNotReady(
            "Excel diagnostic artifact is unavailable."
        ) from exc
    if not isinstance(diagnostic, dict):
        raise ExcelDiagnosticNotReady("Excel diagnostic artifact is malformed.")
    return PersistedExcelDiagnostic(diagnostic=diagnostic, artifact=artifact)


def serialize_workbook_diagnostic(diagnostic: WorkbookDiagnostic) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rules_version": DIAGNOSTIC_RULES_VERSION,
        "sheet_count": diagnostic.sheet_count,
        "importable": diagnostic.importable,
        "blockers": list(diagnostic.blockers),
        "warnings": list(diagnostic.warnings),
        "cleaned_header_collisions": dict(diagnostic.cleaned_header_collisions),
        "sheets": [serialize_sheet_diagnostic(sheet) for sheet in diagnostic.sheets],
    }


def serialize_sheet_diagnostic(sheet: SheetDiagnostic) -> dict[str, Any]:
    return {
        "name": sheet.name,
        "state": sheet.state,
        "rows": sheet.rows,
        "columns": sheet.columns,
        "ignored": sheet.ignored,
        "ignore_reason": sheet.ignore_reason,
        "importable": sheet.importable,
        "blockers": list(sheet.blockers),
        "warnings": list(sheet.warnings),
        "header_row": sheet.header_row,
        "non_empty_headers": sheet.non_empty_headers,
        "empty_header_columns_with_data": list(sheet.empty_header_columns_with_data),
        "duplicate_headers": list(sheet.duplicate_headers),
        "cleaned_header_collisions": list(sheet.cleaned_header_collisions),
        "id_candidates": [asdict(candidate) for candidate in sheet.id_candidates],
        "region_candidates": [
            asdict(candidate) for candidate in sheet.region_candidates
        ],
        "department_candidates": [
            asdict(candidate) for candidate in sheet.department_candidates
        ],
        "date_candidates": [asdict(candidate) for candidate in sheet.date_candidates],
        "image_candidates": [asdict(candidate) for candidate in sheet.image_candidates],
        "sensitive_candidates": [
            asdict(candidate) for candidate in sheet.sensitive_candidates
        ],
        "source_headers": [asdict(candidate) for candidate in sheet.source_headers],
        "hidden_columns": list(sheet.hidden_columns),
        "hidden_rows": list(sheet.hidden_rows),
        "merged_ranges": list(sheet.merged_ranges),
        "formula_cells_sample": list(sheet.formula_cells_sample),
        "headers_preview": list(sheet.headers_preview),
        "dimension_limits_exceeded": list(sheet.dimension_limits_exceeded),
    }


def persist_diagnostic_problems(
    repositories: Repositories,
    *,
    lot_id: str,
    run_id: str,
    diagnostic: WorkbookDiagnostic,
) -> dict[str, int]:
    counts = {"bloquant": 0, "alerte": 0, "information": 0}
    for sheet in diagnostic.sheets:
        for problem in sheet_problems(sheet):
            record_problem(
                repositories,
                lot_id=lot_id,
                step_key=DIAGNOSTIC_STEP_KEY,
                run_id=run_id,
                severity=problem["severity"],
                code=problem["code"],
                title=problem["title"],
                cause=problem["cause"],
                action=problem["action"],
                location=problem.get("location"),
                technical=problem.get("technical"),
            )
            counts[problem["severity"]] += 1
    for cleaned_name, sources in diagnostic.cleaned_header_collisions.items():
        record_problem(
            repositories,
            lot_id=lot_id,
            step_key=DIAGNOSTIC_STEP_KEY,
            run_id=run_id,
            severity="bloquant",
            code="SIRCOM_EXCEL_CSV_HEADER_COLLISION",
            title="Collision de noms CSV",
            cause=(
                "Plusieurs colonnes produisent le même nom CSV après nettoyage "
                "InDesign."
            ),
            action="Renommer une des colonnes sources, puis relancer le diagnostic.",
            location=_location_from_source(sources[0]) if sources else None,
            technical={
                "columns_count": len(sources),
                "checks_count": 1,
                "warning_code": cleaned_name,
            },
        )
        counts["bloquant"] += 1
    return counts


def sheet_problems(sheet: SheetDiagnostic) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    location = {"onglet": sheet.name}
    for details in sheet.dimension_limits_exceeded:
        problems.append(
            {
                "severity": "bloquant",
                "code": EXCEL_DIMENSIONS_EXCEEDED_CODE,
                "title": "Classeur Excel hors limites",
                "cause": (
                    "Un onglet dépasse les limites de lignes, colonnes ou cellules "
                    "parcourues."
                ),
                "action": (
                    "Réduire l'onglet ou supprimer les lignes et colonnes inutiles, "
                    "puis redéposer l'Excel."
                ),
                "location": location,
                "technical": dict(details),
            }
        )
    if problems:
        return problems
    if sheet.ignored and sheet.ignore_reason == "empty sheet":
        problems.append(
            {
                "severity": "information",
                "code": "SIRCOM_EXCEL_EMPTY_SHEET_IGNORED",
                "title": "Onglet vide ignoré",
                "cause": "Un onglet vide a été ignoré par le diagnostic.",
                "action": "Aucune action requise si cet onglet est attendu vide.",
                "location": location,
                "technical": {"rows_count": sheet.rows, "columns_count": sheet.columns},
            }
        )
        return problems
    if sheet.state != "visible":
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_HIDDEN_SHEET",
                "title": "Onglet masqué",
                "cause": "Un onglet non vide est masqué.",
                "action": "Afficher ou supprimer l'onglet, puis relancer le diagnostic.",
                "location": location,
                "technical": {"status": sheet.state},
            }
        )
    if sheet.hidden_columns:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_HIDDEN_COLUMNS",
                "title": "Colonnes masquées détectées",
                "cause": "Le classeur contient une colonne masquée dans un onglet utile.",
                "action": "Afficher ou supprimer la colonne, puis relancer le diagnostic.",
                "location": _column_location(sheet.name, sheet.hidden_columns),
                "technical": {"hidden_columns": len(sheet.hidden_columns)},
            }
        )
    if sheet.hidden_rows:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_HIDDEN_ROWS",
                "title": "Lignes masquées détectées",
                "cause": "Le classeur contient une ligne masquée dans un onglet utile.",
                "action": "Afficher ou supprimer la ligne, puis relancer le diagnostic.",
                "location": _row_location(sheet.name, sheet.hidden_rows),
                "technical": {"rows_count": len(sheet.hidden_rows)},
            }
        )
    if sheet.merged_ranges:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_MERGED_CELLS",
                "title": "Cellules fusionnées détectées",
                "cause": "Le classeur contient des cellules fusionnées.",
                "action": "Défusionner les cellules, puis relancer le diagnostic.",
                "location": location,
                "technical": {"checks_count": len(sheet.merged_ranges)},
            }
        )
    if sheet.formula_cells_sample:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_FORMULAS",
                "title": "Formules détectées",
                "cause": "Le classeur contient des formules au lieu de valeurs figées.",
                "action": "Remplacer les formules par leurs valeurs, puis relancer le diagnostic.",
                "location": location,
                "technical": {"checks_count": len(sheet.formula_cells_sample)},
            }
        )
    if sheet.header_row is None:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_HEADER_MISSING",
                "title": "En-tête non détecté",
                "cause": "Le diagnostic ne peut pas identifier une ligne d'en-têtes fiable.",
                "action": "Ajouter une première ligne d'en-têtes, puis relancer le diagnostic.",
                "location": location,
                "technical": {"rows_count": sheet.rows, "columns_count": sheet.columns},
            }
        )
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_ID_MISSING",
                "title": "Colonne id_dossier absente",
                "cause": "Aucune colonne id_dossier ne peut être identifiée sans en-têtes fiables.",
                "action": "Ajouter une première ligne d'en-têtes avec id_dossier, puis relancer le diagnostic.",
                "location": location,
                "technical": {"columns_count": sheet.columns},
            }
        )
    elif sheet.header_row != 1:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_HEADER_MULTIROW",
                "title": "En-tête sur plusieurs lignes",
                "cause": "La ligne d'en-têtes détectée n'est pas la première ligne.",
                "action": "Placer les en-têtes sur la première ligne, puis relancer le diagnostic.",
                "location": {"onglet": sheet.name, "ligne": sheet.header_row},
                "technical": {"rows_count": sheet.header_row},
            }
        )
    if sheet.empty_header_columns_with_data:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_DATA_WITHOUT_HEADER",
                "title": "Données sans en-tête",
                "cause": "Une colonne contient des données mais aucun en-tête exploitable.",
                "action": "Ajouter un en-tête à cette colonne, puis relancer le diagnostic.",
                "location": _column_location(
                    sheet.name, sheet.empty_header_columns_with_data
                ),
                "technical": {
                    "columns_count": len(sheet.empty_header_columns_with_data)
                },
            }
        )
    if sheet.cleaned_header_collisions:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_CSV_HEADER_COLLISION",
                "title": "Collision de noms CSV",
                "cause": "Plusieurs colonnes produisent le même nom CSV après nettoyage InDesign.",
                "action": "Renommer une des colonnes sources, puis relancer le diagnostic.",
                "location": location,
                "technical": {"columns_count": len(sheet.cleaned_header_collisions)},
            }
        )
    if sheet.header_row is not None and not sheet.id_candidates:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_ID_MISSING",
                "title": "Colonne id_dossier absente",
                "cause": "Un onglet non vide ne contient pas de colonne id_dossier détectable.",
                "action": "Ajouter ou renommer la colonne id_dossier, puis relancer le diagnostic.",
                "location": location,
                "technical": {"columns_count": sheet.columns},
            }
        )
    elif len(sheet.id_candidates) > 1:
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_EXCEL_ID_AMBIGUOUS",
                "title": "Colonne id_dossier ambiguë",
                "cause": "Plusieurs colonnes peuvent être interprétées comme id_dossier.",
                "action": "Conserver une seule colonne id_dossier, puis relancer le diagnostic.",
                "location": location,
                "technical": {"columns_count": len(sheet.id_candidates)},
            }
        )
    elif sheet.id_candidates:
        candidate = sheet.id_candidates[0]
        if candidate.duplicate_values:
            problems.append(
                {
                    "severity": "bloquant",
                    "code": "SIRCOM_EXCEL_ID_DUPLICATES",
                    "title": "Doublons id_dossier",
                    "cause": "Un onglet contient plusieurs lignes avec le même id_dossier.",
                    "action": "Corriger les doublons id_dossier, puis relancer le diagnostic.",
                    "location": {"onglet": sheet.name, "colonne": candidate.column},
                    "technical": {"duplicates_count": candidate.duplicate_values},
                }
            )
        if candidate.blank_values:
            problems.append(
                {
                    "severity": "alerte",
                    "code": "SIRCOM_EXCEL_ID_BLANK_ROWS",
                    "title": "Lignes sans id_dossier",
                    "cause": "Certaines lignes n'ont pas d'id_dossier et seront ignorées à l'export.",
                    "action": "Compléter ces identifiants ou accepter leur suppression à l'export.",
                    "location": {"onglet": sheet.name, "colonne": candidate.column},
                    "technical": {"rows_count": candidate.blank_values},
                }
            )
    if sheet.duplicate_headers:
        problems.append(
            {
                "severity": "alerte",
                "code": "SIRCOM_EXCEL_DUPLICATE_SOURCE_HEADERS",
                "title": "En-têtes sources dupliqués",
                "cause": (
                    "Un onglet contient plusieurs colonnes avec le même en-tête source, "
                    "mais la provenance permet de les distinguer."
                ),
                "action": "Vérifier le mapping proposé avant de continuer.",
                "location": location,
                "technical": {"columns_count": len(sheet.duplicate_headers)},
            }
        )
    return problems


def _current_excel_source_artifact(
    repositories: Repositories,
    lot_id: str,
) -> dict[str, Any] | None:
    upload_step = repositories.steps.get_by_lot_key(lot_id, UPLOAD_STEP_KEY)
    if upload_step is None or not upload_step["current_run_id"]:
        return None
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=UPLOAD_STEP_KEY,
        run_id=upload_step["current_run_id"],
        role="source",
    )
    if artifact is None or artifact["status"] != "committed":
        return None
    return artifact


def _require_current_lease(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    if (
        repositories.jobs.get_committable_by_run(
            lot_id=context.lot_id,
            step_key=context.step_key,
            run_id=context.run_id,
            lease_version=context.leased_job.lease_version,
            expected_input_fingerprint=context.leased_job.input_fingerprint,
        )
        is None
    ):
        raise WorkerLeaseLost("Worker lease is no longer current.")


def _current_diagnostic_artifact(
    repositories: Repositories,
    lot_id: str,
) -> dict[str, Any] | None:
    diagnostic_step = repositories.steps.get_by_lot_key(lot_id, DIAGNOSTIC_STEP_KEY)
    if diagnostic_step is None or not diagnostic_step["current_run_id"]:
        return None
    if diagnostic_step["status"] not in {"termine", "termine_avec_alertes", "bloque"}:
        return None
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=DIAGNOSTIC_STEP_KEY,
        run_id=diagnostic_step["current_run_id"],
        role=DIAGNOSTIC_ARTIFACT_ROLE,
    )
    if artifact is None or artifact["status"] != "committed":
        return None
    return artifact


def _record_missing_source_problem(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=DIAGNOSTIC_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_EXCEL_SOURCE_MISSING",
        title="Excel source introuvable",
        cause="Le diagnostic ne trouve pas l'artefact Excel source courant.",
        action="Déposer à nouveau le fichier Excel, puis relancer le diagnostic.",
    )


def _column_location(sheet_name: str, columns: list[str]) -> dict[str, Any]:
    if len(columns) == 1:
        return {"onglet": sheet_name, "colonne": columns[0]}
    return {"onglet": sheet_name}


def _row_location(sheet_name: str, rows: list[int]) -> dict[str, Any]:
    if len(rows) == 1:
        return {"onglet": sheet_name, "ligne": rows[0]}
    return {"onglet": sheet_name}


def _location_from_source(source: str) -> dict[str, Any]:
    sheet_name, separator, column = source.partition("!")
    if not separator:
        return {}
    return {"onglet": sheet_name, "colonne": column}
