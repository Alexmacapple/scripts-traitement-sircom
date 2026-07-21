from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError
from sircom2026.config import Settings
from sircom2026.csv_contract import (
    CSV_CONTRACT_ARTIFACT_ROLE,
    CSV_CONTRACT_STEP_KEY,
    verify_indesign_csv_bytes,
    write_indesign_csv_bytes,
)
from sircom2026.database import LOT_WRITE_BLOCKED_STATUSES, Repositories
from sircom2026.image_naming import image_id_for_dossier
from sircom2026.invalidation import record_human_validation_snapshot, step_input_fingerprint
from sircom2026.lots import get_lot_detail
from sircom2026.state import complete_step, record_problem, require_human_validation, transition_step


CSV_PREVIEW_STEP_KEY = "previsualisation_csv"
CSV_PREVIEW_ARTIFACT_KIND = "json"
CSV_PREVIEW_ARTIFACT_ROLE = "preview"
CSV_PREVIEW_MIME_TYPE = "application/json"
CSV_FINAL_ARTIFACT_KIND = "csv"
CSV_FINAL_ARTIFACT_ROLE = "csv_final"
CSV_FINAL_MIME_TYPE = "text/csv"
CSV_PREVIEW_RULES_VERSION = "csv-preview-validation-v1"
CSV_PREVIEW_SCHEMA_VERSION = 1
CSV_PREVIEW_API_WORKER_ID = "api"
CSV_PREVIEW_ROWS_LIMIT = 10
SORT_STEP_KEY = "tri_region_departement"
SORT_ARTIFACT_ROLE = "result"
IMAGE_MATCHING_STEP_KEY = "matching_images"
IMAGE_MATCHING_ARTIFACT_ROLE = "result"


@dataclass(frozen=True)
class CurrentJsonArtifact:
    artifact: dict[str, Any]
    payload: dict[str, Any]


@dataclass(frozen=True)
class CsvPreviewValidationResult:
    preview: dict[str, Any]
    preview_artifact: dict[str, Any]
    csv_artifact: dict[str, Any]
    lot: dict[str, Any]
    invalidated_steps: tuple[str, ...] = ()


class CsvPreviewError(ValueError):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def get_csv_preview_payload(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any]:
    preview = _build_current_preview(repositories, settings=settings, lot_id=lot_id)
    current = _current_preview_artifacts(repositories, settings=settings, lot_id=lot_id)
    if current is not None and current["input_fingerprint"] == preview["input_fingerprint"]:
        return {
            "preview": current["preview"],
            "preview_artifact": current["preview_artifact"],
            "csv_artifact": current["csv_artifact"],
        }
    return {
        "preview": _public_preview(preview),
        "preview_artifact": None,
        "csv_artifact": None,
    }


