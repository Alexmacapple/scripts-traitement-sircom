from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from sircom2026.artifacts import (
    ArtifactStore,
    ArtifactUnavailableError,
    cleanup_artifact_paths,
)
from sircom2026.config import Settings
from sircom2026.database import LOT_WRITE_BLOCKED_STATUSES, Repositories
from sircom2026.image_formats import (
    DEFAULT_IMAGE_DIMENSION_LIMITS,
    IMAGE_DIMENSIONS_EXCEEDED_CODE,
    ImageDimensionLimitError,
    ImageDimensionLimits,
    check_image_dimensions,
    image_dimension_limits_from_settings,
    prepare_image_for_jpeg,
)
from sircom2026.image_naming import image_id_for_dossier
from sircom2026.image_matching_rules import (
    MATCHABLE_IMAGE_SOURCE_ROLE,
    MATCHING_RULES_VERSION,
    MATCHING_SCHEMA_VERSION,
    mark_duplicate_automatic_sources as _mark_duplicate_automatic_sources,
    match_row_image as _match_row_image,
    root_image_inventory as _root_image_inventory,
    source_image_columns as _source_image_columns,
    source_image_values as _source_image_values,
)
from sircom2026.images import (
    INSPECTION_ARTIFACT_ROLE,
    INSPECTION_IMAGES_STEP_KEY,
    UPLOAD_IMAGES_STEP_KEY,
)
from sircom2026.invalidation import (
    fingerprint_payload,
    invalidate_downstream,
    step_input_fingerprint,
)
from sircom2026.lots import get_lot_detail
from sircom2026.state import record_problem
from sircom2026.transform import NORMALIZATION_ARTIFACT_ROLE, NORMALIZATION_STEP_KEY
from sircom2026.worker import (
    EnqueuedJob,
    IdempotencyKeyConsumedError,
    JobResult,
    WorkerJobContext,
    WorkerLeaseLost,
    enqueue_job,
)


MATCHING_IMAGES_STEP_KEY = "matching_images"
MATCHING_ARTIFACT_KIND = "json"
MATCHING_ARTIFACT_ROLE = "result"
MATCHING_MIME_TYPE = "application/json"
PROCESSED_IMAGES_ARTIFACT_KIND = "zip"
PROCESSED_IMAGES_ARTIFACT_ROLE = "processed_images"
PROCESSED_IMAGES_MIME_TYPE = "application/zip"
MANUAL_RESOLUTIONS_RULES_VERSION = "image-manual-resolutions-v1"
EXPORT_IMAGES_FOLDER = "export-jpg-resize"
FINAL_IMAGE_MAX_WIDTH_PX = 350
FINAL_IMAGE_JPEG_QUALITY = 100
FINAL_IMAGE_DPI = 300


@dataclass(frozen=True)
class CurrentJsonArtifact:
    artifact: dict[str, Any]
    payload: dict[str, Any]


@dataclass(frozen=True)
class PersistedImageMatching:
    matching: dict[str, Any]
    artifact: dict[str, Any]
    processed_images_artifact: dict[str, Any] | None


@dataclass(frozen=True)
class ImageResolutionResult:
    matching_job: dict[str, Any]
    matching_job_created: bool
    lot: dict[str, Any]
    invalidated_steps: tuple[str, ...]
    obsolete_artifacts_count: int
    canceled_jobs_count: int


class ImageMatchingNotReady(RuntimeError):
    """Raised when no current image matching artifact can be exposed yet."""


class ImageResolutionError(ValueError):
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


def image_matching_input_payload(
    repositories: Repositories,
    *,
    lot_id: str,
) -> dict[str, Any]:
    return {
        "manual_resolutions_fingerprint": fingerprint_payload(
            {
                "schema_version": 1,
                "rules_version": MANUAL_RESOLUTIONS_RULES_VERSION,
                "resolutions": _manual_resolutions_items(repositories, lot_id),
            }
        ),
        "rules_version": MATCHING_RULES_VERSION,
        "schema_version": MATCHING_SCHEMA_VERSION,
    }


def enqueue_image_matching_job(
    repositories: Repositories,
    *,
    lot_id: str,
    idempotency_key: str,
) -> EnqueuedJob:
    input_fingerprint = step_input_fingerprint(
        repositories,
        lot_id=lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        input_payload=image_matching_input_payload(repositories, lot_id=lot_id),
    )
    try:
        return enqueue_job(
            repositories,
            lot_id=lot_id,
            step_key=MATCHING_IMAGES_STEP_KEY,
            idempotency_key=f"{idempotency_key}:{input_fingerprint[:16]}",
            input_fingerprint=input_fingerprint,
        )
    except IdempotencyKeyConsumedError as exc:
        raise ImageResolutionError(
            409,
            "SIRCOM_IDEMPOTENCY_KEY_CONSUMED",
            "Cette demande de traitement images a déjà été consommée.",
        ) from exc


