from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field

from sircom2026.api.dependencies import get_database
from sircom2026.api.errors import ApiError
from sircom2026.api.security import AccessAction, ActorContext, require_action
from sircom2026.csv_preview import (
    CsvPreviewError,
    get_csv_export_payload,
    get_csv_preview_payload,
    validate_csv_preview,
)
from sircom2026.database import LOT_WRITE_BLOCKED_STATUSES, Database
from sircom2026.excel_diagnostic_pipeline import (
    ExcelDiagnosticNotReady,
    get_persisted_excel_diagnostic,
)
from sircom2026.excel_upload import ExcelUploadError, upload_excel_for_lot
from sircom2026.image_matching import (
    ImageMatchingNotReady,
    ImageResolutionError,
    get_persisted_image_matching,
    save_image_resolutions,
)
from sircom2026.images import (
    ImageInspectionNotReady,
    ImageZipUploadError,
    get_persisted_image_inspection,
    prepare_image_zip_artifact_for_commit,
    prepare_image_zip_upload_temp,
    upload_prepared_image_zip_for_lot,
)
from sircom2026.invalidation import RetryNotAllowedError, UnknownStepError, retry_step
from sircom2026.lots import (
    create_lot_with_steps,
    get_lot_detail,
    group_problems_by_severity,
    list_lots,
    serialize_problem,
)
from sircom2026.mapping import (
    MappingError,
    apply_profile_as_draft,
    get_mapping_payload,
    save_mapping_draft,
    save_profile_from_validated_mapping,
    validate_mapping,
)
from sircom2026.package import (
    PackageError,
    PackageNotReady,
    get_persisted_package,
    request_package_generation,
)
from sircom2026.purge import delete_lot_and_purge_if_idle
from sircom2026.reports import ReportsNotReady, get_persisted_reports
from sircom2026.sorting import (
    SortDecisionError,
    get_sort_payload,
    validate_sort_decision,
)


router = APIRouter(prefix="/api/lots", tags=["lots"])

PERSISTED_MAPPING_VALIDATION_ERROR_CODES = {
    "SIRCOM_MAPPING_CSV_HEADER_COLLISION",
    "SIRCOM_MAPPING_CSV_NAME_MISSING",
    "SIRCOM_MAPPING_ID_DOSSIER_INVALID",
    "SIRCOM_MAPPING_NO_BUSINESS_COLUMN",
}


class CreateLotRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class RetryStepRequest(BaseModel):
    step_key: str = Field(min_length=1, max_length=64)


class MappingColumnRequest(BaseModel):
    id: str = Field(min_length=1, max_length=240)
    status: str = Field(min_length=1, max_length=16)
    csv_name: str | None = Field(default=None, max_length=128)
    logical_role: str | None = Field(default=None, max_length=64)
    suppression_reason: str | None = Field(default=None, max_length=240)


class MappingSubmissionRequest(BaseModel):
    structural_fingerprint: str = Field(min_length=64, max_length=64)
    columns: list[MappingColumnRequest]


class SaveMappingProfileRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)


class ApplyMappingProfileRequest(BaseModel):
    profile_id: str = Field(min_length=1, max_length=160)


class SortDecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=32)


class ImageResolutionItemRequest(BaseModel):
    id_dossier: str = Field(min_length=1, max_length=120)
    source_name: str = Field(min_length=1, max_length=240)


class ImageResolutionSubmissionRequest(BaseModel):
    resolutions: list[ImageResolutionItemRequest] = Field(min_length=1, max_length=200)


class PackageGenerationRequest(BaseModel):
    accept_warnings: bool = False


@router.post("", status_code=201)
async def create_lot(
    response: Response,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_CREATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[CreateLotRequest | None, Body()] = None,
) -> dict[str, object]:
    creation_payload = payload or CreateLotRequest()
    with database.transaction() as repositories:
        lot = create_lot_with_steps(
            repositories,
            title=creation_payload.title,
            idempotency_key=idempotency_key_from_request(request),
        )

    response.headers["Location"] = f"/api/lots/{lot['id']}"
    return {"lot": lot}


