from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpyxl.utils.cell import column_index_from_string

from sircom2026.artifacts import (
    ArtifactStore,
    ArtifactUnavailableError,
    safe_artifact_filename,
)
from sircom2026.config import Settings
from sircom2026.database import LOT_WRITE_BLOCKED_STATUSES, Repositories
from sircom2026.excel_diagnostic_pipeline import (
    ExcelDiagnosticNotReady,
    get_persisted_excel_diagnostic,
)
from sircom2026.invalidation import (
    fingerprint_payload,
    record_human_validation_snapshot,
    step_input_fingerprint,
)
from sircom2026.mapping_rules import (
    MAPPING_LOGICAL_ROLES,
    MAPPING_RULES_VERSION,
    MAPPING_SCHEMA_VERSION,
    MAPPING_STATUS_VALUES,
    SYSTEM_COLUMN_IDS as SYSTEM_COLUMN_IDS,
    assign_output_positions,
    clean_submitted_csv_name,
    default_csv_name,
    logical_roles_by_letter,
    role_from_header,
    source_column_id,
    structural_payload,
    system_columns,
    useful_sheets,
)
from sircom2026.state import record_problem, require_human_validation, transition_step
from sircom2026.worker import enqueue_job


MAPPING_STEP_KEY = "mapping"
FUSION_STEP_KEY = "fusion_multi_onglets"
MAPPING_MIME_TYPE = "application/json"
MAPPING_API_WORKER_ID = "api"


@dataclass(frozen=True)
class MappingOperationResult:
    mapping: dict[str, Any]
    artifact: dict[str, Any]
    lot: dict[str, Any]
    invalidated_steps: tuple[str, ...] = ()


@dataclass(frozen=True)
class PersistedMappingSnapshot:
    artifact: dict[str, Any]
    created: bool


class MappingError(ValueError):
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


def get_mapping_payload(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any]:
    default_mapping = build_default_mapping_from_current_diagnostic(
        repositories,
        settings=settings,
        lot_id=lot_id,
    )
    mapping = read_current_mapping_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
    )
    if mapping is None:
        mapping = default_mapping

    profiles = MappingProfileStore(settings.data_dir).list_profiles_for(default_mapping)
    return {
        "mapping": mapping,
        "profiles": profiles,
    }


