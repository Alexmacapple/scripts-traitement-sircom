from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError, cleanup_artifact_paths
from sircom2026.config import Settings
from sircom2026.csv_contract import CSV_CONTRACT_ARTIFACT_ROLE, CSV_CONTRACT_STEP_KEY
from sircom2026.csv_preview import (
    CSV_FINAL_ARTIFACT_ROLE,
    CSV_PREVIEW_ARTIFACT_ROLE,
    CSV_PREVIEW_STEP_KEY,
)
from sircom2026.database import Repositories, TECHNICAL_EVENT_PAYLOAD_KEYS
from sircom2026.excel_diagnostic_pipeline import DIAGNOSTIC_ARTIFACT_ROLE, DIAGNOSTIC_STEP_KEY
from sircom2026.image_matching import (
    MATCHING_ARTIFACT_ROLE,
    MATCHING_IMAGES_STEP_KEY,
    PROCESSED_IMAGES_ARTIFACT_ROLE,
)
from sircom2026.images import (
    INSPECTION_ARTIFACT_ROLE,
    INSPECTION_IMAGES_STEP_KEY,
    UPLOAD_IMAGES_STEP_KEY,
)
from sircom2026.invalidation import fingerprint_payload
from sircom2026.mapping import MAPPING_STEP_KEY
from sircom2026.sorting import SORT_ARTIFACT_ROLE, SORT_STEP_KEY
from sircom2026.state import record_problem
from sircom2026.transform import (
    FUSION_ARTIFACT_ROLE,
    FUSION_STEP_KEY,
    NORMALIZATION_ARTIFACT_ROLE,
    NORMALIZATION_STEP_KEY,
)
from sircom2026.worker import JobResult, WorkerJobContext, WorkerLeaseLost


REPORTS_STEP_KEY = "rapports"
BUSINESS_REPORT_ARTIFACT_KIND = "markdown"
BUSINESS_REPORT_ARTIFACT_ROLE = "rapport-metier"
BUSINESS_REPORT_FILENAME = "rapport-metier.md"
BUSINESS_REPORT_MIME_TYPE = "text/markdown; charset=utf-8"
TECHNICAL_REPORT_ARTIFACT_KIND = "json"
TECHNICAL_REPORT_ARTIFACT_ROLE = "rapport-technique"
TECHNICAL_REPORT_FILENAME = "rapport-technique.json"
TECHNICAL_REPORT_MIME_TYPE = "application/json"
REPORTS_RULES_VERSION = "reports-v1"
REPORTS_SCHEMA_VERSION = 1
READY_STATUSES = ("termine", "termine_avec_alertes")


@dataclass(frozen=True)
class CurrentJsonArtifact:
    artifact: dict[str, Any]
    payload: dict[str, Any]


@dataclass(frozen=True)
class PersistedReports:
    business_artifact: dict[str, Any]
    technical_artifact: dict[str, Any]


class ReportsNotReady(RuntimeError):
    """Raised when current reports cannot be exposed yet."""


class ReportsPrerequisiteMissing(RuntimeError):
    def __init__(self, step_key: str, role: str) -> None:
        super().__init__(f"{step_key}:{role}")
        self.step_key = step_key
        self.role = role


