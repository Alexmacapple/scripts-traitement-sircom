from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sircom2026.database import Repositories


@dataclass(frozen=True)
class StepDefinition:
    key: str
    label: str


LOT_STATUS_LABELS = {
    "brouillon": "Brouillon",
    "en_cours": "En cours",
    "action_requise": "Action requise",
    "bloque": "Bloqué",
    "termine": "Terminé",
    "termine_avec_alertes": "Terminé avec alertes",
    "echoue": "Échoué",
    "annule": "Annulé",
    "supprime": "Supprimé",
    "purge": "Purgé",
}
STEP_STATUS_LABELS = {
    "non_demarre": "Non démarrée",
    "pret": "Prête",
    "en_cours": "En cours",
    "action_requise": "Action requise",
    "bloque": "Bloquée",
    "termine": "Terminée",
    "termine_avec_alertes": "Terminée avec alertes",
    "echoue": "Échouée",
    "ignore": "Ignorée",
    "annule": "Annulée",
    "invalide": "Invalidée",
}
V1_STEPS = (
    StepDefinition("upload_excel", "Déposer l'Excel"),
    StepDefinition("diagnostic_excel", "Diagnostiquer l'Excel"),
    StepDefinition("mapping", "Valider le mapping"),
    StepDefinition("fusion_multi_onglets", "Fusionner les onglets"),
    StepDefinition("normalisation_contenu", "Normaliser le contenu"),
    StepDefinition("tri_region_departement", "Valider le tri région/département"),
    StepDefinition("verification_csv_indesign", "Vérifier le contrat CSV InDesign"),
    StepDefinition("previsualisation_csv", "Prévisualiser le CSV"),
    StepDefinition("upload_images", "Déposer le zip images"),
    StepDefinition("inspection_images", "Inspecter les images"),
    StepDefinition("matching_images", "Associer les images"),
    StepDefinition("rapports", "Générer les rapports"),
    StepDefinition("package_final", "Préparer le package final"),
)
STEP_DEFINITIONS_BY_KEY = {step.key: step for step in V1_STEPS}
STEP_ORDER = {step.key: index for index, step in enumerate(V1_STEPS)}
STEP_DONE_STATUSES = {"termine", "termine_avec_alertes", "ignore"}
PROBLEM_SEVERITY_LABELS = {
    "bloquant": "Bloquant",
    "alerte": "Alerte",
    "information": "Information",
}
PROBLEM_ALERT_CLASSES = {
    "bloquant": "error",
    "alerte": "warning",
    "information": "info",
}
EVENT_LEVEL_LABELS = {
    "info": "Information",
    "warning": "Alerte",
    "error": "Erreur",
}
EVENT_TYPE_LABELS = {
    "excel.uploaded": "Excel déposé",
    "lot.created": "Lot créé",
    "lot.deleted": "Suppression logique demandée",
    "artifact.commit_rejected": "Commit d'artefact refusé",
    "job.acquired": "Job pris par le worker",
    "job.canceled": "Job annulé",
    "job.finish_rejected": "Fin de job refusée",
    "job.progress": "Progression du job",
    "job.queued": "Job ajouté à la file",
    "job.started": "Job démarré",
    "job.succeeded": "Job terminé",
    "lot.cancel_requested": "Annulation du lot demandée",
    "problem.recorded": "Problème enregistré",
    "retry.requested": "Relance demandée",
    "step.input_changed": "Input modifié",
    "step.invalidated": "Étape invalidée",
    "step.ready": "Étape prête",
    "step.status_changed": "Statut d'étape modifié",
    "step.validation_snapshot_frozen": "Validation figée",
    "step.completed": "Étape terminée",
    "step.validation_required": "Validation humaine attendue",
    "step.blocked": "Étape bloquée",
    "step.failed": "Étape échouée",
    "step.canceled": "Étape annulée",
}
VISIBLE_TECHNICAL_DETAIL_KEYS = {
    "active_jobs",
    "actual_sha256",
    "artifact_id",
    "artifacts_count",
    "checks_count",
    "code",
    "columns_count",
    "duplicates_count",
    "duration_ms",
    "error_code",
    "expected_sha256",
    "free_mb",
    "hidden_columns",
    "required_mb",
    "rows_count",
    "rows_removed",
    "size_bytes",
    "status",
    "step_key",
    "warning_code",
}