def build_default_mapping_from_current_diagnostic(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> dict[str, Any]:
    try:
        persisted = get_persisted_excel_diagnostic(
            repositories,
            settings=settings,
            lot_id=lot_id,
        )
    except ExcelDiagnosticNotReady as exc:
        raise MappingError(
            409,
            "SIRCOM_MAPPING_DIAGNOSTIC_NOT_READY",
            "Diagnostic Excel non disponible pour le mapping.",
        ) from exc

    diagnostic = persisted.diagnostic
    if not bool(diagnostic.get("importable")):
        raise MappingError(
            409,
            "SIRCOM_MAPPING_DIAGNOSTIC_BLOCKED",
            "Le mapping est indisponible tant que le diagnostic Excel est bloquant.",
        )

    sheets = useful_sheets(diagnostic)
    if any("source_headers" not in sheet for sheet in sheets):
        raise MappingError(
            409,
            "SIRCOM_MAPPING_SOURCE_HEADERS_MISSING",
            "La liste structurée des colonnes est absente du diagnostic Excel.",
        )

    structural = structural_payload(sheets)
    structural_fingerprint = fingerprint_payload(structural)
    columns: list[dict[str, Any]] = []
    exported_id_seen = False

    for sheet in sheets:
        sheet_name = str(sheet["name"])
        role_by_letter = logical_roles_by_letter(sheet)
        for header in sheet["source_headers"]:
            letter = str(header["column"])
            source_header = str(header["header"])
            role = role_by_letter.get(letter) or role_from_header(source_header)
            column_id = source_column_id(sheet_name, letter)
            status = "exporte"
            csv_name = default_csv_name(letter, source_header)
            suppression_reason = None
            if role == "id_dossier":
                if not exported_id_seen:
                    csv_name = "id_dossier"
                    exported_id_seen = True
                else:
                    status = "supprime"
                    csv_name = "id_dossier"
                    suppression_reason = (
                        "Colonne identifiée comme clé primaire dossier utilisée seulement pour la fusion interne."
                    )

            columns.append(
                {
                    "id": column_id,
                    "system": False,
                    "source_sheet": sheet_name,
                    "source_column_index": column_index_from_string(letter),
                    "source_column_letter": letter,
                    "source_header": source_header,
                    "logical_role": role,
                    "status": status,
                    "csv_name": csv_name,
                    "default_csv_name": csv_name,
                    "suppression_reason": suppression_reason,
                    "output_position": None,
                    "locked": role == "id_dossier",
                }
            )
            if status == "exporte" and role == "id_dossier":
                columns.extend(system_columns())

    assign_output_positions(columns)
    return {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "rules_version": MAPPING_RULES_VERSION,
        "source": "default",
        "structural_fingerprint": structural_fingerprint,
        "source_diagnostic_artifact_id": persisted.artifact["id"],
        "sheets": [
            {
                "name": str(sheet["name"]),
                "header_row": sheet.get("header_row"),
                "columns_count": len(sheet.get("source_headers", [])),
            }
            for sheet in sheets
        ],
        "columns": columns,
    }


def save_mapping_draft(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    submission: dict[str, Any],
    idempotency_key: str,
    source: str = "draft",
    profile_id: str | None = None,
) -> MappingOperationResult:
    _require_mutable_lot(repositories, lot_id)
    default_mapping = build_default_mapping_from_current_diagnostic(
        repositories,
        settings=settings,
        lot_id=lot_id,
    )
    mapping = mapping_from_submission(default_mapping, submission)
    mapping["source"] = source
    if profile_id:
        mapping["profile_id"] = profile_id

    persisted = persist_mapping_snapshot(
        repositories,
        settings=settings,
        lot_id=lot_id,
        mapping=mapping,
        role="draft",
        idempotency_key=idempotency_key,
    )
    artifact = persisted.artifact
    if persisted.created:
        require_human_validation(
            repositories,
            lot_id=lot_id,
            step_key=MAPPING_STEP_KEY,
            run_id=artifact["run_id"],
        )
        repositories.events.create(
            lot_id=lot_id,
            step_key=MAPPING_STEP_KEY,
            run_id=artifact["run_id"],
            event_type="mapping.draft_saved",
            payload={
                "artifact_id": artifact["id"],
                "status": "action_requise",
                "step_key": MAPPING_STEP_KEY,
            },
        )
    from sircom2026.lots import get_lot_detail

    return MappingOperationResult(
        mapping=mapping,
        artifact=artifact,
        lot=get_lot_detail(repositories, lot_id),
    )


def validate_mapping(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    submission: dict[str, Any],
    idempotency_key: str,
) -> MappingOperationResult:
    _require_mutable_lot(repositories, lot_id)
    default_mapping = build_default_mapping_from_current_diagnostic(
        repositories,
        settings=settings,
        lot_id=lot_id,
    )
    mapping = mapping_from_submission(default_mapping, submission)
    validation_errors = mapping_validation_errors(mapping)
    if validation_errors:
        block_mapping_validation(repositories, lot_id=lot_id, errors=validation_errors)
        raise validation_errors[0]

    mapping["source"] = "validated"
    persisted = persist_mapping_snapshot(
        repositories,
        settings=settings,
        lot_id=lot_id,
        mapping=mapping,
        role="validated",
        idempotency_key=idempotency_key,
    )
    artifact = persisted.artifact
    invalidated_steps: tuple[str, ...] = ()
    if persisted.created:
        snapshot = record_human_validation_snapshot(
            repositories,
            lot_id=lot_id,
            step_key=MAPPING_STEP_KEY,
            run_id=artifact["run_id"],
            decision_payload={
                "artifact_id": artifact["id"],
                "rules_version": MAPPING_RULES_VERSION,
                "schema_version": MAPPING_SCHEMA_VERSION,
                "sha256": artifact["sha256"],
                "structural_fingerprint": mapping["structural_fingerprint"],
            },
            reason="mapping_validated",
        )
        invalidated_steps = snapshot.invalidated_steps
        transition_step(
            repositories,
            lot_id=lot_id,
            step_key=MAPPING_STEP_KEY,
            status="termine",
            run_id=artifact["run_id"],
            event_type="mapping.validated",
        )
        fusion_input_fingerprint = step_input_fingerprint(
            repositories,
            lot_id=lot_id,
            step_key=FUSION_STEP_KEY,
        )
        enqueue_job(
            repositories,
            lot_id=lot_id,
            step_key=FUSION_STEP_KEY,
            idempotency_key=f"{FUSION_STEP_KEY}:{artifact['id']}",
            input_fingerprint=fusion_input_fingerprint,
        )
    from sircom2026.lots import get_lot_detail

    return MappingOperationResult(
        mapping=mapping,
        artifact=artifact,
        lot=get_lot_detail(repositories, lot_id),
        invalidated_steps=invalidated_steps,
    )


def save_profile_from_validated_mapping(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    name: str | None,
) -> dict[str, Any]:
    _require_mutable_lot(repositories, lot_id)
    mapping = read_current_mapping_artifact(
        repositories,
        settings=settings,
        lot_id=lot_id,
        required_role="validated",
    )
    if mapping is None:
        raise MappingError(
            409,
            "SIRCOM_MAPPING_VALIDATED_NOT_FOUND",
            "Aucun mapping validé ne peut être transformé en profil.",
        )
    profile = MappingProfileStore(settings.data_dir).save_profile(mapping, name=name)
    repositories.events.create(
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        event_type="mapping.profile_saved",
        payload={
            "status": "termine",
            "step_key": MAPPING_STEP_KEY,
        },
    )
    return profile


def apply_profile_as_draft(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    profile_id: str,
    idempotency_key: str,
) -> MappingOperationResult:
    _require_mutable_lot(repositories, lot_id)
    default_mapping = build_default_mapping_from_current_diagnostic(
        repositories,
        settings=settings,
        lot_id=lot_id,
    )
    store = MappingProfileStore(settings.data_dir)
    profile = store.get_profile(profile_id)
    if profile is None:
        raise MappingError(
            404,
            "SIRCOM_MAPPING_PROFILE_NOT_FOUND",
            "Profil de mapping introuvable.",
        )
    compatibility = profile_compatibility(default_mapping, profile)
    if not compatibility["compatible"]:
        raise MappingError(
            409,
            "SIRCOM_MAPPING_PROFILE_INCOMPATIBLE",
            "Le profil ne correspond pas à la structure Excel courante.",
            details={"reasons": compatibility["reasons"]},
        )
    mapping = apply_profile_to_default_mapping(default_mapping, profile)
    result = save_mapping_draft(
        repositories,
        settings=settings,
        lot_id=lot_id,
        submission=mapping,
        idempotency_key=idempotency_key,
        source="profile_draft",
        profile_id=profile["id"],
    )
    store.touch_profile(profile["id"])
    repositories.events.create(
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        run_id=result.artifact["run_id"],
        event_type="mapping.profile_loaded",
        payload={
            "status": "action_requise",
            "step_key": MAPPING_STEP_KEY,
        },
    )
    return result


def _require_mutable_lot(repositories: Repositories, lot_id: str) -> None:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise MappingError(
            409,
            "SIRCOM_LOT_NOT_MUTABLE",
            "Lot non modifiable.",
        )


def mapping_from_submission(
    default_mapping: dict[str, Any],
    submission: dict[str, Any],
) -> dict[str, Any]:
    if (
        submission.get("structural_fingerprint")
        != default_mapping["structural_fingerprint"]
    ):
        raise MappingError(
            409,
            "SIRCOM_MAPPING_STRUCTURE_MISMATCH",
            "Le mapping envoyé ne correspond plus à la structure Excel courante.",
        )

    submitted_columns = submission.get("columns")
    if not isinstance(submitted_columns, list):
        raise MappingError(
            422,
            "SIRCOM_MAPPING_PAYLOAD_INVALID",
            "Le mapping envoyé est incomplet.",
        )
    by_id = {
        str(column.get("id")): column
        for column in submitted_columns
        if isinstance(column, dict) and column.get("id")
    }
    expected_ids = {column["id"] for column in default_mapping["columns"]}
    if set(by_id) != expected_ids:
        raise MappingError(
            422,
            "SIRCOM_MAPPING_COLUMNS_MISMATCH",
            "Les colonnes envoyées ne correspondent pas au diagnostic courant.",
        )

    columns: list[dict[str, Any]] = []
    for default_column in default_mapping["columns"]:
        submitted = by_id[default_column["id"]]
        column = dict(default_column)
        if column["system"]:
            column["status"] = "exporte"
            column["csv_name"] = column["default_csv_name"]
            column["logical_role"] = column["logical_role"]
            column["suppression_reason"] = None
        elif column["logical_role"] == "id_dossier":
            column["status"] = default_column["status"]
            column["csv_name"] = "id_dossier"
            column["suppression_reason"] = default_column["suppression_reason"]
        else:
            status = str(submitted.get("status") or column["status"])
            if status not in MAPPING_STATUS_VALUES:
                raise MappingError(
                    422,
                    "SIRCOM_MAPPING_STATUS_INVALID",
                    "Un statut de colonne mapping est invalide.",
                )
            role = submitted.get("logical_role")
            if role is not None:
                role = str(role).strip() or None
            if role is not None and role not in MAPPING_LOGICAL_ROLES:
                raise MappingError(
                    422,
                    "SIRCOM_MAPPING_ROLE_INVALID",
                    "Un rôle logique de colonne est invalide.",
                )
            column["status"] = status
            column["logical_role"] = role or "texte"
            column["csv_name"] = clean_submitted_csv_name(
                str(submitted.get("csv_name") or column["csv_name"]),
                source_column_letter=column["source_column_letter"],
            )
            reason = submitted.get("suppression_reason")
            column["suppression_reason"] = str(reason).strip() if reason else None
        columns.append(column)

    assign_output_positions(columns)
    mapping = {
        **default_mapping,
        "columns": columns,
    }
    return mapping


def mapping_validation_errors(mapping: dict[str, Any]) -> list[MappingError]:
    errors: list[MappingError] = []
    exported = [
        column for column in mapping["columns"] if column["status"] == "exporte"
    ]
    business_exported = [
        column
        for column in exported
        if not column["system"] and column["logical_role"] != "id_dossier"
    ]
    if not business_exported:
        errors.append(
            MappingError(
                422,
                "SIRCOM_MAPPING_NO_BUSINESS_COLUMN",
                "Aucune colonne métier n'est sélectionnée pour l'export.",
                details={"checks_count": 1},
            )
        )

    csv_names: dict[str, int] = {}
    for column in exported:
        csv_name = str(column["csv_name"]).strip()
        if not csv_name:
            errors.append(
                MappingError(
                    422,
                    "SIRCOM_MAPPING_CSV_NAME_MISSING",
                    "Une colonne exportée n'a pas de nom CSV.",
                    details={"checks_count": 1},
                )
            )
            continue
        csv_names[csv_name] = csv_names.get(csv_name, 0) + 1
    collisions = sorted(name for name, count in csv_names.items() if count > 1)
    if collisions:
        errors.append(
            MappingError(
                422,
                "SIRCOM_MAPPING_CSV_HEADER_COLLISION",
                "Plusieurs colonnes exportées utilisent le même nom CSV.",
                details={
                    "columns_count": sum(csv_names[name] for name in collisions),
                    "warning_code": collisions[0],
                },
            )
        )

    if sum(1 for column in exported if column["csv_name"] == "id_dossier") != 1:
        errors.append(
            MappingError(
                422,
                "SIRCOM_MAPPING_ID_DOSSIER_INVALID",
                "Le mapping doit exporter une seule clé primaire dossier.",
                details={"checks_count": 1},
            )
        )
    return errors


def block_mapping_validation(
    repositories: Repositories,
    *,
    lot_id: str,
    errors: list[MappingError],
) -> None:
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(MAPPING_STEP_KEY,),
    )
    for error in errors:
        record_problem(
            repositories,
            lot_id=lot_id,
            step_key=MAPPING_STEP_KEY,
            severity="bloquant",
            code=error.code,
            title=mapping_error_title(error.code),
            cause=error.message,
            action="Corriger le mapping, puis valider à nouveau.",
            technical=error.details,
        )
    transition_step(
        repositories,
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        status="bloque",
        event_type="step.blocked",
    )