def run_reports_job(context: WorkerJobContext, *, settings: Settings) -> JobResult:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )

    context.set_progress(1, 4)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        try:
            snapshot = _build_report_snapshot(
                repositories,
                store,
                lot_id=context.lot_id,
            )
        except ReportsPrerequisiteMissing as exc:
            _record_missing_prerequisite_problem(repositories, context, exc)
            return JobResult(final_step_status="bloque")

    context.set_progress(2, 4)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    business_content = build_business_report(snapshot, generated_at=generated_at).encode("utf-8")
    technical_report = build_technical_report(snapshot, generated_at=generated_at)
    technical_content = json.dumps(
        technical_report,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ).encode("utf-8")

    context.set_progress(3, 4)
    committed_artifact_paths = []
    reports_committed = False
    try:
        with context.database.transaction() as repositories:
            _require_current_lease(repositories, context)
            repositories.problems.mark_open_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(REPORTS_STEP_KEY,),
            )
            repositories.artifacts.mark_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(REPORTS_STEP_KEY,),
            )
            source_metadata = _report_source_metadata(snapshot)
            business_artifact = store.put_temp_then_commit(
                repositories,
                lot_id=context.lot_id,
                step_key=REPORTS_STEP_KEY,
                run_id=context.run_id,
                kind=BUSINESS_REPORT_ARTIFACT_KIND,
                role=BUSINESS_REPORT_ARTIFACT_ROLE,
                filename=BUSINESS_REPORT_FILENAME,
                content=business_content,
                metadata=dict(source_metadata),
                mime_type=BUSINESS_REPORT_MIME_TYPE,
                lease_version=context.leased_job.lease_version,
            )
            committed_artifact_paths.append(store.path_for(business_artifact["relative_path"]))
            technical_artifact = store.put_temp_then_commit(
                repositories,
                lot_id=context.lot_id,
                step_key=REPORTS_STEP_KEY,
                run_id=context.run_id,
                kind=TECHNICAL_REPORT_ARTIFACT_KIND,
                role=TECHNICAL_REPORT_ARTIFACT_ROLE,
                filename=TECHNICAL_REPORT_FILENAME,
                content=technical_content,
                metadata=dict(source_metadata),
                mime_type=TECHNICAL_REPORT_MIME_TYPE,
                lease_version=context.leased_job.lease_version,
            )
            committed_artifact_paths.append(store.path_for(technical_artifact["relative_path"]))
            output_fingerprint = fingerprint_payload(
                {
                    "business_artifact_id": business_artifact["id"],
                    "business_sha256": business_artifact["sha256"],
                    "kind": "reports",
                    "rules_version": REPORTS_RULES_VERSION,
                    "schema_version": REPORTS_SCHEMA_VERSION,
                    "source_artifacts": {
                        key: {
                            "id": artifact["id"],
                            "sha256": artifact["sha256"],
                        }
                        for key, artifact in snapshot["artifacts"].items()
                        if artifact is not None
                    },
                    "technical_artifact_id": technical_artifact["id"],
                    "technical_sha256": technical_artifact["sha256"],
                }
            )
            has_alerts = snapshot["problem_counts"]["alerte"] > 0
            repositories.events.create(
                lot_id=context.lot_id,
                step_key=REPORTS_STEP_KEY,
                run_id=context.run_id,
                event_type="reports.generated",
                payload={
                    "artifact_id": business_artifact["id"],
                    "artifacts_count": 2,
                    "rows_count": snapshot["integrity"]["csv_rows_count"],
                    "status": "termine_avec_alertes" if has_alerts else "termine",
                    "step_key": REPORTS_STEP_KEY,
                },
            )
            reports_committed = True
    finally:
        if not reports_committed:
            cleanup_artifact_paths(committed_artifact_paths)

    context.set_progress(4, 4)
    return JobResult(
        with_warnings=has_alerts,
        output_fingerprint=output_fingerprint,
        require_next_validations=("package_final",),
    )


def get_persisted_reports(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PersistedReports:
    repositories.lots.get_required(lot_id)
    step = repositories.steps.get_by_lot_key(lot_id, REPORTS_STEP_KEY)
    if (
        step is None
        or not step["current_run_id"]
        or step["status"] not in READY_STATUSES
    ):
        raise ReportsNotReady("Reports are not ready.")

    business_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=REPORTS_STEP_KEY,
        run_id=step["current_run_id"],
        role=BUSINESS_REPORT_ARTIFACT_ROLE,
    )
    technical_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=REPORTS_STEP_KEY,
        run_id=step["current_run_id"],
        role=TECHNICAL_REPORT_ARTIFACT_ROLE,
    )
    if (
        business_artifact is None
        or technical_artifact is None
        or business_artifact["status"] != "committed"
        or technical_artifact["status"] != "committed"
    ):
        raise ReportsNotReady("Reports artifacts are unavailable.")

    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    try:
        store.open_for_read(repositories, lot_id=lot_id, artifact_id=business_artifact["id"])
        store.open_for_read(repositories, lot_id=lot_id, artifact_id=technical_artifact["id"])
    except (ArtifactUnavailableError, KeyError, ValueError) as exc:
        raise ReportsNotReady("Reports artifacts are unavailable.") from exc

    return PersistedReports(
        business_artifact=business_artifact,
        technical_artifact=technical_artifact,
    )


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
            f"- Fichier final attendu : sircom-indesign-utf16.csv",
            f"- Encodage : UTF-16 avec BOM",
            f"- Séparateur : virgule",
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
            f"- Dossier final images : export-jpg-resize/",
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