def validate_csv_preview(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    idempotency_key: str,
) -> CsvPreviewValidationResult:
    _require_mutable_lot(repositories, lot_id)
    _require_export_testable(repositories, lot_id=lot_id)
    preview = _build_current_preview(repositories, settings=settings, lot_id=lot_id)

    existing = _existing_preview_validation(
        repositories,
        settings=settings,
        lot_id=lot_id,
        idempotency_key=idempotency_key,
        input_fingerprint=preview["input_fingerprint"],
    )
    if existing is not None:
        _enqueue_ready_auto_steps(
            repositories,
            lot_id=lot_id,
            source_step_key=CSV_PREVIEW_STEP_KEY,
            source_run_id=str(existing["csv_artifact"]["run_id"]),
        )
        return CsvPreviewValidationResult(
            preview=existing["preview"],
            preview_artifact=existing["preview_artifact"],
            csv_artifact=existing["csv_artifact"],
            lot=get_lot_detail(repositories, lot_id),
        )

    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(CSV_PREVIEW_STEP_KEY,),
    )
    if repositories.problems.count_open_by_severity(lot_id=lot_id, severity="bloquant"):
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_BLOCKERS_OPEN",
            "L'export CSV est bloqué par des problèmes ouverts.",
        )

    headers, rows, csv_content = _csv_content_from_preview(preview)
    contract = verify_indesign_csv_bytes(csv_content, expected_headers=headers)
    if not contract.valid:
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_CONTRACT_INVALID",
            "Le CSV final ne passe pas le vérificateur InDesign.",
            details={"issues_count": len(contract.issues)},
        )

    run_id = f"run_{uuid.uuid4().hex}"
    input_fingerprint = preview["input_fingerprint"]
    validated_at = datetime.now(UTC).isoformat(timespec="seconds")
    preview["validated"] = True
    preview["validated_at"] = validated_at
    preview["csv_contract"] = contract.to_public_dict()
    public_preview = _public_preview(preview)

    preview_content = json.dumps(
        public_preview,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )

    repositories.jobs.cancel_active_for_step(lot_id, CSV_PREVIEW_STEP_KEY)
    repositories.artifacts.mark_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(CSV_PREVIEW_STEP_KEY,),
    )
    repositories.steps.prepare_run(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        input_fingerprint=input_fingerprint,
    )
    transition_step(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        status="en_cours",
        run_id=run_id,
    )
    job = repositories.jobs.create_owned_running(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        idempotency_key=idempotency_key,
        lease_owner=CSV_PREVIEW_API_WORKER_ID,
        lease_seconds=settings.worker_lease_ttl_seconds,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        event_type="job.started",
        payload={"status": "en_cours", "step_key": CSV_PREVIEW_STEP_KEY},
    )
    preview_artifact = store.put_temp_then_commit(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        kind=CSV_PREVIEW_ARTIFACT_KIND,
        role=CSV_PREVIEW_ARTIFACT_ROLE,
        filename="apercu-csv.json",
        content=preview_content,
        metadata={
            "columns_count": len(headers),
            "rows_count": public_preview["rows_count"],
            "rules_version": CSV_PREVIEW_RULES_VERSION,
            "schema_version": CSV_PREVIEW_SCHEMA_VERSION,
        },
        mime_type=CSV_PREVIEW_MIME_TYPE,
        lease_version=int(job["lease_version"]),
    )
    csv_artifact = store.put_temp_then_commit(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        kind=CSV_FINAL_ARTIFACT_KIND,
        role=CSV_FINAL_ARTIFACT_ROLE,
        filename="sircom-indesign-utf16.csv",
        content=csv_content,
        metadata={
            "columns_count": len(headers),
            "rows_count": len(rows),
            "rules_version": CSV_PREVIEW_RULES_VERSION,
            "schema_version": CSV_PREVIEW_SCHEMA_VERSION,
        },
        mime_type=CSV_FINAL_MIME_TYPE,
        lease_version=int(job["lease_version"]),
    )
    finished = repositories.jobs.finish_owned(
        job_id=job["id"],
        worker_id=CSV_PREVIEW_API_WORKER_ID,
        run_id=run_id,
        lease_version=int(job["lease_version"]),
        status="succeeded",
        expected_input_fingerprint=input_fingerprint,
    )
    if finished is None:
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_PREVIEW_COMMIT_REJECTED",
            "La validation de l'aperçu CSV n'est plus courante.",
        )

    snapshot = record_human_validation_snapshot(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        decision_payload={
            "csv_artifact_id": csv_artifact["id"],
            "csv_sha256": csv_artifact["sha256"],
            "preview_artifact_id": preview_artifact["id"],
            "preview_sha256": preview_artifact["sha256"],
            "rules_version": CSV_PREVIEW_RULES_VERSION,
            "schema_version": CSV_PREVIEW_SCHEMA_VERSION,
        },
        reason="csv_preview_validated",
    )
    for warning in public_preview["warnings"]:
        if warning.get("persist_problem"):
            record_problem(
                repositories,
                lot_id=lot_id,
                step_key=CSV_PREVIEW_STEP_KEY,
                run_id=run_id,
                severity="alerte",
                code=warning["code"],
                title=warning["title"],
                cause=warning["cause"],
                action=warning["action"],
            )
    complete_step(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        with_warnings=bool(public_preview["warnings"]),
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        event_type="csv.preview_validated",
        payload={
            "artifact_id": csv_artifact["id"],
            "columns_count": len(headers),
            "rows_count": len(rows),
            "status": "termine_avec_alertes" if public_preview["warnings"] else "termine",
            "step_key": CSV_PREVIEW_STEP_KEY,
        },
    )
    _enqueue_ready_auto_steps(
        repositories,
        lot_id=lot_id,
        source_step_key=CSV_PREVIEW_STEP_KEY,
        source_run_id=run_id,
    )
    return CsvPreviewValidationResult(
        preview=public_preview,
        preview_artifact=preview_artifact,
        csv_artifact=csv_artifact,
        lot=get_lot_detail(repositories, lot_id),
        invalidated_steps=snapshot.invalidated_steps,
    )


