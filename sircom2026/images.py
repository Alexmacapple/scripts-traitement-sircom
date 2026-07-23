from __future__ import annotations

import hashlib
import json
import shutil
import unicodedata
import uuid
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from sircom2026.artifacts import (
    ArtifactStore,
    ArtifactUnavailableError,
    PreparedArtifactFile,
    safe_path_part,
)
from sircom2026.config import Settings
from sircom2026.database import LOT_WRITE_BLOCKED_STATUSES, Repositories
from sircom2026.image_formats import (
    ACCEPTED_SOURCE_IMAGE_EXTENSIONS,
    REFUSED_SOURCE_IMAGE_EXTENSION_CODES,
)
from sircom2026.invalidation import (
    fingerprint_payload,
    record_input_change,
    step_input_fingerprint,
)
from sircom2026.state import complete_step, record_problem, transition_step
from sircom2026.worker import JobResult, WorkerJobContext, WorkerLeaseLost, enqueue_job


ALLOWED_ZIP_EXTENSIONS = (".zip",)
IMAGE_ZIP_MIME_TYPE = "application/zip"
IMAGE_ZIP_UPLOAD_RULES_VERSION = "image-zip-upload-v1"
IMAGE_ZIP_INSPECTION_RULES_VERSION = "image-zip-inspection-v2"
UPLOAD_IMAGES_STEP_KEY = "upload_images"
INSPECTION_IMAGES_STEP_KEY = "inspection_images"
UPLOAD_WORKER_ID = "http-upload"
INSPECTION_ARTIFACT_KIND = "json"
INSPECTION_ARTIFACT_ROLE = "result"
INSPECTION_MIME_TYPE = "application/json"
INSPECTABLE_IMAGE_EXTENSIONS = ACCEPTED_SOURCE_IMAGE_EXTENSIONS


@dataclass(frozen=True)
class ImageZipUploadValidation:
    extension: str


@dataclass(frozen=True)
class ImageZipUploadResult:
    artifact: dict[str, Any]
    inspection_job: dict[str, Any]
    inspection_job_created: bool
    invalidated_steps: tuple[str, ...]


@dataclass(frozen=True)
class PreparedImageZipUpload:
    validation: ImageZipUploadValidation
    path: Path
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class PersistedImageInspection:
    inspection: dict[str, Any]
    artifact: dict[str, Any]


class ImageZipUploadError(ValueError):
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
        self.details = details


class ImageInspectionNotReady(RuntimeError):
    """Raised when no current image inspection artifact can be exposed yet."""


def validate_image_zip_file(
    *,
    filename: str | None,
    path: Path,
    size_bytes: int,
    max_zip_mb: int,
) -> ImageZipUploadValidation:
    validation = _validate_image_zip_metadata(
        filename=filename,
        size_bytes=size_bytes,
        max_zip_mb=max_zip_mb,
    )
    if not zipfile.is_zipfile(path):
        raise ImageZipUploadError(
            422,
            "SIRCOM_IMAGE_ZIP_SIGNATURE_INVALID",
            "Signature zip invalide.",
        )
    return validation


def prepare_image_zip_upload_temp(
    *,
    settings: Settings,
    lot_id: str,
    filename: str | None,
    source_file: BinaryIO,
) -> PreparedImageZipUpload:
    _validate_image_zip_extension(filename)
    upload_path = _upload_temp_path(settings, lot_id)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        size_bytes, sha256 = _copy_stream_to_upload_temp(
            source_file,
            upload_path,
            max_bytes=settings.max_zip_mb * 1024 * 1024,
        )
        validation = validate_image_zip_file(
            filename=filename,
            path=upload_path,
            size_bytes=size_bytes,
            max_zip_mb=settings.max_zip_mb,
        )
        return PreparedImageZipUpload(
            validation=validation,
            path=upload_path,
            size_bytes=size_bytes,
            sha256=sha256,
        )
    except Exception:
        upload_path.unlink(missing_ok=True)
        raise


def prepare_image_zip_artifact_for_commit(
    *,
    settings: Settings,
    lot_id: str,
    prepared: PreparedImageZipUpload,
) -> PreparedArtifactFile:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    return store.prepare_file_for_commit(
        lot_id=lot_id,
        filename=f"source-images{prepared.validation.extension}",
        source_path=prepared.path,
        sha256=prepared.sha256,
        size_bytes=prepared.size_bytes,
        mime_type=IMAGE_ZIP_MIME_TYPE,
    )