def run_image_matching_job(
    context: WorkerJobContext, *, settings: Settings
) -> JobResult:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    context.set_progress(1, 5)
    with context.database.transaction() as repositories:
        _require_current_lease(repositories, context)
        normalized = _current_json_artifact(
            repositories,
            store,
            lot_id=context.lot_id,
            step_key=NORMALIZATION_STEP_KEY,
            role=NORMALIZATION_ARTIFACT_ROLE,
            ready_statuses=("termine", "termine_avec_alertes"),
        )
        inspection = _current_json_artifact(
            repositories,
            store,
            lot_id=context.lot_id,
            step_key=INSPECTION_IMAGES_STEP_KEY,
            role=INSPECTION_ARTIFACT_ROLE,
            ready_statuses=("termine", "termine_avec_alertes"),
        )
        source_artifact = _current_image_zip_source_artifact(
            repositories, context.lot_id
        )
        manual_resolutions = read_manual_image_resolutions(
            repositories, lot_id=context.lot_id
        )
        if normalized is None:
            _record_missing_normalization_problem(repositories, context)
            return JobResult(final_step_status="bloque")
        if inspection is None:
            _record_missing_inspection_problem(repositories, context)
            return JobResult(final_step_status="bloque")
        if not bool(inspection.payload.get("inspectable")):
            _record_blocked_inspection_problem(repositories, context)
            return JobResult(final_step_status="bloque")
        if source_artifact is None:
            _record_missing_zip_problem(repositories, context)
            return JobResult(final_step_status="bloque")
        try:
            readable_zip = store.open_for_read(
                repositories,
                lot_id=context.lot_id,
                artifact_id=source_artifact["id"],
            )
        except (ArtifactUnavailableError, KeyError, ValueError):
            _record_missing_zip_problem(repositories, context)
            return JobResult(final_step_status="bloque")

    context.set_progress(2, 5)
    matching = build_image_matching_payload(
        normalized.payload,
        inspection.payload,
        source_image_zip_artifact=source_artifact,
        source_normalization_artifact_id=normalized.artifact["id"],
        source_inspection_artifact_id=inspection.artifact["id"],
        indesign_image_root=settings.indesign_image_root,
        manual_resolutions=manual_resolutions,
    )

    context.set_progress(3, 5)
    processed_zip_content = build_processed_images_zip(
        readable_zip.path,
        matching,
        image_limits=image_dimension_limits_from_settings(settings),
    )
    _refresh_matching_counts(matching)
    matching_content = json.dumps(
        matching,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    context.set_progress(4, 5)
    committed_artifact_paths: list[Path] = []
    matching_committed = False
    try:
        with context.database.transaction() as repositories:
            _require_current_lease(repositories, context)
            repositories.problems.mark_open_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(MATCHING_IMAGES_STEP_KEY,),
            )
            repositories.artifacts.mark_obsolete_for_steps(
                lot_id=context.lot_id,
                step_keys=(MATCHING_IMAGES_STEP_KEY,),
            )
            matching_artifact = store.put_temp_then_commit(
                repositories,
                lot_id=context.lot_id,
                step_key=MATCHING_IMAGES_STEP_KEY,
                run_id=context.run_id,
                kind=MATCHING_ARTIFACT_KIND,
                role=MATCHING_ARTIFACT_ROLE,
                filename="matching-images.json",
                content=matching_content,
                metadata={
                    "ambiguous_count": matching["ambiguous_count"],
                    "conversion_failed_count": matching["conversion_failed_count"],
                    "matched_count": matching["matched_count"],
                    "missing_count": matching["missing_count"],
                    "processed_images_count": matching["processed_images_count"],
                    "rules_version": MATCHING_RULES_VERSION,
                    "schema_version": MATCHING_SCHEMA_VERSION,
                    "source_image_zip_artifact_id": source_artifact["id"],
                    "source_inspection_artifact_id": inspection.artifact["id"],
                    "source_normalization_artifact_id": normalized.artifact["id"],
                    "tolerant_count": matching["tolerant_count"],
                    "unreferenced_count": matching["unreferenced_count"],
                },
                mime_type=MATCHING_MIME_TYPE,
                lease_version=context.leased_job.lease_version,
            )
            committed_artifact_paths.append(
                store.path_for(matching_artifact["relative_path"])
            )
            processed_artifact = store.put_temp_then_commit(
                repositories,
                lot_id=context.lot_id,
                step_key=MATCHING_IMAGES_STEP_KEY,
                run_id=context.run_id,
                kind=PROCESSED_IMAGES_ARTIFACT_KIND,
                role=PROCESSED_IMAGES_ARTIFACT_ROLE,
                filename="images-traitees.zip",
                content=processed_zip_content,
                metadata={
                    "folder": EXPORT_IMAGES_FOLDER,
                    "images_count": matching["processed_images_count"],
                    "jpeg_quality": FINAL_IMAGE_JPEG_QUALITY,
                    "max_width_px": FINAL_IMAGE_MAX_WIDTH_PX,
                    "rules_version": MATCHING_RULES_VERSION,
                    "schema_version": MATCHING_SCHEMA_VERSION,
                },
                mime_type=PROCESSED_IMAGES_MIME_TYPE,
                lease_version=context.leased_job.lease_version,
            )
            committed_artifact_paths.append(
                store.path_for(processed_artifact["relative_path"])
            )
            for problem in image_matching_problems(matching):
                record_problem(
                    repositories,
                    lot_id=context.lot_id,
                    step_key=MATCHING_IMAGES_STEP_KEY,
                    run_id=context.run_id,
                    severity=problem["severity"],
                    code=problem["code"],
                    title=problem["title"],
                    cause=problem["cause"],
                    action=problem["action"],
                    location=problem.get("location"),
                    technical=problem.get("technical"),
                )
            output_fingerprint = fingerprint_payload(
                {
                    "artifact_sha256": matching_artifact["sha256"],
                    "kind": "image_matching",
                    "matching_artifact_id": matching_artifact["id"],
                    "processed_images_artifact_id": processed_artifact["id"],
                    "processed_images_sha256": processed_artifact["sha256"],
                    "rules_version": MATCHING_RULES_VERSION,
                    "schema_version": MATCHING_SCHEMA_VERSION,
                    "source_image_zip_artifact_id": source_artifact["id"],
                    "source_image_zip_sha256": source_artifact["sha256"],
                    "source_inspection_artifact_id": inspection.artifact["id"],
                    "source_normalization_artifact_id": normalized.artifact["id"],
                }
            )
            repositories.events.create(
                lot_id=context.lot_id,
                step_key=MATCHING_IMAGES_STEP_KEY,
                run_id=context.run_id,
                event_type="images.matching_completed",
                payload={
                    "artifact_id": matching_artifact["id"],
                    "ambiguous_count": matching["ambiguous_count"],
                    "conversion_failed_count": matching["conversion_failed_count"],
                    "missing_count": matching["missing_count"],
                    "processed_images_count": matching["processed_images_count"],
                    "status": "bloque"
                    if matching["blocking"]
                    else (
                        "termine_avec_alertes"
                        if matching["has_warnings"]
                        else "termine"
                    ),
                    "step_key": MATCHING_IMAGES_STEP_KEY,
                    "tolerant_count": matching["tolerant_count"],
                    "unreferenced_count": matching["unreferenced_count"],
                },
            )
            matching_committed = True
    finally:
        if not matching_committed:
            cleanup_artifact_paths(committed_artifact_paths)

    context.set_progress(5, 5)
    return JobResult(
        final_step_status="bloque" if matching["blocking"] else None,
        with_warnings=bool(matching["has_warnings"]),
        output_fingerprint=output_fingerprint,
    )