def get_csv_export_payload(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any]:
    _require_export_testable(repositories, lot_id=lot_id)
    if repositories.problems.count_open_by_severity(lot_id=lot_id, severity="bloquant"):
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_BLOCKERS_OPEN",
            "L'export CSV est bloqué par des problèmes ouverts.",
        )
    preview = _build_current_preview(repositories, settings=settings, lot_id=lot_id)
    current = _current_preview_artifacts(repositories, settings=settings, lot_id=lot_id)
    if current is None or current["input_fingerprint"] != preview["input_fingerprint"]:
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_PREVIEW_NOT_VALIDATED",
            "L'aperçu CSV courant n'a pas encore été validé.",
        )
    return {
        "preview": current["preview"],
        "artifact": current["csv_artifact"],
    }


def require_csv_preview_validation_if_ready(
    repositories: Repositories,
    *,
    lot_id: str,
) -> None:
    sort_step = repositories.steps.get_by_lot_key(lot_id, SORT_STEP_KEY)
    contract_step = repositories.steps.get_by_lot_key(lot_id, CSV_CONTRACT_STEP_KEY)
    preview_step = repositories.steps.get_by_lot_key(lot_id, CSV_PREVIEW_STEP_KEY)
    if sort_step is None or contract_step is None or preview_step is None:
        return
    if sort_step["status"] not in {"termine", "termine_avec_alertes"}:
        return
    if contract_step["status"] not in {"termine", "termine_avec_alertes"}:
        return
    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
    )
    if (
        preview_step["status"] == "action_requise"
        and preview_step["input_fingerprint"] == input_fingerprint
    ):
        return
    run_id = f"run_{uuid.uuid4().hex}"
    repositories.steps.prepare_run(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
        input_fingerprint=input_fingerprint,
    )
    require_human_validation(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=run_id,
    )


def _build_current_preview(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any]:
    repositories.lots.get_required(lot_id)
    sort = _current_json_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        role=SORT_ARTIFACT_ROLE,
        ready_statuses=("termine", "termine_avec_alertes"),
    )
    if sort is None:
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_SORT_NOT_VALIDATED",
            "Le tri doit être validé avant l'aperçu CSV.",
        )
    contract = _current_json_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        step_key=CSV_CONTRACT_STEP_KEY,
        role=CSV_CONTRACT_ARTIFACT_ROLE,
        ready_statuses=("termine", "termine_avec_alertes"),
    )
    if contract is None:
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_CONTRACT_NOT_READY",
            "Le vérificateur CSV doit être terminé avant l'aperçu.",
        )
    if not bool(contract.payload.get("valid")):
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_CONTRACT_INVALID",
            "Le vérificateur CSV signale un contrat invalide.",
        )

    matching = _current_json_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        step_key=IMAGE_MATCHING_STEP_KEY,
        role=IMAGE_MATCHING_ARTIFACT_ROLE,
        ready_statuses=("termine", "termine_avec_alertes", "bloque"),
    )
    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
    )
    headers, rows = _headers_and_rows_from_sort(
        sort.payload,
        image_bindings=_image_bindings_by_id(matching.payload if matching else None),
    )
    warnings = _preview_warnings(sort.payload, matching.payload if matching else None)
    return {
        "schema_version": CSV_PREVIEW_SCHEMA_VERSION,
        "rules_version": CSV_PREVIEW_RULES_VERSION,
        "input_fingerprint": input_fingerprint,
        "source_sort_artifact_id": sort.artifact["id"],
        "source_csv_contract_artifact_id": contract.artifact["id"],
        "source_image_matching_artifact_id": matching.artifact["id"] if matching else None,
        "validated": False,
        "validated_at": None,
        "headers": headers,
        "headers_count": len(headers),
        "rows_count": len(rows),
        "preview_rows_limit": CSV_PREVIEW_ROWS_LIMIT,
        "rows": rows[:CSV_PREVIEW_ROWS_LIMIT],
        "_all_rows": rows,
        "removed_columns_count": _removed_columns_count(sort.payload),
        "removed_columns": _removed_columns(sort.payload),
        "removed_rows_without_id_count": int(
            sort.payload.get("upstream_removed_rows_without_id_count") or 0
        ),
        "removed_rows": sort.payload.get("upstream_removed_rows_without_id", []),
        "warnings": warnings,
    }