def build_technical_report(snapshot: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    steps = snapshot["steps"]
    artifacts = snapshot["artifacts"]
    problems = snapshot["problems"]
    events = snapshot["events"]
    return {
        "schema_version": REPORTS_SCHEMA_VERSION,
        "rules_version": REPORTS_RULES_VERSION,
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
                "rows_removed": _int(snapshot["fusion"].get("removed_rows_without_id_count")),
                "columns_count": _int(snapshot["fusion"].get("columns_count")),
            },
            "normalisation": {
                "rows_count": _int(snapshot["normalization"].get("rows_count")),
                "columns_count": _int(snapshot["normalization"].get("columns_count")),
                "date_issues_count": _int(snapshot["normalization"].get("date_issues_count")),
                "invalid_dates_count": _int(snapshot["normalization"].get("invalid_dates_count")),
                "missing_dates_count": _int(snapshot["normalization"].get("missing_dates_count")),
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
                "unreferenced_count": _int(snapshot["matching"].get("unreferenced_count")),
                "conversion_failed_count": _int(
                    snapshot["matching"].get("conversion_failed_count")
                ),
                "tolerant_count": _int(snapshot["matching"].get("tolerant_count")),
            },
        },
        "codes_erreur": _technical_problem_codes(problems),
        "traces_anonymisees": [_technical_event_entry(event) for event in events],
    }


def _build_report_snapshot(
    repositories: Repositories,
    store: ArtifactStore,
    *,
    lot_id: str,
) -> dict[str, Any]:
    lot = repositories.lots.get_required(lot_id)
    steps = repositories.steps.list_for_lot(lot_id)
    problems = repositories.problems.list_for_lot(lot_id, limit=500)
    problem_counts = {
        severity: repositories.problems.count_open_by_severity(
            lot_id=lot_id,
            severity=severity,
        )
        for severity in ("bloquant", "alerte", "information")
    }
    events = repositories.events.list_for_lot(lot_id, limit=200)

    excel_source = _required_current_artifact(
        repositories,
        lot_id=lot_id,
        step_key="upload_excel",
        role="source",
        ready_statuses=READY_STATUSES,
    )
    diagnostic = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=DIAGNOSTIC_STEP_KEY,
        role=DIAGNOSTIC_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    mapping = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        role="validated",
        ready_statuses=READY_STATUSES,
    )
    fusion = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=FUSION_STEP_KEY,
        role=FUSION_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    normalization = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=NORMALIZATION_STEP_KEY,
        role=NORMALIZATION_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    sort = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        role=SORT_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    csv_contract = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=CSV_CONTRACT_STEP_KEY,
        role=CSV_CONTRACT_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    csv_preview = _required_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        role=CSV_PREVIEW_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    csv_final = _required_current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        role=CSV_FINAL_ARTIFACT_ROLE,
        ready_statuses=READY_STATUSES,
    )
    image_zip_source = _current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        role="source",
        ready_statuses=READY_STATUSES,
    )
    if image_zip_source is None:
        inspection_artifact = None
        inspection_payload = _empty_image_inspection_payload()
        matching_artifact = None
        matching_payload = _empty_image_matching_payload()
        processed_images = None
    else:
        inspection = _required_json_artifact(
            repositories,
            store,
            lot_id=lot_id,
            step_key=INSPECTION_IMAGES_STEP_KEY,
            role=INSPECTION_ARTIFACT_ROLE,
            ready_statuses=READY_STATUSES,
        )
        matching = _required_json_artifact(
            repositories,
            store,
            lot_id=lot_id,
            step_key=MATCHING_IMAGES_STEP_KEY,
            role=MATCHING_ARTIFACT_ROLE,
            ready_statuses=READY_STATUSES,
        )
        processed_images = _current_artifact(
            repositories,
            lot_id=lot_id,
            step_key=MATCHING_IMAGES_STEP_KEY,
            role=PROCESSED_IMAGES_ARTIFACT_ROLE,
            ready_statuses=READY_STATUSES,
        )
        inspection_artifact = inspection.artifact
        inspection_payload = inspection.payload
        matching_artifact = matching.artifact
        matching_payload = matching.payload
    artifacts = {
        "excel_source": excel_source,
        "diagnostic": diagnostic.artifact,
        "mapping": mapping.artifact,
        "fusion": fusion.artifact,
        "normalization": normalization.artifact,
        "sort": sort.artifact,
        "csv_contract": csv_contract.artifact,
        "csv_preview": csv_preview.artifact,
        "csv_final": csv_final,
        "image_zip_source": image_zip_source,
        "inspection": inspection_artifact,
        "matching": matching_artifact,
        "processed_images": processed_images,
    }
    return {
        "lot": lot,
        "steps": steps,
        "problems": problems,
        "problem_counts": problem_counts,
        "events": events,
        "artifacts": artifacts,
        "diagnostic": diagnostic.payload,
        "mapping": mapping.payload,
        "fusion": fusion.payload,
        "normalization": normalization.payload,
        "sort": sort.payload,
        "csv_contract": csv_contract.payload,
        "csv_preview": csv_preview.payload,
        "inspection": inspection_payload,
        "matching": matching_payload,
        "integrity": _integrity_payload(
            normalization.payload,
            csv_preview.payload,
            matching_payload,
            problems_count=sum(problem_counts.values()),
        ),
    }