def build_image_matching_payload(
    normalized_payload: dict[str, Any],
    inspection_payload: dict[str, Any],
    *,
    source_image_zip_artifact: dict[str, Any],
    source_normalization_artifact_id: str | None,
    source_inspection_artifact_id: str | None,
    indesign_image_root: str,
    manual_resolutions: dict[str, str] | None = None,
) -> dict[str, Any]:
    resolutions = dict(manual_resolutions or {})
    image_inventory = _root_image_inventory(inspection_payload)
    referenced_sources: set[str] = set()
    bindings: list[dict[str, Any]] = []
    duplicate_manual_sources = {
        source_name
        for source_name, count in Counter(resolutions.values()).items()
        if count > 1
    }
    final_names_by_id: dict[str, str] = {}
    for source_row in normalized_payload.get("rows", []):
        if not isinstance(source_row, dict):
            continue
        id_dossier = str(source_row.get("id_dossier") or "").strip()
        if id_dossier:
            final_names_by_id[id_dossier] = image_id_for_dossier(id_dossier)
    duplicate_final_names = {
        final_name
        for final_name, count in Counter(final_names_by_id.values()).items()
        if count > 1
    }
    source_columns = _source_image_columns(normalized_payload)
    source_zip_sha256 = str(source_image_zip_artifact.get("sha256") or "")
    rules_fingerprint = fingerprint_payload(
        {
            "kind": "image_matching_rules",
            "schema_version": MATCHING_SCHEMA_VERSION,
            "rules_version": MATCHING_RULES_VERSION,
            "matchable_image_source_role": MATCHABLE_IMAGE_SOURCE_ROLE,
            "final_folder": EXPORT_IMAGES_FOLDER,
            "final_width_max_px": FINAL_IMAGE_MAX_WIDTH_PX,
            "final_jpeg_quality": FINAL_IMAGE_JPEG_QUALITY,
            "final_dpi": FINAL_IMAGE_DPI,
        }
    )

    for source_row in normalized_payload.get("rows", []):
        if not isinstance(source_row, dict):
            continue
        id_dossier = str(source_row.get("id_dossier") or "").strip()
        if not id_dossier:
            continue
        values = (
            source_row.get("values")
            if isinstance(source_row.get("values"), dict)
            else {}
        )
        original_names = _source_image_values(values, source_columns)
        final_name = final_names_by_id[id_dossier]
        manual_source = resolutions.get(id_dossier)
        binding = _match_row_image(
            id_dossier=id_dossier,
            original_names=original_names,
            final_name=final_name,
            manual_source=manual_source,
            duplicate_manual_sources=duplicate_manual_sources,
            duplicate_final_names=duplicate_final_names,
            image_inventory=image_inventory,
            source_artifact_id=str(source_image_zip_artifact["id"]),
            source_zip_sha256=source_zip_sha256,
            rules_fingerprint=rules_fingerprint,
        )
        bindings.append(binding)

    _mark_duplicate_automatic_sources(bindings)
    referenced_sources = {
        str(binding["source_name"])
        for binding in bindings
        if binding.get("status") == "matched" and binding.get("source_name")
    }
    unreferenced_images = [
        {
            "source_name": image["name"],
            "status": "ignored",
            "reason": "not_referenced",
            "source_artifact_id": source_image_zip_artifact["id"],
        }
        for image in image_inventory["images"]
        if image["name"] not in referenced_sources
    ]
    payload: dict[str, Any] = {
        "schema_version": MATCHING_SCHEMA_VERSION,
        "rules_version": MATCHING_RULES_VERSION,
        "source_normalization_artifact_id": source_normalization_artifact_id,
        "source_inspection_artifact_id": source_inspection_artifact_id,
        "source_image_zip_artifact_id": source_image_zip_artifact["id"],
        "source_image_zip_sha256": source_zip_sha256,
        "rules_fingerprint": rules_fingerprint,
        "image_root": indesign_image_root,
        "final_folder": EXPORT_IMAGES_FOLDER,
        "final_width_max_px": FINAL_IMAGE_MAX_WIDTH_PX,
        "final_jpeg_quality": FINAL_IMAGE_JPEG_QUALITY,
        "final_dpi": FINAL_IMAGE_DPI,
        "manual_resolutions": _public_manual_resolutions(resolutions),
        "source_image_columns": source_columns,
        "rows_count": len(bindings),
        "bindings_count": len(bindings),
        "bindings": bindings,
        "unreferenced_images": unreferenced_images,
    }
    _refresh_matching_counts(payload)
    return payload