def _headers_and_rows_from_sort(
    sort_payload: dict[str, Any],
    *,
    image_bindings: dict[str, dict[str, str]] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    headers = [
        str(column["csv_name"])
        for column in sort_payload.get("columns", [])
        if isinstance(column, dict) and column.get("csv_name") is not None
    ]
    rows: list[dict[str, Any]] = []
    for source_row in sort_payload.get("rows", []):
        if not isinstance(source_row, dict):
            continue
        values = (
            source_row.get("values")
            if isinstance(source_row.get("values"), dict)
            else {}
        )
        row_values = {
            header: "" if values.get(header) is None else str(values.get(header, ""))
            for header in headers
        }
        id_dossier = str(source_row.get("id_dossier") or "").strip()
        if "imageid" in row_values and id_dossier:
            binding_values = (image_bindings or {}).get(id_dossier, {})
            row_values["imageid"] = binding_values.get("imageid") or image_id_for_dossier(id_dossier)
            if "@pathimg" in row_values:
                row_values["@pathimg"] = binding_values.get("@pathimg", "")
        rows.append(
            {
                "id_dossier": source_row.get("id_dossier"),
                "source_rank": source_row.get("source_rank"),
                "values": row_values,
            }
        )
    return headers, rows


def _csv_content_from_preview(preview: dict[str, Any]) -> tuple[list[str], list[list[str]], bytes]:
    headers = [str(header) for header in preview["headers"]]
    rows = [
        [str(row.get("values", {}).get(header, "")) for header in headers]
        for row in preview.get("_all_rows", preview["rows"])
        if isinstance(row, dict)
    ]
    return headers, rows, write_indesign_csv_bytes(headers, rows)


def _public_preview(preview: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in preview.items()
        if not key.startswith("_")
    }


def _image_bindings_by_id(matching_payload: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    if not matching_payload:
        return {}
    result: dict[str, dict[str, str]] = {}
    for binding in matching_payload.get("bindings", []):
        if not isinstance(binding, dict):
            continue
        id_dossier = str(binding.get("id_dossier") or "").strip()
        if not id_dossier:
            continue
        result[id_dossier] = {
            "imageid": str(binding.get("imageid") or ""),
            "@pathimg": str(binding.get("pathimg") or ""),
        }
    return result


def _preview_warnings(
    sort_payload: dict[str, Any],
    matching_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if sort_payload.get("warning_code"):
        warnings.append(
            {
                "code": sort_payload["warning_code"],
                "title": "Tri conservé en ordre source",
                "cause": "Le tri région/département n'a pas été appliqué automatiquement.",
                "action": "Vérifier l'ordre de l'aperçu avant validation.",
                "persist_problem": False,
            }
        )
    if matching_payload is None:
        warnings.append(
            {
                "code": "SIRCOM_CSV_IMAGES_NOT_PROVIDED",
                "title": "Images non fournies",
                "cause": "Les images finales ne sont pas encore validées pour ce lot.",
                "action": "Le CSV peut être exporté ; le package images sera traité dans les étapes suivantes.",
                "persist_problem": True,
            }
        )
    if int(sort_payload.get("upstream_removed_rows_without_id_count") or 0):
        warnings.append(
            {
                "code": "SIRCOM_CSV_ROWS_WITHOUT_ID_REMOVED",
                "title": "Lignes sans id_dossier supprimées",
                "cause": "Des lignes source sans id_dossier ne sont pas exportées.",
                "action": "Vérifier l'aperçu et corriger l'Excel si nécessaire.",
                "persist_problem": False,
            }
        )
    if _removed_columns_count(sort_payload):
        warnings.append(
            {
                "code": "SIRCOM_CSV_EMPTY_COLUMNS_REMOVED",
                "title": "Colonnes vides supprimées",
                "cause": "Des colonnes entièrement vides ne sont pas exportées.",
                "action": "Vérifier que les colonnes supprimées ne sont pas attendues.",
                "persist_problem": False,
            }
        )
    return warnings


def _removed_columns_count(sort_payload: dict[str, Any]) -> int:
    return int(sort_payload.get("removed_empty_columns_count") or 0) + int(
        sort_payload.get("upstream_removed_empty_columns_count") or 0
    )


def _removed_columns(sort_payload: dict[str, Any]) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for key in ("removed_empty_columns", "upstream_removed_empty_columns"):
        for column in sort_payload.get(key, []):
            if isinstance(column, dict):
                columns.append(column)
    return columns


def _existing_preview_validation(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    idempotency_key: str,
    input_fingerprint: str,
) -> dict[str, Any] | None:
    existing_job = repositories.jobs.get_by_idempotency_key(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        idempotency_key=idempotency_key,
    )
    if existing_job is None:
        return None
    if existing_job["status"] != "succeeded":
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_PREVIEW_ALREADY_SUBMITTED",
            "Cette validation d'aperçu CSV est déjà en cours.",
        )
    step = repositories.steps.get_by_lot_key(lot_id, CSV_PREVIEW_STEP_KEY)
    if (
        step is None
        or step["current_run_id"] != existing_job["run_id"]
        or step["input_fingerprint"] != input_fingerprint
        or step["status"] not in {"termine", "termine_avec_alertes"}
    ):
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_PREVIEW_IDEMPOTENCY_REUSED",
            "Cette clé d'idempotence correspond à un aperçu CSV qui n'est plus courant.",
        )
    preview_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=existing_job["run_id"],
        role=CSV_PREVIEW_ARTIFACT_ROLE,
    )
    csv_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=existing_job["run_id"],
        role=CSV_FINAL_ARTIFACT_ROLE,
    )
    if (
        preview_artifact is None
        or csv_artifact is None
        or preview_artifact["status"] != "committed"
        or csv_artifact["status"] != "committed"
    ):
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_PREVIEW_ALREADY_SUBMITTED",
            "Cette clé d'idempotence a déjà été utilisée pour une autre validation.",
        )
    preview = _read_json_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        artifact=preview_artifact,
    )
    return {
        "preview": preview,
        "preview_artifact": preview_artifact,
        "csv_artifact": csv_artifact,
    }