@router.post("/{lot_id}/retry", status_code=202)
async def retry_lot_step(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[RetryStepRequest, Body()],
) -> dict[str, object]:
    idempotency_key = idempotency_key_from_request(request)
    if idempotency_key is None:
        idempotency_key = f"retry:{payload.step_key}:{uuid.uuid4().hex}"

    with database.transaction() as repositories:
        try:
            result = retry_step(
                repositories,
                lot_id=lot_id,
                step_key=payload.step_key,
                idempotency_key=idempotency_key,
            )
            lot = get_lot_detail(repositories, lot_id)
        except UnknownStepError as exc:
            raise ApiError(
                400,
                "SIRCOM_STEP_INVALID",
                "Etape inconnue.",
            ) from exc
        except RetryNotAllowedError as exc:
            raise ApiError(
                409,
                "SIRCOM_RETRY_NOT_ALLOWED",
                "Relance impossible pour cette etape.",
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    return {
        "lot": lot,
        "job": {
            "id": result.job["id"],
            "step_key": result.job["step_key"],
            "run_id": result.job["run_id"],
            "status": result.job["status"],
            "created": result.job_created,
        },
        "invalidated_steps": list(result.invalidated_steps),
        "obsolete_artifacts_count": result.obsolete_artifacts_count,
        "canceled_jobs_count": result.canceled_jobs_count,
    }


@router.post("/{lot_id}/excel", status_code=202)
async def upload_lot_excel(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    file: Annotated[UploadFile, File()],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request)
    if idempotency_key is None:
        idempotency_key = f"upload_excel:{uuid.uuid4().hex}"

    with database.transaction() as repositories:
        try:
            require_mutable_upload_target(repositories, lot_id)
        except KeyError as exc:
            raise lot_not_found() from exc

    max_bytes = settings.max_excel_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)

    with database.transaction() as repositories:
        try:
            result = upload_excel_for_lot(
                repositories,
                settings=settings,
                lot_id=lot_id,
                filename=file.filename,
                content=content,
                content_type=file.content_type,
                idempotency_key=idempotency_key,
            )
            lot = get_lot_detail(repositories, lot_id)
        except ExcelUploadError as exc:
            raise ApiError(
                exc.status_code,
                exc.code,
                exc.message,
                details=exc.details,
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    artifact = result.artifact
    job = result.diagnostic_job
    return {
        "lot": lot,
        "artifact": {
            "id": artifact["id"],
            "kind": artifact["kind"],
            "role": artifact["role"],
            "status": artifact["status"],
            "size_bytes": artifact["size_bytes"],
            "sha256": artifact["sha256"],
            "mime_type": artifact["mime_type"],
            "download_url": f"/api/lots/{lot_id}/downloads/{artifact['id']}",
        },
        "job": {
            "id": job["id"],
            "step_key": job["step_key"],
            "run_id": job["run_id"],
            "status": job["status"],
            "created": result.diagnostic_job_created,
        },
        "invalidated_steps": list(result.invalidated_steps),
    }


@router.get("/{lot_id}/excel/diagnostic")
async def read_lot_excel_diagnostic(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.transaction() as repositories:
        try:
            persisted = get_persisted_excel_diagnostic(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
            problems = [
                serialize_problem(problem)
                for problem in repositories.problems.list_for_lot(lot_id, limit=100)
                if problem["step_key"] == "diagnostic_excel"
                and problem["run_id"] == persisted.artifact["run_id"]
            ]
        except ExcelDiagnosticNotReady as exc:
            raise ApiError(
                409,
                "SIRCOM_EXCEL_DIAGNOSTIC_NOT_READY",
                "Diagnostic Excel non disponible.",
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    artifact = persisted.artifact
    return {
        "diagnostic": persisted.diagnostic,
        "problems": problems,
        "problem_groups": group_problems_by_severity(problems),
        "artifact": {
            "id": artifact["id"],
            "kind": artifact["kind"],
            "role": artifact["role"],
            "status": artifact["status"],
            "size_bytes": artifact["size_bytes"],
            "sha256": artifact["sha256"],
            "mime_type": artifact["mime_type"],
            "download_url": f"/api/lots/{lot_id}/downloads/{artifact['id']}",
        },
    }


@router.post("/{lot_id}/images", status_code=202)
async def upload_lot_images(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    file: Annotated[UploadFile, File()],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request)
    if idempotency_key is None:
        idempotency_key = f"upload_images:{uuid.uuid4().hex}"

    with database.transaction() as repositories:
        try:
            require_mutable_upload_target(repositories, lot_id)
        except KeyError as exc:
            raise lot_not_found() from exc

    prepared = None
    prepared_artifact = None
    artifact_registered = False
    try:
        prepared = prepare_image_zip_upload_temp(
            settings=settings,
            lot_id=lot_id,
            filename=file.filename,
            source_file=file.file,
        )
        prepared_artifact = prepare_image_zip_artifact_for_commit(
            settings=settings,
            lot_id=lot_id,
            prepared=prepared,
        )
        with database.transaction() as repositories:
            result = upload_prepared_image_zip_for_lot(
                repositories,
                settings=settings,
                lot_id=lot_id,
                prepared=prepared,
                prepared_artifact=prepared_artifact,
                content_type=file.content_type,
                idempotency_key=idempotency_key,
            )
            lot = get_lot_detail(repositories, lot_id)
        artifact_registered = result.artifact["id"] == prepared_artifact.artifact_id
    except ImageZipUploadError as exc:
        raise ApiError(
            exc.status_code,
            exc.code,
            exc.message,
            details=exc.details,
        ) from exc
    except (KeyError, ValueError) as exc:
        raise lot_not_found() from exc
    finally:
        if prepared is not None:
            prepared.path.unlink(missing_ok=True)
        if prepared_artifact is not None and not artifact_registered:
            prepared_artifact.final_path.unlink(missing_ok=True)

    artifact = result.artifact
    job = result.inspection_job
    return {
        "lot": lot,
        "artifact": {
            "id": artifact["id"],
            "kind": artifact["kind"],
            "role": artifact["role"],
            "status": artifact["status"],
            "size_bytes": artifact["size_bytes"],
            "sha256": artifact["sha256"],
            "mime_type": artifact["mime_type"],
            "download_url": f"/api/lots/{lot_id}/downloads/{artifact['id']}",
        },
        "job": {
            "id": job["id"],
            "step_key": job["step_key"],
            "run_id": job["run_id"],
            "status": job["status"],
            "created": result.inspection_job_created,
        },
        "invalidated_steps": list(result.invalidated_steps),
    }


@router.get("/{lot_id}/images/status")
async def read_lot_images_status(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.transaction() as repositories:
        try:
            persisted = get_persisted_image_inspection(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
            problems = [
                serialize_problem(problem)
                for problem in repositories.problems.list_for_lot(lot_id, limit=100)
                if problem["step_key"] == "inspection_images"
                and problem["run_id"] == persisted.artifact["run_id"]
            ]
        except ImageInspectionNotReady as exc:
            raise ApiError(
                409,
                "SIRCOM_IMAGE_INSPECTION_NOT_READY",
                "Inspection images non disponible.",
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    artifact = persisted.artifact
    return {
        "inspection": persisted.inspection,
        "problems": problems,
        "problem_groups": group_problems_by_severity(problems),
        "artifact": {
            "id": artifact["id"],
            "kind": artifact["kind"],
            "role": artifact["role"],
            "status": artifact["status"],
            "size_bytes": artifact["size_bytes"],
            "sha256": artifact["sha256"],
            "mime_type": artifact["mime_type"],
            "download_url": f"/api/lots/{lot_id}/downloads/{artifact['id']}",
        },
    }


@router.get("/{lot_id}/images/matching")
async def read_lot_images_matching(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.transaction() as repositories:
        try:
            persisted = get_persisted_image_matching(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
            problems = [
                serialize_problem(problem)
                for problem in repositories.problems.list_for_lot(lot_id, limit=100)
                if problem["step_key"] == "matching_images"
                and problem["run_id"] == persisted.artifact["run_id"]
            ]
        except ImageMatchingNotReady as exc:
            raise ApiError(
                409,
                "SIRCOM_IMAGE_MATCHING_NOT_READY",
                "Matching images non disponible.",
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    return {
        "matching": persisted.matching,
        "problems": problems,
        "problem_groups": group_problems_by_severity(problems),
        "artifact": mapping_artifact_response(persisted.artifact, lot_id),
        "processed_images_artifact": (
            mapping_artifact_response(persisted.processed_images_artifact, lot_id)
            if persisted.processed_images_artifact
            else None
        ),
    }


@router.post("/{lot_id}/images/resolutions", status_code=202)
async def resolve_lot_images(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[ImageResolutionSubmissionRequest, Body()],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request)
    if idempotency_key is None:
        idempotency_key = f"images_resolution:{uuid.uuid4().hex}"

    with database.transaction() as repositories:
        try:
            result = save_image_resolutions(
                repositories,
                settings=settings,
                lot_id=lot_id,
                resolutions=[
                    {
                        "id_dossier": item.id_dossier,
                        "source_name": item.source_name,
                    }
                    for item in payload.resolutions
                ],
                idempotency_key=idempotency_key,
            )
        except ImageResolutionError as exc:
            raise image_resolution_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    return {
        "lot": result.lot,
        "job": {
            "id": result.matching_job["id"],
            "step_key": result.matching_job["step_key"],
            "run_id": result.matching_job["run_id"],
            "status": result.matching_job["status"],
            "created": result.matching_job_created,
        },
        "invalidated_steps": list(result.invalidated_steps),
        "obsolete_artifacts_count": result.obsolete_artifacts_count,
        "canceled_jobs_count": result.canceled_jobs_count,
    }


@router.get("/{lot_id}/mapping")
async def read_lot_mapping(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.session() as repositories:
        try:
            return get_mapping_payload(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
        except MappingError as exc:
            raise mapping_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc


@router.post("/{lot_id}/mapping/draft")
async def save_lot_mapping_draft(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[MappingSubmissionRequest, Body()],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request) or f"mapping_draft:{uuid.uuid4().hex}"
    with database.transaction() as repositories:
        try:
            result = save_mapping_draft(
                repositories,
                settings=settings,
                lot_id=lot_id,
                submission=mapping_submission_to_dict(payload),
                idempotency_key=idempotency_key,
            )
        except MappingError as exc:
            raise mapping_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {
        "mapping": result.mapping,
        "artifact": mapping_artifact_response(result.artifact, lot_id),
        "lot": result.lot,
    }


@router.post("/{lot_id}/mapping/validate")
async def validate_lot_mapping(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[MappingSubmissionRequest, Body()],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request) or f"mapping_validate:{uuid.uuid4().hex}"
    validation_error: MappingError | None = None
    with database.transaction() as repositories:
        try:
            result = validate_mapping(
                repositories,
                settings=settings,
                lot_id=lot_id,
                submission=mapping_submission_to_dict(payload),
                idempotency_key=idempotency_key,
            )
        except MappingError as exc:
            if exc.code not in PERSISTED_MAPPING_VALIDATION_ERROR_CODES:
                raise mapping_api_error(exc) from exc
            validation_error = exc
        except KeyError as exc:
            raise lot_not_found() from exc

    if validation_error is not None:
        raise mapping_api_error(validation_error) from validation_error

    return {
        "mapping": result.mapping,
        "artifact": mapping_artifact_response(result.artifact, lot_id),
        "lot": result.lot,
        "invalidated_steps": list(result.invalidated_steps),
    }


@router.post("/{lot_id}/mapping/profile", status_code=201)
async def save_lot_mapping_profile(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[SaveMappingProfileRequest | None, Body()] = None,
) -> dict[str, object]:
    settings = request.app.state.settings
    body = payload or SaveMappingProfileRequest()
    with database.transaction() as repositories:
        try:
            profile = save_profile_from_validated_mapping(
                repositories,
                settings=settings,
                lot_id=lot_id,
                name=body.name,
            )
        except MappingError as exc:
            raise mapping_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {"profile": profile}


@router.post("/{lot_id}/mapping/profile-draft")
async def apply_lot_mapping_profile_as_draft(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[ApplyMappingProfileRequest, Body()],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request) or f"mapping_profile:{uuid.uuid4().hex}"
    with database.transaction() as repositories:
        try:
            result = apply_profile_as_draft(
                repositories,
                settings=settings,
                lot_id=lot_id,
                profile_id=payload.profile_id,
                idempotency_key=idempotency_key,
            )
        except MappingError as exc:
            raise mapping_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {
        "mapping": result.mapping,
        "artifact": mapping_artifact_response(result.artifact, lot_id),
        "lot": result.lot,
    }


@router.get("/{lot_id}/tri")
async def read_lot_sort(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.session() as repositories:
        try:
            payload = get_sort_payload(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
        except SortDecisionError as exc:
            raise sort_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    artifact = payload["artifact"]
    return {
        "proposal": payload["proposal"],
        "decision": payload["decision"],
        "artifact": mapping_artifact_response(artifact, lot_id) if artifact else None,
    }


@router.post("/{lot_id}/tri/validate")
async def validate_lot_sort(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[SortDecisionRequest, Body()],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request) or f"sort_validate:{uuid.uuid4().hex}"
    with database.transaction() as repositories:
        try:
            result = validate_sort_decision(
                repositories,
                settings=settings,
                lot_id=lot_id,
                decision=payload.decision,
                idempotency_key=idempotency_key,
            )
        except SortDecisionError as exc:
            raise sort_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {
        "decision": result.decision,
        "artifact": mapping_artifact_response(result.artifact, lot_id),
        "lot": result.lot,
        "invalidated_steps": list(result.invalidated_steps),
    }


@router.get("/{lot_id}/csv/preview")
async def read_lot_csv_preview(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.session() as repositories:
        try:
            result = get_csv_preview_payload(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
        except CsvPreviewError as exc:
            raise csv_preview_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {
        "preview": result["preview"],
        "preview_artifact": (
            mapping_artifact_response(result["preview_artifact"], lot_id)
            if result["preview_artifact"]
            else None
        ),
        "csv_artifact": (
            mapping_artifact_response(result["csv_artifact"], lot_id)
            if result["csv_artifact"]
            else None
        ),
    }


@router.post("/{lot_id}/csv/preview/validate")
async def validate_lot_csv_preview(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    idempotency_key = idempotency_key_from_request(request) or f"csv_preview:{uuid.uuid4().hex}"
    with database.transaction() as repositories:
        try:
            result = validate_csv_preview(
                repositories,
                settings=settings,
                lot_id=lot_id,
                idempotency_key=idempotency_key,
            )
        except CsvPreviewError as exc:
            raise csv_preview_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {
        "preview": result.preview,
        "preview_artifact": mapping_artifact_response(result.preview_artifact, lot_id),
        "csv_artifact": mapping_artifact_response(result.csv_artifact, lot_id),
        "lot": result.lot,
        "invalidated_steps": list(result.invalidated_steps),
    }


@router.get("/{lot_id}/csv/export")
async def read_lot_csv_export(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.session() as repositories:
        try:
            result = get_csv_export_payload(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
        except CsvPreviewError as exc:
            raise csv_preview_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {
        "preview": result["preview"],
        "artifact": mapping_artifact_response(result["artifact"], lot_id),
    }


@router.get("/{lot_id}/reports")
async def read_lot_reports(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.session() as repositories:
        try:
            reports = get_persisted_reports(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
        except ReportsNotReady as exc:
            raise ApiError(
                409,
                "SIRCOM_REPORTS_NOT_READY",
                "Rapports non disponibles.",
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {
        "business_report_artifact": mapping_artifact_response(
            reports.business_artifact,
            lot_id,
        ),
        "technical_report_artifact": mapping_artifact_response(
            reports.technical_artifact,
            lot_id,
        ),
    }


@router.post("/{lot_id}/package", status_code=202)
async def generate_lot_package(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_UPDATE))],
    database: Annotated[Database, Depends(get_database)],
    payload: Annotated[PackageGenerationRequest | None, Body()] = None,
) -> dict[str, object]:
    settings = request.app.state.settings
    body = payload or PackageGenerationRequest()
    idempotency_key = idempotency_key_from_request(request)
    if idempotency_key is None:
        idempotency_key = f"package:{uuid.uuid4().hex}"

    with database.transaction() as repositories:
        try:
            result = request_package_generation(
                repositories,
                settings=settings,
                lot_id=lot_id,
                idempotency_key=idempotency_key,
                accept_warnings=body.accept_warnings,
            )
        except PackageError as exc:
            raise package_api_error(exc) from exc
        except KeyError as exc:
            raise lot_not_found() from exc

    return {
        "lot": result.lot,
        "job": {
            "id": result.job["id"],
            "step_key": result.job["step_key"],
            "run_id": result.job["run_id"],
            "status": result.job["status"],
            "created": result.job_created,
        },
    }


@router.get("/{lot_id}/package")
async def read_lot_package(
    lot_id: str,
    request: Request,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.session() as repositories:
        try:
            package = get_persisted_package(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
        except PackageNotReady as exc:
            raise ApiError(
                409,
                "SIRCOM_PACKAGE_NOT_READY",
                "Package final non disponible.",
            ) from exc
        except KeyError as exc:
            raise lot_not_found() from exc
    return {"artifact": mapping_artifact_response(package.artifact, lot_id)}


@router.get("")
async def read_lots(
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    with database.session() as repositories:
        return list_lots(
            repositories,
            limit=limit,
            offset=offset,
        )


@router.get("/{lot_id}")
async def read_lot(
    lot_id: str,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_READ))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    with database.session() as repositories:
        try:
            lot = get_lot_detail(repositories, lot_id)
        except KeyError as exc:
            raise lot_not_found() from exc
    return {"lot": lot}


@router.delete("/{lot_id}")
async def delete_lot(
    lot_id: str,
    request: Request,
    response: Response,
    _actor: Annotated[ActorContext, Depends(require_action(AccessAction.LOT_DELETE))],
    database: Annotated[Database, Depends(get_database)],
) -> dict[str, object]:
    settings = request.app.state.settings
    with database.transaction() as repositories:
        try:
            outcome = delete_lot_and_purge_if_idle(
                repositories,
                settings=settings,
                lot_id=lot_id,
            )
        except KeyError as exc:
            raise lot_not_found() from exc

    if outcome.deferred:
        response.status_code = 202
    return {
        "lot": outcome.lot,
        "cancel_requested_jobs": outcome.cancel_requested_jobs,
        "purge": {
            "status": outcome.purge_status,
            "active_jobs_remaining": outcome.active_jobs_remaining,
            "trace": outcome.trace,
        },
    }


def lot_not_found() -> ApiError:
    return ApiError(
        404,
        "SIRCOM_LOT_NOT_FOUND",
        "Lot introuvable.",
    )


def require_mutable_upload_target(repositories, lot_id: str) -> None:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise ApiError(
            409,
            "SIRCOM_LOT_NOT_MUTABLE",
            "Lot non modifiable.",
        )


def mapping_submission_to_dict(payload: MappingSubmissionRequest) -> dict[str, object]:
    return {
        "structural_fingerprint": payload.structural_fingerprint,
        "columns": [
            {
                "id": column.id,
                "status": column.status,
                "csv_name": column.csv_name,
                "logical_role": column.logical_role,
                "suppression_reason": column.suppression_reason,
            }
            for column in payload.columns
        ],
    }


def mapping_artifact_response(artifact: dict[str, object], lot_id: str) -> dict[str, object]:
    return {
        "id": artifact["id"],
        "kind": artifact["kind"],
        "role": artifact["role"],
        "status": artifact["status"],
        "size_bytes": artifact["size_bytes"],
        "sha256": artifact["sha256"],
        "mime_type": artifact["mime_type"],
        "download_url": f"/api/lots/{lot_id}/downloads/{artifact['id']}",
    }


def mapping_api_error(exc: MappingError) -> ApiError:
    return ApiError(
        exc.status_code,
        exc.code,
        exc.message,
        details=exc.details,
    )


def sort_api_error(exc: SortDecisionError) -> ApiError:
    return ApiError(
        exc.status_code,
        exc.code,
        exc.message,
        details=exc.details,
    )


def csv_preview_api_error(exc: CsvPreviewError) -> ApiError:
    return ApiError(
        exc.status_code,
        exc.code,
        exc.message,
        details=exc.details,
    )


def image_resolution_api_error(exc: ImageResolutionError) -> ApiError:
    return ApiError(
        exc.status_code,
        exc.code,
        exc.message,
        details=exc.details,
    )


def package_api_error(exc: PackageError) -> ApiError:
    return ApiError(
        exc.status_code,
        exc.code,
        exc.message,
        details=exc.details,
    )


def idempotency_key_from_request(request: Request) -> str | None:
    raw_value = request.headers.get("x-idempotency-key")
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    if len(value) > 128:
        raise ApiError(
            400,
            "SIRCOM_IDEMPOTENCY_KEY_INVALID",
            "Cle d'idempotence invalide.",
        )
    return value
