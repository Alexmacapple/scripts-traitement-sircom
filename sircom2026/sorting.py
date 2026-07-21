from __future__ import annotations

import json
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sircom2026.artifacts import ArtifactStore, ArtifactUnavailableError
from sircom2026.config import Settings
from sircom2026.database import LOT_WRITE_BLOCKED_STATUSES, Repositories
from sircom2026.invalidation import record_human_validation_snapshot, step_input_fingerprint
from sircom2026.lots import get_lot_detail
from sircom2026.state import complete_step, record_problem, transition_step
from sircom2026.transform import NORMALIZATION_ARTIFACT_ROLE, NORMALIZATION_STEP_KEY


SORT_STEP_KEY = "tri_region_departement"
SORT_ARTIFACT_KIND = "json"
SORT_ARTIFACT_ROLE = "result"
SORT_RULES_VERSION = "sort-validation-v1"
SORT_MIME_TYPE = "application/json"
SORT_SCHEMA_VERSION = 1
SORT_API_WORKER_ID = "api"
SORT_DECISIONS = {"tri_region_departement", "ordre_source"}
SORT_WARNING_CODES = {
    "missing": "SIRCOM_SORT_COLUMNS_NOT_DETECTED",
    "ambiguous": "SIRCOM_SORT_COLUMNS_AMBIGUOUS",
}


@dataclass(frozen=True)
class CurrentJsonArtifact:
    artifact: dict[str, Any]
    payload: dict[str, Any]


@dataclass(frozen=True)
class SortDecisionResult:
    decision: dict[str, Any]
    artifact: dict[str, Any]
    lot: dict[str, Any]
    invalidated_steps: tuple[str, ...] = ()


class SortDecisionError(ValueError):
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


def get_sort_payload(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any]:
    normalized = _current_normalization_artifact(repositories, settings=settings, lot_id=lot_id)
    if normalized is None:
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_NORMALIZATION_NOT_READY",
            "Normalisation du contenu non disponible pour le tri.",
        )
    proposal = build_sort_proposal(
        normalized.payload,
        source_normalization_artifact_id=normalized.artifact["id"],
    )
    current_decision = _current_sort_artifact(repositories, settings=settings, lot_id=lot_id)
    return {
        "proposal": proposal,
        "decision": current_decision.payload if current_decision else None,
        "artifact": current_decision.artifact if current_decision else None,
    }