def upload_prepared_image_zip_for_lot(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    prepared: PreparedImageZipUpload,
    prepared_artifact: PreparedArtifactFile,
    content_type: str | None,
    idempotency_key: str,
) -> ImageZipUploadResult:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise ImageZipUploadError(
            409,
            "SIRCOM_LOT_NOT_MUTABLE",
            "Lot non modifiable.",
        )
    existing_result = _existing_upload_result(
        repositories,
        lot_id=lot_id,
        idempotency_key=idempotency_key,
    )
    if existing_result is not None:
        return existing_result

    run_id = f"run_{uuid.uuid4().hex}"
    repositories.jobs.cancel_active_for_step(lot_id, UPLOAD_IMAGES_STEP_KEY)
    repositories.artifacts.mark_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(UPLOAD_IMAGES_STEP_KEY,),
    )
    repositories.steps.prepare_run(
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        run_id=run_id,
    )
    transition_step(
        repositories,
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        status="en_cours",
        run_id=run_id,
    )
    upload_job = repositories.jobs.create_owned_running(
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        run_id=run_id,
        idempotency_key=idempotency_key,
        lease_owner=UPLOAD_WORKER_ID,
        lease_seconds=settings.worker_lease_ttl_seconds,
    )

    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    artifact = store.create_committed_from_prepared_file(
        repositories,
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        run_id=run_id,
        kind="zip",
        role="source",
        prepared_file=prepared_artifact,
        metadata={
            "content_type": content_type,
            "extension": prepared.validation.extension,
            "rules_version": IMAGE_ZIP_UPLOAD_RULES_VERSION,
        },
        lease_version=upload_job["lease_version"],
    )
    source_change = record_input_change(
        repositories,
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        input_payload={
            "artifact_id": artifact["id"],
            "extension": prepared.validation.extension,
            "rules_version": IMAGE_ZIP_UPLOAD_RULES_VERSION,
            "sha256": artifact["sha256"],
            "size_bytes": artifact["size_bytes"],
        },
        reason="new_image_zip",
    )
    finished_job = repositories.jobs.finish_owned(
        job_id=upload_job["id"],
        worker_id=UPLOAD_WORKER_ID,
        run_id=run_id,
        lease_version=upload_job["lease_version"],
        status="succeeded",
    )
    if finished_job is None:
        raise ImageZipUploadError(
            409,
            "SIRCOM_IMAGE_ZIP_UPLOAD_RUN_NOT_CURRENT",
            "Upload du zip images interrompu par une exécution plus récente.",
        )
    complete_step(
        repositories,
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        run_id=run_id,
    )
    inspection_input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=INSPECTION_IMAGES_STEP_KEY,
        input_payload={
            "rules_version": IMAGE_ZIP_INSPECTION_RULES_VERSION,
            "schema_version": 1,
        },
    )
    inspection = enqueue_job(
        repositories,
        lot_id=lot_id,
        step_key=INSPECTION_IMAGES_STEP_KEY,
        idempotency_key=f"{INSPECTION_IMAGES_STEP_KEY}:{artifact['id']}",
        input_fingerprint=inspection_input_fingerprint,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        run_id=run_id,
        event_type="image_zip.uploaded",
        payload={
            "artifact_id": artifact["id"],
            "output_fingerprint": source_change.source_fingerprint,
            "run_id": run_id,
            "size_bytes": artifact["size_bytes"],
            "step_key": UPLOAD_IMAGES_STEP_KEY,
        },
    )
    return ImageZipUploadResult(
        artifact=artifact,
        inspection_job=inspection.job,
        inspection_job_created=inspection.created,
        invalidated_steps=source_change.invalidated_steps,
    )