def _report_source_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "rules_version": REPORTS_RULES_VERSION,
        "schema_version": REPORTS_SCHEMA_VERSION,
        "source_csv_artifact_id": snapshot["artifacts"]["csv_final"]["id"],
    }
    matching = snapshot["artifacts"].get("matching")
    if matching is not None:
        metadata["source_matching_artifact_id"] = matching["id"]
    return metadata


def _empty_image_inspection_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rules_version": "image-zip-inspection-v2",
        "inspectable": False,
        "image_count": 0,
        "images": [],
        "skipped": True,
        "reason": "no_image_zip",
    }


def _empty_image_matching_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rules_version": "image-matching-v1",
        "rows_count": 0,
        "bindings_count": 0,
        "bindings": [],
        "manual_resolutions": [],
        "matched_count": 0,
        "processed_images_count": 0,
        "missing_count": 0,
        "ambiguous_count": 0,
        "unreferenced_count": 0,
        "conversion_failed_count": 0,
        "fallback_count": 0,
        "tolerant_count": 0,
        "blocking": False,
        "has_warnings": False,
        "skipped": True,
        "reason": "no_image_zip",
    }


def _required_json_artifact(
    repositories: Repositories,
    store: ArtifactStore,
    *,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> CurrentJsonArtifact:
    artifact = _required_current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        role=role,
        ready_statuses=ready_statuses,
    )
    try:
        readable = store.open_for_read(
            repositories,
            lot_id=lot_id,
            artifact_id=artifact["id"],
        )
        payload = json.loads(readable.path.read_text(encoding="utf-8"))
    except (ArtifactUnavailableError, OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise ReportsPrerequisiteMissing(step_key, role) from exc
    if not isinstance(payload, dict):
        raise ReportsPrerequisiteMissing(step_key, role)
    return CurrentJsonArtifact(artifact=artifact, payload=payload)


def _required_current_artifact(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> dict[str, Any]:
    artifact = _current_artifact(
        repositories,
        lot_id=lot_id,
        step_key=step_key,
        role=role,
        ready_statuses=ready_statuses,
    )
    if artifact is None:
        raise ReportsPrerequisiteMissing(step_key, role)
    return artifact


def _current_artifact(
    repositories: Repositories,
    *,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> dict[str, Any] | None:
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if step is None or not step["current_run_id"] or step["status"] not in ready_statuses:
        return None
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=step_key,
        run_id=step["current_run_id"],
        role=role,
    )
    if artifact is None or artifact["status"] != "committed":
        return None
    return artifact


def _record_missing_prerequisite_problem(
    repositories: Repositories,
    context: WorkerJobContext,
    missing: ReportsPrerequisiteMissing,
) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=context.lot_id,
        step_keys=(REPORTS_STEP_KEY,),
    )
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=REPORTS_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_REPORTS_PREREQUISITE_MISSING",
        title="Rapports impossibles",
        cause="Un artefact courant requis pour générer les rapports est absent ou illisible.",
        action="Relancer l'étape indiquée puis relancer les rapports.",
        technical={
            "step_key": missing.step_key,
            "status": "missing",
        },
    )