def validate_sort_decision(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    decision: str,
    idempotency_key: str,
) -> SortDecisionResult:
    _require_mutable_lot(repositories, lot_id)
    decision = decision.strip()
    if decision not in SORT_DECISIONS:
        raise SortDecisionError(
            422,
            "SIRCOM_SORT_DECISION_INVALID",
            "Décision de tri invalide.",
        )

    existing = _existing_sort_decision(
        repositories,
        settings=settings,
        lot_id=lot_id,
        decision=decision,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return SortDecisionResult(
            decision=existing.payload,
            artifact=existing.artifact,
            lot=get_lot_detail(repositories, lot_id),
        )

    normalized = _current_normalization_artifact(repositories, settings=settings, lot_id=lot_id)
    if normalized is None:
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_NORMALIZATION_NOT_READY",
            "Normalisation du contenu non disponible pour le tri.",
        )
    proposal = build_sort_proposal(
        normalized.payload,
        source_normalization_artifact_id=normalized.artifact["id"],
    )
    if decision == "tri_region_departement" and not proposal["can_sort"]:
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_COLUMNS_NOT_CLEAR",
            "Les colonnes de tri ne sont pas détectées clairement.",
            details={"warning_code": proposal["warning_code"]},
        )

    payload = build_sort_decision_payload(normalized.payload, proposal, decision)
    content = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
    )
    run_id = f"run_{uuid.uuid4().hex}"
    repositories.jobs.cancel_active_for_step(lot_id, SORT_STEP_KEY)
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(SORT_STEP_KEY,),
    )
    repositories.artifacts.mark_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(SORT_STEP_KEY,),
    )
    repositories.steps.prepare_run(
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        input_fingerprint=input_fingerprint,
    )
    transition_step(
        repositories,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        status="en_cours",
        run_id=run_id,
    )
    job = repositories.jobs.create_owned_running(
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        idempotency_key=idempotency_key,
        lease_owner=SORT_API_WORKER_ID,
        lease_seconds=settings.worker_lease_ttl_seconds,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        event_type="job.started",
        payload={"status": "en_cours", "step_key": SORT_STEP_KEY},
    )

    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    artifact = store.put_temp_then_commit(
        repositories,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        kind=SORT_ARTIFACT_KIND,
        role=SORT_ARTIFACT_ROLE,
        filename="tri-region-departement.json",
        content=content,
        metadata={
            "decision": decision,
            "detection_status": proposal["detection_status"],
            "rows_count": payload["rows_count"],
            "rules_version": SORT_RULES_VERSION,
            "schema_version": SORT_SCHEMA_VERSION,
            "source_normalization_artifact_id": normalized.artifact["id"],
        },
        mime_type=SORT_MIME_TYPE,
        lease_version=int(job["lease_version"]),
    )
    finished = repositories.jobs.finish_owned(
        job_id=job["id"],
        worker_id=SORT_API_WORKER_ID,
        run_id=run_id,
        lease_version=int(job["lease_version"]),
        status="succeeded",
        expected_input_fingerprint=input_fingerprint,
    )
    if finished is None:
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_COMMIT_REJECTED",
            "La décision de tri n'est plus courante.",
        )

    snapshot = record_human_validation_snapshot(
        repositories,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        decision_payload={
            "artifact_id": artifact["id"],
            "decision": decision,
            "detection_status": proposal["detection_status"],
            "rules_version": SORT_RULES_VERSION,
            "schema_version": SORT_SCHEMA_VERSION,
            "sha256": artifact["sha256"],
            "source_normalization_artifact_id": normalized.artifact["id"],
        },
        reason="sort_decision_validated",
    )
    warning_code = _warning_code_for_decision(proposal, decision)
    if warning_code:
        _record_sort_warning(repositories, lot_id=lot_id, run_id=run_id, code=warning_code)
    complete_step(
        repositories,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        with_warnings=warning_code is not None,
    )
    from sircom2026.csv_preview import require_csv_preview_validation_if_ready

    require_csv_preview_validation_if_ready(repositories, lot_id=lot_id)
    repositories.events.create(
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        event_type="sort.validated",
        payload={
            "artifact_id": artifact["id"],
            "rows_count": payload["rows_count"],
            "status": "termine_avec_alertes" if warning_code else "termine",
            "step_key": SORT_STEP_KEY,
            "warning_code": warning_code,
        },
    )

    return SortDecisionResult(
        decision=payload,
        artifact=artifact,
        lot=get_lot_detail(repositories, lot_id),
        invalidated_steps=snapshot.invalidated_steps,
    )


def build_sort_proposal(
    normalized_payload: dict[str, Any],
    *,
    source_normalization_artifact_id: str | None = None,
) -> dict[str, Any]:
    columns = [dict(column) for column in normalized_payload.get("columns", [])]
    region_columns = _columns_with_role(columns, "region")
    department_columns = _columns_with_role(columns, "departement")
    if len(region_columns) == 1 and len(department_columns) == 1:
        detection_status = "detected"
    elif len(region_columns) > 1 or len(department_columns) > 1:
        detection_status = "ambiguous"
    else:
        detection_status = "missing"
    can_sort = detection_status == "detected"
    region_column = region_columns[0] if len(region_columns) == 1 else None
    department_column = department_columns[0] if len(department_columns) == 1 else None
    warning_code = None if can_sort else SORT_WARNING_CODES[detection_status]
    return {
        "schema_version": SORT_SCHEMA_VERSION,
        "rules_version": SORT_RULES_VERSION,
        "source_normalization_artifact_id": source_normalization_artifact_id,
        "detection_status": detection_status,
        "can_sort": can_sort,
        "default_decision": "tri_region_departement" if can_sort else "ordre_source",
        "warning_code": warning_code,
        "region_column": _public_column(region_column) if region_column else None,
        "department_column": _public_column(department_column) if department_column else None,
        "region_candidates": [_public_column(column) for column in region_columns],
        "department_candidates": [_public_column(column) for column in department_columns],
        "preview_rows": _preview_rows(
            normalized_payload.get("rows", []),
            region_column=region_column,
            department_column=department_column,
        ),
    }