def persist_mapping_snapshot(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    mapping: dict[str, Any],
    role: str,
    idempotency_key: str,
) -> PersistedMappingSnapshot:
    mapping_content = json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    mapping_sha256 = sha256_bytes(mapping_content)
    existing_job = repositories.jobs.get_by_idempotency_key(
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        idempotency_key=idempotency_key,
    )
    if existing_job is not None:
        if existing_job["status"] == "succeeded":
            artifact = repositories.artifacts.get_for_step_run_role(
                lot_id=lot_id,
                step_key=MAPPING_STEP_KEY,
                run_id=existing_job["run_id"],
                role=role,
            )
            if (
                artifact is not None
                and artifact["status"] == "committed"
                and artifact["sha256"] == mapping_sha256
            ):
                return PersistedMappingSnapshot(artifact=artifact, created=False)
        raise MappingError(
            409,
            "SIRCOM_MAPPING_IDEMPOTENCY_REUSED",
            "Cette clé d'idempotence a déjà été utilisée pour une autre action mapping.",
        )

    run_id = f"run_{uuid.uuid4().hex}"
    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
    )
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(MAPPING_STEP_KEY,),
    )
    repositories.artifacts.mark_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(MAPPING_STEP_KEY,),
    )
    repositories.steps.prepare_run(
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        run_id=run_id,
        input_fingerprint=input_fingerprint,
    )
    job = repositories.jobs.create_owned_running(
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        run_id=run_id,
        idempotency_key=idempotency_key,
        lease_owner=MAPPING_API_WORKER_ID,
        lease_seconds=settings.worker_lease_ttl_seconds,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        run_id=run_id,
        event_type="job.started",
        payload={
            "status": "en_cours",
            "step_key": MAPPING_STEP_KEY,
        },
    )
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    artifact = store.put_temp_then_commit(
        repositories,
        lot_id=lot_id,
        step_key=MAPPING_STEP_KEY,
        run_id=run_id,
        kind="json",
        role=role,
        filename=f"mapping-{role}.json",
        content=mapping_content,
        metadata={
            "rules_version": MAPPING_RULES_VERSION,
            "schema_version": MAPPING_SCHEMA_VERSION,
            "source": mapping["source"],
            "structural_fingerprint": mapping["structural_fingerprint"],
        },
        mime_type=MAPPING_MIME_TYPE,
        lease_version=int(job["lease_version"]),
    )
    finished = repositories.jobs.finish_owned(
        job_id=job["id"],
        worker_id=MAPPING_API_WORKER_ID,
        run_id=run_id,
        lease_version=int(job["lease_version"]),
        status="succeeded",
        expected_input_fingerprint=input_fingerprint,
    )
    if finished is None:
        raise MappingError(
            409,
            "SIRCOM_MAPPING_COMMIT_REJECTED",
            "Le snapshot de mapping n'est plus courant.",
        )
    return PersistedMappingSnapshot(artifact=artifact, created=True)