def build_processed_images_zip(
    source_zip_path: Path,
    matching_payload: dict[str, Any],
    *,
    image_limits: ImageDimensionLimits = DEFAULT_IMAGE_DIMENSION_LIMITS,
) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        target.writestr(f"{EXPORT_IMAGES_FOLDER}/", b"")
        try:
            with zipfile.ZipFile(source_zip_path) as source:
                for binding in matching_payload.get("bindings", []):
                    if (
                        not isinstance(binding, dict)
                        or binding.get("status") != "matched"
                    ):
                        continue
                    source_name = str(binding.get("source_name") or "")
                    final_name = str(binding.get("final_name") or "")
                    if not source_name or not final_name:
                        continue
                    try:
                        final_content = _convert_source_image_to_jpeg(
                            source,
                            source_name,
                            image_limits=image_limits,
                        )
                    except ImageDimensionLimitError as exc:
                        binding["status"] = "conversion_failed"
                        binding["pathimg"] = ""
                        binding["conversion_error"] = IMAGE_DIMENSIONS_EXCEEDED_CODE
                        binding["dimension_limits_exceeded"] = [
                            exc.violation.public_details()
                        ]
                        continue
                    except (
                        KeyError,
                        OSError,
                        RuntimeError,
                        UnidentifiedImageError,
                        ValueError,
                    ) as exc:
                        binding["status"] = "conversion_failed"
                        binding["pathimg"] = ""
                        binding["conversion_error"] = exc.__class__.__name__
                        continue
                    final_relative_path = f"{EXPORT_IMAGES_FOLDER}/{final_name}"
                    target.writestr(final_relative_path, final_content)
                    binding["final_sha256"] = hashlib.sha256(final_content).hexdigest()
                    binding["final_size_bytes"] = len(final_content)
                    binding["pathimg"] = _indesign_path(
                        str(matching_payload.get("image_root") or ""),
                        final_name,
                    )
        except zipfile.BadZipFile:
            for binding in matching_payload.get("bindings", []):
                if isinstance(binding, dict) and binding.get("status") == "matched":
                    binding["status"] = "conversion_failed"
                    binding["pathimg"] = ""
                    binding["conversion_error"] = "BadZipFile"
    return output.getvalue()