def build_sort_decision_payload(
    normalized_payload: dict[str, Any],
    proposal: dict[str, Any],
    decision: str,
) -> dict[str, Any]:
    columns = [dict(column) for column in normalized_payload.get("columns", [])]
    rows = [
        dict(row)
        for row in normalized_payload.get("rows", [])
        if isinstance(row, dict)
    ]
    if decision == "tri_region_departement":
        region_name = proposal["region_column"]["csv_name"]
        department_name = proposal["department_column"]["csv_name"]
        ordered_rows = sorted(
            rows,
            key=lambda row: (
                _sort_value(row, region_name),
                _sort_value(row, department_name),
                _source_rank(row),
            ),
        )
    else:
        ordered_rows = sorted(rows, key=_source_rank)
    return {
        "schema_version": SORT_SCHEMA_VERSION,
        "rules_version": SORT_RULES_VERSION,
        "source_normalization_artifact_id": proposal["source_normalization_artifact_id"],
        "source_normalization_rules_version": normalized_payload.get("rules_version"),
        "structural_fingerprint": normalized_payload.get("structural_fingerprint"),
        "decision": decision,
        "detection_status": proposal["detection_status"],
        "warning_code": _warning_code_for_decision(proposal, decision),
        "confirmed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "columns_count": len(columns),
        "rows_count": len(ordered_rows),
        "removed_empty_columns_count": normalized_payload.get("removed_empty_columns_count", 0),
        "removed_empty_columns": normalized_payload.get("removed_empty_columns", []),
        "upstream_removed_empty_columns_count": normalized_payload.get(
            "upstream_removed_empty_columns_count",
            0,
        ),
        "upstream_removed_empty_columns": normalized_payload.get(
            "upstream_removed_empty_columns",
            [],
        ),
        "upstream_removed_rows_without_id_count": normalized_payload.get(
            "upstream_removed_rows_without_id_count",
            0,
        ),
        "upstream_removed_rows_without_id": normalized_payload.get(
            "upstream_removed_rows_without_id",
            [],
        ),
        "columns": [_public_column(column) for column in columns],
        "rows": ordered_rows,
        "sort": {
            "region_column": proposal["region_column"],
            "department_column": proposal["department_column"],
            "comparator": "case_accents_ignored_empty_last_source_rank_tiebreaker",
        },
    }


def _existing_sort_decision(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    decision: str,
    idempotency_key: str,
) -> CurrentJsonArtifact | None:
    existing_job = repositories.jobs.get_by_idempotency_key(
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        idempotency_key=idempotency_key,
    )
    if existing_job is None:
        return None
    if existing_job["status"] != "succeeded":
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_ALREADY_SUBMITTED",
            "Cette décision de tri est déjà en cours de traitement.",
        )
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=existing_job["run_id"],
        role=SORT_ARTIFACT_ROLE,
    )
    if artifact is None or artifact["status"] != "committed":
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_ALREADY_SUBMITTED",
            "Cette clé d'idempotence a déjà été utilisée pour une autre décision de tri.",
        )
    payload = _read_json_artifact(repositories, settings=settings, lot_id=lot_id, artifact=artifact)
    if payload.get("decision") != decision:
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_IDEMPOTENCY_REUSED",
            "Cette clé d'idempotence a déjà été utilisée pour une autre décision de tri.",
        )
    return CurrentJsonArtifact(artifact=artifact, payload=payload)


def _current_normalization_artifact(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> CurrentJsonArtifact | None:
    return _current_step_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        step_key=NORMALIZATION_STEP_KEY,
        role=NORMALIZATION_ARTIFACT_ROLE,
        ready_statuses=("termine", "termine_avec_alertes"),
    )


