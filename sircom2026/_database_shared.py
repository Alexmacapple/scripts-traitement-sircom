from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any


SCHEMA_VERSION = 5

LOT_STATUSES = (
    "brouillon",
    "en_cours",
    "action_requise",
    "bloque",
    "termine",
    "termine_avec_alertes",
    "echoue",
    "annule",
    "supprime",
    "purge",
)
STEP_STATUSES = (
    "non_demarre",
    "pret",
    "en_cours",
    "action_requise",
    "bloque",
    "termine",
    "termine_avec_alertes",
    "echoue",
    "ignore",
    "annule",
    "invalide",
)
JOB_STATUSES = ("queued", "leased", "running", "succeeded", "failed", "canceled", "expired")
ARTIFACT_STATUSES = ("pending", "committed", "obsolete", "deleted", "quarantined")
PROBLEM_SEVERITIES = ("bloquant", "alerte", "information")
PROBLEM_STATUSES = ("open", "resolved", "obsolete")
EVENT_LEVELS = ("info", "warning", "error")
LOT_WRITE_BLOCKED_STATUSES = ("annule", "supprime", "purge")
MANAGED_TABLES = (
    "lots",
    "etapes",
    "jobs",
    "artefacts",
    "evenements",
    "problemes",
    "purge_traces",
)
EXPECTED_TABLE_COLUMNS = {
    "lots": {
        "id",
        "created_at",
        "updated_at",
        "status",
        "title",
        "idempotency_key",
        "active_run_id",
        "cancel_requested_at",
        "delete_requested_at",
        "deleted_at",
        "purge_requested_at",
        "bytes_uploaded",
        "bytes_artifacts",
        "artifacts_count",
        "problems_open_count",
    },
    "etapes": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "status",
        "current_run_id",
        "input_fingerprint",
        "output_fingerprint",
        "progress_current",
        "progress_total",
        "started_at",
        "finished_at",
        "invalidated_at",
        "summary_json",
    },
    "jobs": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "status",
        "run_id",
        "idempotency_key",
        "lease_owner",
        "lease_version",
        "lease_until",
        "heartbeat_at",
        "attempt",
        "cancel_requested_at",
        "started_at",
        "finished_at",
        "error_code",
        "error_message",
    },
    "artefacts": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "run_id",
        "status",
        "kind",
        "role",
        "relative_path",
        "sha256",
        "size_bytes",
        "schema_version",
        "mime_type",
        "metadata_json",
        "committed_at",
        "obsoleted_at",
        "deleted_at",
        "quarantined_at",
    },
    "evenements": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "run_id",
        "level",
        "event_type",
        "payload_json",
    },
    "problemes": {
        "id",
        "created_at",
        "updated_at",
        "lot_id",
        "step_key",
        "run_id",
        "severity",
        "code",
        "title",
        "cause",
        "message",
        "action",
        "location_json",
        "technical_json",
        "status",
        "resolved_at",
    },
    "purge_traces": {
        "id",
        "created_at",
        "updated_at",
        "lot_id_hash",
        "lot_created_at",
        "lot_deleted_at",
        "purged_at",
        "final_status",
        "trace_json",
        "trace_schema_version",
    },
}
EXPECTED_INDEXES = {
    "idx_lots_idempotency_key",
    "idx_etapes_lot_status",
    "idx_jobs_status_lease",
    "idx_jobs_lot_step",
    "idx_jobs_active_lot_step",
    "idx_artefacts_lot_status",
    "idx_artefacts_lot_step_run",
    "idx_evenements_lot_created",
    "idx_problemes_lot_status",
    "idx_purge_traces_purged_at",
}
EXPECTED_FOREIGN_KEY_GROUPS = {
    "etapes": {("lot_id",)},
    "jobs": {("lot_id",), ("lot_id", "step_key")},
    "artefacts": {("lot_id",), ("lot_id", "step_key")},
    "evenements": {("lot_id",), ("lot_id", "step_key")},
    "problemes": {("lot_id",), ("lot_id", "step_key")},
}
TECHNICAL_EVENT_PAYLOAD_KEYS = {
    "artifact_id",
    "artifacts_count",
    "ambiguous_count",
    "code",
    "columns_count",
    "conversion_failed_count",
    "duration_ms",
    "error_code",
    "free_mb",
    "has_image_warnings",
    "job_id",
    "level",
    "lot_id",
    "missing_count",
    "required_mb",
    "run_id",
    "rows_count",
    "rows_removed",
    "size_bytes",
    "status",
    "step_key",
    "steps_total",
    "tolerant_count",
    "warning_code",
    "active_jobs",
    "attempt",
    "input_fingerprint",
    "invalidated_steps_count",
    "lease_version",
    "manual_resolutions_count",
    "obsolete_artifacts_count",
    "output_fingerprint",
    "progress_current",
    "progress_total",
    "processed_images_count",
    "reason",
    "source_step_key",
    "unreferenced_count",
    "worker_id",
}
ACTIVE_JOB_STATUSES = ("queued", "leased", "running")
COMMITTABLE_JOB_STATUSES = ("leased", "running")


def _fetch_one(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
) -> dict[str, Any] | None:
    row = connection.execute(sql, params).fetchone()
    if row is None:
        return None
    return dict(row)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _now_plus(*, seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_technical_payload(payload: Mapping[str, Any]) -> str:
    unknown_keys = set(payload) - TECHNICAL_EVENT_PAYLOAD_KEYS
    if unknown_keys:
        keys = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Event payload contains non-technical keys: {keys}.")

    for key, value in payload.items():
        if not isinstance(value, str | int | float | bool | type(None)):
            raise ValueError(f"Event payload value for {key!r} must be scalar.")
        if isinstance(value, str) and ("/" in value or "\\" in value):
            raise ValueError(f"Event payload value for {key!r} must not contain a path.")

    return _json(payload)


def _check_in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _placeholders(count: int) -> str:
    if count <= 0:
        raise ValueError("count must be greater than 0.")
    return ", ".join("?" for _index in range(count))


def _validate_choice(label: str, value: str, allowed_values: tuple[str, ...]) -> None:
    if value not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValueError(f"Invalid {label}: {value!r}. Allowed values: {allowed}.")