def image_matching_problems(matching: dict[str, Any]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    if matching.get("ambiguous_count"):
        problems.append(
            {
                "severity": "bloquant",
                "code": "SIRCOM_IMAGE_MATCHING_AMBIGUOUS",
                "title": "Association image ambiguë",
                "cause": "Au moins un dossier a plusieurs images candidates ou une suggestion à valider.",
                "action": "Choisir manuellement l'image source à retenir puis relancer le traitement.",
                "technical": {"checks_count": int(matching["ambiguous_count"])},
            }
        )
    if matching.get("missing_count"):
        problems.append(
            {
                "severity": "alerte",
                "code": "SIRCOM_IMAGE_MATCHING_MISSING",
                "title": "Images manquantes",
                "cause": "Certains dossiers n'ont pas d'image correspondante dans le zip courant.",
                "action": "Ajouter les images manquantes au zip ou accepter un chemin image vide.",
                "technical": {"checks_count": int(matching["missing_count"])},
            }
        )
    if matching.get("unreferenced_count"):
        problems.append(
            {
                "severity": "alerte",
                "code": "SIRCOM_IMAGE_MATCHING_UNREFERENCED",
                "title": "Images non référencées",
                "cause": "Certaines images du zip ne correspondent à aucun dossier exporté.",
                "action": "Vérifier le zip ; ces images seront ignorées dans le package.",
                "technical": {"checks_count": int(matching["unreferenced_count"])},
            }
        )
    if matching.get("fallback_count"):
        problems.append(
            {
                "severity": "information",
                "code": "SIRCOM_IMAGE_MATCHING_ID_FALLBACK_USED",
                "title": "Fallback id_dossier utilisé",
                "cause": "Le nom original n'était pas disponible ou n'a pas suffi pour certains dossiers.",
                "action": "Vérifier que les images retenues correspondent bien aux dossiers.",
                "technical": {"checks_count": int(matching["fallback_count"])},
            }
        )
    if matching.get("tolerant_count"):
        problems.append(
            {
                "severity": "information",
                "code": "SIRCOM_IMAGE_MATCHING_TOLERANCE_USED",
                "title": "Tolérance de nommage utilisée",
                "cause": "Certaines images ont été associées après normalisation de la casse, des espaces, de l'extension ou des séparateurs.",
                "action": "Vérifier les associations signalées avant le package final.",
                "technical": {"checks_count": int(matching["tolerant_count"])},
            }
        )
    if matching.get("conversion_failed_count"):
        problems.append(
            {
                "severity": "alerte",
                "code": "SIRCOM_IMAGE_CONVERSION_FAILED",
                "title": "Conversion image échouée",
                "cause": "Certaines images associées n'ont pas pu être converties en JPG final.",
                "action": "Remplacer les images sources concernées puis relancer le traitement.",
                "technical": {"checks_count": int(matching["conversion_failed_count"])},
            }
        )
    return problems


def get_persisted_image_matching(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> PersistedImageMatching:
    repositories.lots.get_required(lot_id)
    step = repositories.steps.get_by_lot_key(lot_id, MATCHING_IMAGES_STEP_KEY)
    if (
        step is None
        or not step["current_run_id"]
        or step["status"] not in {"termine", "termine_avec_alertes", "bloque"}
    ):
        raise ImageMatchingNotReady("Image matching is not ready.")
    artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        run_id=step["current_run_id"],
        role=MATCHING_ARTIFACT_ROLE,
    )
    if artifact is None or artifact["status"] != "committed":
        raise ImageMatchingNotReady("Image matching artifact is unavailable.")
    processed_artifact = repositories.artifacts.get_for_step_run_role(
        lot_id=lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        run_id=step["current_run_id"],
        role=PROCESSED_IMAGES_ARTIFACT_ROLE,
    )
    if processed_artifact is not None and processed_artifact["status"] != "committed":
        processed_artifact = None
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
        matching = json.loads(readable.path.read_text(encoding="utf-8"))
    except (
        ArtifactUnavailableError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
    ) as exc:
        raise ImageMatchingNotReady("Image matching artifact is unavailable.") from exc
    if not isinstance(matching, dict):
        raise ImageMatchingNotReady("Image matching artifact is malformed.")
    return PersistedImageMatching(
        matching=matching,
        artifact=artifact,
        processed_images_artifact=processed_artifact,
    )


def save_image_resolutions(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
    resolutions: list[dict[str, Any]],
    idempotency_key: str,
) -> ImageResolutionResult:
    lot = repositories.lots.get_required(lot_id)
    if lot["status"] in LOT_WRITE_BLOCKED_STATUSES:
        raise ImageResolutionError(
            409,
            "SIRCOM_LOT_NOT_MUTABLE",
            "Lot non modifiable.",
        )
    normalized, inspection = _current_resolution_prerequisites(
        repositories,
        settings=settings,
        lot_id=lot_id,
    )
    known_ids = {
        str(row.get("id_dossier") or "").strip()
        for row in normalized.payload.get("rows", [])
        if isinstance(row, dict) and str(row.get("id_dossier") or "").strip()
    }
    known_source_names = {
        str(image.get("name") or "")
        for image in inspection.payload.get("images", [])
        if isinstance(image, dict) and image.get("name")
    }
    submitted = _validated_resolution_map(
        resolutions,
        known_ids=known_ids,
        known_source_names=known_source_names,
    )
    existing = read_manual_image_resolutions(repositories, lot_id=lot_id)
    existing.update(submitted)
    duplicate_sources = [
        source_name
        for source_name, count in Counter(existing.values()).items()
        if count > 1
    ]
    if duplicate_sources:
        raise ImageResolutionError(
            422,
            "SIRCOM_IMAGE_RESOLUTION_SOURCE_DUPLICATED",
            "Une image source est affectée à plusieurs dossiers.",
            details={"source_name": duplicate_sources[0]},
        )
    summary = {
        "manual_resolutions": _public_manual_resolutions(existing),
        "manual_resolutions_count": len(existing),
        "manual_resolutions_rules_version": MANUAL_RESOLUTIONS_RULES_VERSION,
        "manual_resolutions_updated_at": datetime.now(UTC).isoformat(
            timespec="seconds"
        ),
    }
    own_canceled_jobs = repositories.jobs.cancel_active_for_step(
        lot_id,
        MATCHING_IMAGES_STEP_KEY,
    )
    repositories.problems.mark_open_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(MATCHING_IMAGES_STEP_KEY,),
    )
    own_obsolete = repositories.artifacts.mark_obsolete_for_steps(
        lot_id=lot_id,
        step_keys=(MATCHING_IMAGES_STEP_KEY,),
    )
    repositories.steps.set_summary(
        lot_id=lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        summary=summary,
    )
    invalidation = invalidate_downstream(
        repositories,
        lot_id=lot_id,
        source_step_key=MATCHING_IMAGES_STEP_KEY,
        reason="image_resolution_updated",
    )
    queued = enqueue_image_matching_job(
        repositories,
        lot_id=lot_id,
        idempotency_key=idempotency_key,
    )
    repositories.events.create(
        lot_id=lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        run_id=queued.job["run_id"],
        event_type="images.manual_resolutions_saved",
        payload={
            "invalidated_steps_count": len(invalidation.invalidated_steps),
            "manual_resolutions_count": len(existing),
            "obsolete_artifacts_count": invalidation.obsolete_artifacts_count
            + own_obsolete,
            "status": "pret",
            "step_key": MATCHING_IMAGES_STEP_KEY,
        },
    )
    return ImageResolutionResult(
        matching_job=queued.job,
        matching_job_created=queued.created,
        lot=get_lot_detail(repositories, lot_id),
        invalidated_steps=invalidation.invalidated_steps,
        obsolete_artifacts_count=invalidation.obsolete_artifacts_count + own_obsolete,
        canceled_jobs_count=invalidation.canceled_jobs_count + own_canceled_jobs,
    )