def _require_export_testable(repositories: Repositories, *, lot_id: str) -> None:
    required_steps = (
        "diagnostic_excel",
        "mapping",
        "fusion_multi_onglets",
        "normalisation_contenu",
        SORT_STEP_KEY,
        CSV_CONTRACT_STEP_KEY,
    )
    missing = []
    for step_key in required_steps:
        step = repositories.steps.get_by_lot_key(lot_id, step_key)
        if step is None or step["status"] not in {"termine", "termine_avec_alertes"}:
            missing.append(step_key)
    if missing:
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_EXPORT_PREREQUISITES_MISSING",
            "L'export CSV n'a pas encore tous ses prérequis testables.",
            details={"missing_steps": missing},
        )


def _enqueue_ready_auto_steps(
    repositories: Repositories,
    *,
    lot_id: str,
    source_step_key: str,
    source_run_id: str,
) -> None:
    from sircom2026.pipeline import ready_auto_enqueue_step_keys
    from sircom2026.worker import enqueue_job

    for step_key in ready_auto_enqueue_step_keys(
        repositories,
        lot_id=lot_id,
        source_step_key=source_step_key,
    ):
        input_fingerprint = step_input_fingerprint(
            repositories,
            lot_id=lot_id,
            step_key=step_key,
        )
        enqueue_job(
            repositories,
            lot_id=lot_id,
            step_key=step_key,
            idempotency_key=f"{step_key}:{source_step_key}:{source_run_id}",
            input_fingerprint=input_fingerprint,
        )


def _current_preview_artifacts(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any] | None:
    step = repositories.steps.get_by_lot_key(lot_id, CSV_PREVIEW_STEP_KEY)
    if (
        step is None
        or not step["current_run_id"]
        or step["status"] not in {"termine", "termine_avec_alertes"}
    ):
        return None
    preview_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=step["current_run_id"],
        role=CSV_PREVIEW_ARTIFACT_ROLE,
    )
    csv_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=CSV_PREVIEW_STEP_KEY,
        run_id=step["current_run_id"],
        role=CSV_FINAL_ARTIFACT_ROLE,
    )
    if preview_artifact is None or csv_artifact is None:
        return None
    preview = _read_json_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        artifact=preview_artifact,
    )
    return {
        "input_fingerprint": step["input_fingerprint"],
        "preview": preview,
        "preview_artifact": preview_artifact,
        "csv_artifact": csv_artifact,
    }


def _current_json_artifact(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> CurrentJsonArtifact | None:
    step = repositories.steps.get_by_lot_key(lot_id, step_key)
    if (
        step is None
        or not step["current_run_id"]
        or step["status"] not in ready_statuses
    ):
        return None
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=step_key,
        run_id=step["current_run_id"],
        role=role,
    )
    if artifact is None or artifact["status"] != "committed":
        return None
    payload = _read_json_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        artifact=artifact,
    )
    return CurrentJsonArtifact(artifact=artifact, payload=payload)


def _read_json_artifact(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
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
        payload = json.loads(readable.path.read_text(encoding="utf-8"))
    except (ArtifactUnavailableError, OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_ARTIFACT_UNAVAILABLE",
            "Un artefact nécessaire à l'aperçu CSV est indisponible.",
        ) from exc
    if not isinstance(payload, dict):
        raise CsvPreviewError(
            409,
            "SIRCOM_CSV_ARTIFACT_INVALID",
            "Un artefact nécessaire à l'aperçu CSV est invalide.",
        )
    return payload


def _require_mutable_lot(repositories: Repositories, lot_id: str) -> None:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise CsvPreviewError(
            409,
            "SIRCOM_LOT_NOT_MUTABLE",
            "Lot non modifiable.",
        )