def create_lot_with_steps(
    repositories: Repositories,
    *,
    title: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if idempotency_key is not None:
        existing_lot = repositories.lots.get_by_idempotency_key(idempotency_key)
        if existing_lot is not None:
            return get_lot_detail(repositories, existing_lot["id"])

    lot = repositories.lots.create(
        title=clean_lot_title(title),
        idempotency_key=idempotency_key,
    )
    for step in V1_STEPS:
        repositories.steps.create(lot_id=lot["id"], step_key=step.key)
    repositories.events.create(
        lot_id=lot["id"],
        event_type="lot.created",
        payload={
            "lot_id": lot["id"],
            "steps_total": len(V1_STEPS),
            "status": lot["status"],
        },
    )
    return get_lot_detail(repositories, lot["id"])


def get_lot_detail(repositories: Repositories, lot_id: str) -> dict[str, Any]:
    lot = repositories.lots.get_required(lot_id)
    steps = repositories.steps.list_for_lot(lot_id)
    problems = repositories.problems.list_for_lot(lot_id)
    events = repositories.events.list_for_lot(lot_id)
    return serialize_lot(lot, steps=steps, problems=problems, events=events)


def list_lots(
    repositories: Repositories,
    *,
    include_deleted: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    lots = repositories.lots.list(
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    total = repositories.lots.count(include_deleted=include_deleted)
    return {
        "items": [serialize_lot_summary(lot) for lot in lots],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
        },
    }


def mark_lot_deleted(repositories: Repositories, lot_id: str) -> tuple[dict[str, Any], int]:
    existing_lot = repositories.lots.get_required(lot_id)
    if existing_lot["status"] in {"supprime", "purge"}:
        return get_lot_detail(repositories, lot_id), 0

    active_job_count = repositories.jobs.count_active_for_lot(lot_id)
    if active_job_count:
        repositories.jobs.request_cancel_for_lot(lot_id)
    lot = repositories.lots.mark_deleted(lot_id)
    repositories.events.create(
        lot_id=lot["id"],
        event_type="lot.deleted",
        payload={
            "lot_id": lot["id"],
            "active_jobs": active_job_count,
            "status": lot["status"],
        },
    )
    return get_lot_detail(repositories, lot_id), active_job_count


def serialize_lot(
    lot: dict[str, Any],
    *,
    steps: list[dict[str, Any]],
    problems: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    serialized_steps = [serialize_step(step) for step in sorted_steps(steps)]
    serialized_problems = [serialize_problem(problem) for problem in problems or []]
    serialized_events = [serialize_event(event) for event in events or []]
    return {
        **serialize_lot_summary(lot),
        "steps": serialized_steps,
        "problems": serialized_problems,
        "problem_groups": group_problems_by_severity(serialized_problems),
        "events": serialized_events,
        "counters": {
            **lot_counters(lot),
            "steps_total": len(serialized_steps),
            "steps_done": sum(
                1
                for step in serialized_steps
                if step["status"] in STEP_DONE_STATUSES
            ),
        },
    }


def serialize_lot_summary(lot: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": lot["id"],
        "title": lot["title"],
        "status": lot["status"],
        "status_label": LOT_STATUS_LABELS.get(lot["status"], lot["status"]),
        "created_at": lot["created_at"],
        "updated_at": lot["updated_at"],
        "deleted_at": lot["deleted_at"],
        "counters": lot_counters(lot),
        "actions": {
            "can_delete": lot["status"] not in {"supprime", "purge"},
        },
    }


def serialize_step(step: dict[str, Any]) -> dict[str, Any]:
    definition = STEP_DEFINITIONS_BY_KEY.get(step["step_key"])
    return {
        "id": step["id"],
        "key": step["step_key"],
        "label": definition.label if definition else step["step_key"],
        "status": step["status"],
        "status_label": STEP_STATUS_LABELS.get(step["status"], step["status"]),
        "progress": {
            "current": step["progress_current"],
            "total": step["progress_total"],
        },
        "started_at": step["started_at"],
        "finished_at": step["finished_at"],
        "invalidated_at": step["invalidated_at"],
        "fingerprints": {
            "input": step["input_fingerprint"],
            "output": step["output_fingerprint"],
        },
        "actions": {
            "can_retry": step["status"] in {"echoue", "bloque", "invalide"},
        },
    }


def serialize_problem(problem: dict[str, Any]) -> dict[str, Any]:
    location = _json_dict(problem["location_json"])
    technical = scrub_technical_details(_json_dict(problem["technical_json"]))
    return {
        "id": problem["id"],
        "step_key": problem["step_key"],
        "step_label": step_label(problem["step_key"]),
        "run_id": problem["run_id"],
        "severity": problem["severity"],
        "severity_label": PROBLEM_SEVERITY_LABELS.get(problem["severity"], problem["severity"]),
        "alert_class": PROBLEM_ALERT_CLASSES.get(problem["severity"], "info"),
        "code": problem["code"],
        "title": problem["title"],
        "cause": problem["cause"],
        "message": problem["message"],
        "action": problem["action"],
        "location": location,
        "location_label": format_location(location),
        "technical": technical,
        "technical_items": sorted(technical.items()),
        "status": problem["status"],
        "created_at": problem["created_at"],
    }


def group_problems_by_severity(
    problems: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    groups = {
        severity: {
            "severity": severity,
            "label": PROBLEM_SEVERITY_LABELS[severity],
            "alert_class": PROBLEM_ALERT_CLASSES[severity],
            "items": [],
        }
        for severity in ("bloquant", "alerte", "information")
    }
    for problem in problems:
        groups[problem["severity"]]["items"].append(problem)
    return groups


def serialize_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = _json_dict(event["payload_json"])
    event_step_key = event["step_key"] or payload.get("step_key")
    return {
        "id": event["id"],
        "created_at": event["created_at"],
        "step_key": event_step_key,
        "step_label": step_label(event_step_key) if isinstance(event_step_key, str) else None,
        "run_id": event["run_id"],
        "level": event["level"],
        "level_label": EVENT_LEVEL_LABELS.get(event["level"], event["level"]),
        "event_type": event["event_type"],
        "label": EVENT_TYPE_LABELS.get(event["event_type"], "Événement technique"),
        "summary": format_event_payload(payload),
    }


def sorted_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(steps, key=lambda step: (STEP_ORDER.get(step["step_key"], 999), step["id"]))


def lot_counters(lot: dict[str, Any]) -> dict[str, int]:
    return {
        "artifacts_count": lot["artifacts_count"],
        "problems_open_count": lot["problems_open_count"],
        "bytes_uploaded": lot["bytes_uploaded"],
        "bytes_artifacts": lot["bytes_artifacts"],
    }


def clean_lot_title(title: str | None) -> str | None:
    if title is None:
        return None
    stripped = " ".join(title.split())
    return stripped or None


def step_label(step_key: str) -> str:
    definition = STEP_DEFINITIONS_BY_KEY.get(step_key)
    return definition.label if definition else step_key


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def scrub_technical_details(payload: dict[str, Any]) -> dict[str, Any]:
    scrubbed: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in VISIBLE_TECHNICAL_DETAIL_KEYS:
            continue
        if isinstance(value, str | int | float | bool) or value is None:
            scrubbed[key] = value
    return scrubbed


def format_location(location: dict[str, Any]) -> str:
    parts: list[str] = []
    sheet = location.get("onglet") or location.get("sheet")
    column = location.get("colonne") or location.get("column") or location.get("column_letter")
    row = location.get("ligne") or location.get("row")
    artifact_id = location.get("artifact_id")
    if sheet:
        parts.append(f"Onglet {sheet}")
    if column:
        parts.append(f"Colonne {column}")
    if row:
        parts.append(f"Ligne {row}")
    if artifact_id:
        parts.append(f"Artefact {artifact_id}")
    return ", ".join(parts) if parts else "Non précisé"


def format_event_payload(payload: dict[str, Any]) -> str | None:
    parts: list[str] = []
    status = payload.get("status")
    step_key = payload.get("step_key")
    code = payload.get("code")
    if isinstance(step_key, str):
        parts.append(step_label(step_key))
    if isinstance(status, str):
        parts.append(STEP_STATUS_LABELS.get(status) or LOT_STATUS_LABELS.get(status) or status)
    if isinstance(code, str):
        parts.append(code)
    return " - ".join(parts) if parts else None