def read_manual_image_resolutions(
    repositories: Repositories,
    *,
    lot_id: str,
) -> dict[str, str]:
    step = repositories.steps.get_by_lot_key(lot_id, MATCHING_IMAGES_STEP_KEY)
    if step is None:
        return {}
    try:
        summary = json.loads(step.get("summary_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    raw_resolutions = summary.get("manual_resolutions", [])
    if isinstance(raw_resolutions, dict):
        return {
            str(id_dossier): str(source_name)
            for id_dossier, source_name in raw_resolutions.items()
            if str(id_dossier).strip() and str(source_name).strip()
        }
    if isinstance(raw_resolutions, list):
        result: dict[str, str] = {}
        for item in raw_resolutions:
            if not isinstance(item, dict):
                continue
            id_dossier = str(item.get("id_dossier") or "").strip()
            source_name = str(item.get("source_name") or "").strip()
            if id_dossier and source_name:
                result[id_dossier] = source_name
        return result
    return {}


def _convert_source_image_to_jpeg(
    source: zipfile.ZipFile,
    source_name: str,
    *,
    image_limits: ImageDimensionLimits = DEFAULT_IMAGE_DIMENSION_LIMITS,
) -> bytes:
    with source.open(source_name) as handle:
        with Image.open(handle) as image:
            check_image_dimensions(image, image_limits, image_name=source_name)
            prepared = prepare_image_for_jpeg(image)
            if prepared.width > FINAL_IMAGE_MAX_WIDTH_PX:
                ratio = FINAL_IMAGE_MAX_WIDTH_PX / prepared.width
                height = max(1, round(prepared.height * ratio))
                prepared = prepared.resize(
                    (FINAL_IMAGE_MAX_WIDTH_PX, height),
                    Image.Resampling.LANCZOS,
                )
            output = BytesIO()
            save_kwargs: dict[str, Any] = {
                "format": "JPEG",
                "quality": FINAL_IMAGE_JPEG_QUALITY,
                "dpi": (FINAL_IMAGE_DPI, FINAL_IMAGE_DPI),
            }
            icc_profile = prepared.info.get("icc_profile")
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile
            prepared.save(output, **save_kwargs)
            return output.getvalue()


def _indesign_path(root: str, final_name: str) -> str:
    clean_root = root.rstrip("/")
    return f"{clean_root}/{final_name}" if clean_root else final_name


def _refresh_matching_counts(payload: dict[str, Any]) -> None:
    counts = Counter(
        str(binding.get("status") or "")
        for binding in payload.get("bindings", [])
        if isinstance(binding, dict)
    )
    fallback_count = sum(
        1
        for binding in payload.get("bindings", [])
        if isinstance(binding, dict) and bool(binding.get("fallback_used"))
    )
    tolerant_count = sum(
        1
        for binding in payload.get("bindings", [])
        if isinstance(binding, dict)
        and binding.get("status") == "matched"
        and "tolerant" in str(binding.get("match_level") or "")
    )
    processed_images_count = sum(
        1
        for binding in payload.get("bindings", [])
        if isinstance(binding, dict)
        and binding.get("status") == "matched"
        and bool(binding.get("final_sha256"))
    )
    payload["matched_count"] = counts["matched"]
    payload["missing_count"] = counts["missing"]
    payload["ambiguous_count"] = counts["ambiguous"]
    payload["conversion_failed_count"] = counts["conversion_failed"]
    payload["fallback_count"] = fallback_count
    payload["tolerant_count"] = tolerant_count
    payload["processed_images_count"] = processed_images_count
    payload["unreferenced_count"] = len(payload.get("unreferenced_images", []))
    payload["blocking"] = bool(payload["ambiguous_count"])
    payload["has_warnings"] = bool(
        payload["missing_count"]
        or payload["unreferenced_count"]
        or payload["conversion_failed_count"]
        or payload["fallback_count"]
        or payload["tolerant_count"]
    )


def _public_manual_resolutions(resolutions: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"id_dossier": id_dossier, "source_name": source_name}
        for id_dossier, source_name in sorted(resolutions.items())
    ]


def _manual_resolutions_items(
    repositories: Repositories,
    lot_id: str,
) -> list[dict[str, str]]:
    return _public_manual_resolutions(
        read_manual_image_resolutions(repositories, lot_id=lot_id)
    )


def _validated_resolution_map(
    resolutions: list[dict[str, Any]],
    *,
    known_ids: set[str],
    known_source_names: set[str],
) -> dict[str, str]:
    if not resolutions:
        raise ImageResolutionError(
            422,
            "SIRCOM_IMAGE_RESOLUTION_EMPTY",
            "Aucune résolution image fournie.",
        )
    result: dict[str, str] = {}
    for item in resolutions:
        id_dossier = str(item.get("id_dossier") or "").strip()
        source_name = str(item.get("source_name") or "").strip()
        if not id_dossier or id_dossier not in known_ids:
            raise ImageResolutionError(
                422,
                "SIRCOM_IMAGE_RESOLUTION_DOSSIER_UNKNOWN",
                "La résolution cible un dossier inconnu.",
            )
        if not source_name or source_name not in known_source_names:
            raise ImageResolutionError(
                422,
                "SIRCOM_IMAGE_RESOLUTION_SOURCE_UNKNOWN",
                "La résolution cible une image source inconnue du zip courant.",
            )
        result[id_dossier] = source_name
    duplicate_sources = [
        source for source, count in Counter(result.values()).items() if count > 1
    ]
    if duplicate_sources:
        raise ImageResolutionError(
            422,
            "SIRCOM_IMAGE_RESOLUTION_SOURCE_DUPLICATED",
            "Une image source est affectée à plusieurs dossiers.",
            details={"source_name": duplicate_sources[0]},
        )
    return result


def _current_resolution_prerequisites(
    repositories: Repositories,
    *,
    settings: Settings,
    lot_id: str,
) -> tuple[CurrentJsonArtifact, CurrentJsonArtifact]:
    store = ArtifactStore(
        settings.data_dir,
        pending_ttl_seconds=settings.artifact_pending_ttl_seconds,
    )
    normalized = _current_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=NORMALIZATION_STEP_KEY,
        role=NORMALIZATION_ARTIFACT_ROLE,
        ready_statuses=("termine", "termine_avec_alertes"),
    )
    if normalized is None:
        raise ImageResolutionError(
            409,
            "SIRCOM_IMAGE_RESOLUTION_NORMALIZATION_NOT_READY",
            "Normalisation du contenu non disponible pour résoudre les images.",
        )
    inspection = _current_json_artifact(
        repositories,
        store,
        lot_id=lot_id,
        step_key=INSPECTION_IMAGES_STEP_KEY,
        role=INSPECTION_ARTIFACT_ROLE,
        ready_statuses=("termine", "termine_avec_alertes"),
    )
    if inspection is None or not bool(inspection.payload.get("inspectable")):
        raise ImageResolutionError(
            409,
            "SIRCOM_IMAGE_RESOLUTION_INSPECTION_NOT_READY",
            "Inspection images non disponible pour résoudre les ambiguïtés.",
        )
    return normalized, inspection