def _require_current_lease(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    if repositories.jobs.get_committable_by_run(
        lot_id=context.lot_id,
        step_key=context.step_key,
        run_id=context.run_id,
        lease_version=context.leased_job.lease_version,
        expected_input_fingerprint=context.leased_job.input_fingerprint,
    ) is None:
        raise WorkerLeaseLost("Worker lease is no longer current.")


def _integrity_payload(
    normalization: dict[str, Any],
    csv_preview: dict[str, Any],
    matching: dict[str, Any],
    *,
    problems_count: int,
) -> dict[str, int]:
    source_ids = {
        str(row.get("id_dossier") or "").strip()
        for row in normalization.get("rows", [])
        if isinstance(row, dict) and str(row.get("id_dossier") or "").strip()
    }
    removed_empty_columns_count = _int(normalization.get("removed_empty_columns_count")) + _int(
        normalization.get("upstream_removed_empty_columns_count")
    )
    return {
        "source_ids_count": len(source_ids),
        "csv_rows_count": _int(csv_preview.get("rows_count")),
        "removed_rows_without_id_count": _int(
            csv_preview.get("removed_rows_without_id_count")
        ),
        "removed_empty_columns_count": removed_empty_columns_count,
        "present_images_count": _int(matching.get("processed_images_count")),
        "missing_images_count": _int(matching.get("missing_count")),
        "ignored_images_count": _int(matching.get("unreferenced_count")),
        "open_problems_count": problems_count,
    }


def _mapping_table_lines(mapping: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    columns = [
        column
        for column in mapping.get("columns", [])
        if isinstance(column, dict)
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
        letter = "Système" if column.get("system") else _text(column.get("source_column_letter"))
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
        lines.append("| Non précisé | Non précisé | Non précisé | Non précisé | Non précisé |")
    return lines


def _sheet_lines(diagnostic: dict[str, Any]) -> list[str]:
    sheets = [sheet for sheet in diagnostic.get("sheets", []) if isinstance(sheet, dict)]
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
        warning
        for warning in preview.get("warnings", [])
        if isinstance(warning, dict)
    ]
    issues = [
        issue
        for issue in contract.get("issues", [])
        if isinstance(issue, dict)
    ]
    if not warnings and not issues:
        return ["- Alertes CSV : aucune"]
    lines = ["- Alertes CSV :"]
    for warning in warnings:
        lines.append(f"  - {_text(warning.get('code'))} : {_text(warning.get('title'))}")
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


def _technical_event_entry(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": event["created_at"],
        "event_type": event["event_type"],
        "step_key": event["step_key"],
        "run_id": event["run_id"],
        "level": event["level"],
        "payload": _scrub_event_payload(_json_dict(event.get("payload_json"))),
    }


def _scrub_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key in TECHNICAL_EVENT_PAYLOAD_KEYS
        and isinstance(value, str | int | float | bool | type(None))
        and not (isinstance(value, str) and ("/" in value or "\\" in value))
    }


def _problem_counts(problems: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"bloquant": 0, "alerte": 0, "information": 0}
    for problem in problems:
        severity = str(problem.get("severity") or "")
        if severity in counts:
            counts[severity] += 1
    return counts


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