def run_image_inspection_job(
    context: WorkerJobContext, *, settings: Settings
) -> JobResult:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    context.set_progress(1, 3)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        source_artifact = _current_image_zip_source_artifact(
            repositories, context.lot_id
        )
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
    temp_dir = _inspection_temp_dir(settings, context.lot_id, context.run_id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        inspection = inspect_image_zip(readable.path, settings=settings)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    inspection_content = json.dumps(
        inspection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        repositories.problems.mark_open_obsolete_for_steps(
            lot_id=context.lot_id,
            step_keys=(INSPECTION_IMAGES_STEP_KEY,),
        )
        repositories.artifacts.mark_obsolete_for_steps(
            lot_id=context.lot_id,
            step_keys=(INSPECTION_IMAGES_STEP_KEY,),
        )
        artifact = store.put_temp_then_commit(
            repositories,
            lot_id=context.lot_id,
            step_key=INSPECTION_IMAGES_STEP_KEY,
            run_id=context.run_id,
            kind=INSPECTION_ARTIFACT_KIND,
            role=INSPECTION_ARTIFACT_ROLE,
            filename="inspection-images.json",
            content=inspection_content,
            metadata={
                "blockers_count": len(inspection["blockers"]),
                "image_count": inspection["image_count"],
                "inspectable": inspection["inspectable"],
                "rules_version": IMAGE_ZIP_INSPECTION_RULES_VERSION,
                "source_artifact_id": source_artifact["id"],
                "warnings_count": len(inspection["warnings"]),
            },
            mime_type=INSPECTION_MIME_TYPE,
            lease_version=context.leased_job.lease_version,
        )
        problem_counts = persist_image_inspection_problems(
            repositories,
            lot_id=context.lot_id,
            run_id=context.run_id,
            inspection=inspection,
        )
        output_fingerprint = fingerprint_payload(
            {
                "artifact_sha256": artifact["sha256"],
                "image_count": inspection["image_count"],
                "inspection_artifact_id": artifact["id"],
                "inspectable": inspection["inspectable"],
                "kind": "image_zip_inspection",
                "rules_version": IMAGE_ZIP_INSPECTION_RULES_VERSION,
                "schema_version": 1,
                "source_artifact_id": source_artifact["id"],
            }
        )
        repositories.events.create(
            lot_id=context.lot_id,
            step_key=INSPECTION_IMAGES_STEP_KEY,
            run_id=context.run_id,
            event_type="images.inspection_completed",
            payload={
                "artifact_id": artifact["id"],
                "status": "bloque" if problem_counts["bloquant"] else "termine",
                "step_key": INSPECTION_IMAGES_STEP_KEY,
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


def inspect_image_zip(path: Path, *, settings: Settings) -> dict[str, Any]:
    max_unzipped_bytes = settings.max_unzipped_mb * 1024 * 1024
    max_image_bytes = settings.max_image_mb * 1024 * 1024
    blockers: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    images: list[dict[str, Any]] = []
    ignored_entries_count = 0
    entries_count = 0
    non_ignored_files_count = 0
    total_uncompressed_bytes = 0
    normalized_root_names: Counter[str] = Counter()

    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
    except zipfile.BadZipFile:
        blockers["SIRCOM_IMAGE_ZIP_UNREADABLE"] += 1
        infos = []

    for info in infos:
        entries_count += 1
        name = _zip_name(info.filename)
        safety_code = _unsafe_zip_path_code(name)
        if safety_code is not None:
            blockers[safety_code] += 1
            continue
        if info.is_dir():
            continue
        total_uncompressed_bytes += max(0, int(info.file_size))

        parts = _zip_parts(name)
        if _is_ignorable_system_entry(parts):
            ignored_entries_count += 1
            continue
        non_ignored_files_count += 1
        if info.flag_bits & 0x1:
            blockers["SIRCOM_IMAGE_ZIP_ENCRYPTED_ENTRY"] += 1
            continue

        extension = Path(parts[-1]).suffix.lower()
        refused_format_code = REFUSED_SOURCE_IMAGE_EXTENSION_CODES.get(extension)
        if refused_format_code is not None:
            blockers[refused_format_code] += 1
            continue
        is_image = extension in INSPECTABLE_IMAGE_EXTENSIONS
        if len(parts) > 1:
            if is_image:
                blockers["SIRCOM_IMAGE_ZIP_IMAGE_IN_SUBFOLDER"] += 1
            else:
                blockers["SIRCOM_IMAGE_ZIP_ENTRY_IN_SUBFOLDER"] += 1
            continue
        if not is_image:
            ignored_entries_count += 1
            continue

        normalized_name = _normalized_zip_name(parts[-1])
        normalized_root_names[normalized_name] += 1
        if info.file_size > max_image_bytes:
            blockers["SIRCOM_IMAGE_ZIP_IMAGE_TOO_LARGE"] += 1
        images.append(
            {
                "name": parts[-1],
                "normalized_name": normalized_name,
                "extension": extension,
                "size_bytes": int(info.file_size),
                "compressed_size_bytes": int(info.compress_size),
            }
        )

    duplicate_count = sum(1 for count in normalized_root_names.values() if count > 1)
    if duplicate_count:
        blockers["SIRCOM_IMAGE_ZIP_DUPLICATE_NAMES"] += duplicate_count
    if non_ignored_files_count > settings.max_image_count:
        blockers["SIRCOM_IMAGE_ZIP_TOO_MANY_FILES"] += 1
    if len(images) > settings.max_image_count:
        blockers["SIRCOM_IMAGE_ZIP_TOO_MANY_IMAGES"] += 1
    if total_uncompressed_bytes > max_unzipped_bytes:
        blockers["SIRCOM_IMAGE_ZIP_UNCOMPRESSED_TOO_LARGE"] += 1
    if not images and not blockers:
        warnings["SIRCOM_IMAGE_ZIP_NO_TREATABLE_IMAGE"] += 1

    serialized_blockers = _serialize_problem_codes(blockers)
    serialized_warnings = _serialize_problem_codes(warnings)
    return {
        "schema_version": 1,
        "rules_version": IMAGE_ZIP_INSPECTION_RULES_VERSION,
        "inspectable": not serialized_blockers,
        "image_count": len(images),
        "entries_count": entries_count,
        "files_count": non_ignored_files_count,
        "ignored_entries_count": ignored_entries_count,
        "total_uncompressed_bytes": total_uncompressed_bytes,
        "accepted_extensions": list(INSPECTABLE_IMAGE_EXTENSIONS),
        "refused_extensions": sorted(REFUSED_SOURCE_IMAGE_EXTENSION_CODES),
        "blockers": serialized_blockers,
        "warnings": serialized_warnings,
        "images": images,
        "limits": {
            "max_image_count": settings.max_image_count,
            "max_image_mb": settings.max_image_mb,
            "max_unzipped_mb": settings.max_unzipped_mb,
        },
    }


def get_persisted_image_inspection(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PersistedImageInspection:
    repositories.lots.get_required(lot_id)
    artifact = _current_inspection_artifact(repositories, lot_id)
    if artifact is None:
        raise ImageInspectionNotReady("Image inspection is not ready.")
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
        raise ImageInspectionNotReady(
            "Image inspection artifact is unavailable."
        ) from exc
    try:
        inspection = json.loads(readable.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImageInspectionNotReady(
            "Image inspection artifact is unavailable."
        ) from exc
    if not isinstance(inspection, dict):
        raise ImageInspectionNotReady("Image inspection artifact is malformed.")
    return PersistedImageInspection(inspection=inspection, artifact=artifact)


def persist_image_inspection_problems(
    repositories: Repositories,
    *,
    lot_id: str,
    run_id: str,
    inspection: dict[str, Any],
) -> dict[str, int]:
    counts = {"bloquant": 0, "alerte": 0, "information": 0}
    for problem in image_inspection_problems(inspection):
        record_problem(
            repositories,
            lot_id=lot_id,
            step_key=INSPECTION_IMAGES_STEP_KEY,
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
    return counts


def image_inspection_problems(inspection: dict[str, Any]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    for item in inspection.get("blockers", []):
        code = str(item.get("code", ""))
        count = int(item.get("count", 1))
        definition = _PROBLEM_DEFINITIONS.get(code, _default_problem_definition(code))
        problems.append(
            {
                **definition,
                "severity": "bloquant",
                "location": {"archive": "zip images"},
                "technical": {"checks_count": count},
            }
        )
    for item in inspection.get("warnings", []):
        code = str(item.get("code", ""))
        count = int(item.get("count", 1))
        definition = _PROBLEM_DEFINITIONS.get(code, _default_problem_definition(code))
        problems.append(
            {
                **definition,
                "severity": "alerte",
                "location": {"archive": "zip images"},
                "technical": {"checks_count": count},
            }
        )
    return problems


def _validate_image_zip_metadata(
    *,
    filename: str | None,
    size_bytes: int,
    max_zip_mb: int,
) -> ImageZipUploadValidation:
    extension = _validate_image_zip_extension(filename)
    _validate_image_zip_size(size_bytes=size_bytes, max_zip_mb=max_zip_mb)
    return ImageZipUploadValidation(extension=extension)


def _validate_image_zip_extension(filename: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_ZIP_EXTENSIONS:
        raise ImageZipUploadError(
            415,
            "SIRCOM_IMAGE_ZIP_EXTENSION_UNSUPPORTED",
            "Format de zip images non supporte.",
            details={"allowed_extensions": list(ALLOWED_ZIP_EXTENSIONS)},
        )
    return extension


def _validate_image_zip_size(*, size_bytes: int, max_zip_mb: int) -> None:
    max_bytes = max_zip_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ImageZipUploadError(
            413,
            "SIRCOM_IMAGE_ZIP_TOO_LARGE",
            "Zip images trop volumineux.",
            details={"max_mb": max_zip_mb, "size_bytes": size_bytes},
        )
    if size_bytes <= 0:
        raise ImageZipUploadError(
            422,
            "SIRCOM_IMAGE_ZIP_EMPTY",
            "Zip images vide.",
        )


def _copy_stream_to_upload_temp(
    source_file: BinaryIO,
    destination: Path,
    *,
    max_bytes: int,
) -> tuple[int, str]:
    total = 0
    digest = hashlib.sha256()
    with destination.open("wb") as handle:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            total += len(chunk)
            if total > max_bytes:
                handle.close()
                destination.unlink(missing_ok=True)
                raise ImageZipUploadError(
                    413,
                    "SIRCOM_IMAGE_ZIP_TOO_LARGE",
                    "Zip images trop volumineux.",
                    details={
                        "max_mb": max_bytes // (1024 * 1024),
                        "size_bytes": total,
                    },
                )
            digest.update(chunk)
            handle.write(chunk)
    return total, digest.hexdigest()


def _upload_temp_path(settings: Settings, lot_id: str) -> Path:
    return (
        settings.data_dir
        / "lots"
        / safe_path_part(lot_id, "lot_id")
        / "tmp"
        / f"upload-images-{uuid.uuid4().hex}.zip"
    )


def _current_image_zip_source_artifact(
    repositories: Repositories,
    lot_id: str,
) -> dict[str, Any] | None:
    upload_step = repositories.steps.get_by_lot_key(lot_id, UPLOAD_IMAGES_STEP_KEY)
    if upload_step is None or not upload_step["current_run_id"]:
        return None
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        run_id=upload_step["current_run_id"],
        role="source",
    )
    if artifact is None or artifact["status"] != "committed":
        return None
    return artifact


def _current_inspection_artifact(
    repositories: Repositories,
    lot_id: str,
) -> dict[str, Any] | None:
    inspection_step = repositories.steps.get_by_lot_key(
        lot_id, INSPECTION_IMAGES_STEP_KEY
    )
    if inspection_step is None or not inspection_step["current_run_id"]:
        return None
    if inspection_step["status"] not in {"termine", "termine_avec_alertes", "bloque"}:
        return None
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=INSPECTION_IMAGES_STEP_KEY,
        run_id=inspection_step["current_run_id"],
        role=INSPECTION_ARTIFACT_ROLE,
    )
    if artifact is None or artifact["status"] != "committed":
        return None
    return artifact


def _existing_upload_result(
    repositories: Repositories,
    *,
    lot_id: str,
    idempotency_key: str,
) -> ImageZipUploadResult | None:
    existing_job = repositories.jobs.get_by_idempotency_key(
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        idempotency_key=idempotency_key,
    )
    if existing_job is None:
        return None
    if existing_job["status"] != "succeeded":
        raise ImageZipUploadError(
            409,
            "SIRCOM_IMAGE_ZIP_UPLOAD_ALREADY_SUBMITTED",
            "Upload du zip images déjà soumis.",
        )

    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=UPLOAD_IMAGES_STEP_KEY,
        run_id=existing_job["run_id"],
        role="source",
    )
    if artifact is None or artifact["status"] != "committed":
        raise ImageZipUploadError(
            409,
            "SIRCOM_IMAGE_ZIP_UPLOAD_ALREADY_SUBMITTED",
            "Upload du zip images déjà soumis.",
        )
    inspection_job = repositories.jobs.get_by_idempotency_key(
        lot_id=lot_id,
        step_key=INSPECTION_IMAGES_STEP_KEY,
        idempotency_key=f"{INSPECTION_IMAGES_STEP_KEY}:{artifact['id']}",
    )
    if inspection_job is None:
        raise ImageZipUploadError(
            409,
            "SIRCOM_IMAGE_ZIP_UPLOAD_ALREADY_SUBMITTED",
            "Upload du zip images déjà soumis.",
        )

    return ImageZipUploadResult(
        artifact=artifact,
        inspection_job=inspection_job,
        inspection_job_created=False,
        invalidated_steps=(),
    )


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


def _record_missing_source_problem(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=INSPECTION_IMAGES_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_IMAGE_ZIP_SOURCE_MISSING",
        title="Zip images source introuvable",
        cause="L'inspection ne trouve pas l'artefact zip images source courant.",
        action="Déposer à nouveau le zip images, puis relancer l'inspection.",
    )


def _inspection_temp_dir(settings: Settings, lot_id: str, run_id: str) -> Path:
    return (
        settings.data_dir
        / "lots"
        / safe_path_part(lot_id, "lot_id")
        / "tmp"
        / f"inspection-{safe_path_part(run_id, 'run_id')}"
    )


def _serialize_problem_codes(counts: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"code": code, "count": count}
        for code, count in sorted(counts.items())
        if count > 0
    ]


def _zip_name(raw_name: str) -> str:
    return raw_name.replace("\\", "/")


def _zip_parts(name: str) -> list[str]:
    stripped = name[:-1] if name.endswith("/") else name
    return stripped.split("/")


def _unsafe_zip_path_code(name: str) -> str | None:
    if not name:
        return "SIRCOM_IMAGE_ZIP_EMPTY_NAME"
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        return "SIRCOM_IMAGE_ZIP_CONTROL_CHARACTERS"
    if name.startswith("/") or (len(name) >= 2 and name[1] == ":"):
        return "SIRCOM_IMAGE_ZIP_UNSAFE_PATH"
    parts = _zip_parts(name)
    if not parts or any(part == "" for part in parts):
        return "SIRCOM_IMAGE_ZIP_EMPTY_NAME"
    if any(part == ".." for part in parts):
        return "SIRCOM_IMAGE_ZIP_UNSAFE_PATH"
    return None


def _is_ignorable_system_entry(parts: list[str]) -> bool:
    return bool(parts) and (parts[0] == "__MACOSX" or parts[-1] == ".DS_Store")


def _normalized_zip_name(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def _default_problem_definition(code: str) -> dict[str, str]:
    return {
        "code": code or "SIRCOM_IMAGE_ZIP_INVALID",
        "title": "Zip images invalide",
        "cause": "Le zip images ne respecte pas les contraintes d'import V1.",
        "action": "Corriger le zip images puis le déposer à nouveau.",
    }


_PROBLEM_DEFINITIONS: dict[str, dict[str, str]] = {
    "SIRCOM_IMAGE_ZIP_CONTROL_CHARACTERS": {
        "code": "SIRCOM_IMAGE_ZIP_CONTROL_CHARACTERS",
        "title": "Nom de fichier invalide",
        "cause": "Le zip contient un nom avec caractère de contrôle.",
        "action": "Renommer le fichier concerné puis déposer un nouveau zip.",
    },
    "SIRCOM_IMAGE_ZIP_DUPLICATE_NAMES": {
        "code": "SIRCOM_IMAGE_ZIP_DUPLICATE_NAMES",
        "title": "Noms d'images en doublon",
        "cause": "Plusieurs images ont le même nom après normalisation Unicode et casse.",
        "action": "Renommer les images en doublon puis déposer un nouveau zip.",
    },
    "SIRCOM_IMAGE_ZIP_EMPTY_NAME": {
        "code": "SIRCOM_IMAGE_ZIP_EMPTY_NAME",
        "title": "Nom de fichier vide",
        "cause": "Le zip contient une entrée sans nom exploitable.",
        "action": "Recréer le zip sans entrée vide puis le déposer à nouveau.",
    },
    "SIRCOM_IMAGE_ZIP_ENCRYPTED_ENTRY": {
        "code": "SIRCOM_IMAGE_ZIP_ENCRYPTED_ENTRY",
        "title": "Entrée zip chiffrée",
        "cause": "Le zip contient une entrée protégée par mot de passe que le worker ne peut pas extraire.",
        "action": "Recréer le zip sans chiffrement puis le déposer à nouveau.",
    },
    "SIRCOM_IMAGE_ZIP_ENTRY_IN_SUBFOLDER": {
        "code": "SIRCOM_IMAGE_ZIP_ENTRY_IN_SUBFOLDER",
        "title": "Fichier en sous-dossier",
        "cause": "La V1 accepte uniquement des fichiers à la racine du zip, hors fichiers système ignorables.",
        "action": "Placer les fichiers utiles à la racine du zip puis le déposer à nouveau.",
    },
    "SIRCOM_IMAGE_ZIP_IMAGE_IN_SUBFOLDER": {
        "code": "SIRCOM_IMAGE_ZIP_IMAGE_IN_SUBFOLDER",
        "title": "Image en sous-dossier",
        "cause": "La V1 accepte uniquement les images placées à la racine du zip.",
        "action": "Placer toutes les images à la racine du zip puis le déposer à nouveau.",
    },
    "SIRCOM_IMAGE_ZIP_IMAGE_TOO_LARGE": {
        "code": "SIRCOM_IMAGE_ZIP_IMAGE_TOO_LARGE",
        "title": "Image trop volumineuse",
        "cause": "Au moins une image dépasse la taille maximale configurée.",
        "action": "Réduire la taille des images concernées puis déposer un nouveau zip.",
    },
    "SIRCOM_IMAGE_HEIC_REFUSED": {
        "code": "SIRCOM_IMAGE_HEIC_REFUSED",
        "title": "Format HEIC refusé",
        "cause": "Le traitement images V1 ne prend pas en charge les fichiers HEIC.",
        "action": "Convertir les fichiers HEIC en JPG, PNG, WEBP ou TIFF puis déposer un nouveau zip.",
    },
    "SIRCOM_IMAGE_HEIF_REFUSED": {
        "code": "SIRCOM_IMAGE_HEIF_REFUSED",
        "title": "Format HEIF refusé",
        "cause": "Le traitement images V1 ne prend pas en charge les fichiers HEIF.",
        "action": "Convertir les fichiers HEIF en JPG, PNG, WEBP ou TIFF puis déposer un nouveau zip.",
    },
    "SIRCOM_IMAGE_ZIP_NO_TREATABLE_IMAGE": {
        "code": "SIRCOM_IMAGE_ZIP_NO_TREATABLE_IMAGE",
        "title": "Aucune image traitable",
        "cause": "Le zip ne contient aucune image exploitable à la racine.",
        "action": "Déposer un zip avec images à la racine ou continuer sans images.",
    },
    "SIRCOM_IMAGE_ZIP_TOO_MANY_IMAGES": {
        "code": "SIRCOM_IMAGE_ZIP_TOO_MANY_IMAGES",
        "title": "Trop d'images",
        "cause": "Le zip contient plus d'images que la limite configurée.",
        "action": "Réduire le nombre d'images puis déposer un nouveau zip.",
    },
    "SIRCOM_IMAGE_ZIP_TOO_MANY_FILES": {
        "code": "SIRCOM_IMAGE_ZIP_TOO_MANY_FILES",
        "title": "Trop de fichiers",
        "cause": "Le zip contient plus de fichiers que la limite configurée.",
        "action": "Réduire le contenu du zip puis le déposer à nouveau.",
    },
    "SIRCOM_IMAGE_ZIP_UNCOMPRESSED_TOO_LARGE": {
        "code": "SIRCOM_IMAGE_ZIP_UNCOMPRESSED_TOO_LARGE",
        "title": "Zip trop volumineux après décompression",
        "cause": "La taille totale annoncée après décompression dépasse la limite configurée.",
        "action": "Réduire le contenu du zip puis le déposer à nouveau.",
    },
    "SIRCOM_IMAGE_ZIP_UNREADABLE": {
        "code": "SIRCOM_IMAGE_ZIP_UNREADABLE",
        "title": "Zip images illisible",
        "cause": "Le zip source ne peut pas être relu par le worker.",
        "action": "Déposer à nouveau le zip images.",
    },
    "SIRCOM_IMAGE_ZIP_UNSAFE_PATH": {
        "code": "SIRCOM_IMAGE_ZIP_UNSAFE_PATH",
        "title": "Chemin dangereux dans le zip",
        "cause": "Le zip contient un chemin absolu ou une remontée de répertoire.",
        "action": "Recréer le zip avec des images à la racine, sans chemin spécial.",
    },
}