def _current_json_artifact(
    repositories: Repositories,
    store: ArtifactStore,
    *,
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
    try:
        readable = store.open_for_read(
            repositories,
            lot_id=lot_id,
            artifact_id=artifact["id"],
        )
        payload = json.loads(readable.path.read_text(encoding="utf-8"))
    except (
        ArtifactUnavailableError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
    ):
        return None
    if not isinstance(payload, dict):
        return None
    return CurrentJsonArtifact(artifact=artifact, payload=payload)


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


def _record_missing_normalization_problem(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_IMAGE_MATCHING_NORMALIZATION_MISSING",
        title="Normalisation contenu introuvable",
        cause="Le matching images ne trouve pas l'artefact normalisé courant.",
        action="Terminer la fusion et la normalisation, puis relancer le matching images.",
    )


def _record_missing_inspection_problem(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_IMAGE_MATCHING_INSPECTION_MISSING",
        title="Inspection images introuvable",
        cause="Le matching images ne trouve pas l'inspection du zip courant.",
        action="Déposer un zip images valide, attendre l'inspection, puis relancer le matching.",
    )


def _record_blocked_inspection_problem(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_IMAGE_MATCHING_INSPECTION_BLOCKED",
        title="Inspection images bloquante",
        cause="Le zip images courant a été refusé par l'inspection.",
        action="Corriger le zip images puis le redéposer.",
    )


def _record_missing_zip_problem(
    repositories: Repositories,
    context: WorkerJobContext,
) -> None:
    record_problem(
        repositories,
        lot_id=context.lot_id,
        step_key=MATCHING_IMAGES_STEP_KEY,
        run_id=context.run_id,
        severity="bloquant",
        code="SIRCOM_IMAGE_MATCHING_SOURCE_ZIP_MISSING",
        title="Zip images source introuvable",
        cause="Le matching images ne trouve pas l'artefact zip images source courant.",
        action="Déposer à nouveau le zip images, puis relancer le matching.",
    )