def _current_sort_artifact(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> CurrentJsonArtifact | None:
    return _current_step_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        role=SORT_ARTIFACT_ROLE,
        ready_statuses=("termine", "termine_avec_alertes"),
    )


def _current_step_artifact(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    step_key: str,
    role: str,
    ready_statuses: tuple[str, ...],
) -> CurrentJsonArtifact | None:
    repositories.lots.get_required(lot_id)
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
    payload = _read_json_artifact(repositories, settings=settings, lot_id=lot_id, artifact=artifact)
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
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_ARTIFACT_UNAVAILABLE",
            "Un artefact nécessaire au tri est indisponible.",
        ) from exc
    if not isinstance(payload, dict):
        raise SortDecisionError(
            409,
            "SIRCOM_SORT_ARTIFACT_INVALID",
            "Un artefact nécessaire au tri est invalide.",
        )
    return payload


def _columns_with_role(columns: list[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    return [column for column in columns if column.get("logical_role") == role]


def _preview_rows(
    rows: Any,
    *,
    region_column: dict[str, Any] | None,
    department_column: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    region_name = region_column["csv_name"] if region_column else None
    department_name = department_column["csv_name"] if department_column else None
    for row in rows[:10] if isinstance(rows, list) else []:
        values = row.get("values") if isinstance(row, dict) and isinstance(row.get("values"), dict) else {}
        preview.append(
            {
                "id_dossier": row.get("id_dossier"),
                "source_rank": row.get("source_rank"),
                "region": values.get(region_name, "") if region_name else "",
                "departement": values.get(department_name, "") if department_name else "",
            }
        )
    return preview


def _sort_value(row: dict[str, Any], csv_name: str) -> tuple[int, str]:
    values = row.get("values") if isinstance(row.get("values"), dict) else {}
    raw = values.get(csv_name, "")
    text = "" if raw is None else str(raw).strip()
    if not text:
        return (1, "")
    return (0, _fold_for_sort(text))


def _fold_for_sort(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(character for character in ascii_text if not unicodedata.combining(character))
    return " ".join(ascii_text.casefold().split())


def _source_rank(row: dict[str, Any]) -> int:
    try:
        return int(row.get("source_rank") or 0)
    except (TypeError, ValueError):
        return 0


def _public_column(column: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": column["id"],
        "system": bool(column.get("system")),
        "source_sheet": column.get("source_sheet"),
        "source_column_letter": column.get("source_column_letter"),
        "source_header": column.get("source_header"),
        "logical_role": column.get("logical_role"),
        "csv_name": column["csv_name"],
        "output_position": column.get("output_position"),
    }


def _warning_code_for_decision(proposal: dict[str, Any], decision: str) -> str | None:
    if decision != "ordre_source":
        return None
    return proposal["warning_code"] if proposal["detection_status"] != "detected" else None


def _record_sort_warning(
    repositories: Repositories,
    *,
    lot_id: str,
    run_id: str,
    code: str,
) -> None:
    if code == "SIRCOM_SORT_COLUMNS_AMBIGUOUS":
        title = "Colonnes de tri ambiguës"
        cause = "Plusieurs colonnes région ou département sont candidates pour le tri."
        action = "Corriger les rôles du mapping si un tri région/département doit être appliqué."
    else:
        title = "Colonnes de tri non détectées"
        cause = "Les colonnes région et département ne sont pas détectées clairement."
        action = "Confirmer la conservation de l'ordre source ou corriger les rôles du mapping."
    record_problem(
        repositories,
        lot_id=lot_id,
        step_key=SORT_STEP_KEY,
        run_id=run_id,
        severity="alerte",
        code=code,
        title=title,
        cause=cause,
        action=action,
    )


def _require_mutable_lot(repositories: Repositories, lot_id: str) -> dict[str, Any]:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise SortDecisionError(
            409,
            "SIRCOM_LOT_NOT_MUTABLE",
            "Lot non modifiable.",
        )
    return lot