def read_current_mapping_artifact(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    required_role: str | None = None,
) -> dict[str, Any] | None:
    roles = (required_role,) if required_role else ("validated", "draft")
    role_filter = ",".join("?" for _ in roles)
    row = repositories.connection.execute(
        f"""
        SELECT * FROM artefacts
        WHERE lot_id = ?
          AND step_key = ?
          AND status = 'committed'
          AND role IN ({role_filter})
        ORDER BY committed_at DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (lot_id, MAPPING_STEP_KEY, *roles),
    ).fetchone()
    if row is None:
        return None
    artifact = dict(row)
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
        mapping = json.loads(readable.path.read_text(encoding="utf-8"))
    except (
        ArtifactUnavailableError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
    ) as exc:
        raise MappingError(
            409,
            "SIRCOM_MAPPING_ARTIFACT_UNAVAILABLE",
            "Le snapshot de mapping courant est indisponible.",
        ) from exc
    if not isinstance(mapping, dict):
        raise MappingError(
            409,
            "SIRCOM_MAPPING_ARTIFACT_INVALID",
            "Le snapshot de mapping courant est invalide.",
        )
    return mapping


def apply_profile_to_default_mapping(
    default_mapping: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    profile_columns = {
        str(column.get("id")): column
        for column in profile.get("columns", [])
        if isinstance(column, dict) and column.get("id")
    }
    submitted = {
        "structural_fingerprint": default_mapping["structural_fingerprint"],
        "columns": [
            {
                "id": column["id"],
                "status": profile_columns.get(column["id"], {}).get(
                    "status", column["status"]
                ),
                "csv_name": profile_columns.get(column["id"], {}).get(
                    "csv_name", column["csv_name"]
                ),
                "logical_role": profile_columns.get(column["id"], {}).get(
                    "logical_role",
                    column["logical_role"],
                ),
                "suppression_reason": profile_columns.get(column["id"], {}).get(
                    "suppression_reason",
                    column["suppression_reason"],
                ),
            }
            for column in default_mapping["columns"]
        ],
    }
    return mapping_from_submission(default_mapping, submitted)


def profile_compatibility(
    default_mapping: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if profile.get("version") != MAPPING_SCHEMA_VERSION:
        reasons.append("Version de profil incompatible.")
    if profile.get("rules_version") != MAPPING_RULES_VERSION:
        reasons.append("Version des règles de mapping différente.")
    if (
        profile.get("structural_fingerprint")
        != default_mapping["structural_fingerprint"]
    ):
        reasons.append("Structure Excel différente.")
    return {
        "compatible": not reasons,
        "reasons": reasons,
    }


def profile_from_mapping(
    mapping: dict[str, Any],
    *,
    name: str | None,
    profile_id: str | None = None,
    last_used_at: str | None = None,
) -> dict[str, Any]:
    columns = [
        {
            "id": column["id"],
            "status": column["status"],
            "csv_name": column["csv_name"],
            "logical_role": column["logical_role"],
            "suppression_reason": column["suppression_reason"],
        }
        for column in mapping["columns"]
    ]
    source_columns = [column for column in mapping["columns"] if not column["system"]]
    return {
        "id": profile_id or f"profile_{uuid.uuid4().hex}",
        "name": clean_profile_name(name),
        "version": MAPPING_SCHEMA_VERSION,
        "rules_version": MAPPING_RULES_VERSION,
        "structural_fingerprint": mapping["structural_fingerprint"],
        "sheets": list(mapping["sheets"]),
        "headers": [
            {
                "sheet": column["source_sheet"],
                "letter": column["source_column_letter"],
                "header": column["source_header"],
            }
            for column in source_columns
        ],
        "letters": [
            f"{column['source_sheet']}!{column['source_column_letter']}"
            for column in source_columns
        ],
        "logical_roles": {
            column["id"]: column["logical_role"] for column in mapping["columns"]
        },
        "columns": columns,
        "last_used_at": last_used_at or now_iso(),
    }


class MappingProfileStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "profiles" / "mapping"

    def list_profiles_for(
        self, default_mapping: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        compatible: list[dict[str, Any]] = []
        incompatible: list[dict[str, Any]] = []
        for profile in self.list_profiles():
            compatibility = profile_compatibility(default_mapping, profile)
            item = profile_summary(profile, compatibility)
            if compatibility["compatible"]:
                compatible.append(item)
            else:
                incompatible.append(item)
        return {
            "compatible": compatible,
            "incompatible": incompatible,
        }

    def list_profiles(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        profiles: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and isinstance(payload.get("id"), str):
                profiles.append(payload)
        return sorted(
            profiles,
            key=lambda profile: str(profile.get("last_used_at", "")),
            reverse=True,
        )

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        safe_id = safe_profile_id(profile_id)
        path = self.root / f"{safe_id}.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def save_profile(
        self, mapping: dict[str, Any], *, name: str | None
    ) -> dict[str, Any]:
        profile = profile_from_mapping(mapping, name=name)
        self._write_profile(profile)
        return profile

    def touch_profile(self, profile_id: str) -> None:
        profile = self.get_profile(profile_id)
        if profile is None:
            return
        profile["last_used_at"] = now_iso()
        self._write_profile(profile)

    def _write_profile(self, profile: dict[str, Any]) -> None:
        safe_id = safe_profile_id(str(profile["id"]))
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{safe_id}.json"
        tmp_path = self.root / f".{safe_id}.{uuid.uuid4().hex}.tmp"
        content = json.dumps(
            profile,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)


def profile_summary(
    profile: dict[str, Any], compatibility: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": profile["id"],
        "name": profile.get("name") or profile["id"],
        "last_used_at": profile.get("last_used_at"),
        "compatible": compatibility["compatible"],
        "reasons": compatibility["reasons"],
    }


def clean_profile_name(name: str | None) -> str:
    if not name:
        return "Profil mapping"
    cleaned = " ".join(str(name).split())
    return cleaned[:120] or "Profil mapping"


def safe_profile_id(profile_id: str) -> str:
    filename = safe_artifact_filename(profile_id)
    return Path(filename).stem


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def mapping_error_title(code: str) -> str:
    return {
        "SIRCOM_MAPPING_CSV_HEADER_COLLISION": "Collision de noms CSV",
        "SIRCOM_MAPPING_NO_BUSINESS_COLUMN": "Aucune colonne métier exportée",
        "SIRCOM_MAPPING_CSV_NAME_MISSING": "Nom CSV manquant",
        "SIRCOM_MAPPING_ID_DOSSIER_INVALID": "Clé primaire dossier invalide",
    }.get(code, "Mapping invalide")
